"""Tests for skill_eater_procedural_dungeon module."""

from __future__ import annotations

from skill_eater_procedural_dungeon import RoomType


def test_room_type_enum():
    assert RoomType.CORRIDOR.value == "corridor"
    assert RoomType.GUARD_ROOM.value == "guard_room"
    assert RoomType.STORAGE.value == "storage"
    assert RoomType.SERVER_ROOM.value == "server_room"
    assert RoomType.EXPERIMENT_CHAMBER.value == "experiment_chamber"
    assert RoomType.SAFE_ZONE.value == "safe_zone"
    assert RoomType.TRAP_CORRIDOR.value == "trap_corridor"
    assert RoomType.BOSS_ROOM.value == "boss_room"
    assert RoomType.SECRET_ROOM.value == "secret_room"
