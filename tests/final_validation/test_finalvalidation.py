from __future__ import annotations

"""Final i18n validation suite"""

import unittest

from localization_manager import LocalizationManager


class TestFinalValidation(unittest.TestCase):
    def test_all(self):
        lm = LocalizationManager()
        self.assertTrue(lm.test())
        # Integration-level checks across supported languages
        supported = lm.get_supported_languages()
        self.assertIn("en", supported)
        for lang in supported:
            self.assertTrue(lm.get_language_data(lang).get("hello"))


if __name__ == "__main__":
    unittest.main()
