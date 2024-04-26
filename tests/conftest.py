from progress_api import set_backend
from progress_api.backends.mock import MockProgressBackend

import pytest

from manylog import LogListener


@pytest.fixture
def listener():
    listener = LogListener()
    listener.start()
    try:
        yield listener
    finally:
        listener.close()


@pytest.fixture
def progress_mock():
    mock = MockProgressBackend()
    set_backend(mock)
    try:
        yield mock
    finally:
        set_backend("null")
