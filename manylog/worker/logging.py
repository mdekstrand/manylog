from __future__ import annotations

import copy
from logging import Handler, LogRecord

from manylog.connection import Socket
from manylog.messages import LogMsg


class ZMQLogHandler(Handler):
    socket: Socket

    def __init__(self, socket: Socket):
        self.socket = socket

    def handle(self, record: LogRecord) -> LogRecord | bool:  # type: ignore
        # copy so other handlers don't have a problem
        record = copy.copy(record)

        # update messages for copyability
        if not hasattr(record, "message"):
            record.message = record.msg % record.args
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None

        msg = LogMsg.create(record)
        data = msg.encode()
        self.socket.send(data)
        return record
