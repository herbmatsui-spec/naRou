"""Unit tests for animated tile system."""
import sys
sys.path.insert(0, '.')

from core.animated_tile import AnimatedTile, ANIMATED_TILES, get_animated_tile


def test_animated_tile_creation():
    """Test AnimatedTile creation and basic properties."""
    tile = AnimatedTile(
        tile_ids=["TR_EFFECT_01", "TR_EFFECT_02", "TR_EFFECT_03"],
        fps=10
    )
    assert tile.tile_ids == ["TR_EFFECT_01", "TR_EFFECT_02", "TR_EFFECT_03"]
    assert tile.fps == 10
    assert tile.loop is True
    assert tile.frame_count == 3
    assert tile.frame_duration == 0.1


def test_animated_tile_get_frame():
    """Test frame retrieval by index."""
    tile = AnimatedTile(
        tile_ids=["A", "B", "C"],
        fps=5
    )
    assert tile.get_frame(0) == "A"
    assert tile.get_frame(1) == "B"
    assert tile.get_frame(2) == "C"
    assert tile.get_frame(3) == "A"  # loops


def test_animated_tile_get_frame_at_time():
    """Test frame retrieval at specific time."""
    tile = AnimatedTile(
        tile_ids=["FRAME1", "FRAME2"],
        fps=10  # 0.1s per frame
    )
    # At t=0, should be frame 0
    assert tile.get_frame_at_time(0.0) == "FRAME1"
    # At t=0.05, still frame 0
    assert tile.get_frame_at_time(0.05) == "FRAME1"
    # At t=0.1, frame 1
    assert tile.get_frame_at_time(0.1) == "FRAME2"
    # At t=0.2, back to frame 0
    assert tile.get_frame_at_time(0.2) == "FRAME1"


def test_animated_tile_validation():
    """Test AnimatedTile validation."""
    # Empty tile_ids should raise
    try:
        AnimatedTile(tile_ids=[], fps=10)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    
    # Negative fps should raise
    try:
        AnimatedTile(tile_ids=["A"], fps=-1)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_predefined_animated_tiles():
    """Test that predefined animated tiles exist and are valid."""
    for name in ["water", "lava", "torch", "magic_portal"]:
        tile = get_animated_tile(name)
        assert tile is not None, f"Missing animated tile: {name}"
        assert isinstance(tile, AnimatedTile)
        assert tile.frame_count > 0
        assert tile.fps > 0


def test_get_animated_tile_unknown():
    """Test getting unknown animated tile returns None."""
    assert get_animated_tile("nonexistent") is None


if __name__ == "__main__":
    test_animated_tile_creation()
    test_animated_tile_get_frame()
    test_animated_tile_get_frame_at_time()
    test_animated_tile_validation()
    test_predefined_animated_tiles()
    test_get_animated_tile_unknown()
    print("All animated tile tests passed!")