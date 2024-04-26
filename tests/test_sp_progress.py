import logging
import multiprocessing as mp
import time

from progress_api import make_progress

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
    log.info("starting job")
    prog = make_progress(log, "tasks", 50)
    for _i in range(10):
        time.sleep(0.01)
        prog.update()
    prog.finish()
    log.info("finished job")
    print("worker finished")


def test_single_progress(listener: LogListener, caplog: pytest.LogCaptureFixture):
    proc = mp.Process(target=_worker, args=[listener.address])
    proc.start()
    proc.join()
    assert proc.exitcode == 0

    assert any([r.message == "starting job" for r in caplog.records])
    assert any([r.message == "finished job" for r in caplog.records])
