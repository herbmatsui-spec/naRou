from __future__ import annotations

import logging
import os
import threading
from typing import Any

import yaml

logger = logging.getLogger(__name__)

try:
    import winsound

    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# Import audio backend for OGG playback
try:
    from audio.backend import get_audio_backend, load_audio_manifest, preload_all_audio

    HAS_AUDIO_BACKEND = True
except ImportError:
    HAS_AUDIO_BACKEND = False

from feature_flags import is_enabled


class BGMManager:
    """BGM管理システム（クロスフェード・テーマ切り替え） (Step 7.1, 7.3)"""

    def __init__(self, config_path: str = "data/audio_config.yaml"):
        self.config_path = config_path
        self.current_track: str | None = None
        self.current_theme: str | None = None
        self.volume: float = 0.8
        self.is_crisis: bool = False
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                logger.exception("ロード失敗")
            return {}

    def play_bgm(self, theme: str, fade_in: bool = True) -> str:
        """指定テーマのBGMを再生/クロスフェード切り替え (Step 7.1)"""
        bgm_conf = (self.config or {}).get("bgm", {}).get(theme, {})
        track_id = bgm_conf.get("track", f"bgm_{theme}")
        self.current_theme = theme
        self.current_track = track_id
        self.volume = bgm_conf.get("volume", 0.8)
        return f"Playing BGM [{track_id}] (Theme: {theme}, Volume: {self.volume})"

    def check_crisis_trigger(self, hp: int, max_hp: int) -> str | None:
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
        self.current_ambient: str | None = None
        self.volume: float = 0.5
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                logger.exception("ロード失敗")
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
            logger.exception("ロード失敗")

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

    # ===== NEW: OGG Audio Pack Integration =====

    _audio_initialized = False
    _se_cache: dict[str, str] = {}  # se_type -> suggested_id mapping
    _terrain_footstep_map: dict[str, str] = {}

    @classmethod
    def _init_audio_pack(cls):
        """Initialize audio pack - load manifest and preload sounds."""
        if cls._audio_initialized or not HAS_AUDIO_BACKEND:
            return
        if not is_enabled("ENABLE_AUDIO_PACK"):
            return

        backend = get_audio_backend()
        if not backend.is_available:
            return

        # Load SE mappings from config
        cls._load_se_mappings()

        # Preload all audio
        loaded = preload_all_audio("assets/audio/manifest.csv")
        if loaded > 0:
            cls._audio_initialized = True
            print(f"Audio pack initialized: {loaded} sounds loaded (backend: {backend.backend})")

    @classmethod
    def _load_se_mappings(cls):
        """Load SE type -> suggested_id mappings from audio config."""
        try:
            if os.path.exists("data/audio_config.yaml"):
                with open("data/audio_config.yaml", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                se_map = config.get("se", {})
                for se_type, filename in se_map.items():
                    # Convert filename to suggested_id (e.g., metalClick.ogg -> se_metal_click)
                    suggested_id = "se_" + filename.replace(".ogg", "").replace(".", "_").lower()
                    cls._se_cache[se_type] = suggested_id

                # Load terrain footstep mapping
                footstep_keys = [k for k in se_map if k.startswith("footstep_")]
                for key in footstep_keys:
                    terrain = key.replace("footstep_", "")
                    cls._terrain_footstep_map[terrain] = cls._se_cache.get(key, "")
        except Exception:
            logger.exception("ロード失敗")

    @classmethod
    def play_se_ogg(cls, se_type: str, volume: float = 1.0):
        """Play SE using OGG file from audio pack."""
        if not cls._enabled:
            return
        if not is_enabled("ENABLE_AUDIO_PACK"):
            # Fall back to tone-based SE
            cls.play_se(se_type)
            return

        cls._init_audio_pack()

        if not HAS_AUDIO_BACKEND:
            cls.play_se(se_type)
            return

        backend = get_audio_backend()
        if not backend.is_available:
            cls.play_se(se_type)
            return

        suggested_id = cls._se_cache.get(se_type)
        if not suggested_id:
            # Try direct mapping
            suggested_id = cls._se_cache.get(se_type.lower())
        if not suggested_id:
            cls.play_se(se_type)  # Fallback
            return

        def _worker():
            backend.play_sound(suggested_id, volume=volume)

        threading.Thread(target=_worker, daemon=True).start()

    @classmethod
    def play_footstep(cls, terrain: str = "stone", volume: float = 0.6):
        """Play terrain-specific footstep sound."""
        if not cls._enabled:
            return
        if not is_enabled("ENABLE_AUDIO_PACK"):
            cls.play_se("step")
            return

        cls._init_audio_pack()

        if not HAS_AUDIO_BACKEND:
            cls.play_se("step")
            return

        backend = get_audio_backend()
        if not backend.is_available:
            cls.play_se("step")
            return

        se_type = cls._terrain_footstep_map.get(terrain, "footstep_stone")
        suggested_id = cls._se_cache.get(se_type)
        if suggested_id:

            def _worker():
                backend.play_sound(suggested_id, volume=volume)

            threading.Thread(target=_worker, daemon=True).start()
        else:
            cls.play_se("step")

    @classmethod
    def play_ui_sound(cls, ui_type: str, volume: float = 0.7):
        """Play UI sound (click, hover, notify, select, cancel)."""
        se_map = {
            "click": "ui_click",
            "hover": "ui_hover",
            "notify": "ui_notify",
            "select": "ui_select",
            "cancel": "ui_cancel",
        }
        se_type = se_map.get(ui_type, "ui_click")
        cls.play_se_ogg(se_type, volume)

    @classmethod
    def play_bgm_ogg(cls, theme: str = "dungeon", fade_in: float = 1.0, loop: bool = True):
        """Play BGM using OGG file with crossfade."""
        if not cls._enabled:
            return
        if not is_enabled("ENABLE_AUDIO_PACK"):
            cls.bgm_manager.play_bgm(theme, fade_in=fade_in)
            return

        cls._init_audio_pack()

        if not HAS_AUDIO_BACKEND:
            cls.bgm_manager.play_bgm(theme, fade_in=fade_in)
            return

        backend = get_audio_backend()
        if not backend.is_available:
            cls.bgm_manager.play_bgm(theme, fade_in=fade_in)
            return

        config = cls.bgm_manager.config
        bgm_conf = config.get("bgm", {}).get(theme, {})
        track_filename = bgm_conf.get("track", f"bgm_{theme}.ogg")
        volume = bgm_conf.get("volume", 0.7)

        # Try to find the OGG file
        bgm_path = f"assets/audio/{track_filename}"
        if not os.path.exists(bgm_path):
            # Try with .ogg extension
            if not track_filename.endswith(".ogg"):
                bgm_path = f"assets/audio/{track_filename}.ogg"

        if os.path.exists(bgm_path):
            backend.play_bgm(bgm_path, volume=volume, loop=loop, fade_in=fade_in)
        else:
            cls.bgm_manager.play_bgm(theme, fade_in=fade_in)

    @classmethod
    def update_ambient_ogg(cls, location_type: str, depth: int = 0):
        """Update ambient loop with depth-based variation."""
        if not cls._enabled:
            return
        if not is_enabled("ENABLE_AUDIO_PACK"):
            cls.ambient_layer.update_ambient(location_type)
            return

        cls._init_audio_pack()

        if not HAS_AUDIO_BACKEND:
            cls.ambient_layer.update_ambient(location_type)
            return

        backend = get_audio_backend()
        if not backend.is_available:
            cls.ambient_layer.update_ambient(location_type)
            return

        # Determine ambient variant based on location and depth
        if location_type == "dungeon":
            if depth >= 10:
                ambient_key = "dungeon_deep"
            elif depth >= 5:
                ambient_key = "dungeon_shallow"
            else:
                ambient_key = "dungeon_shallow"
        elif location_type == "town":
            ambient_key = "town_day"
        elif location_type == "forest":
            ambient_key = "forest"
        elif location_type == "cave":
            ambient_key = "cave"
        else:
            ambient_key = "dungeon_shallow"

        config = cls.ambient_layer.config
        ambient_loops = config.get("ambient_loops", {})
        sound_filename = ambient_loops.get(ambient_key, "amb_water_drop")

        ambient_path = f"assets/audio/{sound_filename}"
        if not ambient_path.endswith(".ogg"):
            ambient_path += ".ogg"

        if os.path.exists(ambient_path):
            # For ambient, we play as a looping BGM at lower volume
            volume = 0.3
            backend.play_bgm(ambient_path, volume=volume, loop=True, fade_in=2.0)
            cls.ambient_layer.current_ambient = ambient_key
        else:
            cls.ambient_layer.update_ambient(location_type)

    @classmethod
    def stop_bgm(cls, fade_out: float = 1.0):
        """Stop BGM with fade out."""
        if HAS_AUDIO_BACKEND and is_enabled("ENABLE_AUDIO_PACK"):
            backend = get_audio_backend()
            if backend.is_available:
                backend.stop_bgm(fade_out)
        cls.bgm_manager.current_track = None
