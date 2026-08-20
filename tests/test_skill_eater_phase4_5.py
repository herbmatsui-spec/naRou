"""
test_skill_eater_phase4_5.py
Phase 4 (従属・移植・AI) & Phase 5 (派閥・経済・買収) の検証テスト
"""
from __future__ import annotations

import unittest
from pathlib import Path

from skill_eater_economy_system import SkillEaterEconomySystem
from skill_eater_servant_system import SkillEaterServantSystem
from skill_eater_system import CharacterState, SkillEaterRegistry


class TestSkillEaterPhase4And5(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = SkillEaterRegistry.get_instance()
        yaml_path = Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"
        cls.registry.load_from_yaml(yaml_path)

    def setUp(self):
        self.servant_sys = SkillEaterServantSystem(self.registry)
        self.economy_sys = SkillEaterEconomySystem(self.registry)

    def test_husk_capture_and_skill_transplant(self):
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
        player.add_skill("com_combat_002")  # 小ヒール

        # 空っぽの敵
        enemy = CharacterState(
            id="e_husk",
            name="元ガードマン",
            hp=1,
            max_hp=50,
            mp=0,
            max_mp=20,
            atk=5,
            defense=5,
            intelligence=10,
            speed=5,
            is_husk=True,
        )

        # 捕獲
        servant = self.servant_sys.capture_husk(enemy, custom_name="忠実な衛生兵")
        self.assertIsNotNone(servant)
        self.assertEqual(servant.custom_name, "忠実な衛生兵")
        self.assertEqual(servant.get_skill_count(), 0)

        # スキル移植
        success, _msg = self.servant_sys.transplant_skill(
            player, servant, "com_combat_002"
        )
        self.assertTrue(success)
        self.assertFalse(player.has_skill("com_combat_002"))  # プレイヤーから消費
        self.assertTrue(servant.state.has_skill("com_combat_002"))
        self.assertEqual(servant.duration_turns, 3)

    def test_servant_turret_healing_and_crumble(self):
        servant_char = CharacterState(
            id="s1",
            name="衛生兵",
            hp=50,
            max_hp=50,
            mp=50,
            max_mp=50,
            atk=5,
            defense=5,
            intelligence=20,
            speed=10,
            is_husk=True,
        )
        servant_char.add_skill("com_combat_002")
        servant = self.servant_sys.capture_husk(servant_char)
        servant.duration_turns = 1  # 残り1ターン

        wounded_ally = CharacterState(
            id="ally",
            name="レジスタンス戦士",
            hp=10,
            max_hp=100,
            mp=10,
            max_mp=10,
            atk=20,
            defense=10,
            intelligence=5,
            speed=5,
        )

        res = self.servant_sys.execute_servant_turn(
            servant, enemies=[], allies=[wounded_ally]
        )
        self.assertEqual(res.action_type, "SKILL")
        self.assertEqual(res.skill_used_id, "com_combat_002")
        self.assertGreater(wounded_ally.hp, 10)  # 回復された
        self.assertTrue(res.is_crumbled)  # 寿命で自壊した
        self.assertNotIn("servant_s1", self.servant_sys.servant_party)

    def test_economy_net_worth_and_tier(self):
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
        self.assertEqual(
            self.economy_sys.evaluate_social_tier(player), "奴隷（ノースキル）"
        )

        # レアスキル所持（市場価値85,000）
        player.add_skill("rar_combat_012")  # 鋼鉄の皮膚
        self.assertEqual(self.economy_sys.get_player_skill_net_worth(player), 85000)
        self.assertEqual(
            self.economy_sys.evaluate_social_tier(player), "中流階級（シルバー）"
        )

    def test_black_market_sale_and_facility_upgrade(self):
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
        player.add_skill("com_labor_001")  # 500アルド
        player.add_skill("rar_utility_005")  # 思考加速（秘密スキル・200,000アルド）

        # 売却
        succ, val, _ = self.economy_sys.sell_skill_to_black_market(
            player, "com_labor_001"
        )
        self.assertTrue(succ)
        self.assertEqual(val, 500)
        self.assertEqual(self.economy_sys.aldo_currency, 500)

        # 支店買収でボーナス資金獲得
        self.economy_sys.takeover_branch("スラム第1支店", seized_aldo=5000)
        self.assertEqual(self.economy_sys.aldo_currency, 5500)

        # 施設アップグレード（思考加速が必要なラボ）
        succ_up, _msg = self.economy_sys.upgrade_facility(player, "rehab_lab")
        self.assertTrue(succ_up)
        self.assertEqual(self.economy_sys.base_facilities["rehab_lab"].level, 2)
        self.assertEqual(self.economy_sys.aldo_currency, 3500)  # 5500 - 2000


if __name__ == "__main__":
    unittest.main()
