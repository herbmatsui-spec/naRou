"""Engine / project localization suite"""
import unittest

from engine import get_localizer
from project import available_languages
class TestEngineProject(unittest.TestCase):
    def test_localizer(self):
        loc = get_localizer()
        self.assertEqual(loc.localize('hello'), 'Hello')
    def test_languages(self):
        self.assertIn('en', available_languages())

if __name__ == '__main__':
    unittest.main()
