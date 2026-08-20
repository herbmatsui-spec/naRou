"""
test_skill_eater_phase3.py
Phase 3: スキル合成（静的＆プロシージャル）とダイナミックツリーの検証テスト
"""

import unittest
from pathlib import Path
from skill_eater_system import (
    SkillEaterRegistry,
    SkillTier,
    CharacterState
)
from skill_eater_synthesis_system import SkillEaterSynthesisSystem


class TestSkillEaterPhase3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = SkillEaterRegistry.get_instance()
        yaml_path = Path("e:/narou2/data/worlds/skill_eater/skills.yaml")
        cls.registry.load_from_yaml(yaml_path)
        cls.synthesis = SkillEaterSynthesisSystem(cls.registry)

    def test_static_synthesis(self):
        player = CharacterState(
            id="player", name="主人公",
            hp=100, max_hp=100, mp=50, max_mp=50,
            atk=10, defense=10, intelligence=20, speed=10
        )
        player.add_skill("com_magic_001")  # 火種
        player.add_skill("com_labor_002")  # 夜目

        res = self.synthesis.synthesize(player, "com_magic_001", "com_labor_002")
        self.assertTrue(res.success)
        self.assertFalse(res.is_procedural)
        self.assertEqual(res.result_skill.id, "rar_infrared_vision")
        
        # 消費と新規付与の確認
        self.assertFalse(player.has_skill("com_magic_001"))
        self.assertFalse(player.has_skill("com_labor_002"))
        self.assertTrue(player.has_skill("rar_infrared_vision"))

    def test_procedural_synthesis(self):
        player = CharacterState(
            id="player", name="主人公",
            hp=100, max_hp=100, mp=50, max_mp=50,
            atk=10, defense=10, intelligence=20, speed=10
        )
        player.add_skill("com_combat_001")  # 初級剣術 (Common, [Combat, Sword])
        player.add_skill("rar_combat_012")  # 鋼鉄の皮膚 (Rare, [Combat, Defense])

        res = self.synthesis.synthesize(player, "com_combat_001", "rar_combat_012")
        self.assertTrue(res.success)
        self.assertTrue(res.is_procedural)
        
        # タグの融合と上位Tierの継承
        self.assertEqual(res.result_skill.tier, SkillTier.RARE)
        self.assertIn("Sword", res.result_skill.tags)
        self.assertIn("Defense", res.result_skill.tags)
        self.assertTrue(player.has_skill(res.result_skill.id))

    def test_dynamic_tree_generation(self):
        player = CharacterState(
            id="player", name="主人公",
            hp=100, max_hp=100, mp=50, max_mp=50,
            atk=10, defense=10, intelligence=20, speed=10
        )
        player.add_skill("com_labor_001")
        
        nodes = self.synthesis.generate_dynamic_tree(player)
        self.assertEqual(len(nodes), 2)  # Root + 1 skill
        self.assertEqual(nodes[0].skill_id, "root_analysis")
        self.assertEqual(nodes[1].skill_id, "com_labor_001")
        self.assertEqual(nodes[1].parent_ids, ["root_analysis"])


if __name__ == "__main__":
    unittest.main()
