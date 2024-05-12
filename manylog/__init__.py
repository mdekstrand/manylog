"""
Collect log messages and progress updates from multiple processes.
"""

import os
from importlib.metadata import PackageNotFoundError, version
from uuid import UUID

from progress_api.api import Progress

try:
    __version__ = version("manylog")
except PackageNotFoundError:
    # package is not installed
    pass

from .listener import LogListener, global_listener
from .worker import connect_progress, init_worker_logging

__all__ = [
    "LogListener",
    "init_worker_logging",
    "initialize",
    "global_listener",
    "share_progress",
    "connect_progress",
]
MANYLOG_ENV_VAR = "MANYLOG_ADDRESS"
_init_called: bool = False


def initialize() -> None:
    """
    Zero-config initialization of manylog.  If no listener is configured, then
    it initializes a global listener and stores its address in an environment
    variable for child processes to consult.  If that environment variable is
    set, then it connects to it as a worker process.
    """
    global _init_called

    if _init_called:
        return

    _init_called = True
    if MANYLOG_ENV_VAR in os.environ:
        init_worker_logging(os.environ[MANYLOG_ENV_VAR])
    else:
        listener = global_listener()
        assert listener.address is not None
        os.environ[MANYLOG_ENV_VAR] = listener.address


def share_progress(progress: Progress) -> UUID:
    """
    Share a progress bar using the global listener (:func:`global_listener`).
    """
    listener = global_listener()
    return listener.share_progress(progress)
