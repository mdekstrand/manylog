manylog intro
=============

The ``manylog`` package facilitates logging and progress reporting in Python
multiprocessing settings.  Right now, logging across process doesn't work
well, except for the natural interleaving that sometimes works acceptably
when using the ``fork`` multiprocessing context.  It supports log messages
through the Python standard library's logging module, and progress reported
with progress-api_.

.. _progress-api: https://progress-api.readthedocs.io/en/latest/

This package fixes that, through two parts:

*   A listener that runs in a parent process, listening for log messages and
    progress updates.  It republishes these log messages into the parent
    process's logging infrastructure so filters, handlers, etc. all apply.

*   Logging and progress backend for worker processes that forwards messages
    to the parent process.

It is agnostic to the specific multiprocessing framework in use, and will work
with stdlib :py:mod:`multiprocessing`, joblib (although Joblib lacks the setup
API needed to make it work easily), ipyparallel, Torch multiprocessing, and
others. It uses ZeroMQ to route messages between parent and child processes.

Currently, only single-machine multiprocessing is supported, but ZeroMQ will
make it easy to add cluster log and progress aggregation in the future.

Example
-------

In the parent, do::

    import multiprocessing.Pool
    from manylog import LogListener, init_worker_logging

    ctx = mp.get_context('spawn')
    with LogListener() as ll, ctx.Pool(4, init_worker_logging, (ll.address,)) as pool:
        # use `pool` to schedule parallel work

Log messages from worker processes will be routed through whatever logging and
progress configuration you have set up.

Contents
--------

.. toctree::
    parent.rst
    worker.rst
