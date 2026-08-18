#!/usr/bin/env python3
"""
Latency Performance Test
レイテンシパフォーマンステスト
"""
import unittest
import time
from tools.performance_monitor import PerformanceMonitor


class TestLatencyPerformance(unittest.TestCase):
    """レイテンシパフォーマンステストクラス"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor()
    
    def test_latency_measurement(self):
        """レイテンシ測定テスト"""
        def sample_task():
            time.sleep(0.005)
            return "done"
        
        latency = self.monitor.measure_latency(sample_task)
        self.assertIsInstance(latency, float)
        self.assertGreaterEqual(latency, 0.005)
    
    def test_latency_percentiles(self):
        """レイテンシパーセンタイルテスト"""
        def variable_task():
            time.sleep(0.001 * (hash(str(time.time())) % 10))
            return "done"
        
        latencies = []
        for _ in range(100):
            latency = self.monitor.measure_latency(variable_task)
            latencies.append(latency)
        
        latencies.sort()
        p50 = latencies[50]
        p95 = latencies[95]
        p99 = latencies[99]
        
        self.assertGreater(p50, 0)
        self.assertGreater(p95, p50)
        self.assertGreater(p99, p95)
    
    def test_latency_consistency(self):
        """レイテンシ一貫性テスト"""
        def consistent_task():
            return sum(range(100))
        
        latencies = []
        for _ in range(50):
            latency = self.monitor.measure_latency(consistent_task)
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        # 最大値が平均の10倍以内であること（安定性の目安）
        self.assertLess(max_latency, avg_latency * 10)


def run_latency_tests():
    """レイテンシテスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLatencyPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_latency_tests()
    exit(0 if success else 1)