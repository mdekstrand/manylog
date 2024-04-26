"""
Listener to obtain and re-inject log messages and progress updates.
"""

from __future__ import annotations

import logging
import os
import warnings
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Any, Optional
from uuid import UUID

import zmq
from progress_api.api import Progress
from progress_api.backends import ProgressBarSpec
from progress_api.config import get_backend

import manylog.connection as x
import manylog.messages as m

_log = logging.getLogger(__name__)


class LogListener:
    """
    Class that listens for logging messages and reinjects them in the parent.

    The listener is not listening for messages until :meth:`start` is called. It
    must be properly shut down with :meth:`close`.  The log listener can be used
    as a context manager, in which case `start` and `close` will be
    automatically called.  If the process terminates without calling `close`,
    log messages may be lost.

    Args:
        ctx: A ZeroMQ context to use.
    """

    address: str | None = None
    "The address where the socket is listening for log messages."
    context: x.Context
    thread: ListenThread | None = None
    _tmpdir: TemporaryDirectory[str]

    def __init__(self, ctx: Optional[x.Context] = None):
        if ctx is None:
            self.context = zmq.Context.instance()
        else:
            self.context = ctx

    def start(self):
        """
        Start the log listener.
        """
        rt_dir = os.environ.get("XDG_RUNTIME_DIR", None)
        self._tmpdir = TemporaryDirectory(prefix="manylog-", dir=rt_dir)
        try:
            socket = self.context.socket(zmq.PULL, zmq.Socket)
            self.address = f"ipc://{self._tmpdir.name}/logging.ipc"
            socket.bind(self.address)
            self.thread = ListenThread(socket)
            self.thread.start()
        except Exception as e:
            self._tmpdir.cleanup()
            raise e

    def close(self):
        """
        Shut down the log listener.
        """
        if not self.thread:
            warnings.warn("listener thread not running")
            return
        self.thread.shutdown()
        self.thread = None
        self._tmpdir.cleanup()

    def __begin__(self):
        self.start()
        return self

    def __end__(self, *args: Any):
        self.close()


class ListenThread(Thread):
    socket: x.Socket
    _shutdown_wanted: bool = False
    active_pbs: dict[UUID, Progress]

    def __init__(self, socket: x.Socket):
        super().__init__(name="manylog-listener", daemon=True)
        self.socket = socket
        self.active_pbs = {}

    def run(self):
        while True:
            # we poll for 250ms, to allow shutdown signals
            evt = self.socket.poll(250)
            if evt:
                data = self.socket.recv(zmq.NOBLOCK)
                try:
                    msg = m.decode_message(data)
                except Exception as e:
                    _log.error("error decoding log message: %s", e)
                    continue
                try:
                    self._dispatch_message(msg)
                except Exception as e:
                    _log.error("error dispatching log message: %s", e)
                    continue
            elif self._shutdown_wanted:
                self.socket.close()
                return

    def shutdown(self):
        self._shutdown_wanted = True
        self.join()

    def _dispatch_message(self, msg: m.BaseMsg) -> None:
        match msg:
            case m.LogMsg():
                self._dispatch_log(msg)
            case m.ProgressBegin(uuid=uuid, spec=spec):
                spec["logger"] = logging.getLogger(spec["logger"])
                spec = ProgressBarSpec(**spec)
                self.active_pbs[uuid] = get_backend().create_bar(spec)
            case m.ProgressEnd(uuid=uuid):
                pb = self.active_pbs[uuid]
                pb.finish()
                del self.active_pbs[uuid]
            case m.ProgressSetParam(uuid=uuid, name="label", value=lbl):
                self.active_pbs[uuid].set_label(lbl)  # type: ignore
            case m.ProgressSetParam(uuid=uuid, name="total", value=tot):
                self.active_pbs[uuid].set_total(tot)  # type: ignore
            case m.ProgressSetMetric(uuid=uuid):
                self.active_pbs[uuid].set_metric(msg.label, msg.metric, msg.format)
            case m.ProgressUpdate(uuid=uuid):
                self.active_pbs[uuid].update(msg.incr, msg.state, msg.src_state, msg.metric)
            case _:
                raise TypeError(f"unsupported message type {type(msg)}")

    def _dispatch_log(self, msg: m.LogMsg) -> None:
        logger = logging.getLogger(msg.name)
        rec = msg.decode_log_record()
        if rec is None:
            raise RuntimeError("non-pickled log messages not supported")
        else:
            logger.handle(rec)
