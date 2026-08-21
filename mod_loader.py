import os
import importlib.util
import sys
from pathlib import Path

class ModLoader:
    """
    Phase 7: スクリプトMOD対応 API (Step 50-56)
    Dynamic script mod loading system.
    """
    def __init__(self, mods_dir: str = "mods"):
        self.mods_dir = Path(__file__).parent / mods_dir
        self.mods_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_mods = {}

    def load_all(self):
        """Step 55: 起動時の ModLoader.load_all() 実行処理"""
        for entry in os.listdir(self.mods_dir):
            path = self.mods_dir / entry
            if path.is_dir() and (path / "__init__.py").exists():
                self._load_mod(entry, path / "__init__.py")

    def _load_mod(self, mod_name: str, path: Path):
        """Step 51: importlib による動的インポート機能の実装"""
        try:
            spec = importlib.util.spec_from_file_location(f"mods.{mod_name}", str(path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[f"mods.{mod_name}"] = mod
                spec.loader.exec_module(mod)
                self.loaded_mods[mod_name] = mod
                print(f"Successfully loaded mod: {mod_name}")
        except Exception as e:
            # Step 56: エラーMODスキップと安全機構の実装
            print(f"Failed to load mod {mod_name}: {e}")

    # Step 52: 公開APIメソッド（register_item()等）の定義
    def register_item(self, item_id: str, data: dict):
        """Mods call this to add new items."""
        from data_manager import data_manager
        data_manager.items[item_id] = data
        print(f"Mod API: Registered item {item_id}")

    def register_event_listener(self, event_type: str, callback):
        """Mods call this to hook into game events."""
        from event_bus import event_bus
        event_bus.subscribe(event_type, callback)
        print(f"Mod API: Registered event hook for {event_type}")

# Global instance
mod_loader = ModLoader()
