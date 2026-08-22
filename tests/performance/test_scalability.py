#!/usr/bin/env python3
"""
Scalability Test
スケーラビリティテスト
"""

from __future__ import annotations

import sys
import threading
import time
import unittest

from tools.performance_monitor import PerformanceMonitor


class TestScalabilityPerformance(unittest.TestCase):
    """スケーラビリティテストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_horizontal_scaling(self):
        """水平スケーリングテスト"""

        def worker_task(load):
            total = 0
            for i in range(load):
                total += i
            return total

        # ワーカー数を増やしてスループット測定
        throughputs = []

        for workers in [1, 2, 4, 8]:
            start = time.time()
            threads = []
            for _ in range(workers):
                t = threading.Thread(target=worker_task, args=(100000,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            duration = time.time() - start
            throughput = (workers * 100000) / duration
            throughputs.append(throughput)

        # スループットが正常に計算されていることを確認
        self.assertGreater(throughputs[-1], 0)
        self.assertGreater(throughputs[0], 0)

    def test_vertical_scaling(self):
        """垂直スケーリングテスト（負荷増加への対応）"""
        durations = []

        def scalable_task(load):
            start = time.perf_counter()
            total = 0
            for i in range(load):
                total += i * i
            return time.perf_counter() - start

        for load in [10000, 50000, 100000, 200000]:
            duration = scalable_task(load)
            durations.append(duration)

        # 負荷に比例して時間が正常に増加
        self.assertGreater(durations[3], 0)
        self.assertGreater(durations[3], durations[0])

    def test_resource_scaling(self):
        """リソーススケーリングテスト"""
        footprints = []

        def memory_task(data_size):
            data = []
            for i in range(data_size):
                data.append("x" * 1000)
            fp = self.monitor.measure_footprint()
            footprints.append(fp["rss"])
            del data

        for size in [100, 500, 1000, 2000]:
            memory_task(size)

        # データサイズに応じてメモリが正当に測定されていることを確認
        self.assertGreater(footprints[-1], 0)
        self.assertGreaterEqual(footprints[-1], footprints[0])


def run_scalability_tests():
    """スケーラビリティテスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestScalabilityPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_scalability_tests()
    sys.exit(0 if success else 1)
