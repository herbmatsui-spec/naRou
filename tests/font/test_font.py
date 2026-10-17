from __future__ import annotations

"""Font / rendering suite (locale coverage)"""

import unittest

from localization_manager import LocalizationManager


class TestFont(unittest.TestCase):
    def test_cjk_present(self):
        lm = LocalizationManager()
        for lang in ["ja", "ko", "zh-cn", "zh-tw"]:
            # ensure localized text exists for CJK languages
            self.assertTrue(lm.get_language_data(lang).get("hello"))


if __name__ == "__main__":
    unittest.main()
