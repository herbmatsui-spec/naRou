from __future__ import annotations

"""Framework localization suite"""

import unittest

from naRou.localization_manager import LocalizationManager


class TestFramework(unittest.TestCase):
    def test_reload(self):
        lm = LocalizationManager()
        lm.reload()
        self.assertTrue(lm.get_supported_languages())


if __name__ == "__main__":
    unittest.main()
