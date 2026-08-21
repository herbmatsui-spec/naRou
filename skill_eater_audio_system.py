"""
skill_eater_audio_system.py
Aの世界（スキル喰い） 音響エンジン・SE管理システム
Phase 1: オーディオ基盤 (Kenney Foley / Sound Effect System)
"""
from __future__ import annotations

import logging
logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Any

# Step 2: 物理パス定数の定義
AUDIO_DIR = Path(__file__).parents[0] / "assets/audio"


class SkillEaterAudioSystem:
    _instance: SkillEaterAudioSystem | None = None

    def __init__(self, audio_dir: Path | None = None, enable_real_audio: bool = True):
        self.audio_dir = audio_dir or AUDIO_DIR
        self.played_sounds: list[str] = []
        self.volume: float = 1.0
        self.is_muted: bool = False
        self.has_pygame: bool = False
        self._sound_cache: dict[str, Any] = {}

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

    def set_mute(self, muted: bool) -> None:
        """Step 71: ミュート切り替え"""
        self.is_muted = muted

    def play_sound(self, sound_name: str) -> bool:
        """
        Step 4 & Step 6: 音声再生
        - キュー (played_sounds) に常に記録
        - pygame が有効かつファイルが存在する場合は実際に再生
        """
        if self.is_muted:
            return False

        # キューに追加
        self.played_sounds.append(sound_name)

        if not self.has_pygame:
            return True

        # 実体ファイルの再生試行
        sound_path = self.audio_dir / sound_name
        if not sound_path.exists():
            return False

        try:
            import pygame

            if sound_name not in self._sound_cache:
                self._sound_cache[sound_name] = pygame.mixer.Sound(str(sound_path))
            snd = self._sound_cache[sound_name]
            snd.set_volume(self.volume)
            snd.play()
            return True
        except Exception:
            logger.exception("Unhandled exception")
            # TODO: handle exception properly
            return False

    def get_and_clear_played_sounds(self) -> list[str]:
        """Step 8: 再生ログの取得とクリア（テスト・Result連携用）"""
        sounds = list(self.played_sounds)
        self.played_sounds.clear()
        return sounds
