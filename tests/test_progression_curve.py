"""Test experience progression curve (Step 21-22)."""

from __future__ import annotations

from pathlib import Path

import yaml

from ecs.entity import Entity


def test_exp_next_is_monotonic():
    """exp_next must strictly increase with each level."""
    entity = Entity(is_player=True)
    prev = 0
    for level in range(1, 101):
        entity.level = level
        current = entity.exp_next
        assert current > prev, f"exp_next not monotonic at level {level}: {current} <= {prev}"
        prev = current


def test_exp_next_matches_formula():
    """exp_next follows base * growth^(level-1) from balance_standards.yaml."""
    config_path = Path(__file__).resolve().parents[1] / "data" / "balance_standards.yaml"
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    exp_curve = data.get("exp_curve", {"base": 120, "growth": 1.35})
    base = exp_curve["base"]
    growth = exp_curve["growth"]

    entity = Entity(is_player=True)
    for level in [1, 2, 5, 10, 20, 50, 100]:
        entity.level = level
        expected = int(base * (growth ** (level - 1)))
        assert entity.exp_next == expected, f"level {level}: got {entity.exp_next}, expected {expected}"


def test_exp_next_level_1_is_base():
    """Level 1 requires exactly base exp to reach level 2."""
    entity = Entity(is_player=True)
    entity.level = 1
    config_path = Path(__file__).resolve().parents[1] / "data" / "balance_standards.yaml"
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    base = data.get("exp_curve", {}).get("base", 120)
    assert entity.exp_next == base


def test_level_50_requires_at_least_15_floors():
    """Total exp to reach level 50 should require ≥15 dungeon floors.

    Models: each floor has ~7 monsters (test_monsters_per_floor_is_about_6_7),
    each kill at floor d gives 35*d exp (combat_manager.py:40).
    """
    config_path = Path(__file__).resolve().parents[1] / "data" / "balance_standards.yaml"
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    exp_curve = data.get("exp_curve", {"base": 120, "growth": 1.35})
    base = exp_curve["base"]
    growth = exp_curve["growth"]

    # Total exp from level 1 to 50
    total_exp = sum(int(base * (growth ** (l - 1))) for l in range(1, 50))

    # Estimate floors needed assuming player clears floors 1..N sequentially
    def exp_per_floor(d: int) -> int:
        return 7 * 35 * d  # 7 monsters * 35 * floor

    accumulated = 0
    floors = 0
    for d in range(1, 101):
        accumulated += exp_per_floor(d)
        floors += 1
        if accumulated >= total_exp:
            break

    assert floors >= 15, f"Level 50 reached in {floors} floors, expected ≥15"


def test_level_50_costs_a_plausible_number_of_kills():
    """Reaching level 50 should require ≥50 monster kills.

    Uses average exp per kill at median floor depth.
    """
    config_path = Path(__file__).resolve().parents[1] / "data" / "balance_standards.yaml"
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    exp_curve = data.get("exp_curve", {"base": 120, "growth": 1.35})
    base = exp_curve["base"]
    growth = exp_curve["growth"]

    total_exp = sum(int(base * (growth ** (l - 1))) for l in range(1, 50))

    # Median floor ~ floors/2, average exp/kill = 35 * median_floor
    # Conservative: assume player farms at floor 10 (350 exp/kill)
    avg_exp_per_kill = 35 * 10
    kills_needed = total_exp / avg_exp_per_kill

    assert kills_needed >= 50, f"Level 50 needs only {kills_needed:.0f} kills, expected ≥50"
