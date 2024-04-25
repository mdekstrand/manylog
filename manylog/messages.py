from __future__ import annotations

import pickle
from dataclasses import dataclass, fields
from enum import Enum
from logging import LogRecord
from typing import ClassVar, Optional

from msgpack import packb, unpackb  # type: ignore

MSG_TYPES = ["LogMsg"]


class MsgType(Enum):
    LOG = 1


@dataclass
class BaseMsg:
    type: ClassVar[MsgType]
    pid: int
    timestamp: float

    def encode(self) -> bytes:
        attrs = {f.name: getattr(self, f.name) for f in fields(self)}
        return packb((self.type.value, attrs))


@dataclass
class LogMsg(BaseMsg):
    type = MsgType.LOG

    level: int
    name: str
    message: str
    record: Optional[bytes]

    @classmethod
    def create(cls, rec: LogRecord):
        return LogMsg(
            pid=rec.process or -1,
            timestamp=rec.created,
            level=rec.levelno,
            name=rec.name,
            message=rec.message,
            record=pickle.dumps(rec),
        )

    def decode_log_record(self) -> Optional[LogRecord]:
        if not self.record:
            return None

        obj = pickle.loads(self.record)
        if not isinstance(obj, LogRecord):
            raise TypeError("serialized record not LogRecord")

        return obj


MSG_IMPLS = {MsgType.LOG: LogMsg}


def decode_message(data: bytes) -> BaseMsg:
    """
    Decode a logging message from bytes.
    """

    rec = unpackb(data)
    type, attrs = rec
    type = MsgType(type)

    cls = MSG_IMPLS[type]
    return cls(**attrs)
