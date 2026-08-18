"""System localization suite"""
import unittest

from localization_manager import LocalizationManager
class TestSystem(unittest.TestCase):
    def test_stats(self):
        lm = LocalizationManager()
        self.assertIn('total_entries', lm.get_stats())

if __name__ == '__main__':
    unittest.main()
