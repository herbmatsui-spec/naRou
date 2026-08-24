"""
Dummy performance monitor for test environment.
Provides a minimal PerformanceMonitor class with the interface expected by the tests
(e.g., start, stop, record). The real implementation is not required for unit
tests, so methods are no‑ops.
"""

class PerformanceMonitor:
    def __init__(self, *args, **kwargs):
        pass
    def start(self):
        pass
    def stop(self):
        pass
    def record(self, *args, **kwargs):
        pass
