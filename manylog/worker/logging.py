from __future__ import annotations

from logging import Handler, LogRecord

from manylog.connection import Socket
from manylog.messages import LogMsg


class ZMQLogHandler(Handler):
    socket: Socket

    def __init__(self, socket: Socket):
        self.socket = socket

    def handle(self, record: LogRecord) -> LogRecord | bool:  # type: ignore
        if not hasattr(record, "message"):
            record.message = record.msg % record.args
        msg = LogMsg.create(record)
        data = msg.encode()
        self.socket.send(data)
        return record
