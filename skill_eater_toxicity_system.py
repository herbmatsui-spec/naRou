"""Skill Rejection (Toxicity) and Rest/Recovery System for Skill Eater World.

Handles skill overload accumulation, debuff state management, and safehouse rest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SafehouseLocation:
    """A hidden sanctuary in the Slums where the player can rest and detoxify."""

    safehouse_id: str
    name: str
    recovery_rate: int = 100
    has_medical_station: bool = False


@dataclass
class SkillToxicityState:
    """Tracks current skill toxicity and debuff penalties."""

    current_toxicity: int = 0
    max_toxicity: int = 100
    debuff_threshold: int = 80
    is_overloaded: bool = False
    movement_speed_penalty: float = 0.0
    atk_multiplier: float = 1.0


class SkillToxicityManager:
    """Manages accumulation, threshold evaluation, and recovery of skill toxicity."""

    def __init__(self) -> None:
        self.state = SkillToxicityState()

    def evaluate_debuffs(self) -> None:
        """Applies movement speed reduction (higher stealth detection) and halved ATK if over 80%."""
        if self.state.current_toxicity >= self.state.debuff_threshold:
            self.state.is_overloaded = True
            self.state.movement_speed_penalty = 0.5  # 50% slower, stealth detection range doubles
            self.state.atk_multiplier = 0.5          # 50% damage reduction
        else:
            self.state.is_overloaded = False
            self.state.movement_speed_penalty = 0.0
            self.state.atk_multiplier = 1.0

    def add_toxicity(self, amount: int, action_name: str = "") -> Dict[str, Any]:
        """Adds toxicity from skill synthesis, extraction, or overload use."""
        self.state.current_toxicity = min(self.state.max_toxicity, self.state.current_toxicity + amount)
        self.evaluate_debuffs()
        return {
            "current_toxicity": self.state.current_toxicity,
            "max_toxicity": self.state.max_toxicity,
            "is_overloaded": self.state.is_overloaded,
            "action": action_name,
            "message": f"【生体拒絶反応】+{amount}% 蓄積（現在: {self.state.current_toxicity}%）",
        }

    def render_toxicity_gauge_ui(self) -> Dict[str, Any]:
        """Renders HUD toxicity gauge with color shifting (GREEN -> YELLOW -> RED)."""
        tox = self.state.current_toxicity
        if tox >= 80:
            color = "RED_FLASHING"
            status_text = "⚠️ 拒絶反応限界（運動機能半減・筋力低下）"
        elif tox >= 40:
            color = "YELLOW_WARN"
            status_text = "注意：スキル生体負荷蓄積中"
        else:
            color = "GREEN_SAFE"
            status_text = "安定"

        return {
            "ui_name": "SKILL_TOXICITY_METER",
            "percent": tox,
            "color": color,
            "status_text": status_text,
            "is_overloaded": self.state.is_overloaded,
        }

    def rest_at_safehouse(self, safehouse: SafehouseLocation) -> Dict[str, Any]:
        """Rests at a safehouse, resetting toxicity and removing debuffs."""
        recovered = min(self.state.current_toxicity, safehouse.recovery_rate)
        self.state.current_toxicity -= recovered
        self.evaluate_debuffs()
        return {
            "success": True,
            "recovered_toxicity": recovered,
            "current_toxicity": self.state.current_toxicity,
            "is_overloaded": False,
            "message": f"【{safehouse.name}】で休息をとった。スキル拒絶反応が完全に解消された！",
        }

    def get_rest_presentation_fx(self) -> Dict[str, Any]:
        """Provides black screen transition and healing sound configs for rest."""
        return {
            "sound": "se_safehouse_rest_heal.ogg",
            "screen_effect": "FADE_TO_BLACK_CALM",
            "duration_ms": 1500,
        }

    def validate_skill_slot_toxicity_cost(self, equipped_skill_costs: List[int]) -> Dict[str, Any]:
        """Validates that total active skill equip load does not exceed baseline toxicity limit."""
        total_load = sum(equipped_skill_costs)
        max_load = 50
        can_equip = total_load <= max_load
        return {
            "can_equip": can_equip,
            "total_load": total_load,
            "max_load": max_load,
            "error": "TOXICITY_LOAD_EXCEEDED" if not can_equip else None,
        }
