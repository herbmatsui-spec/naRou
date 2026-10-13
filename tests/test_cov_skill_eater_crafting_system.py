"""Coverage tests for skill_eater_crafting_system (patchwork + husk forge)."""

from __future__ import annotations

import pytest

from ecs.components.components import HuskComponent
from skill_eater_crafting_system import (
    CreatedUnitInfo,
    HuskForgeEngine,
    HuskForgeUI,
    PatchworkCraftingEngine,
    PatchworkCraftingUI,
    PatchworkSkill,
    SkillEaterCraftingSystem,
    SkillEaterCraftingUI,
    SkillScrap,
)


def make_husk(**overrides) -> HuskComponent:
    params = dict(husk_id="husk_001", source_monster="orc", slots=4)
    params.update(overrides)
    return HuskComponent(**params)


@pytest.fixture
def engine() -> PatchworkCraftingEngine:
    return PatchworkCraftingEngine()


class TestSkillScrap:
    def test_defaults(self) -> None:
        scrap = SkillScrap(scrap_id="S1", name="牙", element="FIRE")
        assert scrap.tier == 1
        assert scrap.description == ""


class TestPatchworkCraftingUI:
    def test_render_default(self) -> None:
        ui = PatchworkCraftingUI()
        data = ui.render()
        assert data["ui_name"] == "PATCHWORK_CRAFTING_TABLE"
        assert data["slots"] == [None, None, None]
        assert "破片" in data["preview"]
        assert "使用回数制限" in data["warning"]

    def test_render_with_preview(self) -> None:
        ui = PatchworkCraftingUI(slots=["SCRAP_A", "SCRAP_B", None], preview_skill_name="瞬突・牙咬み")
        data = ui.render()
        assert data["preview"] == "瞬突・牙咬み"


class TestHuskForgeUI:
    def test_render_default(self) -> None:
        ui = HuskForgeUI()
        data = ui.render()
        assert data["ui_name"] == "HUSK_FORGE"
        assert data["selected_husk"] == -1
        assert data["preview"] is None
        assert data["show_confirmation"] is False


class TestPatchworkSynthesis:
    def test_requires_two_scraps(self, engine: PatchworkCraftingEngine) -> None:
        res = engine.synthesize_patchwork_skill(["SCRAP_A"])
        assert res["success"] is False
        assert res["error"] == "REQUIRES_AT_LEAST_2_SCRAPS"

    def test_combination_beast_fang_agility(self, engine: PatchworkCraftingEngine) -> None:
        res = engine.synthesize_patchwork_skill(["SCRAP_BEAST_FANG", "SCRAP_AGILITY_FRAGMENT"])
        assert res["success"] is True
        assert res["skill"]["name"] == "継ぎ接ぎスキル《瞬突・牙咬み》"
        assert res["skill"]["effect"]["type"] == "QUICK_ATTACK"
        assert res["skill"]["effect"]["power"] == 45
        assert res["skill"]["current_durability"] == 3

    def test_combination_iron_guard(self, engine: PatchworkCraftingEngine) -> None:
        res = engine.synthesize_patchwork_skill(["SCRAP_A", "SCRAP_IRON_GUARD"])
        assert res["success"] is True
        assert res["skill"]["name"] == "継ぎ接ぎスキル《応急鉄壁》"
        assert res["skill"]["effect"]["type"] == "SHIELD"
        assert res["skill"]["current_durability"] == 2

    def test_default_chaos_strike(self, engine: PatchworkCraftingEngine) -> None:
        res = engine.synthesize_patchwork_skill(["SCRAP_X", "SCRAP_Y"])
        assert res["success"] is True
        assert res["skill"]["name"] == "継ぎ接ぎスキル《混沌の打撃》"
        assert res["skill"]["effect"]["type"] == "CHAOS_STRIKE"
        assert res["skill"]["is_unstable"] is True

    def test_skill_id_is_hex_fingerprint(self, engine: PatchworkCraftingEngine) -> None:
        res = engine.synthesize_patchwork_skill(["SCRAP_X", "SCRAP_Y"])
        skill_id = res["skill"]["skill_id"]
        assert skill_id.startswith("PATCHWORK_")
        assert len(skill_id) == len("PATCHWORK_XXXX")

    def test_message_contains_durability(self, engine: PatchworkCraftingEngine) -> None:
        res = engine.synthesize_patchwork_skill(["SCRAP_A", "SCRAP_IRON_GUARD"])
        assert "耐久度: 2回" in res["message"]


