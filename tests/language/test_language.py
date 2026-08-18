"""Language support suite"""
import unittest

from localization_manager import LocalizationManager
class TestLanguage(unittest.TestCase):
    def setUp(self):
        self.lm = LocalizationManager()
    def test_supported(self):
        for lang in ['en','ja','ko','zh-cn','zh-tw']:
            self.assertIn(lang, self.lm.get_supported_languages())
    def test_set_language(self):
        self.assertTrue(self.lm.set_language('ja'))
        self.assertEqual(self.lm.get_current_language(), 'ja')
    def test_validate_language(self):
        self.assertTrue(self.lm.validate_language('en'))
        self.assertFalse(self.lm.validate_language('xx'))

if __name__ == '__main__':
    unittest.main()
