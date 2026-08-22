"""
test_skill_eater_presentation_integration.py
提案1〜9（全72ステップ）のEmote & Audio演出統合テストスイート
"""

from __future__ import annotations

import unittest
from pathlib import Path

from skill_eater_audio_system import AUDIO_DIR, SkillEaterAudioSystem
from skill_eater_combat_system import SkillEaterCombatSystem
from skill_eater_economy_system import SkillEaterEconomySystem
from skill_eater_exploration_system import SkillEaterExplorationSystem
from skill_eater_meta_quest_system import (
    GlobalRuleEngine,
    SkillEaterQuestSystem,
    SkillEaterReincarnationSystem,
)
from skill_eater_presentation_system import EMOTE_DIR, SkillEaterPresentationSystem
from skill_eater_servant_system import SkillEaterServantSystem
from skill_eater_synthesis_system import SkillEaterSynthesisSystem
from skill_eater_system import CharacterState, SkillEaterRegistry


class TestSkillEaterPresentationIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = SkillEaterRegistry.get_instance()
        yaml_path = Path(__file__).parents[1] / "data/worlds/skill_eater/skills.yaml"
        cls.registry.load_from_yaml(yaml_path)

    def setUp(self):
        SkillEaterAudioSystem.reset_instance()
        SkillEaterPresentationSystem.reset_instance()
        self.audio = SkillEaterAudioSystem.get_instance()
        self.presentation = SkillEaterPresentationSystem.get_instance()
        self.presentation.get_and_clear_events()
        self.audio.get_and_clear_played_sounds()

        self.combat = SkillEaterCombatSystem(self.registry, self.audio, self.presentation)
        self.synthesis = SkillEaterSynthesisSystem(self.registry, self.audio, self.presentation)
        self.servant = SkillEaterServantSystem(self.registry, self.audio, self.presentation)
        self.economy = SkillEaterEconomySystem(self.registry, self.audio, self.presentation)
        self.exploration = SkillEaterExplorationSystem(self.audio, self.presentation)
        self.rules = GlobalRuleEngine.get_instance()
        self.rules.reset_rules()
        self.rules.audio = self.audio
        self.rules.presentation = self.presentation
        self.quests = SkillEaterQuestSystem(self.registry, self.audio, self.presentation)
        self.reincarnation = SkillEaterReincarnationSystem(
            self.registry, self.audio, self.presentation
        )

    # 🎨 提案1: 演出基盤テスト (Steps 1〜8)
    def test_presentation_core_system(self):
        self.assertTrue(EMOTE_DIR.exists())
        self.assertTrue(AUDIO_DIR.exists())

        self.presentation.add_event(
            emote_file="emote_heart.png",
            audio_file="knifeSlice.ogg",
            message="テスト演出",
        )
        events = self.presentation.get_and_clear_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].emote_file, "emote_heart.png")
        self.assertEqual(events[0].audio_file, "knifeSlice.ogg")

    # ⚔️ 提案2: 基本戦闘のEmote & Audio演出 (Steps 9〜16)
    def test_combat_presentation_events(self):
        p1 = CharacterState(
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
        e1 = CharacterState(
            id="e1",
            name="スライム",
            hp=15,
            max_hp=15,
            mp=0,
            max_mp=0,
            atk=5,
            defense=5,
            intelligence=5,
            speed=5,
        )

        res = self.combat.execute_basic_attack(p1, e1)
        self.assertTrue(res.success)
        emotes = [evt.emote_file for evt in res.presentation_events]
        self.assertIn("emote_heartBroken.png", emotes)
        self.assertIn("emote_cross.png", emotes)

    # 🧬 提案3: 《喰らい》＆解析のEmote & Audio演出 (Steps 17〜24)
    def test_devour_presentation_events(self):
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
            analysis_level=8,
        )
        prey = CharacterState(
            id="e1",
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
        prey.add_skill("com_magic_001")

        # 1. 深度解析 (dots3, idea)
        scan_res = self.combat.analyze_target(predator, prey)
        emotes = [evt.emote_file for evt in scan_res.presentation_events]
        self.assertIn("emote_dots3.png", emotes)
        self.assertIn("emote_idea.png", emotes)

        # 2. 喰らい成功 (alert, star)
        dev_res = self.combat.execute_devour(predator, prey, "com_magic_001", force_success=True)
        self.assertTrue(dev_res.success)
        dev_emotes = [evt.emote_file for evt in dev_res.presentation_events]
        self.assertIn("emote_alert.png", dev_emotes)
        self.assertIn("emote_star.png", dev_emotes)

    # 🧪 提案4: 合成錬金のEmote & Audio演出 (Steps 25〜32)
    def test_synthesis_presentation_events(self):
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
        player.add_skill("com_magic_001")
        player.add_skill("com_labor_002")

        res = self.synthesis.synthesize(player, "com_magic_001", "com_labor_002")
        self.assertTrue(res.success)
        emotes = [evt.emote_file for evt in res.presentation_events]
        self.assertIn("emote_dots2.png", emotes)
        self.assertIn("emote_idea.png", emotes)
        self.assertIn("emote_stars.png", emotes)

    # 💰 提案5: 経済・闇市場のEmote & Audio演出 (Steps 33〜40)
    def test_economy_presentation_events(self):
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

        self.economy.sell_skill_to_normal_market(player, "com_combat_001")
        events = self.presentation.get_and_clear_events()
        self.assertTrue(any(e.emote_file == "emote_cash.png" for e in events))

    # 🧳 提案6: 従属者移植＆自壊演出 (Steps 41〜48)
    def test_servant_presentation_events(self):
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
        husk = CharacterState(
            id="h1",
            name="空体",
            hp=10,
            max_hp=10,
            mp=0,
            max_mp=0,
            atk=5,
            defense=5,
            intelligence=5,
            speed=5,
            is_husk=True,
        )
        servant = self.servant.capture_husk(husk)

        self.servant.transplant_skill(player, servant, "com_combat_001")
        events = self.presentation.get_and_clear_events()
        self.assertTrue(any(e.emote_file == "emote_heart.png" for e in events))

    # 🚪 提案7: 探索・環境演出 (Steps 49〜56)
    def test_exploration_presentation_events(self):
        chest_res = self.exploration.open_treasure_chest()
        self.assertEqual(chest_res.presentation_events[0].emote_file, "emote_star.png")

        escape_res = self.exploration.escape_combat()
        self.assertEqual(escape_res.presentation_events[0].emote_file, "emote_drops.png")

    # 💻 提案8: メタシステムと法則書き換え演出 (Steps 57〜64)
    def test_meta_presentation_events(self):
        hacker = CharacterState(
            id="p1",
            name="主人公",
            hp=100,
            max_hp=100,
            mp=50,
            max_mp=50,
            atk=10,
            defense=10,
            intelligence=100,
            speed=10,
        )
        self.rules.root_access_granted = True
        self.rules.override_rule("damage_multiplier", 2.0, cost_type="MAX_HP", player=hacker)

        events = self.presentation.get_and_clear_events()
        emotes = [e.emote_file for e in events]
        self.assertIn("emote_exclamations.png", emotes)
        self.assertIn("emote_stars.png", emotes)

    # 🎧 提案9: ON/OFF切り替えテスト (Steps 65〜72)
    def test_presentation_toggle(self):
        self.presentation.set_enabled(False)
        self.presentation.add_event(emote_file="emote_star.png", audio_file="knifeSlice.ogg")
        events = self.presentation.get_and_clear_events()
        self.assertEqual(len(events), 0)
        self.presentation.set_enabled(True)


if __name__ == "__main__":
    unittest.main()
