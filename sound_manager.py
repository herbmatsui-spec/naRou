import threading
import os
import yaml
import sys
from typing import Optional, Dict, Any

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class BGMManager:
    """BGM管理システム（クロスフェード・テーマ切り替え） (Step 7.1, 7.3)"""
    def __init__(self, config_path: str = "data/audio_config.yaml"):
        self.config_path = config_path
        self.current_track: Optional[str] = None
        self.current_theme: Optional[str] = None
        self.volume: float = 0.8
        self.is_crisis: bool = False
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return {}

    def play_bgm(self, theme: str, fade_in: bool = True) -> str:
        """指定テーマのBGMを再生/クロスフェード切り替え (Step 7.1)"""
        bgm_conf = self.config.get("bgm", {}).get(theme, {})
        track_id = bgm_conf.get("track", f"bgm_{theme}")
        self.current_theme = theme
        self.current_track = track_id
        self.volume = bgm_conf.get("volume", 0.8)
        return f"Playing BGM [{track_id}] (Theme: {theme}, Volume: {self.volume})"

    def check_crisis_trigger(self, hp: int, max_hp: int) -> Optional[str]:
        """HP低下時の緊張BGMトリガー (Step 7.3)"""
        if max_hp > 0 and (hp / max_hp) <= 0.3:
            if not self.is_crisis:
                self.is_crisis = True
                return self.play_bgm("crisis")
        else:
            if self.is_crisis:
                self.is_crisis = False
                return self.play_bgm(self.current_theme or "dungeon")
        return None


class AmbientLayer:
    """環境音（アンビエント）レイヤー管理 (Step 7.2)"""
    def __init__(self, config_path: str = "data/audio_config.yaml"):
        self.config_path = config_path
        self.current_ambient: Optional[str] = None
        self.volume: float = 0.5
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return {}

    def update_ambient(self, location_type: str) -> str:
        """場所に応じた環境音の動的切り替え (Step 7.2)"""
        amb_conf = self.config.get("ambient", {}).get(location_type, {})
        sound_id = amb_conf.get("sound", f"amb_{location_type}")
        self.current_ambient = sound_id
        self.volume = amb_conf.get("volume", 0.5)
        return f"Active Ambient: [{sound_id}] (Location: {location_type})"


class SoundManager:
    """効果音・BGM・環境音総合管理クラス (非同期スレッド再生)"""
    _enabled = True
    bgm_manager = BGMManager()
    ambient_layer = AmbientLayer()

    @classmethod
    def set_enabled(cls, enabled: bool):
        cls._enabled = enabled

    @classmethod
    def is_enabled(cls) -> bool:
        return cls._enabled

    @classmethod
    def _play_tone(cls, frequency: int, duration_ms: int):
        if not cls._enabled or not HAS_WINSOUND:
            return
        try:
            winsound.Beep(frequency, duration_ms)
        except Exception:
            pass

    @classmethod
    def play_se(cls, se_type: str):
        """非同期で効果音を再生 (ゲームループをブロックしない)"""
        if not cls._enabled:
            return

        def _worker():
            if se_type == "hit":
                cls._play_tone(220, 40)
            elif se_type == "kill":
                cls._play_tone(180, 50)
                cls._play_tone(130, 80)
            elif se_type == "level_up":
                for f in [523, 659, 784, 1046]:  # ド・ミ・ソ・高いド
                    cls._play_tone(f, 60)
            elif se_type == "heal":
                cls._play_tone(600, 50)
                cls._play_tone(800, 70)
            elif se_type == "cast":
                cls._play_tone(450, 40)
                cls._play_tone(650, 60)
            elif se_type == "get_item":
                cls._play_tone(880, 35)
                cls._play_tone(1175, 45)
            elif se_type == "equip":
                cls._play_tone(400, 30)
                cls._play_tone(500, 40)
            elif se_type == "mine":
                cls._play_tone(150, 50)
            elif se_type == "fanfare":
                for f in [523, 659, 784, 1046, 1318]:
                    cls._play_tone(f, 80)
            elif se_type == "step":
                pass

        threading.Thread(target=_worker, daemon=True).start()

    @classmethod
    def play_bgm(cls, theme: str = "dungeon", fade_in: bool = True) -> str:
        return cls.bgm_manager.play_bgm(theme, fade_in=fade_in)

    @classmethod
    def update_ambient(cls, location_type: str) -> str:
        return cls.ambient_layer.update_ambient(location_type)
