from __future__ import annotations

"""Internationalization base suite"""

import unittest

from localization_manager import LocalizationManager


class TestInternationalization(unittest.TestCase):
    def setUp(self):
        self.lm = LocalizationManager()

    def test_manager_loads(self):
        self.assertTrue(self.lm.get_supported_languages())

    def test_default_language(self):
        self.assertEqual(self.lm.get_current_language(), "en")

    def test_validate(self):
        self.assertTrue(self.lm.validate()["valid"])


if __name__ == "__main__":
    unittest.main()
