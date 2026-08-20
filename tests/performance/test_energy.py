#!/usr/bin/env python3
"""
Energy Consumption Performance Test
エネルギー消費量パフォーマンステスト
"""

import unittest

from tools.performance_monitor import PerformanceMonitor


class TestEnergyPerformance(unittest.TestCase):
    """エネルギー消費量パフォーマンステストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_energy_measurement(self):
        """エネルギー測定テスト"""
        energy = self.monitor.measure_energy()
        self.assertIn("cpu_percent", energy)
        self.assertIn("estimated_watts", energy)
        self.assertGreaterEqual(energy["cpu_percent"], 0)
        self.assertLessEqual(energy["cpu_percent"], 100)
        self.assertGreaterEqual(energy["estimated_watts"], 0)

    def test_energy_under_load(self):
        """負荷下でのエネルギー測定テスト"""

        def cpu_intensive():
            total = 0
            for i in range(500000):
                total += i * i
            return total

        self.monitor.start_monitoring()
        self.monitor.measure_response_time(cpu_intensive)
        self.monitor.stop_monitoring()

        energy = self.monitor.measure_energy()
        self.assertIn("cpu_percent", energy)

    def test_energy_baseline(self):
        """エネルギーベースラインテスト"""
        baseline = self.monitor.collect_baseline(duration=3)
        self.assertIn("measurements", baseline)
        for m in baseline["measurements"]:
            self.assertIn("energy", m)
            e = m["energy"]
            self.assertIn("cpu_percent", e)
            self.assertIn("estimated_watts", e)


def run_energy_tests():
    """エネルギー消費量テスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEnergyPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_energy_tests()
    exit(0 if success else 1)
