"""Skill Eater Crafting and Patchwork Synthesis System.

Handles SkillScraps, temporary/unstable patchwork skill synthesis,
and Husk Forge for creating Puppet Units.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from naRou.ecs.components.components import HuskComponent, PuppetUnitComponent
from skill_eater_husk_forge import PuppetForgeSystem


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


@dataclass
class HuskForgeUI:
    """UI layout representing the Husk Forge with husk selection and unit preview."""

    selected_husk_index: int = -1
    protocol_rank: int = 0
    preview_unit: Optional[Dict[str, Any]] = None
    show_confirmation: bool = False

    def render(self) -> Dict[str, Any]:
        return {
            "ui_name": "HUSK_FORGE",
            "selected_husk": self.selected_husk_index,
            "protocol_rank": self.protocol_rank,
            "preview": self.preview_unit,
            "show_confirmation": self.show_confirmation,
            "warning": "【傀儡鍛冶】注入スキルとプロトコルランクでユニット性能が決まります",
        }


@dataclass
class CreatedUnitInfo:
    """Information about a created puppet unit."""

    unit_id: str
    role: str
    hp: int
    max_hp: int
    injected_skills: List[str]
    injected_codes: List[str]
    rebellion_risk: float
    effective_power: float


class HuskForgeEngine:
    """Engine for creating puppet units from husks at the forge."""

    def __init__(self) -> None:
        self.forge = PuppetForgeSystem()
        self.created_units: List[CreatedUnitInfo] = []

    def preview_unit(self, husk: HuskComponent, protocol_rank: int = 0) -> Dict[str, Any]:
        """Preview what unit would be created from a husk."""
        role = self.forge.role_of(husk)
        control_load = self.forge.calc_control_load(husk)
        rebellion_risk = self.forge.rebellion_risk(husk)
        effective_power = self.forge.effective_power(husk, protocol_rank)
        base_hp = int(effective_power * 10)

        return {
            "role": role,
            "hp": base_hp,
            "max_hp": base_hp,
            "injected_skills": husk.injected_skills.copy(),
            "injected_codes": husk.injected_codes.copy(),
            "control_load": control_load,
            "rebellion_risk": rebellion_risk,
            "effective_power": effective_power,
            "protocol_rank": protocol_rank,
        }

    def create_unit(
        self,
        husk: HuskComponent,
        protocol_rank: int = 0,
        player: Any = None,
    ) -> Dict[str, Any]:
        """Create a puppet unit from a husk."""
        try:
            unit = self.forge.create_unit(husk, protocol_rank, player)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        # Create info object for display
        unit_info = CreatedUnitInfo(
            unit_id=unit.unit_id,
            role=unit.role,
            hp=unit.hp,
            max_hp=unit.max_hp,
            injected_skills=unit.injected_skills.copy(),
            injected_codes=unit.injected_codes.copy(),
            rebellion_risk=self.forge.rebellion_risk(husk),
            effective_power=self.forge.effective_power(husk, protocol_rank),
        )
        self.created_units.append(unit_info)

        return {
            "success": True,
            "unit": unit,
            "unit_info": unit_info,
            "message": f"【傀儡鍛冶完了】{unit.role} 《{unit.unit_id}》 を創造！ HP: {unit.hp}, 反逆リスク: {unit_info.rebellion_risk:.2f}",
        }

    def get_created_units_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all created units."""
        return [
            {
                "unit_id": u.unit_id,
                "role": u.role,
                "hp": f"{u.hp}/{u.max_hp}",
                "skills": u.injected_skills,
                "codes": u.injected_codes,
                "rebellion_risk": f"{u.rebellion_risk:.2f}",
                "effective_power": f"{u.effective_power:.2f}",
            }
            for u in self.created_units
        ]


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


@dataclass
class SkillEaterCraftingUI:
    """Unified crafting UI with tabs for Patchwork Crafting and Husk Forge."""

    active_tab: str = "patchwork"  # "patchwork" or "forge"
    patchwork_ui: PatchworkCraftingUI = field(default_factory=PatchworkCraftingUI)
    forge_ui: HuskForgeUI = field(default_factory=HuskForgeUI)

    def render(self) -> Dict[str, Any]:
        if self.active_tab == "patchwork":
            return self.patchwork_ui.render()
        else:
            return self.forge_ui.render()

    def switch_tab(self, tab: str) -> None:
        """Switch between crafting tabs."""
        if tab in ("patchwork", "forge"):
            self.active_tab = tab


class SkillEaterCraftingSystem:
    """Unified crafting system combining patchwork synthesis and husk forge."""

    def __init__(self) -> None:
        self.patchwork_engine = PatchworkCraftingEngine()
        self.forge_engine = HuskForgeEngine()
        self.ui = SkillEaterCraftingUI()

    def get_patchwork_ui(self) -> Dict[str, Any]:
        """Get patchwork crafting UI."""
        self.ui.switch_tab("patchwork")
        return self.ui.render()

    def get_forge_ui(self, husks: List[HuskComponent]) -> Dict[str, Any]:
        """Get husk forge UI with available husks."""
        self.ui.switch_tab("forge")
        ui_data = self.ui.render()
        ui_data["available_husks"] = [
            {
                "index": i,
                "husk_id": h.husk_id,
                "source_monster": h.source_monster,
                "tier": h.tier,
                "slots": h.slots,
                "injected_skills": h.injected_skills,
                "injected_codes": h.injected_codes,
                "loyalty": h.loyalty,
            }
            for i, h in enumerate(husks)
        ]
        return ui_data

    def preview_forge_unit(self, husk: HuskComponent, protocol_rank: int = 0) -> Dict[str, Any]:
        """Preview unit creation from husk."""
        preview = self.forge_engine.preview_unit(husk, protocol_rank)
        self.ui.forge_ui.preview_unit = preview
        self.ui.forge_ui.protocol_rank = protocol_rank
        return preview

    def confirm_forge_unit(self, husk: HuskComponent, protocol_rank: int = 0, player: Any = None) -> Dict[str, Any]:
        """Confirm and create unit from husk."""
        result = self.forge_engine.create_unit(husk, protocol_rank, player)
        if result["success"]:
            self.ui.forge_ui.show_confirmation = False
            self.ui.forge_ui.preview_unit = None
        return result

    def get_created_units_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all created puppet units."""
        return self.forge_engine.get_created_units_summary()
