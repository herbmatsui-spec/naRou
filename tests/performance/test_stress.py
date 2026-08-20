#!/usr/bin/env python3
"""
Stress Test
ストレステスト
"""
from __future__ import annotations

import sys
import threading
import time
import unittest

from tools.performance_monitor import PerformanceMonitor


class TestStressPerformance(unittest.TestCase):
    """ストレステストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_cpu_stress(self):
        """CPUストレステスト"""

        def cpu_stress():
            total = 0
            for i in range(2000000):
                total += i * i
            return total

        start = time.time()
        threads = []
        for _ in range(4):
            t = threading.Thread(target=cpu_stress)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        duration = time.time() - start
        self.assertGreater(duration, 0)

    def test_memory_stress(self):
        """メモリストレステスト"""
        data = []
        for i in range(10000):
            data.append("x" * 10000)  # 10KB * 10000 = ~100MB

        footprint = self.monitor.measure_footprint()
        self.assertGreater(footprint["rss"], 50 * 1024 * 1024)  # 50MB以上

        del data

    def test_concurrent_io_stress(self):
        """並行I/Oストレステスト"""
        import os
        import tempfile

        def io_task(idx):
            with tempfile.NamedTemporaryFile(delete=False) as f:
                temp_path = f.name
            try:
                with open(temp_path, "wb") as f:
                    f.write(b"x" * 1024 * 1024)
                with open(temp_path, "rb") as f:
                    f.read()
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        threads = []
        for i in range(8):
            t = threading.Thread(target=io_task, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()


def run_stress_tests():
    """ストレステスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStressPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_stress_tests()
    sys.exit(0 if success else 1)
