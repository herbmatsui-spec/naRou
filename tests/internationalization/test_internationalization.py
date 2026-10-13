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
        # Step 65.4 (GAME_DESIGN_V2): 日本語が主言語のため既定は ja。
        # tests/test_i18n.py::test_default_language_is_japanese と同一契約。
        self.assertEqual(self.lm.get_current_language(), "ja")

    def test_validate(self):
        self.assertTrue(self.lm.validate()["valid"])


if __name__ == "__main__":
    unittest.main()
