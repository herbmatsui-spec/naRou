"""
Skill Eater Phase 2: Comprehensive Integration Test (Steps 68-71)
Step 1〜67で実装した全9システムの結合テスト。
"""

import unittest

from skill_eater_base_defense import BaseDefenseManager
from skill_eater_base_expansion import SlumBaseExpansionManager
from skill_eater_boss_anti_meta import AntiMetaBossBattleManager
from skill_eater_bounty_system import MidasBountyManager
from skill_eater_env_puzzles import EnvironmentalPuzzleManager
from skill_eater_pet_dispatch import PetDispatchManager
from skill_eater_rampage_events import SkillRampageManager
from skill_eater_toxicity_overdrive import ToxicityOverdriveManager
from skill_eater_underground_arena import UndergroundArenaManager


class TestSkillEaterPhase2(unittest.TestCase):
    def test_01_toxicity_overdrive(self):
        """Step 1-6: オーバードライブ、バフ、反動気絶のテスト"""
        manager = ToxicityOverdriveManager(trigger_threshold=100.0, duration_turns=2)
        self.assertFalse(manager.can_trigger_overdrive(50.0))
        self.assertTrue(manager.can_trigger_overdrive(120.0))

        # 発動
        res = manager.trigger_overdrive(120.0)
        self.assertTrue(res["success"])
        buffs = manager.get_overdrive_buffs()
        self.assertEqual(buffs["atk_multiplier"], 3.0)

        # ターン進行 (1ターン目)
        t1 = manager.tick_turn(current_hp=100, max_hp=100)
        self.assertTrue(t1["is_active"])

        # ターン進行 (2ターン目 -> 効果終了 & 反動)
        t2 = manager.tick_turn(current_hp=100, max_hp=100)
        self.assertFalse(t2["is_active"])
        self.assertTrue(t2["is_stunned"])
        self.assertEqual(t2["remaining_hp"], 70)  # 30% HP反動ダメージ

    def test_02_slum_base_expansion(self):
        """Step 7-16: 拠点拡張、Tierアップ、モニュメントのテスト"""
        manager = SlumBaseExpansionManager()
        self.assertEqual(manager.base_tier, 1)

        # Tier 2へ投資
        res = manager.invest_resources(junk_amount=600, skill_point_amount=6)
        self.assertEqual(manager.base_tier, 2)
        self.assertIn("cyber_lab", manager.unlocked_facilities)

        # モニュメント建設
        mon_res = manager.unlock_special_monument("Absolute Glitch")
        self.assertTrue(mon_res["success"])
        self.assertIn("Monument of Absolute Glitch", manager.built_monuments)

    def test_03_pet_dispatch(self):
        """Step 17-23: ペット派遣・適合度・治療のテスト"""
        manager = PetDispatchManager()

        # 適合度チェック
        suit = manager.check_dispatch_suitability("husk_hound_01", "midas_scrap_dump")
        self.assertTrue(suit["can_dispatch"])
        self.assertEqual(suit["match_rate"], 1.0)

        # 派遣開始
        dispatch_res = manager.start_dispatch("husk_hound_01", "midas_scrap_dump", duration_turns=3)
        self.assertTrue(dispatch_res["success"])

        # 探索成功処理
        res = manager.resolve_dispatch("husk_hound_01", force_success=True)
        self.assertEqual(res["result"], "MISSION_ACCOMPLISHED")
        self.assertEqual(res["rewards"]["junk"], 150)

    def test_04_underground_arena(self):
        """Step 24-32: 地下闘技場・DPS計測・制約テスト"""
        arena = UndergroundArenaManager()
        start = arena.start_arena_session(challenge_mode="NO_MAGIC")
        self.assertTrue(start["success"])

        # 魔法攻撃（制約違反）
        magic_atk = arena.simulate_attack(player_damage=500, skill_type="Magic")
        self.assertFalse(magic_atk["success"])

        # 物理攻撃（成功 & DPS計測）
        phys_atk = arena.simulate_attack(player_damage=600, skill_type="Physical")
        self.assertTrue(phys_atk["success"])
        self.assertEqual(phys_atk["damage_dealt"], 600)

        # クリア
        clear_res = arena.complete_wave()
        self.assertTrue(clear_res["success"])
        self.assertEqual(clear_res["cleared_wave"], 1)

    def test_05_environmental_puzzles(self):
        """Step 33-39: 環境ギミックの解除とトラップテスト"""
        puzzles = EnvironmentalPuzzleManager()

        # スキル不足で失敗 -> トラップダメージ
        fail_res = puzzles.attempt_solve_puzzle(
            "neon_security_gate", ["Fire Magic"], player_power=60
        )
        self.assertFalse(fail_res["success"])
        self.assertEqual(fail_res["trap_damage"], 35)

        # スキル充足で成功
        success_res = puzzles.attempt_solve_puzzle(
            "neon_security_gate", ["Lightning Magic", "Network Hacking"], player_power=60
        )
        self.assertTrue(success_res["success"])
        self.assertTrue(success_res["opened_gate"])

    def test_06_skill_rampage_events(self):
        """Step 40-48: スキル暴走発生と討伐ドロップのテスト"""
        rampage = SkillRampageManager()

        # 強制暴走発生
        res = rampage.trigger_synthesis_with_rampage_check(
            "Absolute Black Hole", skill_tier=3, force_rampage=True
        )
        self.assertTrue(res["rampage"])
        boss_id = res["spawned_boss"]["boss_id"]

        # 討伐と安定化スキルの回収
        defeat_res = rampage.defeat_rampage_boss(boss_id)
        self.assertTrue(defeat_res["success"])
        self.assertIn("Stabilized Absolute Black Hole", defeat_res["reward_skill"])

    def test_07_bounty_and_base_defense(self):
        """Step 49-61: 幹部ハイスト & 拠点防衛戦の連携テスト"""
        bounty = MidasBountyManager()
        defense = BaseDefenseManager(base_max_hp=500)

        # 幹部情報収集 & 罠設置
        bounty.gather_intel("exec_01_valerius")
        bounty.set_ambush_trap("exec_01_valerius")
        combat_info = bounty.initiate_combat("exec_01_valerius")
        self.assertEqual(combat_info["effective_hp"], 2100)  # 3000 * 0.7

        # 討伐
        kill_res = bounty.eliminate_executive("exec_01_valerius")
        self.assertTrue(kill_res["success"])

        # 警戒度上昇 -> 防衛戦
        alert = defense.increase_alert(100)
        self.assertTrue(alert["raid_triggered"])

        defense.start_defense_battle()
        defense.place_defense_trap("Spike Gate", damage=200)

        # レイドウェーブ処理（トラップで敵戦力軽減）
        wave_res = defense.process_raid_wave(enemy_power=250)
        self.assertEqual(wave_res["trap_damage_mitigated"], 200)
        self.assertEqual(wave_res["base_damage_taken"], 50)
        self.assertEqual(wave_res["base_hp_remaining"], 450)

    def test_08_anti_meta_boss_battle(self):
        """Step 62-67: 対メタ中ボス戦とPhase 3移行フラグテスト"""
        boss = AntiMetaBossBattleManager()

        # 通常の高火力攻撃は1ダメージに無効化される
        atk1 = boss.process_player_attack(raw_damage=1000, used_skill="Super Mega Slash")
        self.assertEqual(atk1["damage_taken"], 1)
        self.assertTrue(atk1["barrier_triggered"])

        # 弱点ジャンクスキルでバリアを破る
        atk2 = boss.process_player_attack(raw_damage=100, used_skill="Glitched Junk Shot")
        self.assertEqual(atk2["damage_taken"], 300)
        self.assertFalse(boss.meta_barriers["high_dps_nullification"])

        # ボス撃破
        kill_atk = boss.process_player_attack(raw_damage=15000, used_skill="All-Out Glitch Attack")
        self.assertTrue(kill_atk["boss_defeated"])
        self.assertTrue(kill_atk["phase2_completed"])
        self.assertEqual(kill_atk["unlocked_phase"], 3)

    def test_09_facility_alternative_cost_upgrade(self):
        """Step 33-46: 必須スキル未所持時の代替アルド支払い拡張テスト"""
        from skill_eater_economy_system import SkillEaterEconomySystem
        from skill_eater_system import CharacterState

        eco = SkillEaterEconomySystem()
        player = CharacterState(
            id="hero",
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
        # rehab_lab requires rar_utility_005, cost=2000, alternative_cost=10000 -> total 12000

        # Case 1: Insufficient funds & no skill -> False
        eco.aldo_currency = 5000
        ok, msg = eco.upgrade_facility(player, "rehab_lab")
        self.assertFalse(ok)
        self.assertIn("強化には企業秘密スキル", msg)

        # Case 2: Enough funds for alternative cost -> True
        eco.aldo_currency = 15000
        ok, msg = eco.upgrade_facility(player, "rehab_lab")
        self.assertTrue(ok)
        self.assertIn("闇ルート決済", msg)
        self.assertEqual(eco.aldo_currency, 3000)  # 15000 - 12000
        self.assertEqual(eco.base_facilities["rehab_lab"].level, 2)


if __name__ == "__main__":
    unittest.main()
