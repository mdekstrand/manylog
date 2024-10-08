"""
Listener to obtain and re-inject log messages and progress updates.
"""

from __future__ import annotations

import logging
import os
import traceback
import warnings
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Any, Optional
from uuid import UUID, uuid4

import zmq
from progress_api.api import Progress
from progress_api.backends import ProgressBarSpec, ProgressState
from progress_api.config import get_backend

import manylog.connection as x
import manylog.messages as m

_log = logging.getLogger(__name__)
_global_listener: LogListener | None = None


def global_listener(listener: LogListener | None = None) -> LogListener:
    """
    Get the global log listener, setting it up if it does not exist.

    Can also be to _set_ a global listener, if none has been initialized yet.
    """
    global _global_listener
    if listener is not None:
        if _global_listener is not None:
            raise RuntimeError("global listener already initialized")
        _global_listener = listener
        return listener

    if _global_listener is None:
        _global_listener = LogListener()
        _global_listener.start()

    assert _global_listener is not None
    return _global_listener


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
            if zmq.has("ipc"):
                self.address = f"ipc://{self._tmpdir.name}/logging.ipc"
                socket.bind(self.address)
            else:
                socket.bind("tcp://127.0.0.1:0")
                addr = socket.last_endpoint
                if isinstance(addr, bytes):
                    self.address = addr.decode("ascii")
                else:
                    self.address = str(addr)
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

    def share_progress(self, progress: Progress) -> UUID:
        """
        Register a progress bar for sharing with child processes.
        """
        if self.thread is None:
            raise RuntimeError("listener not started")
        uuid = uuid4()
        self.thread.active_pbs[uuid] = progress
        return uuid

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args: Any):
        self.close()
        return False


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
                    if _log.getEffectiveLevel() <= logging.DEBUG:
                        _log.debug(
                            "full dispatch error:\n%s", "".join(traceback.format_exception(e))
                        )
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
                spec["states"] = [ProgressState(n, f) for (n, f) in spec["states"]]
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
