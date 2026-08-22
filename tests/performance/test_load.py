#!/usr/bin/env python3
"""
Load Test
負荷テスト
"""

from __future__ import annotations

import sys
import threading
import time
import unittest

from tools.performance_monitor import PerformanceMonitor


class TestLoadPerformance(unittest.TestCase):
    """負荷テストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_sustained_load(self):
        """持続負荷テスト"""
        results = []

        def worker():
            start = time.time()
            total = 0
            for i in range(100000):
                total += i
            results.append(time.time() - start)

        threads = []
        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(results), 10)
        avg_time = sum(results) / len(results)
        self.assertGreater(avg_time, 0)

    def test_ramp_up_load(self):
        """ラップアップ負荷テスト"""
        results = []

        def worker(iterations):
            start = time.time()
            total = 0
            for i in range(iterations):
                total += i
            results.append(time.time() - start)

        # 段階的に負荷を増加
        for load in [10000, 50000, 100000, 200000]:
            t = threading.Thread(target=worker, args=(load,))
            t.start()
            t.join()

        self.assertEqual(len(results), 4)

    def test_load_with_monitoring(self):
        """監視付き負荷テスト"""
        self.monitor.start_monitoring()

        def load_task():
            total = 0
            for i in range(500000):
                total += i * i
            return total

        threads = []
        for _ in range(4):
            t = threading.Thread(target=load_task)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.monitor.stop_monitoring()

        cpu = self.monitor.measure_cpu()
        mem = self.monitor.measure_memory()

        self.assertGreaterEqual(cpu, 0)
        self.assertGreater(mem["percent"], 0)


def run_load_tests():
    """負荷テスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLoadPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_load_tests()
    sys.exit(0 if success else 1)
