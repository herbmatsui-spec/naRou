#!/usr/bin/env python3
"""
Memory Performance Test
メモリパフォーマンステスト
"""

import unittest

from tools.performance_monitor import PerformanceMonitor


class TestMemoryPerformance(unittest.TestCase):
    """メモリパフォーマンステストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_memory_measurement(self):
        """メモリ測定テスト"""
        mem = self.monitor.measure_memory()
        self.assertIn("total", mem)
        self.assertIn("available", mem)
        self.assertIn("used", mem)
        self.assertIn("percent", mem)
        self.assertGreater(mem["total"], 0)
        self.assertGreaterEqual(mem["percent"], 0)
        self.assertLessEqual(mem["percent"], 100)

    def test_memory_footprint(self):
        """メモリフットプリントテスト"""
        footprint = self.monitor.measure_footprint()
        self.assertIn("rss", footprint)
        self.assertIn("vms", footprint)
        self.assertIn("percent", footprint)
        self.assertGreater(footprint["rss"], 0)

    def test_memory_baseline(self):
        """メモリベースラインテスト"""
        baseline = self.monitor.collect_baseline(duration=3)
        self.assertIn("statistics", baseline)
        self.assertIn("memory_avg", baseline["statistics"])
        self.assertIn("memory_max", baseline["statistics"])
        self.assertIn("memory_min", baseline["statistics"])


def run_memory_tests():
    """メモリテスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMemoryPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_memory_tests()
    exit(0 if success else 1)
