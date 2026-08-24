#!/usr/bin/env python
"""
Meta Intervention System Demo (ASCII version for Windows console)
Demonstrates the complete flow: template generation -> original text view -> intervention -> rewards -> reincarnation
"""

import sys
sys.path.insert(0, '.')

from naRou.systems.skill_eater_template_model import load_templates
from naRou.systems.skill_eater_meta_intervention_system import (
    TemplateEventGenerator, InterventionEngine, InterventionAction
)
from naRou.skill_eater_presentation_system import SkillEaterPresentationSystem
from naRou.skill_eater_audio_system import SkillEaterAudioSystem
from naRou.systems.skill_eater_meta_quest_system import (
    SkillEaterReincarnationSystem, ReincarnationMetaState
)
from naRou.systems.meta_awareness_system import MetaAwarenessSystem
import random


class DemoPlayer:
    def __init__(self, name="Player"):
        self.name = name
        self.gold = 500
        self.skills = set()
        self.karma_law_chaos = 0
        self.karma_good_evil = 0
        self.template_exposure = 0
        self.scenario_flags = {}

    def has_skill(self, skill_id: str) -> bool:
        return skill_id in self.skills

    def add_skill(self, skill_id: str):
        self.skills.add(skill_id)
        print(f"  [SKILL] Acquired: {skill_id}")

    def __repr__(self):
        return f"{self.name}(Gold:{self.gold}, Exposure:{self.template_exposure}, L/C:{self.karma_law_chaos}, G/E:{self.karma_good_evil})"


class DemoRuleEngine:
    def __init__(self):
        self.rules = {}

    def override_rule(self, rule_name: str, value: Any, cost_type: str = "KARMA", available_karma: int = 10000) -> tuple[bool, str, int]:
        self.rules[rule_name] = value
        print(f"  [RULE] World law changed: {rule_name} = {value} (cost: {cost_type})")
        return True, f"Rule {rule_name} set to {value}", 0


class DemoMetaState:
    def __init__(self):
        self.total_karma_points = 0
        self.devoured_template_counts = {}
        self.devoured_element_counts = {}
        self.dominant_element_last_life = None
        self.unlocked_secrets = []
        self.loop_count = 1


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_step(step: str):
    print(f"\n  -> {step}")


