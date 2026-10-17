"""Test dungeon ceiling and dead code removal (Step 23)."""

from __future__ import annotations

import ast
from pathlib import Path


def test_descent_stops_at_max_depth():
    """Verify config.yaml has dungeon max_depth and win_depth settings."""
    import yaml

    config_path = Path(__file__).resolve().parents[1] / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    assert "game" in config
    assert "dungeon" in config["game"]
    dungeon = config["game"]["dungeon"]
    assert "max_depth" in dungeon
    assert "win_depth" in dungeon
    assert dungeon["max_depth"] == 30
    assert dungeon["win_depth"] == 20
    assert dungeon["win_depth"] < dungeon["max_depth"]


def test_dead_code_four_zone_layer_is_removed():
    """Verify the four-zone layer logic (surface/underground/otherworld/heaven) is removed.

    The old code at map_engine.py lines 990-1011 had zone transitions:
    - surface (1-10) -> underground (11-50) -> otherworld (51-100) -> heaven (101-200)
    This should be replaced by simple linear depth with max_depth from config.
    """
    map_engine_path = Path(__file__).resolve().parents[1] / "map_engine.py"
    source = map_engine_path.read_text(encoding="utf-8")

    # Parse the AST to find the specific zone transition logic
    tree = ast.parse(source)

    # Check that handle_stairs_interaction has no callers
    call_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "handle_stairs_interaction":
                    call_count += 1
            elif isinstance(node.func, ast.Name):
                if node.func.id == "handle_stairs_interaction":
                    call_count += 1

    assert call_count == 0, f"handle_stairs_interaction has {call_count} callers, expected 0"

    # Verify _calculate_target_layer_down/up don't have zone comparison logic
    # (The old code had: if current_zone == "surface" and new_depth > 10: etc.)
    assert "current_zone ==" not in source, "Zone comparison logic still present"
    assert "new_zone =" not in source, "Zone assignment logic still present"

    # Verify the four specific zone names are not used in the transition logic
    # (they may appear in docstrings but not in the actual transition code)
    # Check that the old zone transition chain is gone
    assert 'if current_zone == "surface"' not in source
    assert 'if current_zone == "underground"' not in source
    assert 'if current_zone == "otherworld"' not in source
    assert 'if current_zone == "heaven"' not in source
    assert "new_zone = " not in source  # no zone reassignment
    assert "max(11, new_depth)" not in source  # old underground start
    assert "max(51, new_depth)" not in source  # old otherworld start
    assert "max(101, new_depth)" not in source  # old heaven start
    assert "min(10, new_depth)" not in source  # old surface limit
