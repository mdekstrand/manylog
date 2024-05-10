from __future__ import annotations

import logging

import zmq
from progress_api import set_backend

from ..connection import Context, Socket
from .logging import ZMQLogHandler
from .progress import ZMQProgressBackend

_context: Context
_socket: Socket


def init_worker_logging(address: str, level: int = logging.INFO):
    """
    Initialize logging in the worker.

    Args:
        address:
            The address of the socket to connect to.  This can be
            obtained from :attr:`manylog.LogListener.address`.
        level:
            The maximum logging level to forward.
    """
    global _context, _socket
    _context = zmq.Context.instance()
    _socket = _context.socket(zmq.PUSH)
    _socket.connect(address)

    h = ZMQLogHandler(_socket)
    h.setLevel(level)
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(h)

    set_backend(ZMQProgressBackend(_socket))


def get_socket() -> Socket:
    """
    Get the active socket in the worker process.  Fails if the worker
    has not been initialized.
    """
    return _socket