def main():
    print_section("Meta Intervention System Demo")

    # Setup
    templates = load_templates("data/templates")
    audio = SkillEaterAudioSystem()
    pres = SkillEaterPresentationSystem(audio_system=audio, is_mock_only=True)
    rule_engine = DemoRuleEngine()
    meta_state = DemoMetaState()
    meta_state.total_karma_points = 5000

    generator = TemplateEventGenerator(templates, rng=random.Random(42))
    engine = InterventionEngine(
        registry=None, presentation=pres, rule_engine=rule_engine, meta_state=meta_state, templates=templates
    )
    awareness = MetaAwarenessSystem.get_instance()
    awareness.awareness_level = 6

    player = DemoPlayer("Hero")
    player.skills.add("negotiation")

    # Phase 1: Template Event Generation
    print_section("Phase 1: Template Event Generation (Slum Exploration)")

    print_step("Exploring slum...")
    event = generator.maybe_spawn("slum", current_turn=100, loop_count=1, spawn_chance=1.0)

    if event:
        print(f"  Event spawned: {event.template_id}")
        print(f"  Archetype: {event.archetype}")
        print(f"  Context: {event.context}")
        print(f"  Faction: {event.faction}")
        print(f"  Difficulty: {event.difficulty:.2f}")
        print(f"  Exploit windows: {len(event.exploit_windows)}")
        for w in event.exploit_windows:
            print(f"    - [{w.id}] Tier:{w.tier} Success:{w.base_success:.0%} Gold:{w.req_gold} Skills:{w.req_skill}")
    else:
        print("  No event spawned")
        return

    # Phase 2: Original Text View
    print_section("Phase 2: Original Text View - Scenario Flag Reading")

    print_step("Scanning target NPC for template flags...")
    target = type("Target", (), {
        "name": "Incompetent Adventurer A",
        "scenario_flags": {"expel": 0.85, "betray": 0.1}
    })()

    detected = awareness.trigger_template_scan(target, presentation=pres)

    if detected:
        for d in detected:
            print(f"  [DETECTED] {d['archetype']} (weight: {d['weight']:.2f})")

    print_step(f"Reading depth: {awareness.get_reading_depth()} (Full reading)")
    windows = awareness.get_exploit_windows(
        type("Tpl", (), {"exploit_windows": event.exploit_windows})(),
        awareness.get_reading_depth()
    )
    print(f"  Available exploit windows: {len(windows)}")
    for w in windows:
        print(f"    - {w.id} (Tier {w.tier})")

    print_step("Paying deep reading cost...")
    awareness.apply_deep_read_cost(player, depth=3)
    print(f"  Law/Chaos: {player.karma_law_chaos} (deviated from order)")
    print(f"  Exposure: {player.template_exposure} (risk of detection)")

    # Phase 3: Intervention
    print_section("Phase 3: Intervention Execution - Tier Selection")

    print("Player chooses intervention tier:")
    print("  [T1] Surface: Buy skill cheap (Safe, low reward)")
    print("  [T2] Structural: Hijack narrative structure (Medium risk/reward)")
    print("  [T3] Ontological: Erase template from world (High risk/reward)")

    # Demo: Execute T2
    print_step("Choice: T2 Structural Intervention (exclusive_contract)")
    action = InterventionAction(tier=2, window_id="exclusive_contract")
    engine.rng = random.Random(1)
    result = engine.execute(event, action, player)

    if result.success:
        print(f"  [SUCCESS] Completeness: {result.completeness:.0%}")
        print(f"  Karma gained: +{result.karma_gained}")
        print(f"  Exposure increase: +{result.exposure_gained}")
        print(f"  Good/Evil change: {result.karma_good_evil_change:+d}")
        print(f"  Message: {result.message}")
    else:
        print(f"  [FAILED] {result.message}")

    # Apply rewards
    engine.apply_rewards(player, result, event)
    print(f"\n  Post-intervention state: {player}")
    print(f"  Total Karma Points: {meta_state.total_karma_points}")
    print(f"  Devoured counts: {meta_state.devoured_template_counts}")

    # Phase 4: T3 Ontological Intervention
    print_section("Phase 4: T3 Ontological Intervention - Template Erasure")

    event2 = generator.maybe_spawn("noble_quarter", current_turn=200, loop_count=1, spawn_chance=1.0)
    if event2:
        print_step(f"Event in noble quarter: {event2.archetype}")
        print_step("Choice: T3 Ontological - Spend 5000 Karma to erase template")

        action3 = InterventionAction(tier=3, window_id=event2.exploit_windows[0].id)
        engine.rng = random.Random(1)
        result3 = engine.execute(event2, action3, player)

        if result3.success:
            print(f"  [SUCCESS] Full erasure! Completeness: {result3.completeness:.0%}")
            print(f"  Karma gained: +{result3.karma_gained}")
            print(f"  Exposure increase: +{result3.exposure_gained}")
            print(f"  Good/Evil change: {result3.karma_good_evil_change:+d}")

            engine.apply_rewards(player, result3, event2)
            print(f"\n  Post-intervention state: {player}")
            print(f"  Total Karma Points: {meta_state.total_karma_points}")

    # Phase 5: Reincarnation
    print_section("Phase 5: Reincarnation - Carry Over with Decay")

    reincarnation_sys = SkillEaterReincarnationSystem()
    reincarnation_sys.meta_state = meta_state
    reincarnation_sys.registry = None
    reincarnation_sys.presentation = pres
    reincarnation_sys.audio = audio

    class MockPlayerState:
        def get_skill_ids(self): return []
        def has_skill(self, sid): return False

    print_step(f"Current devour counts: {meta_state.devoured_template_counts}")
    new_player, msg = reincarnation_sys.process_reincarnation(MockPlayerState(), [])
    print(f"  {msg}")
    print(f"  Next loop counts (decayed): {meta_state.devoured_template_counts}")
    print(f"  Loop count: {meta_state.loop_count}")

    # Summary
    print_section("Demo Complete - System Summary")
    print("""
  Implemented Features:
  [OK] Procedural template generation (context/faction/weighted)
  [OK] Original Text View: flag detection, depth reading, cost system
  [OK] 3-tier intervention (T1 Surface / T2 Structural / T3 Ontological) + completeness rewards
  [OK] Triple economy: Karma Points, Exposure, Law-Chaos/Good-Evil
  [OK] World law rewriting (GlobalRuleEngine integration)
  [OK] Loop carry-over (devour count decay, world mutation messages)
  [OK] UI integration (AR overlay, reading mode, completeness gauge)
  [OK] Key bindings (Shift+R=Original Text, Shift+I=Template Intervene)

  Core Design:
  - Meta-pleasure of "reader hacking author's rails" systematized
  - Trade-off: wide & shallow (T1) vs deep & narrow (T3)
  - Exposure as "fear of detection" heightening catharsis
  - Loop-based template supply exhaustion/mutation for replayability
""")


if __name__ == "__main__":
    main()