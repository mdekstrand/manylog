import logging
import multiprocessing as mp

import pytest

from manylog import LogListener, init_worker_logging


@pytest.fixture
def listener():
    listener = LogListener()
    try:
        yield listener
    finally:
        listener.close()


def _worker(cstr: str):
    init_worker_logging(cstr)
    log = logging.getLogger()
    log.info("test message from child thread")


def test_mp_one(listener: LogListener, caplog: pytest.LogCaptureFixture):
    proc = mp.Process(target=_worker, args=[listener.address])
    proc.start()
    proc.join()

    assert any([r.message == "test message from child thread" for r in caplog.records])
