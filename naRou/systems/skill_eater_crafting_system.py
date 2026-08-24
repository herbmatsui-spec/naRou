"""Skill Eater Crafting and Patchwork Synthesis System.

Handles SkillScraps and temporary/unstable patchwork skill synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SkillScrap:
    """A fragment of a skill harvested from enemies or environment."""

    scrap_id: str
    name: str
    element: str  # 'FIRE', 'FORCE', 'AGILITY', 'GUARD'
    tier: int = 1
    description: str = ""


@dataclass
class PatchworkSkill:
    """An unstable patchwork skill with limited durability."""

    skill_id: str
    name: str
    effect_type: str
    power: int
    max_durability: int
    current_durability: int
    is_broken: bool = False


@dataclass
class PatchworkCraftingUI:
    """UI layout representing the patchwork crafting table with slots and preview."""

    slots: List[Optional[str]] = field(default_factory=lambda: [None, None, None])
    preview_skill_name: Optional[str] = None
    instability_warning: bool = True

    def render(self) -> Dict[str, Any]:
        return {
            "ui_name": "PATCHWORK_CRAFTING_TABLE",
            "slots": self.slots,
            "preview": self.preview_skill_name or "破片を2つ以上セットしてください",
            "warning": "【不安定合成】生成されるスキルには使用回数制限があります",
        }


class PatchworkCraftingEngine:
    """Engine for stitching together temporary, unstable patchwork skills."""

    def __init__(self) -> None:
        self.scrap_inventory: List[SkillScrap] = []
        self.active_skills: List[PatchworkSkill] = []

    def synthesize_patchwork_skill(self, scrap_ids: List[str]) -> Dict[str, Any]:
        """Stitches together multiple scraps into an unstable patchwork skill."""
        if len(scrap_ids) < 2:
            return {"success": False, "error": "REQUIRES_AT_LEAST_2_SCRAPS"}

        # Combine names and elements
        combo_name = "継ぎ接ぎスキル《"
        if "SCRAP_BEAST_FANG" in scrap_ids and "SCRAP_AGILITY_FRAGMENT" in scrap_ids:
            combo_name += "瞬突・牙咬み"
            skill_effect = {"type": "QUICK_ATTACK", "power": 45, "durability": 3}
        elif "SCRAP_IRON_GUARD" in scrap_ids:
            combo_name += "応急鉄壁"
            skill_effect = {"type": "SHIELD", "power": 50, "durability": 2}
        else:
            combo_name += "混沌の打撃"
            skill_effect = {"type": "CHAOS_STRIKE", "power": 30, "durability": 2}
        combo_name += "》"

        patchwork_skill = {
            "skill_id": f"PATCHWORK_{hash(tuple(scrap_ids)) & 0xFFFF:04X}",
            "name": combo_name,
            "effect": skill_effect,
            "max_durability": skill_effect["durability"],
            "current_durability": skill_effect["durability"],
            "is_unstable": True,
        }
        return {
            "success": True,
            "skill": patchwork_skill,
            "message": f"合成成功！【{combo_name}】を生成（耐久度: {skill_effect['durability']}回）",
        }

    def use_patchwork_skill(self, skill: PatchworkSkill) -> Dict[str, Any]:
        """Uses a patchwork skill, decreasing durability and breaking if 0."""
        if skill.is_broken or skill.current_durability <= 0:
            return {"success": False, "error": "SKILL_ALREADY_BROKEN"}

        skill.current_durability -= 1
        is_shattered = skill.current_durability <= 0
        if is_shattered:
            skill.is_broken = True

        return {
            "success": True,
            "skill_name": skill.name,
            "power": skill.power,
            "remaining_durability": skill.current_durability,
            "is_shattered": is_shattered,
            "message": f"【{skill.name}】を発動！（残り耐久: {skill.current_durability}）"
            + ("\n⚠️ スキル構造が崩壊・消滅した！" if is_shattered else ""),
        }

    def generate_crafting_toast(self, skill: PatchworkSkill) -> Dict[str, Any]:
        """Generates visual and sound toast feedback upon successful craft."""
        return {
            "action": "SHOW_CRAFT_TOAST",
            "title": "【継ぎ接ぎ合成成功】",
            "skill_name": skill.name,
            "durability": skill.current_durability,
            "sound": "se_patchwork_craft_success.ogg",
            "particles": "SPARKLE_GLITCH_YELLOW",
        }
