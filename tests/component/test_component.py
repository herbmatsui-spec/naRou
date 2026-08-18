"""Component localization suite"""
import unittest

from localization_manager import LocalizationManager
class TestComponent(unittest.TestCase):
    def test_compare(self):
        lm = LocalizationManager()
        c = lm.compare_languages('en','ja')
        self.assertEqual(c['total_1'], c['total_2'])

if __name__ == '__main__':
    unittest.main()
