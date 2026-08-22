"""Fallback stub for psutil used in performance_monitor tests.
Provides minimal interfaces returning zero or dummy values so that the code
can run without the external dependency.
"""

from __future__ import annotations

from collections import namedtuple

# Simple memory info mock
_MemoryInfo = namedtuple("MemoryInfo", ["rss", "vms"])

__version__ = "5.9.0"


def cpu_count(logical=True):
    return 8


def cpu_percent(interval=0.0):
    return 0.0


def virtual_memory():
    # Return object with .percent and .total attributes
    Mem = namedtuple("Mem", ["total", "available", "percent", "used", "free"])
    return Mem(
        total=16 * 1024 * 1024 * 1024,
        available=8 * 1024 * 1024 * 1024,
        percent=10.0,
        used=8 * 1024 * 1024 * 1024,
        free=8 * 1024 * 1024 * 1024,
    )


def disk_usage(path):
    Usage = namedtuple("Usage", ["total", "used", "free", "percent"])
    return Usage(
        total=100 * 1024 * 1024 * 1024,
        used=10 * 1024 * 1024 * 1024,
        free=90 * 1024 * 1024 * 1024,
        percent=10.0,
    )


def disk_io_counters():
    IO = namedtuple("IO", ["read_bytes", "write_bytes", "read_count", "write_count"])
    return IO(read_bytes=1000, write_bytes=1000, read_count=10, write_count=10)


def net_io_counters():
    Net = namedtuple("Net", ["bytes_sent", "bytes_recv", "packets_sent", "packets_recv"])
    return Net(bytes_sent=1000, bytes_recv=1000, packets_sent=10, packets_recv=10)


class _Proc:
    def cpu_percent(self, interval=0.0):
        return 1.0

    def memory_info(self):
        return _MemoryInfo(rss=100 * 1024 * 1024, vms=200 * 1024 * 1024)

    def memory_percent(self):
        return 1.0


_process = _Proc()


def Process(*args, **kwargs):
    return _process
