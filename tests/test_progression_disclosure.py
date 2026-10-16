"""Tests for progressive disclosure system."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from core.progression_manager import ProgressionFlagComponent, is_unlocked, unlock_system
from ecs.entity import Entity


def test_progression_flag_defaults_locked():
    """All systems should be locked by default."""
    flags = ProgressionFlagComponent()
    assert not flags.skill_eater
    assert not flags.base_defense
    assert not flags.archaeology
    assert not flags.crafting
    assert not flags.arena


def test_progression_flag_unlock():
    """Systems can be unlocked."""
    flags = ProgressionFlagComponent()
    assert not flags.skill_eater
    unlock_system(flags, "skill_eater")
    assert flags.skill_eater
    # unlocking again should stay True
    unlock_system(flags, "skill_eater")
    assert flags.skill_eater


def test_is_unlocked_helper():
    """Helper function works."""
    flags = ProgressionFlagComponent()
    assert not is_unlocked(flags, "skill_eater")
    unlock_system(flags, "skill_eater")
    assert is_unlocked(flags, "skill_eater")
    assert not is_unlocked(flags, "base_defense")


def test_entity_has_progression_flag_component():
    """Entity should have the component after initialization."""
    entity = Entity(is_player=True)
    # The component should be present (added in _init_components)
    assert entity.has_component(ProgressionFlagComponent)
    flags = entity.get_component(ProgressionFlagComponent)
    assert isinstance(flags, ProgressionFlagComponent)
    assert not flags.skill_eater  # default locked


def test_skill_eater_combat_system_locked(monkeypatch):
    """When skill_eater flag is locked, engine's skill_eater_combat_system property returns None."""
    from engine.engine import Engine

    # Create a dummy engine (headless)
    engine = Engine(headless=True)
    # Ensure the player has the component locked
    player = engine.game_state_data.player
    flags = player.get_component(ProgressionFlagComponent)
    assert not flags.skill_eater  # sanity

    # Mock kernel.has_system to return True (so that if unlocked, it would return a system)
    # We'll monkeypatch kernel.has_system and kernel.get_system to avoid actual system loading.
    monkeypatch.setattr(engine.kernel, "has_system", lambda name: True)
    monkeypatch.setattr(engine.kernel, "get_system", lambda name: Mock())

    # Access the property
    result = engine.skill_eater_combat_system
    # Should be None because flag is locked
    assert result is None


def test_skill_eater_combat_system_unlocked(monkeypatch):
    """When skill_eater flag is unlocked, engine returns the system (or mock)."""
    from engine.engine import Engine

    engine = Engine(headless=True)
    player = engine.game_state_data.player
    flags = player.get_component(ProgressionFlagComponent)
    unlock_system(flags, "skill_eater")
    assert flags.skill_eater

    monkeypatch.setattr(engine.kernel, "has_system", lambda name: True)
    monkeypatch.setattr(engine.kernel, "get_system", lambda name: Mock())

    result = engine.skill_eater_combat_system
    assert result is not None
    assert isinstance(result, Mock)
