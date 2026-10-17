"""
Skill Eater Phase 3: Comprehensive Integration Test (Steps 63-71)
Step 1〜62で実装した全9システムの結合テスト。
"""

import unittest

from skill_eater_ascension_board import AscensionBoard
from skill_eater_bank_dungeon import BankDungeonManager
from skill_eater_combat_deck import CombatDeckSystem
from skill_eater_concept_trials import ConceptTrialsManager
from skill_eater_final_boss import FinalBossCausalityManager
from skill_eater_master_bosses import MasterBossManager
from skill_eater_slum_finale import SlumFinaleManager
from skill_eater_world_hack import WorldLawOverrideManager


class TestSkillEaterPhase3(unittest.TestCase):
    def test_01_ascension_board(self):
        """Step 1-6: 神格化ボード・星座シナジーのテスト"""
        board = AscensionBoard()
        self.assertEqual(board.active_links_count, 0)

        # 2つのノードに同じ属性のコアを装着 (alpha と beta は隣接)
        board.equip_core("alpha", "Flame Core A", "Fire")
        board.equip_core("beta", "Flame Core B", "Fire")

        self.assertEqual(board.active_links_count, 1)
        state = board.get_board_state()
        self.assertAlmostEqual(state["buffs"]["all_damage_multiplier"], 1.20)

    def test_02_combat_deck_system(self):
        """Step 7-16: リアルタイム構築戦・即席合成・疲労リロードのテスト"""
        deck = CombatDeckSystem(initial_skills=["Slash", "Fireball", "Guard", "Poison"])

        # ターン開始
        turn_info = deck.start_turn(draw_count=4)
        self.assertEqual(len(turn_info["hand"]), 4)

        # 即席合成
        syn_res = deck.instant_synthesize("Slash", "Fireball")
        self.assertTrue(syn_res["success"])
        self.assertIn("Instant Fusion: [Slash + Fireball]", syn_res["hand"])

        # 合成スキルで攻撃
        atk_res = deck.execute_skill_attack(
            "Instant Fusion: [Slash + Fireball]", base_power=100, mana_cost=1
        )
        self.assertTrue(atk_res["success"])
        self.assertEqual(atk_res["damage_dealt"], 250)  # 2.5倍

    def test_03_bank_dungeon_and_erosion(self):
        """Step 17-22: 多層要塞ダンジョン・ハザード侵食テスト"""
        dungeon = BankDungeonManager()

        # 探索進行
        step1 = dungeon.advance_exploration_step()
        self.assertEqual(step1["hazard_level"], 15)

        # ハザード上昇によるデバフ
        dungeon.advance_exploration_step()
        step3 = dungeon.advance_exploration_step()
        self.assertGreaterEqual(step3["hazard_level"], 45)

        # 階層クリア
        clear_res = dungeon.clear_current_floor()
        self.assertTrue(clear_res["success"])
        self.assertEqual(clear_res["cleared_floor"], "投資信託部門 (Investment Sector)")
        self.assertEqual(clear_res["next_floor"], "負債回収部門 (Debt Collection Wing)")

    def test_04_master_bosses(self):
        """Step 23-32: マスタースキル保持者戦・専用弱点テスト"""
        boss_mgr = MasterBossManager()

        # 通常攻撃はバリアで大幅カット
        norm_atk = boss_mgr.attack_master_boss(
            "investment_boss", damage=1000, used_skill_name="Normal Slash"
        )
        self.assertEqual(norm_atk["remaining_hp"], 7800)  # 1000 * 0.2 = 200 dmg

        # 専用弱点（Fire + Ice 合成）でバリア破壊 & 3倍ダメージ
        weak_atk = boss_mgr.attack_master_boss(
            "investment_boss", damage=3000, used_skill_name="Instant Fusion: [Fire + Ice]"
        )
        self.assertTrue(weak_atk["weakness_hit"])
        self.assertTrue(weak_atk["boss_defeated"])
        self.assertIn("Concept Key of 投資信託部門", boss_mgr.collected_concept_keys)

    def test_05_concept_trials(self):
        """Step 33-37: 9柱の概念試練・特殊ルール適用テスト"""
        trials = ConceptTrialsManager()
        player_keys = ["Concept Key of 投資信託部門"]

        # 入場
        enter_res = trials.enter_trial("trial_of_time", player_keys)
        self.assertTrue(enter_res["success"])

        # 特殊ルール適用
        mod_stats = trials.apply_trial_rule_effect("trial_of_time", {"max_hp": 100})
        self.assertEqual(mod_stats["auto_regen"], 50)

        # クリア
        clear_res = trials.complete_trial("trial_of_time")
        self.assertTrue(clear_res["success"])
        self.assertIn("Chrono Mastery (先行確定)", clear_res["all_passives"])

    def test_06_world_law_override(self):
        """Step 38-48: 世界法則書き換え (Root Access) テスト"""
        world_hack = WorldLawOverrideManager()

        # 鍵不足で拒絶
        self.assertFalse(world_hack.grant_root_access(key_count=1)["success"])

        # Root Access 獲得
        self.assertTrue(world_hack.grant_root_access(key_count=2)["success"])

        # ダメージ上限撤廃と致死耐性ハック
        world_hack.override_damage_limit(999999)
        world_hack.override_fatal_survive(True)

        # 致死ダメージ適用テスト
        res = world_hack.calculate_modified_damage(raw_damage=50000, is_fatal=True, current_hp=100)
        self.assertEqual(res["effective_damage"], 50000)
        self.assertEqual(res["remaining_hp"], 1)  # 食いしばりハックでHP1残存
        self.assertTrue(res["survived_fatal_by_hack"])

    def test_07_slum_finale(self):
        """Step 49-53: スラム街同時進行最終防衛テスト"""
        slum = SlumFinaleManager(base_power=600)

        # Wave 1: 防衛成功
        w1 = slum.simulate_concurrent_defense(enemy_assault_power=500)
        self.assertEqual(w1["result"], "WAVE_REPELLED_PERFECTLY")

        # 最終局面ブースト
        boost = slum.trigger_final_stand_boost(player_encouragement_buff=400)
        self.assertEqual(boost["boosted_defensive_power"], 1000)

    def test_08_final_boss_causality_battle(self):
        """Step 54-62: ドン・ミダス因果律バトル・論理矛盾フリーズ・Phase 4移行テスト"""
        final_boss = FinalBossCausalityManager()

        # 第一形態 -> 第二形態への移行
        atk1 = final_boss.attack_don_midas("Overload Burst", damage=8000)
        self.assertEqual(atk1["phase"], 2)
        self.assertTrue(atk1["transition"])

        # 第二形態：通常の攻撃は因果律操作でキャンセルされる
        atk_cancel = final_boss.attack_don_midas("Mega Slash", damage=5000)
        self.assertTrue(atk_cancel["action_cancelled"])

        # 第二形態：論理矛盾行動でボスをフリーズさせる
        paradox_res = final_boss.attack_don_midas(
            "Paradox Heal-Attack", damage=0, is_paradox_combo=True
        )
        self.assertTrue(paradox_res["boss_frozen"])

        # フリーズ中に強制抽出コマンドでトドメ
        finish_res = final_boss.execute_core_extraction()
        self.assertTrue(finish_res["boss_defeated"])
        self.assertTrue(finish_res["phase3_completed"])
        self.assertEqual(finish_res["unlocked_phase"], 4)


if __name__ == "__main__":
    unittest.main()
