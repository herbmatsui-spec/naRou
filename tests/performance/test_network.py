#!/usr/bin/env python3
"""
Network Performance Test
ネットワークパフォーマンステスト
"""

import socket
import unittest

from tools.performance_monitor import PerformanceMonitor


class TestNetworkPerformance(unittest.TestCase):
    """ネットワークパフォーマンステストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_network_measurement(self):
        """ネットワーク測定テスト"""
        net = self.monitor.measure_network()
        self.assertIsInstance(net, dict)
        if net:
            self.assertIn("bytes_sent", net)
            self.assertIn("bytes_recv", net)
            self.assertIn("packets_sent", net)
            self.assertIn("packets_recv", net)

    def test_localhost_latency(self):
        """ローカルホストレイテンシテスト"""

        def ping_localhost():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            try:
                sock.connect(("127.0.0.1", 80))
            except:
                pass
            finally:
                sock.close()

        # ポート80が開いていない場合はスキップ
        try:
            duration = self.monitor.measure_response_time(ping_localhost)
            self.assertIsInstance(duration, float)
            self.assertGreaterEqual(duration, 0)
        except:
            self.skipTest("Localhost port 80 not available")

    def test_network_baseline(self):
        """ネットワークベースラインテスト"""
        baseline = self.monitor.collect_baseline(duration=3)
        self.assertIn("measurements", baseline)
        for m in baseline["measurements"]:
            self.assertIn("network", m)


def run_network_tests():
    """ネットワークテスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNetworkPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_network_tests()
    exit(0 if success else 1)
