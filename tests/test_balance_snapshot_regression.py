"""Regression tests for balance snapshot parameters.

These tests ensure that the core balance parameters (monster HP range,
experience next value) remain constant. If they need to be changed,
update this test and the corresponding balance_snapshot test deliberately.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ecs.entity import Entity

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((REPO_ROOT / "config.yaml").read_text(encoding="utf-8"))
MONSTERS = yaml.safe_load((REPO_ROOT / "data" / "monsters.yaml").read_text(encoding="utf-8"))


def _player_entity() -> Entity:
    """Build the player exactly as core/world_state_manager.py:33-40 does."""
    cfg = CONFIG["player"]
    entity = Entity(
        x=cfg["start_x"],
        y=cfg["start_y"],
        char=cfg["char"],
        color=tuple(cfg["color"]),
        name=cfg["name"],
        is_player=True,
        speed=cfg["speed"],
        attributes=cfg["attributes"],
    )
    entity.god_id = "jure"  # packages/character/package.py:11
    entity.recalculate_stats()
    return entity


def test_monster_hp_range_regression():
    """Ensure monster HP range remains [10, 500]."""
    hp = sorted(body["max_hp"] for body in MONSTERS.values())
    assert hp[0] == 10, f"Expected min monster HP 10, got {hp[0]}"
    assert hp[-1] == 500, f"Expected max monster HP 500, got {hp[-1]}"


def test_exp_next_regression():
    """Ensure exp_next for level 1 player remains 120."""
    entity = _player_entity()
    assert entity.exp_next == 120, f"Expected exp_next 120, got {entity.exp_next}"
