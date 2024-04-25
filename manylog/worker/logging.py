from __future__ import annotations

from logging import Handler, LogRecord

import zmq

from manylog.messages import LogMsg


class ZMQLogHandler(Handler):
    socket: zmq.Socket[bytes]

    def __init__(self, socket: zmq.Socket[bytes]):
        self.socket = socket

    def handle(self, record: LogRecord) -> LogRecord | bool:  # type: ignore
        if not hasattr(record, "message"):
            record.message = record.msg % record.args
        msg = LogMsg.create(record)
        data = msg.encode()
        self.socket.send(data)
        return record
