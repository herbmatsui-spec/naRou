import pytest
from narou.engine.engine import Engine


def test_engine_has_tile_display():
    """Engine class should have _TILE_DISPLAY attribute for text mode."""
    assert hasattr(Engine, '_TILE_DISPLAY')
    assert isinstance(Engine._TILE_DISPLAY, dict)
    # Check a few expected keys
    expected_keys = {"TILE_WALL", "TILE_FLOOR", "TILE_STAIRS_DOWN"}
    for key in expected_keys:
        assert key in Engine._TILE_DISPLAY