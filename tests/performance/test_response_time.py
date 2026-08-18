#!/usr/bin/env python3
"""
Response Time Performance Test
応答時間パフォーマンステスト
"""
import unittest
import time
from tools.performance_monitor import PerformanceMonitor


class TestResponseTimePerformance(unittest.TestCase):
    """応答時間パフォーマンステストクラス"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor()
    
    def test_response_time_measurement(self):
        """応答時間測定テスト"""
        def sample_task():
            time.sleep(0.01)
            return "done"
        
        duration = self.monitor.measure_response_time(sample_task)
        self.assertIsInstance(duration, float)
        self.assertGreaterEqual(duration, 0.01)
    
    def test_response_time_multiple_calls(self):
        """複数回呼び出しの応答時間テスト"""
        def quick_task():
            return sum(range(1000))
        
        durations = []
        for _ in range(10):
            duration = self.monitor.measure_response_time(quick_task)
            durations.append(duration)
        
        self.assertEqual(len(durations), 10)
        avg_duration = sum(durations) / len(durations)
        self.assertGreater(avg_duration, 0)
    
    def test_response_time_under_load(self):
        """負荷下での応答時間テスト"""
        def heavy_task():
            total = 0
            for i in range(100000):
                total += i * i
            return total
        
        duration = self.monitor.measure_response_time(heavy_task)
        self.assertIsInstance(duration, float)
        self.assertGreater(duration, 0)


def run_response_time_tests():
    """応答時間テスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestResponseTimePerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_response_time_tests()
    exit(0 if success else 1)