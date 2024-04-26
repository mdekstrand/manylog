"""
Types and utilities for ZeroMQ connections.
"""

from __future__ import annotations

from typing import TypeAlias

import zmq

Socket: TypeAlias = zmq.Socket[bytes]
Context: TypeAlias = zmq.Context[Socket]