class TestPatchworkUsage:
    def test_use_decrements_durability(self, engine: PatchworkCraftingEngine) -> None:
        skill = PatchworkSkill(
            skill_id="P1", name="応急鉄壁", effect_type="SHIELD",
            power=50, max_durability=2, current_durability=2,
        )
        res = engine.use_patchwork_skill(skill)
        assert res["success"] is True
        assert res["remaining_durability"] == 1
        assert res["is_shattered"] is False
        assert skill.is_broken is False

    def test_use_shatters_at_zero(self, engine: PatchworkCraftingEngine) -> None:
        skill = PatchworkSkill(
            skill_id="P1", name="応急鉄壁", effect_type="SHIELD",
            power=50, max_durability=1, current_durability=1,
        )
        res = engine.use_patchwork_skill(skill)
        assert res["is_shattered"] is True
        assert skill.is_broken is True
        assert "崩壊" in res["message"]

    def test_use_broken_skill_fails(self, engine: PatchworkCraftingEngine) -> None:
        skill = PatchworkSkill(
            skill_id="P1", name="x", effect_type="S",
            power=1, max_durability=1, current_durability=0, is_broken=True,
        )
        res = engine.use_patchwork_skill(skill)
        assert res["success"] is False
        assert res["error"] == "SKILL_ALREADY_BROKEN"

    def test_use_zero_durability_not_broken_flag(self, engine: PatchworkCraftingEngine) -> None:
        skill = PatchworkSkill(
            skill_id="P1", name="x", effect_type="S",
            power=1, max_durability=1, current_durability=0, is_broken=False,
        )
        res = engine.use_patchwork_skill(skill)
        assert res["success"] is False
        assert res["error"] == "SKILL_ALREADY_BROKEN"

    def test_crafting_toast(self, engine: PatchworkCraftingEngine) -> None:
        skill = PatchworkSkill(
            skill_id="P1", name="応急鉄壁", effect_type="SHIELD",
            power=50, max_durability=2, current_durability=2,
        )
        toast = engine.generate_crafting_toast(skill)
        assert toast["action"] == "SHOW_CRAFT_TOAST"
        assert toast["skill_name"] == "応急鉄壁"
        assert toast["durability"] == 2
        assert toast["sound"] == "se_patchwork_craft_success.ogg"


class TestHuskForgeEngine:
    def test_forge_value_error_returns_error_dict(self) -> None:
        eng = HuskForgeEngine()

        class FailingForge:
            def create_unit(self, husk, protocol_rank=0, player=None):
                raise ValueError("slots full")

        eng.forge = FailingForge()
        res = eng.create_unit(make_husk())
        assert res == {"success": False, "error": "slots full"}
        assert eng.created_units == []

    def test_preview_unit_empty_husk(self) -> None:
        eng = HuskForgeEngine()
        husk = make_husk(loyalty=0)
        preview = eng.preview_unit(husk, protocol_rank=0)
        assert preview["role"] == "escort"
        assert preview["hp"] == 10
        assert preview["max_hp"] == 10
        assert preview["injected_skills"] == []
        assert preview["control_load"] == 0
        assert preview["rebellion_risk"] == 0.0
        assert preview["protocol_rank"] == 0

    def test_preview_with_skills_and_loyalty(self) -> None:
        eng = HuskForgeEngine()
        husk = make_husk(loyalty=5)
        husk.injected_skills = ["fire_bolt", "heal"]
        husk.injected_codes = ["CODE_1"]
        preview = eng.preview_unit(husk, protocol_rank=2)
        # control load = 2*10 + 1*5 = 25; risk = max(0, (25 - 10) / 100) = 0.15
        assert preview["control_load"] == 25
        assert abs(preview["rebellion_risk"] - 0.15) < 1e-9
        assert preview["injected_skills"] == ["fire_bolt", "heal"]

    def test_preview_does_not_mutate_husk(self) -> None:
        eng = HuskForgeEngine()
        husk = make_husk()
        husk.injected_skills = ["slash"]
        eng.preview_unit(husk)
        assert husk.injected_skills == ["slash"]

    def test_create_unit_success(self) -> None:
        eng = HuskForgeEngine()
        husk = make_husk()
        husk.injected_skills = ["slash"]
        res = eng.create_unit(husk, protocol_rank=0)
        assert res["success"] is True
        unit = res["unit"]
        assert unit.unit_id == "unit_husk_001"
        assert unit.husk_ref == "husk_001"
        assert unit.role == "escort"
        assert unit.injected_skills == ["slash"]
        assert res["unit_info"].unit_id == "unit_husk_001"
        assert len(eng.created_units) == 1

    def test_create_unit_defense_skills_make_turret(self) -> None:
        eng = HuskForgeEngine()
        husk = make_husk()
        husk.injected_skills = ["heal", "shield"]
        res = eng.create_unit(husk)
        assert res["unit"].role == "turret"

    def test_create_unit_movement_skills_make_drone(self) -> None:
        eng = HuskForgeEngine()
        husk = make_husk()
        husk.injected_skills = ["dash", "teleport"]
        res = eng.create_unit(husk)
        assert res["unit"].role == "drone"

    def test_create_unit_summary_format(self) -> None:
        eng = HuskForgeEngine()
        husk = make_husk()
        res = eng.create_unit(husk)
        assert res["success"] is True
        summary = eng.get_created_units_summary()
        assert len(summary) == 1
        entry = summary[0]
        assert entry["unit_id"] == "unit_husk_001"
        assert entry["hp"] == f"{entry['hp'].split('/')[0]}/10" or entry["hp"].endswith("/10")
        assert entry["skills"] == []
        assert entry["rebellion_risk"] == "0.00"

    def test_created_units_info_fields(self) -> None:
        info = CreatedUnitInfo(
            unit_id="u1", role="escort", hp=10, max_hp=10,
            injected_skills=["s"], injected_codes=["c"],
            rebellion_risk=0.5, effective_power=0.5,
        )
        assert info.rebellion_risk == 0.5


