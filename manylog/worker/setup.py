from __future__ import annotations

import logging

import zmq

from .logging import ZMQLogHandler


def init_worker_logging(address: str, level: int = logging.INFO):
    ctx: zmq.Context[zmq.Socket[bytes]] = zmq.Context.instance()
    sock = ctx.socket(zmq.PUSH)
    sock.connect(address)

    h = ZMQLogHandler(sock)
    h.setLevel(level)
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(h)
