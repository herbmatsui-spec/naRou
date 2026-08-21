from __future__ import annotations

"""Data integration localization suite"""

import unittest

from localization_manager import LocalizationManager


class TestData(unittest.TestCase):
    def test_language_mapping(self):
        m = LocalizationManager().get_language_mapping()
        self.assertEqual(m["ja"], "\u65e5\u672c\u8a9e")


if __name__ == "__main__":
    unittest.main()
