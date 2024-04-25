"""
Listener to obtain and re-inject log messages and progress updates.
"""

from __future__ import annotations

import logging
import warnings
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Optional

import zmq

import manylog.messages as m

_log = logging.getLogger(__name__)


class LogListener:
    address: str | None = None
    context: zmq.Context[zmq.Socket[bytes]]
    thread: ListenThread | None = None
    _tmpdir: TemporaryDirectory[str]

    def __init__(self, ctx: Optional[zmq.Context[zmq.Socket[bytes]]] = None):
        if ctx is None:
            self.context = zmq.Context.instance()
        else:
            self.context = ctx

    def start(self):
        self._tmpdir = TemporaryDirectory(prefix="manylog-")
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
        if not self.thread:
            warnings.warn("listener thread not running")
            return
        self.thread.shutdown()
        self.thread = None
        self._tmpdir.cleanup()


class ListenThread(Thread):
    socket: zmq.Socket[bytes]
    _shutdown_wanted: bool = False

    def __init__(self, socket: zmq.Socket[bytes]):
        super().__init__(name="manylog-listener")
        self.socket = socket

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
            case _:
                raise TypeError(f"unsupported message type {type(msg)}")

    def _dispatch_log(self, msg: m.LogMsg) -> None:
        logger = logging.getLogger(msg.name)
        rec = msg.decode_log_record()
        if rec is None:
            raise RuntimeError("non-pickled log messages not supported")
        else:
            logger.handle(rec)
