#!/usr/bin/env python3
"""
Compatibility Test
互換性テスト
"""
import unittest
import sys
import platform
from tools.performance_monitor import PerformanceMonitor


class TestCompatibilityPerformance(unittest.TestCase):
    """互換性テストクラス"""
    
    def setUp(self):
        self.monitor = PerformanceMonitor()
    
    def test_python_version_compatibility(self):
        """Pythonバージョン互換性テスト"""
        # Python 3.8以上で動作することを確認
        major, minor = sys.version_info[:2]
        self.assertGreaterEqual(major, 3)
        if major == 3:
            self.assertGreaterEqual(minor, 8)
    
    def test_platform_compatibility(self):
        """プラットフォーム互換性テスト"""
        system = platform.system()
        self.assertIn(system, ['Linux', 'Darwin', 'Windows'])
        
        # アーキテクチャ確認
        machine = platform.machine().lower()
        self.assertIn(machine, ['x86_64', 'amd64', 'arm64', 'aarch64', 'x86', 'i386', 'i686'])

    
    def test_psutil_compatibility(self):
        """psutilライブラリ互換性テスト"""
        import psutil
        
        # 基本機能が動作すること
        cpu_count = psutil.cpu_count()
        self.assertGreater(cpu_count, 0)
        
        mem = psutil.virtual_memory()
        self.assertGreater(mem.total, 0)
        
        disk = psutil.disk_usage('/')
        self.assertGreater(disk.total, 0)
    
    def test_dependency_versions(self):
        """依存関係バージョンテスト"""
        # 標準ライブラリのみ使用していることを確認
        # （外部依存はpsutilのみ）
        import psutil
        version = psutil.__version__
        self.assertIsInstance(version, str)
        self.assertGreater(len(version), 0)
    
    def test_unicode_handling(self):
        """Unicode処理テスト"""
        test_strings = [
            'ASCII',
            '日本語',
            '中文',
            '한국어',
            '🚀🎉💻',
            'café',
            'naïve'
        ]
        
        for s in test_strings:
            encoded = s.encode('utf-8')
            decoded = encoded.decode('utf-8')
            self.assertEqual(s, decoded)
    
    def test_file_encoding(self):
        """ファイルエンコーディングテスト"""
        import tempfile
        import os
        
        test_content = 'テスト内容\nJapanese: 日本語\nEmoji: 🚀'
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            with open(temp_path, 'r', encoding='utf-8') as f:
                read_content = f.read()
            self.assertEqual(test_content, read_content)
        finally:
            os.unlink(temp_path)


def run_compatibility_tests():
    """互換性テスト実行"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCompatibilityPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_compatibility_tests()
    exit(0 if success else 1)