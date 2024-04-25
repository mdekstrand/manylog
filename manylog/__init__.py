"""
Collect log messages and progress updates from multiple processes.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("manylog")
except PackageNotFoundError:
    # package is not installed
    pass

from .listener import LogListener
from .worker import init_worker_logging

__all__ = ["LogListener", "init_worker_logging"]
