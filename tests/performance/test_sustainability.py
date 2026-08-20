#!/usr/bin/env python3
"""
Sustainability Test
持続性テスト
"""

import threading
import time
import unittest

from tools.performance_monitor import PerformanceMonitor


class TestSustainabilityPerformance(unittest.TestCase):
    """持続性テストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_long_running_stability(self):
        """長時間実行安定性テスト"""
        results = []
        errors = []

        def long_task():
            try:
                for _ in range(100):
                    total = 0
                    for i in range(10000):
                        total += i
                    time.sleep(0.01)
                results.append(True)
            except Exception as e:
                errors.append(e)

        threads = []
        for _ in range(4):
            t = threading.Thread(target=long_task)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=30)

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 4)

    def test_memory_stability(self):
        """メモリ安定性テスト"""
        footprints = []

        def memory_task():
            data = []
            for i in range(100):
                data.append("x" * 1000)
                fp = self.monitor.measure_footprint()
                footprints.append(fp["rss"])
                time.sleep(0.01)
            del data

        memory_task()

        # メモリが安定しているか確認（最初と最後で大きく差がない）
        if len(footprints) > 10:
            early_avg = sum(footprints[:10]) / 10
            late_avg = sum(footprints[-10:]) / 10
            # 2倍以内なら安定とみなす
            self.assertLess(late_avg, early_avg * 2)

    def test_cpu_stability(self):
        """CPU安定性テスト"""
        cpu_values = []

        def cpu_task():
            for _ in range(50):
                cpu = self.monitor.measure_cpu()
                cpu_values.append(cpu)
                time.sleep(0.02)

        cpu_task()

        if len(cpu_values) > 10:
            avg_cpu = sum(cpu_values) / len(cpu_values)
            # 平均CPU使用率が極端に高くないことを確認
            self.assertLess(avg_cpu, 90)


def run_sustainability_tests():
    """持続性テスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSustainabilityPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_sustainability_tests()
    exit(0 if success else 1)
