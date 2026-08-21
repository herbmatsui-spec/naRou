"""Midas Hound Pursuer and Stealth Survival System for Skill Eater World.

Handles relentless high-level pursuer encounters, cone of sight, hiding spots, and stealth evading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MidasHoundPursuer:
    """An overpowered Level 20 Midas tracker hunting escaped dismissals in the slums."""

    hound_id: str = "HOUND_UNIT_09"
    name: str = "ミダス商会 追跡魔導猟犬（ハウンド）"
    level: int = 20
    hp: int = 2500
    atk: int = 180
    pos: Tuple[int, int] = (5, 5)
    patrol_points: List[Tuple[int, int]] = field(default_factory=lambda: [(5, 5), (5, 2), (2, 2), (2, 5)])
    patrol_index: int = 0
    vision_range: int = 2
    alert_level: str = "NORMAL"  # 'NORMAL', 'SUSPICIOUS', 'COMBAT'
    weakness_flaw: str = "魔導首輪のエネルギー充填バルブ"


class HoundSpawnManager:
    """Manages periodic hound encounters and dynamic alert levels."""

    def __init__(self) -> None:
        self.hound = MidasHoundPursuer()
        self.is_spawned: bool = False
        self.hiding_spots: List[Tuple[int, int]] = [(1, 1), (8, 2)]
        self.player_is_hidden: bool = False

    def spawn_hound(self, spawn_pos: Tuple[int, int] = (5, 5)) -> Dict[str, Any]:
        """Spawns the terrifying Midas Hound into the Slum sector."""
        self.hound.pos = spawn_pos
        self.is_spawned = True
        self.hound.alert_level = "NORMAL"
        return {
            "action": "HOUND_SPAWNED",
            "name": self.hound.name,
            "pos": self.hound.pos,
            "message": "【警報】ミダス商会の《追跡魔導猟犬》がスラムに投入された！身を隠せ！",
        }

    def update_hound_patrol_and_detect(self, player_pos: Tuple[int, int], is_running: bool = False) -> Dict[str, Any]:
        """Advances hound patrol and checks player detection (sight + audio hearing)."""
        if not self.is_spawned:
            return {"detected": False}

        # Patrol advance
        if self.hound.alert_level == "NORMAL":
            self.hound.patrol_index = (self.hound.patrol_index + 1) % len(self.hound.patrol_points)
            self.hound.pos = self.hound.patrol_points[self.hound.patrol_index]

        # Calculate distance
        dist = abs(self.hound.pos[0] - player_pos[0]) + abs(self.hound.pos[1] - player_pos[1])

        # Detection check
        if self.player_is_hidden:
            return {"detected": False, "alert_level": "NORMAL", "hound_pos": self.hound.pos}

        # Hearing detection (if player is running near)
        if is_running and dist <= 3:
            self.hound.alert_level = "SUSPICIOUS"
            return {"detected": True, "alert_level": "SUSPICIOUS", "reason": "足音を探知された！", "hound_pos": self.hound.pos}

        # Direct sight detection
        if dist <= self.hound.vision_range:
            self.hound.alert_level = "COMBAT"
            return {"detected": True, "alert_level": "COMBAT", "reason": "魔導猟犬に捕捉された！", "hound_pos": self.hound.pos}

        return {"detected": False, "alert_level": self.hound.alert_level, "hound_pos": self.hound.pos}

    def highlight_hound_routes(self) -> Dict[str, Any]:
        """Provides Analysis skill visual overlay of Hound patrol paths and danger cones."""
        return {
            "hound_pos": self.hound.pos,
            "patrol_line": self.hound.patrol_points,
            "danger_radius": self.hound.vision_range,
            "hearing_radius": 3,
            "weakness": self.hound.weakness_flaw,
            "overlay_color": "RED_SCAN_CONE",
        }

    def trigger_hound_chase_event(self) -> Dict[str, Any]:
        """Triggers tense chase escape sequence when spotted by the hound."""
        return {
            "action": "CHASE_SEQUENCE_START",
            "bgm": "bgm_chase_hound_pursuit.ogg",
            "warning": "【緊急事態】魔導猟犬が突進中！隠れ場所に飛び込むか、環境トラップへ誘導せよ！",
            "countdown_seconds": 10,
        }

    def render_hound_alert_indicator(self) -> Dict[str, str]:
        """Provides dynamic HUD indicator icon over hound (? / ! / !!)."""
        if self.hound.alert_level == "COMBAT":
            return {"icon": "‼️", "color": "RED_ALERT", "status": "追跡突進中"}
        elif self.hound.alert_level == "SUSPICIOUS":
            return {"icon": "❓", "color": "YELLOW_CAUTION", "status": "警戒索敵中"}
        return {"icon": "", "color": "GREEN", "status": "巡回中"}

    def interact_with_hiding_spot(self, player_pos: Tuple[int, int]) -> Dict[str, Any]:
        """Player hides inside a dumpster or locker, evading the hound."""
        if player_pos in self.hiding_spots:
            self.player_is_hidden = True
            self.hound.alert_level = "NORMAL"
            return {
                "success": True,
                "hidden": True,
                "message": "ゴミ箱の中に身を潜めた……魔導猟犬はプレイヤーを見失った！",
            }
        return {"success": False, "error": "NOT_A_HIDING_SPOT"}

    def defeat_hound_with_trap(self) -> Dict[str, Any]:
        """Defeats the Hound using an environmental trap, yielding a complete combat skill."""
        self.hound.hp = 0
        self.is_spawned = False
        return {
            "success": True,
            "reward_skill": "SKILL_SHADOW_STEP_COMPLETE",
            "skill_name": "完全スキル《影渡り・初歩》",
            "message": "【大金星！】環境トラップで魔導猟犬を粉砕！完全なスキル《影渡り・初歩》を奪取した！",
        }
