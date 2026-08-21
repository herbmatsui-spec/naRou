"""
test_skill_eater_full_72_steps.py
全72ステップ（9つの改善案）を包括的に検証する総合ユニットテストスイート
"""
from __future__ import annotations

import unittest
from pathlib import Path

from skill_eater_combat_system import SkillEaterCombatSystem
from skill_eater_economy_system import SkillEaterEconomySystem
from skill_eater_meta_quest_system import (
    GlobalRuleEngine,
    SkillEaterQuestSystem,
    SkillEaterReincarnationSystem,
)
from skill_eater_servant_system import SkillEaterServantSystem
from skill_eater_synthesis_system import SkillEaterSynthesisSystem
from skill_eater_system import (
    CharacterState,
    SkillDef,
    SkillEaterRegistry,
    SkillTier,
    SkillType,
)


class TestSkillEater72Steps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = SkillEaterRegistry.get_instance()
        yaml_path = Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"
        cls.registry.load_from_yaml(yaml_path)

    def setUp(self):
        self.combat = SkillEaterCombatSystem(self.registry)
        self.synthesis = SkillEaterSynthesisSystem(self.registry)
        self.servant = SkillEaterServantSystem(self.registry)
        self.economy = SkillEaterEconomySystem(self.registry)
        self.rules = GlobalRuleEngine.get_instance()
        self.rules.reset_rules()
        self.quests = SkillEaterQuestSystem(self.registry)
        self.reincarnation = SkillEaterReincarnationSystem(self.registry)

    # 💡 改善案1: 違法合成品フラグ＆警戒度監査官レイド (Steps 1-8)
    def test_improvement_1_illegal_synthesis_and_inspector_raid(self):
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
        player.add_skill("com_combat_001")
        player.add_skill("com_magic_001")

        # 動的合成
        syn_res = self.synthesis.synthesize(player, "com_combat_001", "com_magic_001")
        self.assertTrue(syn_res.success)
        self.assertTrue(syn_res.result_skill.is_illegal)

        # 正規市場では売却拒絶
        ok_norm, _, _ = self.economy.sell_skill_to_normal_market(
            player, syn_res.result_skill.id
        )
        self.assertFalse(ok_norm)

        # 闇市場で売却するとheat_level上昇
        ok_blk, _, _ = self.economy.sell_skill_to_black_market(
            player, syn_res.result_skill.id
        )
        self.assertTrue(ok_blk)
        self.assertEqual(self.economy.heat_level, 10)

        # heat_level 100 で監査官レイド発生
        self.economy.heat_level = 100
        is_raid, inspector, _ = self.economy.check_inspector_raid()
        self.assertTrue(is_raid)
        self.assertIsNotNone(inspector)
        self.assertEqual(self.economy.heat_level, 0)

    # 💡 改善案2: 従属者タレット化と自壊 (Steps 9-16)
    def test_improvement_2_servant_turret_crumble(self):
        husk_enemy = CharacterState(
            id="husk1",
            name="警備兵",
            hp=10,
            max_hp=50,
            mp=0,
            max_mp=10,
            atk=10,
            defense=5,
            intelligence=5,
            speed=5,
            is_husk=True,
        )
        servant = self.servant.capture_husk(husk_enemy)
        self.assertEqual(servant.duration_turns, 3)

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
        player.add_skill("com_combat_001")
        self.servant.transplant_skill(player, servant, "com_combat_001")

        enemy = CharacterState(
            id="e1",
            name="敵",
            hp=50,
            max_hp=50,
            mp=0,
            max_mp=0,
            atk=5,
            defense=5,
            intelligence=5,
            speed=5,
        )

        # 3回行動で自壊
        self.servant.execute_servant_turn(servant, [enemy], [player])
        self.assertEqual(servant.duration_turns, 2)
        self.servant.execute_servant_turn(servant, [enemy], [player])
        self.assertEqual(servant.duration_turns, 1)
        res3 = self.servant.execute_servant_turn(servant, [enemy], [player])
        self.assertTrue(res3.is_crumbled)
        self.assertNotIn(servant.id, self.servant.servant_party)

    # 💡 改善案3: 喰らいシナジー＆消化不良 (Steps 17-24)
    def test_improvement_3_devour_synergy_and_indigestion(self):
        predator = CharacterState(
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
            analysis_level=5,
        )

        # 1回目: 炎スキルを喰らう
        prey1 = CharacterState(
            id="f1",
            name="炎術士",
            hp=10,
            max_hp=50,
            mp=0,
            max_mp=0,
            atk=5,
            defense=5,
            intelligence=5,
            speed=5,
        )
        prey1.add_skill("com_magic_001")  # Fire
        self.combat.execute_devour(predator, prey1, "com_magic_001", force_success=True)
        self.assertEqual(predator.last_devoured_element, "Fire")

        # 2回目: 水スキルを喰らう ➔ 消化不良自傷
        prey2 = CharacterState(
            id="w1",
            name="水術士",
            hp=10,
            max_hp=50,
            mp=0,
            max_mp=0,
            atk=5,
            defense=5,
            intelligence=5,
            speed=5,
        )
        water_skill = SkillDef(
            id="w_skill",
            name="水鉄砲",
            tier=SkillTier.COMMON,
            type=SkillType.ACTIVE,
            tags=["Water"],
        )
        self.registry._skills["w_skill"] = water_skill
        prey2.add_skill("w_skill")

        init_hp = predator.hp
        self.combat.execute_devour(predator, prey2, "w_skill", force_success=True)
        self.assertLess(predator.hp, init_hp)  # 消化不良自傷
        self.assertEqual(predator.last_devoured_element, "Water")

    # 💡 改善案4: メモリ容量制限＆任意破棄 (Steps 25-32)
    def test_improvement_4_memory_capacity_and_discard(self):
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
            max_memory_capacity=5,
        )

        # Uniqueスキル（容量4）
        self.assertTrue(player.add_skill("uni_midas_001"))
        self.assertEqual(player.current_memory_usage, 4)

        # 別のRareスキル（容量2）を追加しようとするとメモリ超過でブロック
        self.assertFalse(player.add_skill("rar_combat_012"))

        # スキル破棄で空きを作る
        succ_disc, _, _, _ = self.combat.discard_skill(player, "uni_midas_001")
        self.assertTrue(succ_disc)
        self.assertEqual(player.current_memory_usage, 0)
        self.assertTrue(player.add_skill("rar_combat_012"))

    # 💡 改善案5: 多重解釈型メタ特効 (Steps 33-40)
    def test_improvement_5_multi_meta_counter_strategies(self):
        player = CharacterState(
            id="p1",
            name="主人公",
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            atk=10,
            defense=20,
            intelligence=10,
            speed=10,
        )

        # 対策なし
        succ, _ = self.quests.check_boss_meta_counter(player, "midas_ceo")
        self.assertFalse(succ)

        # 戦略1: 高防御力 (defense >= 80)
        player.defense = 85
        succ_stat, _ = self.quests.check_boss_meta_counter(player, "midas_ceo")
        self.assertTrue(succ_stat)
        self.assertFalse(self.rules.is_boss_instant_kill_enabled)

        # 戦略2: コモンスキル身代わり破壊
        self.rules.is_boss_instant_kill_enabled = True
        player.defense = 10
        player.add_skill("com_labor_001")  # Common
        succ_sac, _ = self.quests.check_boss_meta_counter(player, "midas_ceo")
        self.assertTrue(succ_sac)
        self.assertFalse(player.has_skill("com_labor_001"))  # 身代わりで消失

    # 💡 改善案6: コスト消費型法則書き換え (Steps 41-48)
    def test_improvement_6_cost_based_rule_override(self):
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
        self.rules.root_access_granted = True

        # 1回目書き換え（HP 20消費）
        succ, _msg, _ = self.rules.override_rule(
            "damage_multiplier", 3.0, cost_type="MAX_HP", player=player
        )
        self.assertTrue(succ)
        self.assertEqual(player.max_hp, 80)
        self.assertEqual(self.rules.override_count, 1)

        # 2回目書き換え（HP 40消費）
        succ2, _msg2, _ = self.rules.override_rule(
            "damage_multiplier", 5.0, cost_type="MAX_HP", player=player
        )
        self.assertTrue(succ2)
        self.assertEqual(player.max_hp, 40)
        self.assertEqual(self.rules.override_count, 2)

        # 3回目（HP 80要求 ➔ HP40のため不足で失敗）
        succ3, _msg3, _ = self.rules.override_rule(
            "damage_multiplier", 10.0, cost_type="MAX_HP", player=player
        )
        self.assertFalse(succ3)

    # 💡 改善案7: 世界の初期値変動＆輪廻転生 (Steps 49-56)
    def test_improvement_7_dynamic_world_reincarnation(self):
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

        # 前世で炎属性を乱獲
        self.reincarnation.record_devoured_element("Fire")
        self.reincarnation.record_devoured_element("Fire")

        old_fire_val = self.registry.get_skill("com_magic_001").market_value

        _new_player, _msg = self.reincarnation.process_reincarnation(player, [])
        self.assertEqual(
            self.reincarnation.meta_state.dominant_element_last_life, "Fire"
        )

        new_fire_val = self.registry.get_skill("com_magic_001").market_value
        self.assertLess(new_fire_val, old_fire_val)  # 炎スキルが暴落

    # 💡 改善案8: スキル精神侵食デバフ (Steps 57-64)
    def test_improvement_8_addiction_buildup(self):
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
        player.add_skill("uni_midas_001")  # Unique (+5 per turn)
        player.add_skill("con_fire_001")  # Concept (+10 per turn)

        # 7ターン経過 (15 * 7 = 105 ➔ 100)
        for _ in range(7):
            self.combat.process_turn_end(player)

        self.assertEqual(player.addiction_buildup, 100)
        self.assertIn("Addicted", player.status_effects)

    # 💡 改善案9: 偽装解析＆ハッキング (Steps 65-72)
    def test_improvement_9_encryption_and_hack(self):
        analyzer = CharacterState(
            id="p1",
            name="主人公",
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            atk=10,
            defense=10,
            intelligence=50,
            speed=10,
            analysis_level=8,
        )
        boss = CharacterState(
            id="boss",
            name="ミダスCEO",
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            atk=10,
            defense=10,
            intelligence=10,
            speed=10,
        )
        boss.add_skill("uni_midas_001")  # Encrypted

        # ハック前: 暗号化されている
        scan_pre = self.combat.analyze_target(analyzer, boss)
        info_pre = next(
            s for s in scan_pre.revealed_skills if s.skill_id == "uni_midas_001"
        )
        self.assertTrue(info_pre.is_encrypted)
        self.assertEqual(info_pre.name, "【暗号化プロテクト中】")

        # ハック実行
        boss.encryption_broken = True  # ハック成功状態
        scan_post = self.combat.analyze_target(analyzer, boss)
        info_post = next(
            s for s in scan_post.revealed_skills if s.skill_id == "uni_midas_001"
        )
        self.assertFalse(info_post.is_encrypted)
        self.assertEqual(info_post.name, "黄金錬成")


if __name__ == "__main__":
    unittest.main()
