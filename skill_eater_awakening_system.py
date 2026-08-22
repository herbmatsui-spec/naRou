"""Skill Eater Awakening and Mid-Boss Climax System for Skill Eater World.

Handles the dramatic awakening of the true devour ability during a near-death mid-boss fight.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Phase1MidBoss:
    """The Mid-Boss: Midas Elite Enforcer cornering the player in the Slum depths."""

    boss_id: str = "MIDAS_ELITE_ENFORCER"
    name: str = "ミダス商会 執行官ヴォルクス"
    hp: int = 4000
    max_hp: int = 4000
    atk: int = 220
    unique_skill: str = "ユニークスキル《重圧魔導砲》"
    is_defeated: bool = False


class DevourAwakeningManager:
    """Manages the awakening cutscene and true 'Devour' skill execution."""

    def __init__(self) -> None:
        self.boss = Phase1MidBoss()
        self.devour_unlocked: bool = False
        self.is_time_stopped: bool = False
        self.phase1_completed: bool = False

    def check_near_death_time_stop(self, player_hp: int, player_max_hp: int) -> Dict[str, Any]:
        """Triggers time-stop and dramatic awakening when player HP falls below 10%."""
        if player_hp <= int(player_max_hp * 0.1) and not self.devour_unlocked:
            self.is_time_stopped = True
            return {
                "triggered": True,
                "action": "TIME_STOP_RED_SCREEN",
                "message": "【警告】致命傷を検知……心拍停止直前。世界の因果律が一時停止した。",
            }
        return {"triggered": False}

    def trigger_meta_system_error_glitch(self) -> List[Dict[str, Any]]:
        """Generates the dramatic red screen glitch text frames showing soul restructuring."""
        return [
            {"frame": 1, "text": "CRITICAL_ERROR: 生体認証プロトコル破綻", "color": "RED"},
            {
                "frame": 2,
                "text": "《解析》スキルの根源定義がオーバーフローを起こしています",
                "color": "RED_FLASH",
            },
            {
                "frame": 3,
                "text": "世界法則の強制書き換え：【スキルを観る者】から【スキルを喰らう者】へ変異",
                "color": "WHITE_BLINDING",
            },
        ]

    def unlock_devour_command(self) -> Dict[str, Any]:
        """Forces the 《喰らう（Devour）》 command onto the battle menu in crimson flames."""
        self.devour_unlocked = True
        return {
            "action": "FORCE_COMMAND_UNLOCK",
            "command": "DEVOUR",
            "label": "《暴食：スキル喰らい》",
            "style": "BURNING_CRIMSON",
            "description": "対象のスキル構造を強制分解し、魂ごと喰らい尽くす（必中・即死）",
        }

    def execute_devour_kill(self) -> Dict[str, Any]:
        """Executes the newly awakened Devour attack, instantly defeating the Mid-Boss."""
        if not self.devour_unlocked:
            return {"success": False, "error": "DEVOUR_NOT_UNLOCKED"}
        self.boss.hp = 0
        self.boss.is_defeated = True
        self.is_time_stopped = False
        return {
            "success": True,
            "damage": 99999,
            "target_defeated": True,
            "stolen_skill": self.boss.unique_skill,
            "message": f"【スキル喰らい発動】執行官ヴォルクスの【{self.boss.unique_skill}】を強奪し、魂ごと喰らい尽くした！",
        }

    def get_awakening_fanfare_presentation(self) -> Dict[str, Any]:
        """Provides victory fanfare and visual feast for the Devour awakening."""
        return {
            "action": "FANFARE_AWAKENING",
            "sound": "bgm_glitch_awakening_fanfare.ogg",
            "screen_effect": "RED_GOLD_BURST",
            "title": "【真の能力覚醒：スキル喰い】",
            "subtitle": "〜スキル資本主義を崩壊させる捕食者が誕生した〜",
        }

    def complete_phase1_transition(
        self, world_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Transitions WorldState from Phase 1 to Phase 2 (Template Destruction)."""
        self.phase1_completed = True
        state = world_state or {}
        state["world_id"] = "skill_eater"
        state["template_id"] = "skill_capitalism"
        state["phase"] = "Phase 2: テンプレート破壊 (Lv21-50)"
        state["phase_index"] = 2
        state["phase1_completed"] = True
        return {
            "success": True,
            "next_phase": state["phase"],
            "message": "フェーズ1【基盤構築】完了！フェーズ2【テンプレート破壊】へ移行します。",
        }

    def export_phase1_save_state(
        self, save_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Persists Phase 1 completion, unlocked devour power, and stolen skills into save data."""
        save = save_dict if save_dict is not None else {}
        save["phase1_completed"] = True
        save["devour_unlocked"] = self.devour_unlocked
        save["current_phase"] = 2
        if self.boss.is_defeated:
            acquired = save.get("acquired_skills", [])
            if self.boss.unique_skill not in acquired:
                acquired.append(self.boss.unique_skill)
            save["acquired_skills"] = acquired
        return {
            "success": True,
            "save_data": save,
        }
