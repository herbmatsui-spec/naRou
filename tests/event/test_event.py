"""Event / input localization suite"""

import unittest

from input_handler import InputHandler


class TestEvent(unittest.TestCase):
    def test_localize_method(self):
        self.assertEqual(InputHandler.localize("hello", "en"), "Hello")


if __name__ == "__main__":
    unittest.main()
