"""
test_skill_eater_phase2.py
Phase 2: バトルエンジン＆《喰らい》システムの検証テスト
"""

from __future__ import annotations

import unittest
from pathlib import Path

from skill_eater_combat_system import SkillEaterCombatSystem
from skill_eater_system import CharacterState, SkillEaterRegistry


class TestSkillEaterPhase2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = SkillEaterRegistry.get_instance()
        yaml_path = Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"
        cls.registry.load_from_yaml(yaml_path)
        cls.combat = SkillEaterCombatSystem(cls.registry)

    def test_basic_attack_and_passive(self):
        attacker = CharacterState(
            id="p1",
            name="主人公",
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            atk=20,
            defense=10,
            intelligence=10,
            speed=10,
        )
        defender = CharacterState(
            id="e1",
            name="警備兵",
            hp=50,
            max_hp=50,
            mp=10,
            max_mp=10,
            atk=10,
            defense=10,
            intelligence=5,
            speed=5,
        )

        # 通常攻撃
        res = self.combat.execute_basic_attack(attacker, defender)
        self.assertTrue(res.success)
        self.assertEqual(res.damage_dealt, 15)  # 20 - (10//2) = 15
        self.assertEqual(defender.hp, 35)

        # 鋼鉄の皮膚パッシブ持ちへの攻撃
        defender.add_skill("rar_combat_012")
        res2 = self.combat.execute_basic_attack(attacker, defender)
        # 15 * 0.7 = 10
        self.assertEqual(res2.damage_dealt, 10)
        self.assertEqual(defender.hp, 25)

    def test_devour_success_flow(self):
        predator = CharacterState(
            id="player",
            name="主人公",
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            atk=10,
            defense=10,
            intelligence=20,
            speed=10,
            analysis_level=5,
        )
        prey = CharacterState(
            id="hunter",
            name="下級スキルハンター",
            hp=20,
            max_hp=100,
            mp=10,
            max_mp=10,
            atk=20,
            defense=20,
            intelligence=5,
            speed=5,
        )
        prey.add_skill("com_combat_001")  # 初級剣術

        self.assertFalse(predator.has_skill("com_combat_001"))
        self.assertTrue(prey.has_skill("com_combat_001"))

        # 強制成功で喰らいを実行
        res = self.combat.execute_devour(predator, prey, "com_combat_001", force_success=True)

        self.assertTrue(res.success)
        self.assertEqual(res.stolen_skill_id, "com_combat_001")
        self.assertTrue(predator.has_skill("com_combat_001"))
        self.assertFalse(prey.has_skill("com_combat_001"))
        self.assertTrue(prey.is_husk)  # スキルがゼロになりHusk化
        self.assertIn("SkillLossShock", prey.status_effects)

    def test_devour_failure_backlash(self):
        predator = CharacterState(
            id="player",
            name="主人公",
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            atk=10,
            defense=10,
            intelligence=10,
            speed=10,
            analysis_level=1,
        )
        prey = CharacterState(
            id="boss",
            name="ミダスCEO",
            hp=100,
            max_hp=100,
            mp=200,
            max_mp=200,
            atk=30,
            defense=30,
            intelligence=20,
            speed=10,
        )
        prey.add_skill("uni_midas_001")

        init_hp = predator.hp
        init_prey_atk = prey.atk

        # 強制失敗で喰らいを実行
        res = self.combat.execute_devour(predator, prey, "uni_midas_001", force_success=False)

        self.assertFalse(res.success)
        self.assertLess(predator.hp, init_hp)  # バックラッシュダメージ
        self.assertGreater(prey.atk, init_prey_atk)  # 激怒バフ
        self.assertIn("Enraged", prey.status_effects)


if __name__ == "__main__":
    unittest.main()
