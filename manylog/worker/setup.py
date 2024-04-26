from __future__ import annotations

import logging

import zmq
from progress_api import set_backend

from ..connection import Context
from .logging import ZMQLogHandler
from .progress import ZMQProgressBackend


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
    ctx: Context = zmq.Context.instance()
    sock = ctx.socket(zmq.PUSH)
    sock.connect(address)

    h = ZMQLogHandler(sock)
    h.setLevel(level)
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(h)

    set_backend(ZMQProgressBackend(sock))
