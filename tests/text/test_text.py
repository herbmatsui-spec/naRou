from __future__ import annotations

"""Text retrieval suite"""

import unittest

from localization_manager import LocalizationManager


class TestText(unittest.TestCase):
    def setUp(self):
        self.lm = LocalizationManager()

    def test_get_text(self):
        self.assertEqual(self.lm.get_text("hello", "en"), "Hello")
        self.assertEqual(
            self.lm.get_text("hello", "ja"), "\u3053\u3093\u306b\u3061\u306f"
        )

    def test_fallback(self):
        self.assertEqual(self.lm.get_text_with_fallback("missing", "en"), "missing")


if __name__ == "__main__":
    unittest.main()
