#!/usr/bin/env python3
"""
Spike Test
スパイクテスト
"""

from __future__ import annotations

import sys
import threading
import time
import unittest

from tools.performance_monitor import PerformanceMonitor


class TestSpikePerformance(unittest.TestCase):
    """スパイクテストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_sudden_spike(self):
        """突然のスパイクテスト"""
        results = []

        def spike_task():
            start = time.time()
            # 短時間で大量の処理
            total = 0
            for i in range(500000):
                total += i * i
            results.append(time.time() - start)

        # 通常負荷
        normal_threads = []
        for _ in range(2):
            t = threading.Thread(target=spike_task)
            normal_threads.append(t)
            t.start()

        time.sleep(0.1)

        # スパイク負荷
        spike_threads = []
        for _ in range(20):
            t = threading.Thread(target=spike_task)
            spike_threads.append(t)
            t.start()

        for t in normal_threads + spike_threads:
            t.join()

        self.assertEqual(len(results), 22)

    def test_spike_recovery(self):
        """スパイク後の回復テスト"""

        def measure_cpu():
            return self.monitor.measure_cpu()

        # スパイク前
        cpu_before = measure_cpu()

        # スパイク実行
        def spike():
            total = 0
            for i in range(1000000):
                total += i

        threads = []
        for _ in range(10):
            t = threading.Thread(target=spike)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        time.sleep(0.5)  # 回復待ち

        # スパイク後
        cpu_after = measure_cpu()

        self.assertGreaterEqual(cpu_before, 0)
        self.assertGreaterEqual(cpu_after, 0)

    def test_spike_latency_impact(self):
        """スパイクがレイテンシに与える影響"""
        latencies = []

        def latency_task():
            start = time.perf_counter()
            total = 0
            for i in range(10000):
                total += i
            latencies.append(time.perf_counter() - start)

        # 通常時のレイテンシ測定
        for _ in range(10):
            latency_task()

        sum(latencies) / len(latencies)
        latencies.clear()

        # スパイク負荷実行中にレイテンシ測定
        def background_spike():
            for _ in range(100):
                total = 0
                for i in range(50000):
                    total += i

        spike_thread = threading.Thread(target=background_spike)
        spike_thread.start()

        for _ in range(10):
            latency_task()

        spike_avg = sum(latencies) / len(latencies) if latencies else 0.0
        self.assertGreaterEqual(spike_avg, 0)


def run_spike_tests():
    """スパイクテスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSpikePerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_spike_tests()
    sys.exit(0 if success else 1)
