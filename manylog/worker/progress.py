from __future__ import annotations

import dataclasses
import os
import time
from typing import Optional
from uuid import UUID, uuid4

from progress_api import Progress
from progress_api.backends import ProgressBackend, ProgressBarSpec

import manylog.messages as m
from manylog.connection import Socket


class ZMQProgressBackend(ProgressBackend):
    socket: Socket
    pid: int

    def __init__(self, socket: Socket) -> None:
        super().__init__()
        self.socket = socket
        self.pid = os.getpid()

    def create_bar(self, spec: ProgressBarSpec) -> Progress:
        """
        Create a new progress bar from the given specification.
        """
        id = uuid4()
        sdict = dataclasses.asdict(spec)
        sdict["logger"] = spec.logger.name
        msg = m.ProgressBegin(self.pid, time.time(), id, sdict)
        self.socket.send(msg.encode())
        return ZMQProgress(self.socket, self.pid, id)


class ZMQProgress(Progress):
    socket: Socket
    pid: int
    uuid: UUID

    def __init__(self, socket: Socket, pid: int, id: UUID):
        self.socket = socket
        self.pid = pid
        self.uuid = id

    def set_label(self, label: Optional[str]) -> None:
        msg = m.ProgressSetParam(self.pid, time.time(), self.uuid, "label", label)
        self.socket.send(msg.encode())

    def set_total(self, total: int) -> None:
        msg = m.ProgressSetParam(self.pid, time.time(), self.uuid, "total", total)
        self.socket.send(msg.encode())

    def set_metric(
        self, label: str, value: int | str | float | None, fmt: str | None = None
    ) -> None:
        msg = m.ProgressSetMetric(self.pid, time.time(), self.uuid, label, value, fmt)
        self.socket.send(msg.encode())

    def update(
        self,
        n: int = 1,
        state: Optional[str] = None,
        src_state: Optional[str] = None,
        metric: int | str | float | None = None,
    ) -> None:
        msg = m.ProgressUpdate(self.pid, time.time(), self.uuid, n, state, src_state, metric)
        self.socket.send(msg.encode())

    def finish(self) -> None:
        msg = m.ProgressEnd(self.pid, time.time(), self.uuid)
        self.socket.send(msg.encode())
