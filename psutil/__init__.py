"""Fallback stub for psutil used in performance_monitor tests.
Provides minimal interfaces returning zero or dummy values so that the code
can run without the external dependency.
"""

from collections import namedtuple

# Simple memory info mock
_MemoryInfo = namedtuple('MemoryInfo', ['rss', 'vms'])

def cpu_percent(interval=0.0):
    return 0.0

def virtual_memory():
    # Return object with .percent attribute
    Mem = namedtuple('Mem', ['percent'])
    return Mem(percent=0.0)

def disk_usage(path):
    Usage = namedtuple('Usage', ['total', 'used', 'free'])
    return Usage(total=1, used=0, free=1)

def disk_io_counters():
    IO = namedtuple('IO', ['read_bytes', 'write_bytes', 'read_count', 'write_count'])
    return IO(read_bytes=0, write_bytes=0, read_count=0, write_count=0)

def net_io_counters():
    Net = namedtuple('Net', ['bytes_sent', 'bytes_recv', 'packets_sent', 'packets_recv'])
    return Net(bytes_sent=0, bytes_recv=0, packets_sent=0, packets_recv=0)

def Process(pid=None):
    class _Proc:
        def memory_info(self):
            return _MemoryInfo(rss=0, vms=0)
        def memory_percent(self):
            return 0.0
    return _Proc()

# expose a default process instance similar to real psutil.Process()
_process = Process()

# For compatibility with code that does "psutil.Process()"
def Process(*args, **kwargs):
    return _process
