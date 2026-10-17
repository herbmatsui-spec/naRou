"""Coverage tests for skill_eater_economy_system (SkillEaterEconomySystem)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from skill_eater_economy_system import (
    BaseFacility,
    FactionState,
    SkillEaterEconomySystem,
)


class TestFactionState:
    def test_defaults(self) -> None:
        f = FactionState(id="x", name="X")
        assert f.reputation == 0
        assert f.influence_points == 1000
        assert f.is_hostile is False
        assert f.controlled_districts == []
        assert f.territory_income_per_turn == 0
        assert f.morale == 50
        assert f.is_at_war is False
        assert f.war_target is None

    def test_full(self) -> None:
        f = FactionState(
            id="midas", name="Midas", reputation=-50, influence_points=5000,
            is_hostile=True, controlled_districts=["d1"], territory_income_per_turn=100,
            morale=30, is_at_war=True, war_target="resistance",
        )
        assert f.reputation == -50
        assert f.war_target == "resistance"


class TestBaseFacility:
    def test_defaults(self) -> None:
        b = BaseFacility(id="w", name="Workshop")
        assert b.level == 1
        assert b.max_level == 5
        assert b.upgrade_cost_aldo == 1000
        assert b.required_secret_skill is None
        assert b.alternative_cost_aldo is None
        assert b.effect_description == ""
        assert b.actions == []

    def test_full(self) -> None:
        b = BaseFacility(
            id="lab", name="Lab", level=2, max_level=5, upgrade_cost_aldo=2000,
            required_secret_skill="s1", alternative_cost_aldo=10000,
            effect_description="desc", actions=["a1", "a2"],
        )
        assert b.level == 2
        assert b.actions == ["a1", "a2"]


class TestSkillEaterEconomySystemInit:
    def test_default_instances(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        assert econ.aldo_currency == 0
        assert econ.heat_level == 0
        assert set(econ.factions.keys()) == {"midas", "resistance", "bank", "broker"}
        assert econ.factions["midas"].reputation == -50
        assert econ.factions["midas"].is_hostile is True
        assert set(econ.base_facilities.keys()) == {
            "workshop", "lab", "medbay", "command", "bar", "rehab_lab",
            "synthesis_furnace", "hq_vault",
        }
        assert econ.facility_system is not None

    def test_singleton(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        a = SkillEaterEconomySystem.get_instance()
        b = SkillEaterEconomySystem.get_instance()
        assert a is b
        SkillEaterEconomySystem.reset_instance()

    def test_registry_audio_presentation_default(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        assert econ.registry is not None
        assert econ.audio is not None
        assert econ.presentation is not None

    def test_audio_without_presentation_sets_link(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        from skill_eater_audio_system import SkillEaterAudioSystem
        audio = SkillEaterAudioSystem(enable_real_audio=False)
        econ = SkillEaterEconomySystem(audio=audio)
        assert econ.presentation.audio_system is audio


class TestNetWorthAndTier:
    def test_net_worth_empty(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        player = MagicMock()
        player.get_skill_ids.return_value = []
        assert econ.get_player_skill_net_worth(player) == 0

    def test_net_worth_with_skills(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        player = MagicMock()
        player.get_skill_ids.return_value = ["s1"]
        skill_def = MagicMock()
        skill_def.market_value = 5000
        econ.registry.get_skill.return_value = skill_def
        assert econ.get_player_skill_net_worth(player) == 5000

    def test_evaluate_social_tier_all(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()

        def _tier(net_worth: int) -> str:
            player = MagicMock()
            player.get_skill_ids.return_value = ["s"] if net_worth > 0 else []
            skill_def = MagicMock()
            skill_def.market_value = net_worth
            econ.registry.get_skill.return_value = skill_def
            return econ.evaluate_social_tier(player)

        assert _tier(0) == "奴隷（ノースキル）"
        assert _tier(5000) == "庶民（コモン級）"
        assert _tier(50000) == "中流階級（シルバー）"
        assert _tier(300000) == "新興富裕層（ゴールド）"
        assert _tier(900000) == "支配階級（プラチナ／スキルイーター）"


class TestSellSkillBlackMarket:
    def _player(self, has_skill=True, skills=None):
        player = MagicMock()
        player.has_skill.return_value = has_skill
        player.skills = skills or {}
        return player

    def test_not_owned(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        player = self._player(has_skill=False)
        ok, value, msg = econ.sell_skill_to_black_market(player, "s1")
        assert ok is False
        assert value == 0
        assert "所持していません" in msg

    def test_no_market_value(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        player = self._player(has_skill=True)
        skill_def = MagicMock()
        skill_def.market_value = 0
        econ.registry.get_skill.return_value = skill_def
        ok, value, msg = econ.sell_skill_to_black_market(player, "s1")
        assert ok is False
        assert value == 0

    def test_normal_sale(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        player = self._player(has_skill=True, skills={"s1": MagicMock()})
        skill_def = MagicMock()
        skill_def.market_value = 3000
        skill_def.name = "TestSkill"
        skill_def.is_illegal = False
        econ.registry.get_skill.return_value = skill_def
        ok, value, msg = econ.sell_skill_to_black_market(player, "s1")
        assert ok is True
        assert value == 3000
        assert econ.aldo_currency == 3000
        assert econ.factions["broker"].reputation == 12
        player.remove_skill.assert_called_once_with("s1")

    def test_illegal_sale_heat(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        player = self._player(has_skill=True, skills={"s1": MagicMock()})
        skill_def = MagicMock()
        skill_def.market_value = 1000
        skill_def.name = "IllegalSkill"
        skill_def.is_illegal = True
        econ.registry.get_skill.return_value = skill_def
        ok, value, msg = econ.sell_skill_to_black_market(player, "s1")
        assert ok is True
        assert econ.heat_level == 10
        assert "警戒度" in msg


class TestSellSkillNormalMarket:
    def test_not_owned(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        player = MagicMock()
        player.has_skill.return_value = False
        ok, value, msg = econ.sell_skill_to_normal_market(player, "s1")
        assert ok is False
        assert value == 0

    def test_illegal_rejected(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        player = MagicMock()
        player.has_skill.return_value = True
        player.skills = {"s1": MagicMock()}
        skill_def = MagicMock()
        skill_def.market_value = 1000
        skill_def.name = "IllegalSkill"
        skill_def.is_illegal = True
        econ.registry.get_skill.return_value = skill_def
        ok, value, msg = econ.sell_skill_to_normal_market(player, "s1")
        assert ok is False
        assert value == 0
        assert "査定拒絶" in msg

    def test_normal_sale(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        player = MagicMock()
        player.has_skill.return_value = True
        player.skills = {"s1": MagicMock()}
        skill_def = MagicMock()
        skill_def.market_value = 2000
        skill_def.name = "LegalSkill"
        skill_def.is_illegal = False
        econ.registry.get_skill.return_value = skill_def
        ok, value, msg = econ.sell_skill_to_normal_market(player, "s1")
        assert ok is True
        assert value == 2000
        assert econ.aldo_currency == 2000


class TestInspectorRaid:
    def test_heat_below_threshold(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        econ.heat_level = 50
        triggered, inspector, msg = econ.check_inspector_raid()
        assert triggered is False
        assert inspector is None
        assert "50/100" in msg

    def test_heat_at_threshold(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        econ.heat_level = 100
        triggered, inspector, msg = econ.check_inspector_raid()
        assert triggered is True
        assert econ.heat_level == 0
        assert inspector is not None
        assert inspector.name == "ミダス特別監査局長"
        assert "急襲" in msg


class TestTakeoverBranch:
    def test_takeover(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        econ.aldo_currency = 100
        msg = econ.takeover_branch("東区支店", 5000)
        assert econ.aldo_currency == 5100
        assert econ.factions["midas"].influence_points == 700
        assert econ.factions["resistance"].influence_points == 1300
        assert econ.factions["resistance"].reputation == 50
        assert "支店買収完了" in msg


class TestUpgradeFacility:
    def _setup(self, skill=None, aldos=0):
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        econ.aldo_currency = aldos
        player = MagicMock()
        player.has_skill.return_value = skill is not None
        player.skills = {skill: MagicMock()} if skill else {}
        return econ, player

    def test_nonexistent_facility(self) -> None:
        econ, player = self._setup(aldos=9999)
        ok, msg = econ.upgrade_facility(player, "no_such")
        assert ok is False
        assert "存在しない" in msg

    def test_max_level(self) -> None:
        econ, player = self._setup(aldos=9999)
        econ.base_facilities["workshop"].level = 5
        ok, msg = econ.upgrade_facility(player, "workshop")
        assert ok is False
        assert "最大レベル" in msg

    def test_no_skill_no_alt_funds(self) -> None:
        econ, player = self._setup(skill=None, aldos=100)
        ok, msg = econ.upgrade_facility(player, "workshop")
        assert ok is False
        assert "企業秘密スキル" in msg or "代替闇ルート" in msg

    def test_alt_route(self) -> None:
        econ, player = self._setup(skill=None, aldos=9000)
        # workshop: upgrade 1500 + alternative 7500 = 9000
        ok, msg = econ.upgrade_facility(player, "workshop")
        assert ok is True
        assert econ.base_facilities["workshop"].level == 2
        assert econ.aldo_currency == 0
        assert "闇ルート決済" in msg

    def test_normal_route(self) -> None:
        econ, player = self._setup(skill="rar_utility_005", aldos=2000)
        ok, msg = econ.upgrade_facility(player, "workshop")
        assert ok is True
        assert econ.base_facilities["workshop"].level == 2
        assert econ.aldo_currency == 500
        assert "施設強化完了" in msg

    def test_insufficient_aldo(self) -> None:
        econ, player = self._setup(skill="rar_utility_005", aldos=100)
        ok, msg = econ.upgrade_facility(player, "workshop")
        assert ok is False
        assert "不足" in msg


class TestExecuteFacilityAction:
    def test_facade(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        player = MagicMock()
        result = econ.execute_facility_action("workshop", "craft_implant", player)
        assert result is not None

    def test_no_facility_system(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        econ = SkillEaterEconomySystem()
        econ.facility_system = None
        assert econ.execute_facility_action("workshop", "x", MagicMock()) is None


class TestSingleton:
    def test_get_and_reset(self) -> None:
        SkillEaterEconomySystem.reset_instance()
        inst = SkillEaterEconomySystem.get_instance()
        assert inst is not None
        SkillEaterEconomySystem.reset_instance()
        inst2 = SkillEaterEconomySystem.get_instance()
        assert inst2 is not inst
