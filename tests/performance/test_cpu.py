#!/usr/bin/env python3
"""
CPU Performance Test
CPUパフォーマンステスト
"""

import unittest

from tools.performance_monitor import PerformanceMonitor


class TestCPUPerformance(unittest.TestCase):
    """CPUパフォーマンステストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_cpu_measurement(self):
        """CPU測定テスト"""
        cpu_percent = self.monitor.measure_cpu()
        self.assertIsInstance(cpu_percent, float)
        self.assertGreaterEqual(cpu_percent, 0)
        self.assertLessEqual(cpu_percent, 100)

    def test_cpu_under_load(self):
        """負荷下でのCPU測定テスト"""

        def cpu_intensive_task():
            total = 0
            for i in range(1000000):
                total += i * i
            return total

        self.monitor.start_monitoring()
        result = self.monitor.measure_response_time(cpu_intensive_task)
        self.monitor.stop_monitoring()

        self.assertIsInstance(result, float)
        self.assertGreater(result, 0)

    def test_cpu_baseline_collection(self):
        """CPUベースライン収集テスト"""
        baseline = self.monitor.collect_baseline(duration=3)
        self.assertIn("statistics", baseline)
        self.assertIn("cpu_avg", baseline["statistics"])
        self.assertIn("cpu_max", baseline["statistics"])
        self.assertIn("cpu_min", baseline["statistics"])


def run_cpu_tests():
    """CPUテスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCPUPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_cpu_tests()
    exit(0 if success else 1)
