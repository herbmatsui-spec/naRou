#!/usr/bin/env python3
"""
Footprint Performance Test
フットプリントパフォーマンステスト
"""

import unittest

from tools.performance_monitor import PerformanceMonitor


class TestFootprintPerformance(unittest.TestCase):
    """フットプリントパフォーマンステストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_footprint_measurement(self):
        """フットプリント測定テスト"""
        footprint = self.monitor.measure_footprint()
        self.assertIn("rss", footprint)
        self.assertIn("vms", footprint)
        self.assertIn("percent", footprint)
        self.assertGreater(footprint["rss"], 0)
        self.assertGreater(footprint["vms"], 0)

    def test_footprint_growth(self):
        """フットプリント増加テスト"""
        initial = self.monitor.measure_footprint()

        # メモリを消費する操作
        data = []
        for i in range(10000):
            data.append("x" * 1000)

        after = self.monitor.measure_footprint()

        # RSSが増加していることを確認
        self.assertGreaterEqual(after["rss"], initial["rss"])

        # クリーンアップ
        del data

    def test_footprint_baseline(self):
        """フットプリントベースラインテスト"""
        baseline = self.monitor.collect_baseline(duration=3)
        self.assertIn("measurements", baseline)
        for m in baseline["measurements"]:
            self.assertIn("footprint", m)
            fp = m["footprint"]
            self.assertIn("rss", fp)
            self.assertIn("vms", fp)


def run_footprint_tests():
    """フットプリントテスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFootprintPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_footprint_tests()
    exit(0 if success else 1)
