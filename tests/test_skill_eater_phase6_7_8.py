"""
test_skill_eater_phase6_7_8.py
Phase 6 (クエスト・メタ特効), Phase 7 (法則書き換え), Phase 8 (輪廻転生) の検証テスト
"""

import unittest
from pathlib import Path

from skill_eater_meta_quest_system import (
    GlobalRuleEngine,
    SkillEaterQuestSystem,
    SkillEaterReincarnationSystem,
)
from skill_eater_system import CharacterState, SkillEaterRegistry


class TestSkillEaterPhase678(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = SkillEaterRegistry.get_instance()
        yaml_path = Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"
        cls.registry.load_from_yaml(yaml_path)

    def setUp(self):
        self.rules = GlobalRuleEngine.get_instance()
        self.rules.reset_rules()
        self.quest_sys = SkillEaterQuestSystem(self.registry)
        self.reincarnation_sys = SkillEaterReincarnationSystem(self.registry)

    def test_meta_counter_boss_mechanic(self):
        player = CharacterState(
            id="p1",
            name="主人公",
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            atk=10,
            defense=10,
            intelligence=10,
            speed=10,
        )
        self.assertTrue(self.rules.is_boss_instant_kill_enabled)

        # 対策スキルなし
        succ, _ = self.quest_sys.check_boss_meta_counter(player, "midas_ceo")
        self.assertFalse(succ)
        self.assertTrue(self.rules.is_boss_instant_kill_enabled)

        # 対策合成スキル《赤外線視界》所持で突入
        player.add_skill("rar_infrared_vision")
        succ2, _msg = self.quest_sys.check_boss_meta_counter(player, "midas_ceo")
        self.assertTrue(succ2)
        self.assertFalse(self.rules.is_boss_instant_kill_enabled)  # 即死が無効化された

    def test_global_rule_override_root_access(self):
        player = CharacterState(
            id="p1",
            name="主人公",
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            atk=10,
            defense=10,
            intelligence=10,
            speed=10,
        )
        # ROOT未所持での操作
        succ, _err, _ = self.rules.override_rule("damage_multiplier", 5.0, player=player)
        self.assertFalse(succ)

        # 頭取を倒してマスタースキル(ROOT権限)取得
        self.rules.root_access_granted = True
        succ2, _msg, _ = self.rules.override_rule(
            "damage_multiplier", 10.0, player=player
        )
        self.assertTrue(succ2)
        self.assertEqual(self.rules.damage_multiplier, 10.0)

        # 喰らい確率を100%に固定
        succ3, _, _ = self.rules.override_rule(
            "devour_success_rate_override", 1.0, player=player
        )
        self.assertTrue(succ3)
        self.assertEqual(self.rules.devour_success_rate_override, 1.0)

    def test_reincarnation_inheritance(self):
        player = CharacterState(
            id="p1",
            name="主人公",
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            atk=10,
            defense=10,
            intelligence=10,
            speed=10,
        )
        # 高価値スキル所持
        player.add_skill("rar_combat_012")  # 85,000アルド
        player.add_skill("com_combat_001")  # 1,200アルド

        new_player, _msg = self.reincarnation_sys.process_reincarnation(
            player, selected_carryover_skill_ids=["rar_combat_012"]
        )

        # 2周目キャラのステータス上昇＆継承
        self.assertEqual(self.reincarnation_sys.meta_state.loop_count, 2)
        self.assertEqual(new_player.hp, 140)  # 100 + 40
        self.assertTrue(new_player.has_skill("rar_combat_012"))
        self.assertFalse(new_player.has_skill("com_combat_001"))
        self.assertIn(
            "first_eater_vault", self.reincarnation_sys.meta_state.unlocked_secrets
        )


if __name__ == "__main__":
    unittest.main()
