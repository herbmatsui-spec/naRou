#!/usr/bin/env python3
"""
Interoperability Test
相互運用性テスト
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

from tools.performance_monitor import PerformanceMonitor


class TestInteroperabilityPerformance(unittest.TestCase):
    """相互運用性テストクラス"""

    def setUp(self):
        self.monitor = PerformanceMonitor()

    def test_json_serialization(self):
        """JSONシリアライゼーションテスト"""
        data = {
            "cpu": 50.5,
            "memory": 1024 * 1024 * 100,
            "timestamp": "2024-01-01T00:00:00Z",
            "metrics": [1, 2, 3, 4, 5],
        }

        # シリアライズ
        json_str = json.dumps(data)
        self.assertIsInstance(json_str, str)

        # デシリアライズ
        parsed = json.loads(json_str)
        self.assertEqual(parsed["cpu"], 50.5)
        self.assertEqual(parsed["metrics"], [1, 2, 3, 4, 5])

    def test_csv_compatibility(self):
        """CSV互換性テスト"""
        import csv
        import io

        data = [
            ["timestamp", "cpu", "memory"],
            ["2024-01-01T00:00:00Z", "50.5", "104857600"],
            ["2024-01-01T00:00:01Z", "51.2", "105234432"],
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(data)

        csv_content = output.getvalue()
        self.assertIn("timestamp,cpu,memory", csv_content)

        # 読み戻し
        input_io = io.StringIO(csv_content)
        reader = csv.reader(input_io)
        rows = list(reader)
        self.assertEqual(len(rows), 3)

    def test_subprocess_integration(self):
        """サブプロセス連携テスト"""
        # Pythonスクリプトを実行して結果を取得
        script = """
import json
import sys
result = {'status': 'ok', 'value': 42}
print(json.dumps(result))
"""
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True
        )

        self.assertEqual(result.returncode, 0)
        parsed = json.loads(result.stdout.strip())
        self.assertEqual(parsed["status"], "ok")
        self.assertEqual(parsed["value"], 42)

    def test_cross_platform_paths(self):
        """クロスプラットフォームパステスト"""
        from pathlib import Path

        # パス操作がプラットフォーム非依存で動作
        path = Path("tests") / "performance" / "test_interoperability.py"
        self.assertTrue(str(path).endswith("test_interoperability.py"))

        # 絶対パス取得
        abs_path = path.resolve()
        self.assertTrue(abs_path.is_absolute())


def run_interoperability_tests():
    """相互運用性テスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInteroperabilityPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_interoperability_tests()
    sys.exit(0 if success else 1)
