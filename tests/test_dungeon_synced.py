#!/usr/bin/env python3
"""Test for dungeon synced quest functionality"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from ecs.entity import Entity
from procedural_quest_generator import ProceduralQuestGenerator, QuestGenerationRegistry


def test_dungeon_synced_quest():
    """Test that dungeon synced quest generation works"""
    print("Testing dungeon synced quest generation...")

    # Setup
    registry = QuestGenerationRegistry()
    registry.load()
    gen = ProceduralQuestGenerator(registry)
    player = Entity()

    # Test loading a dungeon spec
    spec = gen._load_dungeon_spec("standard_exploration")
    assert spec is not None, "Failed to load dungeon spec"
    assert spec.spec_id == "standard_exploration"
    print("✓ Dungeon spec loading works")

    # Test generating a dungeon synced quest
    quest = gen.generate_dungeon_synced_quest(
        spec_id="standard_exploration",
        quest_id="test_synced_001",
        title="テストダンジョンクエスト",
        description="テスト用のダンジョン同期クエスト",
        player=player,
        seed=12345,
    )

    assert quest is not None, "Quest generation returned None"
    assert quest.quest_id == "test_synced_001", f"Quest ID mismatch: {quest.quest_id}"
    assert quest.title == "テストダンジョンクエスト", f"Title mismatch: {quest.title}"
    assert quest.description == "テスト用のダンジョン同期クエスト", f"Description mismatch: {quest.description}"
    assert quest.source_type == "dungeon_synced", f"Source type mismatch: {quest.source_type}"
    print("✓ Dungeon synced quest generation works")

    # Test that quest has objectives
    assert len(quest.objectives) > 0, "Quest has no objectives"
    print(f"✓ Quest has {len(quest.objectives)} objectives")

    # Test that objectives are dungeon-related
    obj_desc = " ".join([obj.description for obj in quest.objectives])
    dungeon_related = any(keyword in obj_desc for keyword in ["階層", "部屋", "ボス", "入口", "出口"])
    assert dungeon_related, f"Objective description not dungeon-related: {obj_desc}"
    print("✓ Quest objectives are dungeon-related")

    # Test that feedback is in reward
    assert "dungeon_feedback" in quest.reward, "No dungeon_feedback in reward"
    feedback = quest.reward["dungeon_feedback"]
    assert "spec_id" in feedback, "No spec_id in feedback"
    assert feedback["spec_id"] == "standard_exploration", f"Wrong spec_id in feedback: {feedback['spec_id']}"
    assert "generated_floors" in feedback, "No generated_floors in feedback"
    assert isinstance(feedback["generated_floors"], int) and feedback["generated_floors"] > 0, f"Invalid generated_floors: {feedback['generated_floors']}"
    print("✓ Quest reward contains dungeon feedback")

    print("\nAll tests passed!")

if __name__ == "__main__":
    test_dungeon_synced_quest()
