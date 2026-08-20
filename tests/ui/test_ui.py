"""UI localization suite"""

import unittest

from localization_manager import LocalizationManager


class TestUI(unittest.TestCase):
    def test_ui_keys(self):
        lm = LocalizationManager()
        for k in ["menu", "play", "save", "load", "settings", "quit"]:
            self.assertTrue(lm.get_text(k, "en"))


if __name__ == "__main__":
    unittest.main()