class TestCraftingSystemFacade:
    def test_default_tab_is_patchwork(self) -> None:
        sysm = SkillEaterCraftingSystem()
        assert sysm.ui.active_tab == "patchwork"

    def test_get_patchwork_ui_switches_tab(self) -> None:
        sysm = SkillEaterCraftingSystem()
        ui_data = sysm.get_patchwork_ui()
        assert ui_data["ui_name"] == "PATCHWORK_CRAFTING_TABLE"

    def test_get_forge_ui_lists_husks(self) -> None:
        sysm = SkillEaterCraftingSystem()
        husk = make_husk(tier=3, loyalty=2)
        husk.injected_skills = ["fire_bolt"]
        ui_data = sysm.get_forge_ui([husk])
        assert ui_data["ui_name"] == "HUSK_FORGE"
        assert ui_data["available_husks"][0] == {
            "index": 0,
            "husk_id": "husk_001",
            "source_monster": "orc",
            "tier": 3,
            "slots": 4,
            "injected_skills": ["fire_bolt"],
            "injected_codes": [],
            "loyalty": 2,
        }

    def test_get_forge_ui_empty(self) -> None:
        sysm = SkillEaterCraftingSystem()
        ui_data = sysm.get_forge_ui([])
        assert ui_data["available_husks"] == []

    def test_preview_forge_unit_updates_ui(self) -> None:
        sysm = SkillEaterCraftingSystem()
        husk = make_husk()
        preview = sysm.preview_forge_unit(husk, protocol_rank=1)
        assert preview["protocol_rank"] == 1
        assert sysm.ui.forge_ui.preview_unit == preview
        assert sysm.ui.forge_ui.protocol_rank == 1

    def test_confirm_forge_unit_resets_ui(self) -> None:
        sysm = SkillEaterCraftingSystem()
        husk = make_husk()
        sysm.ui.forge_ui.show_confirmation = True
        sysm.ui.forge_ui.preview_unit = {"role": "escort"}
        res = sysm.confirm_forge_unit(husk)
        assert res["success"] is True
        assert sysm.ui.forge_ui.show_confirmation is False
        assert sysm.ui.forge_ui.preview_unit is None

    def test_confirm_summary_via_facade(self) -> None:
        sysm = SkillEaterCraftingSystem()
        sysm.confirm_forge_unit(make_husk())
        summary = sysm.get_created_units_summary()
        assert len(summary) == 1


class TestCraftingUI:
    def test_switch_tab_valid(self) -> None:
        ui = SkillEaterCraftingUI()
        ui.switch_tab("forge")
        assert ui.active_tab == "forge"
        ui.switch_tab("patchwork")
        assert ui.active_tab == "patchwork"

    def test_switch_tab_invalid_no_change(self) -> None:
        ui = SkillEaterCraftingUI()
        ui.switch_tab("forge")
        ui.switch_tab("bogus")
        assert ui.active_tab == "forge"

    def test_render_forge_tab(self) -> None:
        ui = SkillEaterCraftingUI()
        ui.switch_tab("forge")
        assert ui.render()["ui_name"] == "HUSK_FORGE"
