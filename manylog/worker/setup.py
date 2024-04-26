from __future__ import annotations

import logging

import zmq
from progress_api import set_backend

from ..connection import Context
from .logging import ZMQLogHandler
from .progress import ZMQProgressBackend


def init_worker_logging(address: str, level: int = logging.INFO):
    ctx: Context = zmq.Context.instance()
    sock = ctx.socket(zmq.PUSH)
    sock.connect(address)

    h = ZMQLogHandler(sock)
    h.setLevel(level)
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(h)

    set_backend(ZMQProgressBackend(sock))
