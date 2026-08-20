"""
test_skill_eater_phase1.py
Phase 1: スキルデータ管理および《解析》プロトタイプの検証テスト
"""

import unittest
from pathlib import Path
from skill_eater_system import (
    SkillEaterRegistry,
    SkillTier,
    SkillType,
    CharacterState
)
from skill_eater_combat_system import SkillEaterCombatSystem


class TestSkillEaterPhase1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = SkillEaterRegistry.get_instance()
        yaml_path = Path("e:/narou2/data/worlds/skill_eater/skills.yaml")
        cls.registry.load_from_yaml(yaml_path)
        cls.combat = SkillEaterCombatSystem(cls.registry)

    def test_skills_loaded(self):
        skills = self.registry.get_all_skills()
        self.assertGreater(len(skills), 0)
        
        # 初級剣術の取得確認
        sword_skill = self.registry.get_skill("com_combat_001")
        self.assertIsNotNone(sword_skill)
        self.assertEqual(sword_skill.name, "初級剣術")
        self.assertEqual(sword_skill.tier, SkillTier.COMMON)

        # ユニークスキルの取得確認
        midas_skill = self.registry.get_skill("uni_midas_001")
        self.assertIsNotNone(midas_skill)
        self.assertEqual(midas_skill.name, "黄金錬成")
        self.assertEqual(midas_skill.tier, SkillTier.UNIQUE)

    def test_analysis_system_basic(self):
        # プレイヤー（解析Lv1）
        player = CharacterState(
            id="player",
            name="主人公",
            hp=100, max_hp=100,
            mp=50, max_mp=50,
            atk=10, defense=5, intelligence=15, speed=10,
            analysis_level=1
        )

        # 敵：下級スキルハンター
        enemy = CharacterState(
            id="hunter_01",
            name="下級スキルハンター",
            hp=80, max_hp=80,
            mp=20, max_mp=20,
            atk=15, defense=8, intelligence=5, speed=8
        )
        enemy.add_skill("com_combat_001")  # 初級剣術 (Common)
        enemy.add_skill("rar_combat_012")  # 鋼鉄の皮膚 (Rare)

        # 解析実行
        result = self.combat.analyze_target(player, enemy)
        self.assertEqual(result.target_id, "hunter_01")
        self.assertEqual(result.hologram_visual_mode, "BASIC")

        # Lv1ではCommonは詳細が見えるが、Rareは詳細が隠される
        common_info = next(s for s in result.revealed_skills if s.skill_id == "com_combat_001")
        rare_info = next(s for s in result.revealed_skills if s.skill_id == "rar_combat_012")

        self.assertEqual(common_info.name, "初級剣術")
        self.assertEqual(rare_info.market_value, None)  # 隠されている

    def test_analysis_system_high_level(self):
        # プレイヤー（解析Lv8）
        player = CharacterState(
            id="player",
            name="主人公",
            hp=100, max_hp=100,
            mp=50, max_mp=50,
            atk=10, defense=5, intelligence=15, speed=10,
            analysis_level=8
        )

        # 敵：ミダス商会CEO
        enemy = CharacterState(
            id="midas_ceo",
            name="ドン・ミダス",
            hp=30, max_hp=100,  # HP30%
            mp=200, max_mp=200,
            atk=50, defense=30, intelligence=40, speed=20
        )
        enemy.add_skill("uni_midas_001")
        enemy.add_skill("rar_combat_012")
        enemy.encryption_broken = True  # 暗号化解除済み状態

        result = self.combat.analyze_target(player, enemy)
        self.assertEqual(result.hologram_visual_mode, "EXPLOIT")

        # 高Lv解析ではUniqueの詳細や弱点、高確率の喰らい成功率が取得できる
        unique_info = next(s for s in result.revealed_skills if s.skill_id == "uni_midas_001")
        self.assertEqual(unique_info.name, "黄金錬成")
        self.assertIn("Magic/ArmorPierce", result.weaknesses)
        # HPが減っており解析Lvが高いため、成功率は高水準
        self.assertGreater(result.devour_success_rate, 0.70)


if __name__ == "__main__":
    unittest.main()
