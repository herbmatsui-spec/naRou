"""
test_skill_eater_audio_integration.py
提案1〜9（全72ステップ）のオーディオ演出・音響統合テストスイート
"""

import unittest
from pathlib import Path
from skill_eater_system import (
    SkillEaterRegistry,
    SkillDef,
    SkillTier,
    SkillType,
    CharacterState
)
from skill_eater_audio_system import SkillEaterAudioSystem, AUDIO_DIR
from skill_eater_combat_system import SkillEaterCombatSystem
from skill_eater_synthesis_system import SkillEaterSynthesisSystem
from skill_eater_servant_system import SkillEaterServantSystem
from skill_eater_economy_system import SkillEaterEconomySystem
from skill_eater_exploration_system import SkillEaterExplorationSystem
from skill_eater_meta_quest_system import (
    GlobalRuleEngine,
    SkillEaterQuestSystem,
    SkillEaterReincarnationSystem
)


class TestSkillEaterAudioIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = SkillEaterRegistry.get_instance()
        yaml_path = Path("e:/narou2/data/worlds/skill_eater/skills.yaml")
        cls.registry.load_from_yaml(yaml_path)

    def setUp(self):
        SkillEaterAudioSystem.reset_instance()
        self.audio = SkillEaterAudioSystem.get_instance()
        self.audio.get_and_clear_played_sounds()

        self.combat = SkillEaterCombatSystem(self.registry, self.audio)
        self.synthesis = SkillEaterSynthesisSystem(self.registry, self.audio)
        self.servant = SkillEaterServantSystem(self.registry, self.audio)
        self.economy = SkillEaterEconomySystem(self.registry, self.audio)
        self.exploration = SkillEaterExplorationSystem(self.audio)
        self.rules = GlobalRuleEngine.get_instance()
        self.rules.reset_rules()
        self.rules.audio = self.audio
        self.quests = SkillEaterQuestSystem(self.registry, self.audio)
        self.reincarnation = SkillEaterReincarnationSystem(self.registry, self.audio)

    # 🔊 提案1: オーディオ基盤テスト (Steps 1〜8)
    def test_audio_core_system(self):
        self.assertTrue(AUDIO_DIR.exists())
        self.audio.play_sound("knifeSlice.ogg")
        sounds = self.audio.get_and_clear_played_sounds()
        self.assertEqual(sounds, ["knifeSlice.ogg"])
        self.assertEqual(len(self.audio.played_sounds), 0)

    # ⚔️ 提案2: 基本戦闘SEテスト (Steps 9〜16)
    def test_combat_basic_attack_sounds(self):
        p1 = CharacterState(id="p1", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=20, defense=10, intelligence=10, speed=10)
        e1 = CharacterState(id="e1", name="スライム", hp=15, max_hp=15, mp=0, max_mp=0, atk=5, defense=5, intelligence=5, speed=5)

        res = self.combat.execute_basic_attack(p1, e1)
        self.assertTrue(res.success)
        self.assertIn("dropLeather.ogg", res.played_sounds)  # 撃破で倒れる音

    # 🧬 提案3: 《喰らい》＆シナジーSEテスト (Steps 17〜24)
    def test_devour_and_synergy_sounds(self):
        predator = CharacterState(id="p1", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=10, defense=10, intelligence=10, speed=10, analysis_level=8)
        
        # 1. 深度解析 (Step 22, 23: metalClick, metalLatch)
        prey = CharacterState(id="e1", name="炎術士", hp=10, max_hp=50, mp=0, max_mp=0, atk=5, defense=5, intelligence=5, speed=5)
        prey.add_skill("com_magic_001")  # Fire
        scan_res = self.combat.analyze_target(predator, prey)
        self.assertIn("metalClick.ogg", scan_res.played_sounds)
        self.assertIn("metalLatch.ogg", scan_res.played_sounds)

        # 2. 喰らい発動＆成功 (Step 17, 18: clothBelt, handleSmallLeather2)
        dev_res = self.combat.execute_devour(predator, prey, "com_magic_001", force_success=True)
        self.assertTrue(dev_res.success)
        self.assertIn("clothBelt.ogg", dev_res.played_sounds)
        self.assertIn("handleSmallLeather2.ogg", dev_res.played_sounds)

        # 3. 2連喰らいで爆発シナジー (Step 20: metalPot1)
        prey_wind = CharacterState(id="w1", name="風術士", hp=10, max_hp=50, mp=0, max_mp=0, atk=5, defense=5, intelligence=5, speed=5)
        wind_skill = SkillDef(id="wind_01", name="突風", tier=SkillTier.COMMON, type=SkillType.ACTIVE, tags=["Wind"])
        self.registry._skills["wind_01"] = wind_skill
        prey_wind.add_skill("wind_01")

        dev_res2 = self.combat.execute_devour(predator, prey_wind, "wind_01", force_success=True)
        self.assertIn("metalPot1.ogg", dev_res2.played_sounds)

    # 🧪 提案4: 合成錬金SEテスト (Steps 25〜32)
    def test_synthesis_audio(self):
        player = CharacterState(id="p1", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=10, defense=10, intelligence=10, speed=10)
        player.add_skill("com_magic_001")
        player.add_skill("com_labor_002")

        # 静的レシピ合成 (metalPot2, bookOpen, bookFlip1, metalPot3)
        res = self.synthesis.synthesize(player, "com_magic_001", "com_labor_002")
        self.assertTrue(res.success)
        self.assertIn("metalPot2.ogg", res.played_sounds)
        self.assertIn("bookOpen.ogg", res.played_sounds)
        self.assertIn("metalPot3.ogg", res.played_sounds)

    # 💰 提案5: 経済・闇市場SEテスト (Steps 33〜40)
    def test_economy_audio(self):
        player = CharacterState(id="p1", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=10, defense=10, intelligence=10, speed=10)
        illegal_skill = SkillDef(id="ill_01", name="違法キメラ", tier=SkillTier.RARE, type=SkillType.ACTIVE, market_value=5000, is_illegal=True)
        self.registry._skills["ill_01"] = illegal_skill
        player.add_skill("ill_01")

        # 闇市場密売 (handleCoins, doorClose_1)
        self.economy.sell_skill_to_black_market(player, "ill_01")
        sounds = self.audio.get_and_clear_played_sounds()
        self.assertIn("handleCoins.ogg", sounds)
        self.assertIn("doorClose_1.ogg", sounds)

        # 支店買収 (doorOpen_2, handleCoins)
        self.economy.takeover_branch("第2支店", 1000)
        sounds2 = self.audio.get_and_clear_played_sounds()
        self.assertIn("doorOpen_2.ogg", sounds2)
        self.assertIn("handleCoins.ogg", sounds2)

    # 🧳 提案6: 従属者移植＆自壊SEテスト (Steps 41〜48)
    def test_servant_audio(self):
        player = CharacterState(id="p1", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=10, defense=10, intelligence=10, speed=10)
        player.add_skill("com_combat_001")

        husk = CharacterState(id="h1", name="空体", hp=10, max_hp=10, mp=0, max_mp=0, atk=5, defense=5, intelligence=5, speed=5, is_husk=True)
        servant = self.servant.capture_husk(husk)

        # 移植音 (beltHandle1)
        self.servant.transplant_skill(player, servant, "com_combat_001")
        sounds = self.audio.get_and_clear_played_sounds()
        self.assertIn("beltHandle1.ogg", sounds)

        # 寿命自壊 (cloth3, creak3)
        servant.duration_turns = 1
        dummy_enemy = CharacterState(id="e1", name="敵", hp=100, max_hp=100, mp=0, max_mp=0, atk=5, defense=5, intelligence=5, speed=5)
        res = self.servant.execute_servant_turn(servant, [dummy_enemy], [player])
        self.assertTrue(res.is_crumbled)
        self.assertIn("cloth3.ogg", res.played_sounds)
        self.assertIn("creak3.ogg", res.played_sounds)

    # 🚪 提案7: 探索・ダンジョンSEテスト (Steps 49〜56)
    def test_exploration_audio(self):
        step_res = self.exploration.step_forward()
        self.assertTrue(step_res.played_sounds[0].startswith("footstep"))

        move_res = self.exploration.move_to_room("vault_chamber")
        self.assertIn("doorOpen_1.ogg", move_res.played_sounds)

        chest_res = self.exploration.open_treasure_chest()
        self.assertIn("metalLatch.ogg", chest_res.played_sounds)

        escape_res = self.exploration.escape_combat()
        self.assertIn("cloth1.ogg", escape_res.played_sounds)

    # 💻 提案8: メタ書き換え＆輪廻転生SEテスト (Steps 57〜64)
    def test_meta_override_and_reincarnation_audio(self):
        # 1. ハッキング (metalClick, metalLatch, bookOpen)
        hacker = CharacterState(id="p1", name="主人公", hp=100, max_hp=100, mp=50, max_mp=50, atk=10, defense=10, intelligence=100, speed=10)
        target = CharacterState(id="boss", name="ボス", hp=100, max_hp=100, mp=50, max_mp=50, atk=10, defense=10, intelligence=10, speed=10)
        
        hack_res = self.combat.execute_hack(hacker, target)
        self.assertIn("metalClick.ogg", hack_res.played_sounds)
        self.assertIn("metalLatch.ogg", hack_res.played_sounds)

        # 2. 法則書き換え (bookFlip3, metalPot3, doorClose_4)
        self.rules.root_access_granted = True
        self.rules.override_rule("damage_multiplier", 2.0, cost_type="MAX_HP", player=hacker)
        sounds = self.audio.get_and_clear_played_sounds()
        self.assertIn("bookFlip3.ogg", sounds)
        self.assertIn("doorClose_4.ogg", sounds)

        # 3. 輪廻転生 (doorClose_3, bookClose, doorOpen_2, footstep00)
        new_player, _ = self.reincarnation.process_reincarnation(hacker, [])
        sounds_reinc = self.audio.get_and_clear_played_sounds()
        self.assertIn("doorClose_3.ogg", sounds_reinc)
        self.assertIn("bookClose.ogg", sounds_reinc)
        self.assertIn("doorOpen_2.ogg", sounds_reinc)

    # 🎧 提案9: ミュート＆セーフフォールバック (Steps 65〜72)
    def test_mute_setting(self):
        self.audio.set_mute(True)
        ok = self.audio.play_sound("knifeSlice.ogg")
        self.assertFalse(ok)
        self.assertEqual(len(self.audio.played_sounds), 0)


if __name__ == "__main__":
    unittest.main()
