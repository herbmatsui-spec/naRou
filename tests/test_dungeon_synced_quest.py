"""
Test Module for Dungeon Synced Quest (Phase 5 Steps 20-21)
"""

from __future__ import annotations

import pytest

from ecs.entity import Entity
from procedural_quest_generator import ProceduralQuestGenerator, QuestGenerationRegistry


def test_dungeon_synced_quest_generation():
    registry = QuestGenerationRegistry()
    registry.load()
    gen = ProceduralQuestGenerator(registry)
    player = Entity()

    quest = gen.generate_dungeon_synced_quest(
        spec_id="standard_exploration",
        quest_id="synced_test_1",
        title="Sync Test Quest",
        description="Testing dungeon sync",
        player=player,
        seed=42,
    )

    assert quest is not None
    assert quest.source_type == "dungeon_synced"
    assert quest.quest_id == "synced_test_1"
    assert len(quest.objectives) > 0
    assert "dungeon_feedback" in quest.reward
