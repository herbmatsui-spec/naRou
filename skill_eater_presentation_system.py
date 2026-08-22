"""
skill_eater_presentation_system.py
Aの世界（スキル喰い） 演出管理エンジン (Presentation System)
提案1: Emote（画像）＋ Audio（効果音）の連動管理基盤 (Steps 1〜8)
Phase 6: 演出リソース統合・優先度制御・フォールバック (Steps 61-66)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from skill_eater_audio_system import SkillEaterAudioSystem

# Step 2: 物理パス定数の定義
EMOTE_DIR = Path(__file__).parents[0] / "assets/emote/pixel/style1"

# Phase 6 Step 62: 必要エモートファイルリスト
REQUIRED_EMOTE_FILES = {
    "emote_crown.png": "emote_star.png",
    "emote_crystal.png": "emote_star.png",
    "emote_wrench.png": "emote_star.png",
    "emote_shield.png": "emote_star.png",
    "emote_alert.png": "emote_star.png",
    "emote_cross.png": "emote_star.png",
    "emote_stars.png": "emote_star.png",
    "emote_exclamations.png": "emote_star.png",
    "emote_cash.png": "emote_star.png",
}

# Phase 6 Step 65: 演出優先度定義
EVENT_PRIORITY = {
    "rank_up": 100,  # ランクアップ
    "node_unlock": 90,  # ノード解放
    "crystal_drop": 80,  # 結晶ドロップ
    "floor_clear": 70,  # フロアクリア
    "secret_discover": 60,  # 秘密部屋発見
    "bounty_complete": 50,  # バウンティ完了
    "transition": 40,  # フロア遷移
    "step": 10,  # 歩行
    "default": 0,
}


@dataclass
class PresentationEvent:
    """Step 3: 演出イベント定義（画像、音声、メッセージ）"""

    emote_file: str | None = None
    audio_file: str | None = None
    message: str = ""
    duration_ms: int = 1000
    vr_grid_effect: bool = False
    # Phase 6 Step 65: 優先度
    priority: int = 0
    event_type: str = "default"


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

    # Phase 6 Step 63: エモートファイル存在確認・フォールバック
    def _resolve_emote_path(self, emote_file: str | None) -> str | None:
        """エモートファイルパスを解決（フォールバック対応）"""
        if emote_file is None:
            return None

        emote_path = self.emote_dir / emote_file
        if emote_path.exists():
            return emote_file

        # フォールバックチェック
        if emote_file in REQUIRED_EMOTE_FILES:
            fallback = REQUIRED_EMOTE_FILES[emote_file]
            fallback_path = self.emote_dir / fallback
            if fallback_path.exists():
                return fallback

        return None

    def add_event(
        self,
        emote_file: str | None = None,
        audio_file: str | None = None,
        message: str = "",
        duration_ms: int = 1000,
        priority: int = 0,
        event_type: str = "default",
    ) -> PresentationEvent:
        """
        Step 5 & Step 7 & Phase 6: 演出イベントの発行（優先度・フォールバック対応）
        - イベントキューに登録（優先度順）
        - 連動するオーディオを再生
        - ファイル不在時はフォールバック
        """
        # エモートファイル解決（フォールバック）
        resolved_emote = self._resolve_emote_path(emote_file)

        # 優先度自動決定（event_typeから）
        if priority == 0 and event_type != "default":
            priority = EVENT_PRIORITY.get(event_type, 0)

        evt = PresentationEvent(
            emote_file=resolved_emote,
            audio_file=audio_file,
            message=message,
            duration_ms=duration_ms,
            vr_grid_effect=False,
            priority=priority,
            event_type=event_type,
        )

        if self.is_enabled:
            # 優先度順でキューに挿入（高優先度が先頭）
            inserted = False
            for i, existing in enumerate(self.event_queue):
                if evt.priority > existing.priority:
                    self.event_queue.insert(i, evt)
                    inserted = True
                    break
            if not inserted:
                self.event_queue.append(evt)

            if audio_file:
                self.audio_system.play_sound(audio_file)

        return evt

    # Phase 6 Step 65: 優先度ベースのイベント取得
    def get_next_event(self) -> PresentationEvent | None:
        """最高優先度のイベントを取得・除去"""
        if self.event_queue:
            return self.event_queue.pop(0)
        return None

    def get_all_events_sorted(self) -> List[PresentationEvent]:
        """全イベントを優先度順で取得（キューはクリアしない）"""
        return sorted(self.event_queue, key=lambda e: e.priority, reverse=True)

    def get_and_clear_events(self) -> List[PresentationEvent]:
        """Step 6: イベントキューの取得とクリア"""
        events = list(self.event_queue)
        self.event_queue.clear()
        return events

    # Phase 6 Step 66: 動作確認用
    def check_resources(self) -> Dict[str, Any]:
        """必要なリソース（音声・エモート）の存在確認"""
        audio_check = (
            self.audio_system.check_audio_files()
            if hasattr(self.audio_system, "check_audio_files")
            else {}
        )

        emote_check = {}
        for required, fallback in REQUIRED_EMOTE_FILES.items():
            primary_exists = (self.emote_dir / required).exists()
            fallback_exists = (self.emote_dir / fallback).exists()
            emote_check[required] = primary_exists or fallback_exists

        return {
            "audio": audio_check,
            "emote": emote_check,
        }

    # =========================================================================
    # Steps 53〜59: サイバーパンク義眼 (ダイエジェティックAR) UI生成ロジック
    # =========================================================================
    def build_diegetic_ui_data(
        self,
        analyzer: Any,
        target: Any,
        registry: Any = None,
    ) -> dict[str, Any]:
        """Step 53〜58: 義眼所持状態に応じた戦闘UIデータの生成（ARオーラ＆グリッチ）"""
        has_eye = getattr(analyzer, "has_cyberpunk_eye", False)

        if not has_eye:
            # 義眼未所持: 従来のテキストUI用データ (Step 54)
            return {
                "is_diegetic": False,
                "ui_mode": "LEGACY_TEXT_UI",
                "message": "※光学義眼未装着。詳細なデータはテキストログと数値で表示されます。",
                "skills_count": len(target.skills) if hasattr(target, "skills") else 0,
            }

        # 義眼所持: ダイエジェティックARデータ (Step 55〜58)
        from skill_eater_system import SkillEaterRegistry, SkillTier

        reg = registry or SkillEaterRegistry.get_instance()

        has_concept_or_unique = False
        has_combat_fire = False
        has_defense_water = False
        has_encrypted = False
        has_trap = False

        if hasattr(target, "skills"):
            for s_id, slot in target.skills.items():
                if getattr(slot, "is_encrypted", False):
                    has_encrypted = True
                if getattr(slot, "is_trap", False):
                    has_trap = True

                s_def = reg.get_skill(s_id)
                if s_def:
                    if s_def.tier in [SkillTier.CONCEPT, SkillTier.UNIQUE, SkillTier.EATER]:
                        has_concept_or_unique = True
                    for tag in s_def.tags:
                        if tag in ["Fire", "Combat", "Dark", "Sword"]:
                            has_combat_fire = True
                        elif tag in ["Defense", "Water", "Ice", "Holy"]:
                            has_defense_water = True

        if has_concept_or_unique:
            aura_color = "#FFD700"  # 金: 神話/レア概念
            aura_label = "GOLD_CONCEPT"
        elif has_combat_fire:
            aura_color = "#FF0033"  # 赤: 高火力・攻撃特化
            aura_label = "RED_COMBAT"
        elif has_defense_water:
            aura_color = "#0066FF"  # 青: 防御・氷結
            aura_label = "BLUE_DEFENSE"
        else:
            aura_color = "#00FF66"  # 緑: コモン・補助
            aura_label = "GREEN_COMMON"

        glitch_intensity = 0.85 if has_encrypted else 0.0
        pulse_fx = (
            "RAPID_WARNING"
            if has_trap
            else ("GENTLE_GLOW" if not has_encrypted else "CYBER_GLITCH")
        )

        # Step 59: 捕食ストリーム演出用フラグ
        return {
            "is_diegetic": True,
            "ui_mode": "CYBERPUNK_AR_HUD",
            "aura_color": aura_color,
            "aura_label": aura_label,
            "glitch_intensity": glitch_intensity,
            "has_encrypted": has_encrypted,
            "has_trap": has_trap,
            "pulse_fx": pulse_fx,
            "absorption_particle_stream": True,
        }
