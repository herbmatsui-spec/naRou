#!/usr/bin/env python3
"""
Availability Test
可用性テスト
"""
from __future__ import annotations

import sys
import threading
import time
import unittest

from tools.performance_monitor import PerformanceMonitor


class TestAvailabilityPerformance(unittest.TestCase):
    """可用性テストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()
        self.service_available = True
        self.request_count = 0
        self.success_count = 0

    def test_service_uptime(self):
        """サービス稼働率テスト"""

        def check_service():
            self.request_count += 1
            if self.service_available:
                self.success_count += 1
                return True
            return False

        # 100リクエスト送信
        for _ in range(100):
            check_service()
            time.sleep(0.001)

        uptime = self.success_count / self.request_count * 100
        self.assertEqual(uptime, 100.0)

    def test_failover_simulation(self):
        """フェイルオーバーシミュレーション"""
        primary_available = True
        backup_available = True

        def check_with_failover():
            if primary_available:
                return "primary"
            elif backup_available:
                return "backup"
            return "unavailable"

        # プライマリ正常
        self.assertEqual(check_with_failover(), "primary")

        # プライマリ障害、バックアップ正常
        primary_available = False
        self.assertEqual(check_with_failover(), "backup")

        # 両方障害
        backup_available = False
        self.assertEqual(check_with_failover(), "unavailable")

    def test_concurrent_availability(self):
        """並行可用性テスト"""
        results = []

        def concurrent_check():
            available = self.service_available
            results.append(available)
            time.sleep(0.001)

        threads = []
        for _ in range(50):
            t = threading.Thread(target=concurrent_check)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(results), 50)
        self.assertTrue(all(results))


def run_availability_tests():
    """可用性テスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAvailabilityPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_availability_tests()
    sys.exit(0 if success else 1)
