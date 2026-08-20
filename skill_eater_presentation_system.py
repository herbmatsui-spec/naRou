"""
skill_eater_presentation_system.py
Aの世界（スキル喰い） 演出管理エンジン (Presentation System)
提案1: Emote（画像）＋ Audio（効果音）の連動管理基盤 (Steps 1〜8)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skill_eater_audio_system import SkillEaterAudioSystem

# Step 2: 物理パス定数の定義
EMOTE_DIR = Path(__file__).parents[0] / "assets/emote/pixel/style1"


@dataclass
class PresentationEvent:
    """Step 3: 演出イベント定義（画像、音声、メッセージ）"""

    emote_file: str | None = None
    audio_file: str | None = None
    message: str = ""
    duration_ms: int = 1000


class SkillEaterPresentationSystem:
    _instance: SkillEaterPresentationSystem | None = None

    def __init__(
        self,
        emote_dir: Path | None = None,
        audio_system: SkillEaterAudioSystem | None = None,
        is_mock_only: bool = False,
    ):
        self.emote_dir = emote_dir or EMOTE_DIR
        self.audio_system = audio_system or SkillEaterAudioSystem.get_instance()
        self.event_queue: list[PresentationEvent] = []
        self.is_mock_only = is_mock_only
        self.is_enabled = True

    @classmethod
    def get_instance(cls) -> SkillEaterPresentationSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def set_enabled(self, enabled: bool):
        """Step 71: 演出システムの有効/無効切り替え"""
        self.is_enabled = enabled
        if not enabled:
            self.audio_system.set_mute(True)
        else:
            self.audio_system.set_mute(False)

    def add_event(
        self,
        emote_file: str | None = None,
        audio_file: str | None = None,
        message: str = "",
        duration_ms: int = 1000,
    ) -> PresentationEvent:
        """
        Step 5 & Step 7: 演出イベントの発行
        - イベントキューに登録
        - 連動するオーディオを再生
        """
        evt = PresentationEvent(
            emote_file=emote_file,
            audio_file=audio_file,
            message=message,
            duration_ms=duration_ms,
        )

        if self.is_enabled:
            self.event_queue.append(evt)
            if audio_file:
                self.audio_system.play_sound(audio_file)

        return evt

    def get_and_clear_events(self) -> list[PresentationEvent]:
        """Step 6: イベントキューの取得とクリア"""
        events = list(self.event_queue)
        self.event_queue.clear()
        return events
