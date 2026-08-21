"""
Skill Eater Phase 4 & 5: Comprehensive Integration Test (Steps 34-40)
Step 1〜33で実装した全システムの結合テスト。
"""

import unittest
from skill_eater_world_preview import WorldPreviewManager
from skill_eater_concept_crystal import ConceptCrystallizer
from skill_eater_temporal_vault import TemporalVaultManager
from skill_eater_legacy_bequest import LegacyBequestManager
from skill_eater_epilogue import EpilogueAndTransitionManager


class TestSkillEaterPhase4And5(unittest.TestCase):

    def test_01_world_preview_and_solver_tags(self):
        """Step 1-6: 次世界予兆と推奨タグ付与テスト"""
        preview_mgr = WorldPreviewManager()
        preview = preview_mgr.get_world_preview("W1_Magic_Dominant")
        self.assertIn("W1", preview["name"])

        # サンプル所持スキル
        player_skills = [
            {"name": "Fire Magic Blast", "tags": ["Magic", "Fire"]},
            {"name": "Heavy Steel Armor", "tags": ["Heavy Armor", "Defense"]},
            {"name": "Quick Step", "tags": ["Agility"]}
        ]

        tagged = preview_mgr.analyze_and_tag_skills(player_skills)
        self.assertTrue(tagged[0]["solver_recommended"])
        self.assertEqual(tagged[0]["recommendation_badge"], "[★次世界推奨]")
        self.assertTrue(tagged[1]["solver_warning"])
        self.assertEqual(tagged[1]["recommendation_badge"], "[▲非推奨]")

    def test_02_concept_crystallization(self):
        """Step 7-10: 概念結晶化（3スキル統合圧縮）テスト"""
        crystallizer = ConceptCrystallizer()
        fire_skills = [
            {"name": "Fireball", "tags": ["Fire"], "power": 100, "passive": "Burn +10"},
            {"name": "Flame Sword", "tags": ["Fire"], "power": 150, "passive": "Fire ATK +20"},
            {"name": "Inferno Burst", "tags": ["Fire"], "power": 250, "passive": "Explosion"}
        ]

        res = crystallizer.crystallize_skills("Fire", fire_skills)
        self.assertTrue(res["success"])
        crystal = res["concept_skill"]
        self.assertEqual(crystal["power"], 600) # 100+150+250+100ボーナス
        self.assertEqual(len(crystal["passives"]), 3)
        self.assertIn("Concept", crystal["tags"])

    def test_03_temporal_vault_and_carry_slots(self):
        """Step 11-15: 時空金庫と持ち込み確定テスト"""
        vault_mgr = TemporalVaultManager(max_carry_slots=5, max_vault_slots=3)

        # 持ち込み枠登録
        for i in range(5):
            res = vault_mgr.add_to_carry_over({"name": f"Skill {i+1}"})
            self.assertTrue(res["success"])

        # 6個目はエラー
        self.assertFalse(vault_mgr.add_to_carry_over({"name": "Skill 6"})["success"])

        # 時空金庫への保管
        vault_res = vault_mgr.deposit_to_vault({"name": "Vaulted Rare Skill"})
        self.assertTrue(vault_res["success"])

        # ロック確定
        lock_res = vault_mgr.lock_and_finalize_selection()
        self.assertTrue(lock_res["success"])
        self.assertTrue(lock_res["phase4_completed"])

    def test_04_legacy_bequest(self):
        """Step 16-19: 遺産譲渡・復興スコアリングテスト"""
        bequest_mgr = LegacyBequestManager()
        all_inventory = [
            {"name": "Sword Slash", "tags": ["Combat", "Sword"], "power": 100},
            {"name": "Mega Fire", "tags": ["Combat", "Fire"], "power": 200},
            {"name": "Holy Heal", "tags": ["Recovery", "Heal"], "power": 50},
            {"name": "Carried Skill", "tags": ["Magic"], "power": 500} # 除外対象
        ]

        res = bequest_mgr.donate_leftover_skills(all_inventory, excluded_skill_names=["Carried Skill"])
        self.assertTrue(res["success"])
        self.assertEqual(res["donated_count"], 3)
        self.assertEqual(res["dominant_reconstruction_type"], "Combat")
        self.assertEqual(res["bequest_scores"]["Combat"], 300)

    def test_05_epilogue_and_world_transition(self):
        """Step 20-33: エピローグテキスト・残滓アーティファクト・世界移行テスト"""
        epi_mgr = EpilogueAndTransitionManager()

        # エピローグ生成
        story_res = epi_mgr.generate_epilogue_story(
            bequest_scores={"Combat": 500, "Recovery": 100, "Production": 200},
            donated_count=5
        )
        self.assertTrue(story_res["epilogue_completed"])
        self.assertIn("覇道の鉄塞", story_res["epilogue_story"])

        # 残滓アーティファクト生成
        art_res = epi_mgr.generate_remnant_artifact()
        self.assertTrue(art_res["success"])
        self.assertEqual(art_res["artifact"]["name"], "ミダスの砕けた金貨 (Broken Midas Coin)")

        # 世界移行トランジション
        trans_res = epi_mgr.trigger_world_transition("W1_Magic_Dominant")
        self.assertTrue(trans_res["success"])
        self.assertTrue(trans_res["world_a_closed"])
        self.assertTrue(trans_res["phase5_completed"])


if __name__ == "__main__":
    unittest.main()
