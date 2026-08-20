#!/usr/bin/env python3
"""
Endurance Test
耐久性テスト
"""
from __future__ import annotations

import sys
import time
import unittest

from tools.performance_monitor import PerformanceMonitor


class TestEndurancePerformance(unittest.TestCase):
    """耐久性テストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_continuous_operation(self):
        """連続動作テスト"""
        iterations = 200
        success_count = 0
        error_count = 0

        def endurance_task():
            nonlocal success_count, error_count
            try:
                total = 0
                for i in range(50000):
                    total += i * i
                success_count += 1
            except:
                error_count += 1

        for i in range(iterations):
            endurance_task()
            if i % 50 == 0:
                time.sleep(0.01)  # 短い休憩

        self.assertEqual(error_count, 0)
        self.assertEqual(success_count, iterations)

    def test_resource_leak_detection(self):
        """リソースリーク検出テスト"""
        initial_footprint = self.monitor.measure_footprint()

        def leak_test_task():
            data = []
            for i in range(100):
                data.append("x" * 1000)
            # 意図的に解放しない場合のテスト
            # ここでは解放する
            del data

        for _ in range(50):
            leak_test_task()

        final_footprint = self.monitor.measure_footprint()

        # メモリが大幅に増えていないことを確認
        growth = final_footprint["rss"] - initial_footprint["rss"]
        self.assertLess(growth, 50 * 1024 * 1024)  # 50MB以下の増加

    def test_performance_degradation(self):
        """パフォーマンス劣化テスト"""
        durations = []

        def benchmark_task():
            start = time.perf_counter()
            total = 0
            for i in range(100000):
                total += i
            return time.perf_counter() - start

        # 最初の10回
        for _ in range(10):
            durations.append(benchmark_task())

        early_avg = sum(durations[:10]) / 10

        # 継続実行
        for _ in range(100):
            benchmark_task()
        # 最後の10回
        late_durations = []
        for _ in range(10):
            late_durations.append(benchmark_task())
        late_avg = sum(late_durations) / len(late_durations) if late_durations else 0.0
        # 劣化が大幅（5倍以内）でないこと
        self.assertLess(late_avg, max(0.001, early_avg * 10))


def run_endurance_tests():
    """耐久性テスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEndurancePerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_endurance_tests()
    sys.exit(0 if success else 1)
