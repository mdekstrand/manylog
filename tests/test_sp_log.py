import logging
import multiprocessing as mp

import pytest

from manylog import LogListener, init_worker_logging


@pytest.fixture
def listener():
    listener = LogListener()
    listener.start()
    try:
        yield listener
    finally:
        listener.close()


def _worker(cstr: str):
    print("child working")
    init_worker_logging(cstr)
    print("worker initialized")
    log = logging.getLogger()
    log.info("test message from child thread")
    print("worker finished")


def test_single_log(listener: LogListener, caplog: pytest.LogCaptureFixture):
    proc = mp.Process(target=_worker, args=[listener.address])
    proc.start()
    proc.join()
    assert proc.exitcode == 0

    assert any([r.message == "test message from child thread" for r in caplog.records])
