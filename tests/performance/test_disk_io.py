#!/usr/bin/env python3
"""
Disk I/O Performance Test
ディスクI/Oパフォーマンステスト
"""
import unittest
import tempfile
import os
from tools.performance_monitor import PerformanceMonitor


class TestDiskIOPerformance(unittest.TestCase):
    """ディスクI/Oパフォーマンステストクラス"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor()
    
    def test_disk_io_measurement(self):
        """ディスクI/O測定テスト"""
        disk_io = self.monitor.measure_disk_io()
        self.assertIsInstance(disk_io, dict)
        if disk_io:
            self.assertIn('read_bytes', disk_io)
            self.assertIn('write_bytes', disk_io)
            self.assertIn('read_count', disk_io)
            self.assertIn('write_count', disk_io)
    
    def test_disk_write_performance(self):
        """ディスク書き込みパフォーマンステスト"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        try:
            def write_task():
                with open(temp_path, 'wb') as f:
                    f.write(b'x' * 1024 * 1024)  # 1MB書き込み
            
            duration = self.monitor.measure_response_time(write_task)
            self.assertIsInstance(duration, float)
            self.assertGreater(duration, 0)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_disk_read_performance(self):
        """ディスク読み込みパフォーマンステスト"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'x' * 1024 * 1024)  # 1MB書き込み
            temp_path = f.name
        
        try:
            def read_task():
                with open(temp_path, 'rb') as f:
                    return f.read()
            
            duration = self.monitor.measure_response_time(read_task)
            self.assertIsInstance(duration, float)
            self.assertGreater(duration, 0)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


def run_disk_io_tests():
    """ディスクI/Oテスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDiskIOPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_disk_io_tests()
    exit(0 if success else 1)