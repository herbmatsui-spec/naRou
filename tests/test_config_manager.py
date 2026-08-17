import unittest
from config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    def test_get_config(self):
        cm = ConfigManager("config.yaml")
        self.assertEqual(cm.get("log_level"), "INFO")

if __name__ == "__main__":
    unittest.main()
