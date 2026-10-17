"""
Test Module for Dungeon Spec and Generator (Phase 5 Steps 18-19)
"""

from __future__ import annotations

import pytest

from procedural_dungeon_generator import ProceduralDungeonGenerator
from quest_dungeon_spec import (
    DungeonSpec,
    FloorSpec,
    RoomSpec,
    RoomType,
    verify_dungeon_against_spec,
)


def test_dungeon_spec_generation():
    spec = DungeonSpec(
        spec_id="test_spec",
        min_floors=1,
        max_floors=2,
        floor_specs=[
            FloorSpec(
                floor_number=1,
                min_rooms=2,
                max_rooms=4,
                required_rooms=[RoomSpec(room_id="room1", room_type=RoomType.CHAMBER)],
            )
        ],
    )
    generator = ProceduralDungeonGenerator()
    generated = generator.generate_from_spec(spec)

    assert generated["spec_id"] == "test_spec"
    assert len(generated["floors"]) >= 1

    verification = verify_dungeon_against_spec(generated, spec)
    assert verification.satisfied
