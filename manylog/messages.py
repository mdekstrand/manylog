from __future__ import annotations

import pickle
from dataclasses import dataclass, fields
from enum import Enum
from logging import LogRecord
from uuid import UUID

from msgpack import packb, unpackb  # type: ignore
from typing_extensions import Any, ClassVar, Optional, Self, TypeVar

MC = TypeVar("MC", bound="type[BaseMsg]")
MSG_TYPES = ["LogMsg"]
MSG_IMPLS: dict[MsgType, type[BaseMsg]] = {}


def _message_class(cls: MC) -> MC:
    MSG_IMPLS[cls.type] = cls
    return cls


class MsgType(Enum):
    LOG = 1
    PROGRESS_BEGIN = 10
    PROGRESS_END = 11
    PROGRESS_SET_PARAM = 12
    PROGRESS_SET_METRIC = 13
    PROGRESS_UPDATE = 15


@dataclass
class BaseMsg:
    type: ClassVar[MsgType]
    pid: int
    timestamp: float

    def encode(self) -> bytes:
        return packb((self.type.value, self.to_dict()))

    def to_dict(self) -> dict[str, Any]:
        "Convert the message to a MsgPack-encodable dictionary."
        data: dict[str, Any] = {}
        for f in fields(self):
            val = getattr(self, f.name)
            if isinstance(val, UUID):
                data[f.name] = val.bytes
            else:
                data[f.name] = val

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        "Reconstruct the message from a MsgPack-encoded dictionary."
        for f in fields(cls):
            if f.type == "UUID":
                data[f.name] = UUID(bytes=data[f.name])

        return cls(**data)


@_message_class
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


@_message_class
@dataclass
class ProgressBegin(BaseMsg):
    type = MsgType.PROGRESS_BEGIN

    uuid: UUID
    spec: dict[str, Any]


@_message_class
@dataclass
class ProgressEnd(BaseMsg):
    type = MsgType.PROGRESS_END

    uuid: UUID


@_message_class
@dataclass
class ProgressSetParam(BaseMsg):
    type = MsgType.PROGRESS_SET_PARAM

    uuid: UUID
    name: str
    value: int | str | None


@_message_class
@dataclass
class ProgressSetMetric(BaseMsg):
    """
    Progress bar metric messages.
    """

    type = MsgType.PROGRESS_SET_METRIC

    uuid: UUID
    label: str
    metric: int | str | float | None
    format: str | None


@_message_class
@dataclass
class ProgressUpdate(BaseMsg):
    """
    Progress bar update messages.
    """

    type = MsgType.PROGRESS_UPDATE

    uuid: UUID
    incr: int
    state: Optional[str]
    src_state: Optional[str]
    metric: int | str | float | None


def decode_message(data: bytes) -> BaseMsg:
    """
    Decode a logging message from bytes.
    """

    rec = unpackb(data)
    type, attrs = rec
    type = MsgType(type)

    cls = MSG_IMPLS[type]
    return cls.from_dict(attrs)
