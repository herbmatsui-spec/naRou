"""
tests/test_skill_eater_facility_actions.py
Aの世界（スキル喰い） 施設アクションシステム 包括テスト
"""
from __future__ import annotations

import unittest
from pathlib import Path

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_economy_system import BaseFacility, SkillEaterEconomySystem
from skill_eater_facility_actions import (
    FacilityAction,
    FacilityActionRegistry,
    FacilityActionResult,
    MercenaryContract,
    SkillEaterFacilitySystem,
    calculate_success_rate,
    can_afford_action,
    execute_analyze_skill_crystal,
    execute_augment_servant,
    execute_craft_implant,
    execute_develop_countermeasure,
    execute_dispatch_squad,
    execute_gather_intel,
    execute_hire_mercenary,
    execute_install_cybernetic,
    execute_launder_aldo,
    execute_memory_wipe,
    execute_negotiate_truce,
    execute_plan_raid,
    execute_repair_gear,
    execute_reverse_engineer_tech,
    execute_treat_toxicity,
)
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_system import CharacterState, SkillEaterRegistry


class TestFacilityActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = SkillEaterRegistry.get_instance()
        yaml_path = Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"
        if yaml_path.exists():
            cls.registry.load_from_yaml(yaml_path)

    def setUp(self):
        self.registry = SkillEaterRegistry.get_instance()
        self.audio = SkillEaterAudioSystem(enable_real_audio=False)
        self.presentation = SkillEaterPresentationSystem(audio_system=self.audio, is_mock_only=True)
        self.economy = SkillEaterEconomySystem(
            registry=self.registry,
            audio=self.audio,
            presentation=self.presentation,
        )
        self.facility_system = SkillEaterFacilitySystem(
            registry=self.registry,
            economy=self.economy,
            audio=self.audio,
            presentation=self.presentation,
        )

    def _create_test_player(self, **kwargs) -> CharacterState:
        defaults = {
            "id": "test_player",
            "name": "テスト主人公",
            "hp": 100,
            "max_hp": 100,
            "mp": 50,
            "max_mp": 50,
            "atk": 10,
            "defense": 10,
            "intelligence": 10,
            "speed": 10,
            "analysis_level": 1,
            "max_memory_capacity": 10,
            "junk": 1000,
        }
        defaults.update(kwargs)
        return CharacterState(**defaults)

    def _create_test_facility(self, facility_id: str, level: int = 1) -> BaseFacility:
        facility = self.economy.base_facilities.get(facility_id)
        if facility:
            facility.level = level
        return facility

    # --- Registry Tests ---
    def test_registry_singleton(self):
        reg1 = FacilityActionRegistry.get_instance()
        reg2 = FacilityActionRegistry.get_instance()
        self.assertIs(reg1, reg2)

    def test_registry_has_all_actions(self):
        reg = FacilityActionRegistry.get_instance()
        actions = reg.get_all_actions()
        self.assertEqual(len(actions), 15)  # 5 facilities * 3 actions

    def test_registry_workshop_actions(self):
        reg = FacilityActionRegistry.get_instance()
        workshop_actions = reg.get_actions_by_facility("workshop")
        self.assertEqual(len(workshop_actions), 3)
        action_ids = {a.id for a in workshop_actions}
        self.assertEqual(action_ids, {"craft_implant", "repair_gear", "install_cybernetic"})

    def test_registry_lab_actions(self):
        reg = FacilityActionRegistry.get_instance()
        lab_actions = reg.get_actions_by_facility("lab")
        self.assertEqual(len(lab_actions), 3)
        action_ids = {a.id for a in lab_actions}
        self.assertEqual(action_ids, {"analyze_skill_crystal", "reverse_engineer_tech", "develop_countermeasure"})

    def test_registry_medbay_actions(self):
        reg = FacilityActionRegistry.get_instance()
        medbay_actions = reg.get_actions_by_facility("medbay")
        self.assertEqual(len(medbay_actions), 3)
        action_ids = {a.id for a in medbay_actions}
        self.assertEqual(action_ids, {"treat_toxicity", "augment_servant", "memory_wipe"})

    def test_registry_command_actions(self):
        reg = FacilityActionRegistry.get_instance()
        command_actions = reg.get_actions_by_facility("command")
        self.assertEqual(len(command_actions), 3)
        action_ids = {a.id for a in command_actions}
        self.assertEqual(action_ids, {"dispatch_squad", "plan_raid", "negotiate_truce"})

    def test_registry_bar_actions(self):
        reg = FacilityActionRegistry.get_instance()
        bar_actions = reg.get_actions_by_facility("bar")
        self.assertEqual(len(bar_actions), 3)
        action_ids = {a.id for a in bar_actions}
        self.assertEqual(action_ids, {"gather_intel", "hire_mercenary", "launder_aldo"})

    # --- Utility Function Tests ---
    def test_calculate_success_rate_base(self):
        facility = BaseFacility(id="test", name="Test", level=1)
        facility.level = 1
        player = self._create_test_player()
        action = FacilityAction(id="test", name="Test", facility_id="test", base_success_rate=0.5)
        rate = calculate_success_rate(facility, player, action)
        self.assertEqual(rate, 0.65)  # 0.5 + 1*0.15

    def test_calculate_success_rate_with_skill(self):
        facility = BaseFacility(id="test", name="Test", level=2)
        facility.level = 2
        player = self._create_test_player()
        player.add_skill("rar_utility_005")
        action = FacilityAction(
            id="test", name="Test", facility_id="test",
            base_success_rate=0.4, required_skill="rar_utility_005"
        )
        rate = calculate_success_rate(facility, player, action)
        self.assertEqual(rate, 0.75)  # 0.4 + 2*0.15 + 1*0.05

    def test_calculate_success_rate_max_cap(self):
        facility = BaseFacility(id="test", name="Test", level=5)
        facility.level = 5
        player = self._create_test_player()
        player.add_skill("rar_utility_005")
        player.skills["rar_utility_005"].level = 10
        action = FacilityAction(
            id="test", name="Test", facility_id="test",
            base_success_rate=0.5, required_skill="rar_utility_005", max_success_rate=0.95
        )
        rate = calculate_success_rate(facility, player, action)
        self.assertEqual(rate, 0.95)  # Capped at max

    def test_can_afford_action_success(self):
        player = self._create_test_player(junk=100)
        self.economy.aldo_currency = 1000
        action = FacilityAction(id="test", name="Test", facility_id="test", cost_junk=50, cost_aldo=500)
        can_afford, msg = can_afford_action(player, self.economy, action)
        self.assertTrue(can_afford)
        self.assertEqual(msg, "")

    def test_can_afford_action_insufficient_junk(self):
        player = self._create_test_player(junk=10)
        self.economy.aldo_currency = 1000
        action = FacilityAction(id="test", name="Test", facility_id="test", cost_junk=50, cost_aldo=500)
        can_afford, msg = can_afford_action(player, self.economy, action)
        self.assertFalse(can_afford)
        self.assertIn("ジャンク", msg)

    def test_can_afford_action_insufficient_aldo(self):
        player = self._create_test_player(junk=100)
        self.economy.aldo_currency = 100
        action = FacilityAction(id="test", name="Test", facility_id="test", cost_junk=50, cost_aldo=500)
        can_afford, msg = can_afford_action(player, self.economy, action)
        self.assertFalse(can_afford)
        self.assertIn("アルド", msg)

    def test_can_afford_action_cooldown(self):
        player = self._create_test_player(junk=100)
        self.economy.aldo_currency = 1000
        action = FacilityAction(id="craft_implant", name="Test", facility_id="test", cost_junk=50, cost_aldo=500)
        player.facility_action_cooldowns[action.id] = 3
        can_afford, msg = can_afford_action(player, self.economy, action)
        self.assertFalse(can_afford)
        self.assertIn("クールダウン", msg)

    # --- Workshop Action Tests ---
    def test_workshop_craft_implant_success(self):
        player = self._create_test_player(junk=100)
        player.add_skill("rar_utility_005")
        self.economy.aldo_currency = 1000
        facility = self._create_test_facility("workshop", level=3)
        action = FacilityActionRegistry.get_instance().get_action("craft_implant")

        result = execute_craft_implant(player, self.economy, facility, action, self.audio, self.presentation)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.action_id, "craft_implant")
        self.assertEqual(result.facility_name, "ワークショップ")
        self.assertEqual(result.consumed_junk, 50)
        self.assertEqual(result.consumed_aldo, 500)
        self.assertEqual(player.facility_action_cooldowns["craft_implant"], 1)
        self.assertGreaterEqual(len(result.played_sounds), 1)

    def test_workshop_repair_gear(self):
        player = self._create_test_player(junk=100)
        self.economy.aldo_currency = 1000
        facility = self._create_test_facility("workshop", level=1)
        action = FacilityActionRegistry.get_instance().get_action("repair_gear")

        result = execute_repair_gear(player, self.economy, facility, action, self.audio, self.presentation)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_junk, 30)
        self.assertEqual(result.consumed_aldo, 200)

    def test_workshop_install_cybernetic(self):
        player = self._create_test_player(junk=200)
        player.add_skill("rar_utility_005")
        self.economy.aldo_currency = 5000
        facility = self._create_test_facility("workshop", level=2)
        action = FacilityActionRegistry.get_instance().get_action("install_cybernetic")

        result = execute_install_cybernetic(player, self.economy, facility, action, self.audio, self.presentation)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_junk, 100)
        self.assertEqual(result.consumed_aldo, 2000)

    # --- Lab Action Tests ---
    def test_lab_analyze_skill_crystal(self):
        player = self._create_test_player(junk=100)
        player.add_skill("com_magic_001")
        player.unidentified_crystals = ["proc_test_001"]
        self.economy.aldo_currency = 2000
        facility = self._create_test_facility("lab", level=1)
        action = FacilityActionRegistry.get_instance().get_action("analyze_skill_crystal")

        result = execute_analyze_skill_crystal(player, self.economy, facility, action, self.audio, self.presentation)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_junk, 20)
        self.assertEqual(result.consumed_aldo, 1000)

    def test_lab_reverse_engineer_tech(self):
        player = self._create_test_player(junk=200)
        player.add_skill("rar_utility_005")
        self.economy.aldo_currency = 3000
        facility = self._create_test_facility("lab", level=2)
        action = FacilityActionRegistry.get_instance().get_action("reverse_engineer_tech")

        result = execute_reverse_engineer_tech(player, self.economy, facility, action, self.audio, self.presentation)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_junk, 80)
        self.assertEqual(result.consumed_aldo, 1500)

    def test_lab_develop_countermeasure(self):
        player = self._create_test_player(junk=200)
        player.add_skill("uni_midas_001")
        self.economy.aldo_currency = 5000
        facility = self._create_test_facility("lab", level=3)
        action = FacilityActionRegistry.get_instance().get_action("develop_countermeasure")

        result = execute_develop_countermeasure(player, self.economy, facility, action, self.audio, self.presentation, "midas_ceo")

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_junk, 50)
        self.assertEqual(result.consumed_aldo, 3000)

    # --- Medbay Action Tests ---
    def test_medbay_treat_toxicity(self):
        player = self._create_test_player(junk=50)
        player.addiction_buildup = 80
        player.status_effects.append("Addicted")
        self.economy.aldo_currency = 1000
        facility = self._create_test_facility("medbay", level=1)
        action = FacilityActionRegistry.get_instance().get_action("treat_toxicity")

        result = execute_treat_toxicity(player, self.economy, facility, action, self.audio, self.presentation)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_junk, 10)
        self.assertEqual(result.consumed_aldo, 500)

    def test_medbay_augment_servant(self):
        player = self._create_test_player(junk=200)
        player.add_skill("rar_utility_005")
        self.economy.aldo_currency = 3000
        facility = self._create_test_facility("medbay", level=2)
        action = FacilityActionRegistry.get_instance().get_action("augment_servant")

        # This test requires a servant system, so we test the validation
        result = execute_augment_servant(
            player, self.economy, facility, action, self.audio, self.presentation, None, "servant_001"
        )

        self.assertIsInstance(result, FacilityActionResult)
        self.assertFalse(result.success)
        self.assertIn("初期化", result.log_message)

    def test_medbay_memory_wipe(self):
        player = self._create_test_player(junk=0)
        player.add_skill("com_combat_001")
        player.add_skill("rar_combat_012")
        player.archived_skills["com_magic_001"] = player.skills.get("com_magic_001")
        player.addiction_buildup = 90
        self.economy.aldo_currency = 10000
        facility = self._create_test_facility("medbay", level=5)
        action = FacilityActionRegistry.get_instance().get_action("memory_wipe")

        result = execute_memory_wipe(player, self.economy, facility, action, self.audio, self.presentation)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_aldo, 5000)

    # --- Command Action Tests ---
    def test_command_dispatch_squad_scavenge(self):
        player = self._create_test_player(junk=100)
        self.economy.aldo_currency = 3000
        facility = self._create_test_facility("command", level=1)
        action = FacilityActionRegistry.get_instance().get_action("dispatch_squad")

        result = execute_dispatch_squad(player, self.economy, facility, action, self.audio, self.presentation, "scavenge")

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_junk, 30)
        self.assertEqual(result.consumed_aldo, 1000)

    def test_command_plan_raid(self):
        player = self._create_test_player(junk=200)
        player.add_skill("rar_combat_012")
        self.economy.aldo_currency = 5000
        facility = self._create_test_facility("command", level=2)
        action = FacilityActionRegistry.get_instance().get_action("plan_raid")

        result = execute_plan_raid(player, self.economy, facility, action, self.audio, self.presentation, "midas_branch")

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_junk, 50)
        self.assertEqual(result.consumed_aldo, 2000)

    def test_command_negotiate_truce(self):
        player = self._create_test_player(junk=0)
        self.economy.aldo_currency = 20000
        facility = self._create_test_facility("command", level=3)
        action = FacilityActionRegistry.get_instance().get_action("negotiate_truce")

        # Make midas hostile first
        self.economy.factions["midas"].is_hostile = True
        self.economy.factions["midas"].reputation = -50

        result = execute_negotiate_truce(player, self.economy, facility, action, self.audio, self.presentation, "midas")

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_aldo, 10000)

    # --- Bar Action Tests ---
    def test_bar_gather_intel(self):
        player = self._create_test_player(junk=0)
        self.economy.aldo_currency = 1000
        facility = self._create_test_facility("bar", level=1)
        action = FacilityActionRegistry.get_instance().get_action("gather_intel")

        result = execute_gather_intel(player, self.economy, facility, action, self.audio, self.presentation)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_aldo, 500)

    def test_bar_hire_mercenary(self):
        player = self._create_test_player(junk=0)
        self.economy.aldo_currency = 5000
        facility = self._create_test_facility("bar", level=1)
        action = FacilityActionRegistry.get_instance().get_action("hire_mercenary")

        result = execute_hire_mercenary(player, self.economy, facility, action, self.audio, self.presentation)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.consumed_aldo, 3000)

    def test_bar_launder_aldo(self):
        player = self._create_test_player(junk=0)
        self.economy.aldo_currency = 10000
        self.economy.heat_level = 50
        facility = self._create_test_facility("bar", level=1)
        action = FacilityActionRegistry.get_instance().get_action("launder_aldo")

        result = execute_launder_aldo(player, self.economy, facility, action, self.audio, self.presentation, 2000)

        self.assertIsInstance(result, FacilityActionResult)
        # Launder doesn't consume aldo on success (it cleans it)
        if result.success:
            self.assertEqual(result.consumed_aldo, 0)

    def test_launder_aldo_invalid_amount(self):
        player = self._create_test_player(junk=0)
        self.economy.aldo_currency = 10000
        self.economy.heat_level = 10  # max 1000 aldo
        facility = self._create_test_facility("bar", level=1)
        action = FacilityActionRegistry.get_instance().get_action("launder_aldo")

        result = execute_launder_aldo(player, self.economy, facility, action, self.audio, self.presentation, 5000)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertFalse(result.success)
        self.assertIn("無効", result.log_message)

    # --- Facility System Integration Tests ---
    def test_facility_system_execute_workshop(self):
        player = self._create_test_player(junk=100)
        player.add_skill("rar_utility_005")
        self.economy.aldo_currency = 1000

        result = self.facility_system.execute_action("workshop", "craft_implant", player)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.facility_name, "ワークショップ")

    def test_facility_system_execute_lab(self):
        player = self._create_test_player(junk=100)
        player.add_skill("com_magic_001")
        player.unidentified_crystals = ["test_crystal"]
        self.economy.aldo_currency = 2000

        result = self.facility_system.execute_action("lab", "analyze_skill_crystal", player)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.facility_name, "研究室")

    def test_facility_system_execute_medbay(self):
        player = self._create_test_player(junk=50)
        player.addiction_buildup = 50
        self.economy.aldo_currency = 1000

        result = self.facility_system.execute_action("medbay", "treat_toxicity", player)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.facility_name, "医療ベイ")

    def test_facility_system_execute_command(self):
        player = self._create_test_player(junk=100)
        self.economy.aldo_currency = 3000

        result = self.facility_system.execute_action("command", "dispatch_squad", player, mission_type="scavenge")

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.facility_name, "指揮室")

    def test_facility_system_execute_bar(self):
        player = self._create_test_player(junk=0)
        self.economy.aldo_currency = 1000

        result = self.facility_system.execute_action("bar", "gather_intel", player)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertEqual(result.facility_name, "バー/交易所")

    def test_facility_system_invalid_facility(self):
        player = self._create_test_player(junk=100)
        self.economy.aldo_currency = 1000

        result = self.facility_system.execute_action("nonexistent", "craft_implant", player)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertFalse(result.success)
        self.assertIn("存在しません", result.log_message)

    def test_facility_system_invalid_action(self):
        player = self._create_test_player(junk=100)
        self.economy.aldo_currency = 1000

        result = self.facility_system.execute_action("workshop", "nonexistent_action", player)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertFalse(result.success)
        self.assertIn("存在しません", result.log_message)

    def test_facility_system_wrong_facility_for_action(self):
        player = self._create_test_player(junk=100)
        self.economy.aldo_currency = 1000

        result = self.facility_system.execute_action("lab", "craft_implant", player)

        self.assertIsInstance(result, FacilityActionResult)
        self.assertFalse(result.success)
        self.assertIn("実行できません", result.log_message)

    # --- Economy Integration Tests ---
    def test_economy_facility_system_integration(self):
        player = self._create_test_player(junk=100)
        player.add_skill("rar_utility_005")
        self.economy.aldo_currency = 1000

        result = self.economy.execute_facility_action("workshop", "craft_implant", player)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, FacilityActionResult)

    def test_economy_upgrade_facility(self):
        player = self._create_test_player(junk=0)
        player.add_skill("rar_utility_005")
        self.economy.aldo_currency = 5000

        result = self.economy.upgrade_facility(player, "workshop")

        self.assertTrue(result[0])
        facility = self.economy.base_facilities["workshop"]
        self.assertEqual(facility.level, 2)

    # --- Presentation/Audio Integration Tests ---
    def test_presentation_events_generated(self):
        player = self._create_test_player(junk=100)
        self.economy.aldo_currency = 1000
        facility = self._create_test_facility("workshop", level=1)
        action = FacilityActionRegistry.get_instance().get_action("repair_gear")

        result = execute_repair_gear(player, self.economy, facility, action, self.audio, self.presentation)

        events = self.presentation.get_and_clear_events()
        self.assertGreaterEqual(len(events), 1)

        sounds = self.audio.get_and_clear_played_sounds()
        self.assertGreaterEqual(len(sounds), 1)

    # --- Edge Cases ---
    def test_insufficient_resources_blocked(self):
        player = self._create_test_player(junk=0)
        self.economy.aldo_currency = 0
        facility = self._create_test_facility("workshop", level=1)
        action = FacilityActionRegistry.get_instance().get_action("craft_implant")

        result = execute_craft_implant(player, self.economy, facility, action, self.audio, self.presentation)

        self.assertFalse(result.success)
        self.assertIn("不足", result.log_message)

    def test_cooldown_prevents_spam(self):
        player = self._create_test_player(junk=100)
        player.add_skill("rar_utility_005")
        self.economy.aldo_currency = 1000
        facility = self._create_test_facility("workshop", level=1)
        action = FacilityActionRegistry.get_instance().get_action("craft_implant")

        # First execution
        result1 = execute_craft_implant(player, self.economy, facility, action, self.audio, self.presentation)
        self.assertTrue(result1.success or not result1.success)  # Either way, cooldown set

        # Second execution should be blocked by cooldown
        result2 = execute_craft_implant(player, self.economy, facility, action, self.audio, self.presentation)
        self.assertFalse(result2.success)
        self.assertIn("クールダウン", result2.log_message)

    def test_facility_level_affects_success_rate(self):
        facility_l1 = BaseFacility(id="test", name="Test", level=1)
        facility_l1.level = 1
        facility_l5 = BaseFacility(id="test", name="Test", level=5)
        facility_l5.level = 5
        player = self._create_test_player()
        action = FacilityAction(id="test", name="Test", facility_id="test", base_success_rate=0.2, max_success_rate=1.0)

        rate_l1 = calculate_success_rate(facility_l1, player, action)
        rate_l5 = calculate_success_rate(facility_l5, player, action)

        self.assertGreater(rate_l5, rate_l1)
        self.assertAlmostEqual(rate_l5 - rate_l1, 0.6, places=1)  # 4 levels * 0.15


class TestMercenaryContract(unittest.TestCase):
    def test_mercenary_contract_creation(self):
        contract = MercenaryContract(
            merc_type="vanguard",
            name="前衛傭兵",
            duration_turns=3,
            effects={"taunt": True, "damage_reduction": 0.5},
            is_elite=False,
        )
        self.assertEqual(contract.merc_type, "vanguard")
        self.assertEqual(contract.duration_turns, 3)
        self.assertFalse(contract.is_elite)


if __name__ == "__main__":
    unittest.main()
