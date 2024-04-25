"""
Collect log messages and progress updates from multiple processes.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("manylog")
except PackageNotFoundError:
    # package is not installed
    pass
