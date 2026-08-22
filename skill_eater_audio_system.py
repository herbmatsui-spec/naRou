"""
skill_eater_audio_system.py
Aの世界（スキル喰い） 音響エンジン・SE管理システム
Phase 1: オーディオ基盤 (Kenney Foley / Sound Effect System)
Phase 6: 音響リソース統合・フォールバック・音量カテゴリ (Steps 61-66)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Any

# Step 2: 物理パス定数の定義
AUDIO_DIR = Path(__file__).parents[0] / "assets/audio"

# Phase 6 Step 61: 必要音声ファイルリスト
REQUIRED_AUDIO_FILES = {
    "rank_up_fanfare.ogg": "victory.ogg",  # フォールバック
    "ascension_node_unlock.ogg": "fanfare.ogg",
    "crystal_resonance.ogg": "magic_chime.ogg",
}

# Phase 6 Step 64: 音量カテゴリ
VOLUME_CATEGORIES = {
    "sfx": 1.0,  # 効果音
    "bgm": 0.7,  # BGM
    "ui": 0.8,  # UI音
    "ambient": 0.5,  # 環境音
}

# 音声ファイルのカテゴリマッピング
SOUND_CATEGORIES = {
    "rank_up_fanfare.ogg": "ui",
    "ascension_node_unlock.ogg": "ui",
    "crystal_resonance.ogg": "sfx",
    "victory.ogg": "ui",
    "fanfare.ogg": "ui",
    "magic_chime.ogg": "sfx",
    "footstep00.ogg": "sfx",
    "footstep01.ogg": "sfx",
    "footstep02.ogg": "sfx",
    "footstep03.ogg": "sfx",
    "footstep04.ogg": "sfx",
    "footstep05.ogg": "sfx",
    "footstep06.ogg": "sfx",
    "footstep07.ogg": "sfx",
    "footstep08.ogg": "sfx",
    "footstep09.ogg": "sfx",
    "doorOpen_1.ogg": "sfx",
    "doorOpen_2.ogg": "sfx",
    "doorClose_1.ogg": "sfx",
    "doorClose_2.ogg": "sfx",
    "metalLatch.ogg": "sfx",
    "metalClick.ogg": "sfx",
    "metalPot1.ogg": "sfx",
    "handleCoins.ogg": "ui",
    "handleCoins2.ogg": "ui",
    "stair_creak.ogg": "ambient",
    "floor_transition_woosh.ogg": "sfx",
    "elevator_hum.ogg": "ambient",
    "warp.ogg": "sfx",
    "warning.ogg": "ui",
    "alarm.ogg": "ui",
    "heartbeat.ogg": "ambient",
    "cloth1.ogg": "sfx",
    "chop.ogg": "sfx",
}


class SkillEaterAudioSystem:
    _instance: SkillEaterAudioSystem | None = None

    def __init__(self, audio_dir: Path | None = None, enable_real_audio: bool = True):
        self.audio_dir = audio_dir or AUDIO_DIR
        self.played_sounds: list[str] = []
        self.volume: float = 1.0
        self.is_muted: bool = False
        self.has_pygame: bool = False
        self._sound_cache: dict[str, Any] = {}

        # Phase 6 Step 64: カテゴリ別音量
        self.category_volumes: dict[str, float] = VOLUME_CATEGORIES.copy()

        # Step 5: pygame.mixerの安全な初期化試行
        if enable_real_audio:
            try:
                import pygame

                pygame.mixer.init()
                self.has_pygame = True
            except Exception:
                # If pygame not available, disable audio playback
                logger.exception("Unhandled exception")
                self.has_pygame = False

    @classmethod
    def get_instance(cls) -> SkillEaterAudioSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def set_volume(self, level: float) -> None:
        """Step 7: 音量調整 (0.0 〜 1.0)"""
        self.volume = max(0.0, min(1.0, level))

    def set_category_volume(self, category: str, level: float) -> None:
        """Phase 6 Step 64: カテゴリ別音量調整"""
        if category in self.category_volumes:
            self.category_volumes[category] = max(0.0, min(1.0, level))

    def set_mute(self, muted: bool) -> None:
        """Step 71: ミュート切り替え"""
        self.is_muted = muted

    # Phase 6 Step 63: フォールバック機能付き音声再生
    def _resolve_sound_path(self, sound_name: str) -> Path | None:
        """音声ファイルパスを解決（フォールバック対応）"""
        # 直接存在チェック
        sound_path = self.audio_dir / sound_name
        if sound_path.exists():
            return sound_path

        # フォールバックチェック
        if sound_name in REQUIRED_AUDIO_FILES:
            fallback = REQUIRED_AUDIO_FILES[sound_name]
            fallback_path = self.audio_dir / fallback
            if fallback_path.exists():
                logger.debug("Using fallback audio: %s -> %s", sound_name, fallback)
                return fallback_path

        return None

    def play_sound(self, sound_name: str, category: str | None = None) -> bool:
        """
        Step 4 & Step 6 & Phase 6: 音声再生（フォールバック・カテゴリ対応）
        - キュー (played_sounds) に常に記録
        - pygame が有効かつファイルが存在する場合は実際に再生
        """
        if self.is_muted:
            return False

        # キューに追加
        self.played_sounds.append(sound_name)

        if not self.has_pygame:
            return True

        # カテゴリ決定
        if category is None:
            category = SOUND_CATEGORIES.get(sound_name, "sfx")

        # ファイルパス解決（フォールバック込み）
        sound_path = self._resolve_sound_path(sound_name)
        if sound_path is None:
            logger.debug("Sound file not found (no fallback): %s", sound_name)
            return False

        try:
            import pygame

            if sound_name not in self._sound_cache:
                self._sound_cache[sound_name] = pygame.mixer.Sound(str(sound_path))
            snd = self._sound_cache[sound_name]

            # マスターボリューム × カテゴリボリューム
            effective_volume = self.volume * self.category_volumes.get(category, 1.0)
            snd.set_volume(effective_volume)
            snd.play()
            return True
        except Exception as e:
            logger.debug(
                "Sound playback skipped (audio unavailable or failed for %s): %s", sound_name, e
            )
            return False

    def get_and_clear_played_sounds(self) -> list[str]:
        """Step 8: 再生ログの取得とクリア（テスト・Result連携用）"""
        sounds = list(self.played_sounds)
        self.played_sounds.clear()
        return sounds

    # Phase 6 Step 61: 音声ファイル存在確認
    def check_audio_files(self) -> dict[str, bool]:
        """必要な音声ファイルの存在確認"""
        results = {}
        for required, fallback in REQUIRED_AUDIO_FILES.items():
            primary_exists = (self.audio_dir / required).exists()
            fallback_exists = (self.audio_dir / fallback).exists()
            results[required] = primary_exists or fallback_exists
        return results
