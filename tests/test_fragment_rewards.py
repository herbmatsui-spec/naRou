"""
Tests for quest_fragment_rewards.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from quest_fragment_rewards import (
    FragmentDrop,
    FragmentDropTable,
    drop_fragments_for_quest,
    get_fragment_drop_table,
    register_fragment_drop_table,
)


def test_fragment_drop_table_creation():
    """Test that a fragment drop table can be created and used."""
    drop = FragmentDrop(fragment_id="test_frag", min_count=1, max_count=3, weight=50)
    table = FragmentDropTable(table_id="test_table", quest_id="test_quest", drops=[drop])

    assert table.table_id == "test_table"
    assert table.quest_id == "test_quest"
    assert len(table.drops) == 1
    assert table.drops[0].fragment_id == "test_frag"


def test_register_and_get_table():
    """Test registering and retrieving a drop table."""
    drop = FragmentDrop(fragment_id="test_frag2", min_count=2, max_count=2, weight=100)
    table = FragmentDropTable(table_id="test_table2", quest_id="test_quest2", drops=[drop])
    register_fragment_drop_table(table)

    retrieved = get_fragment_drop_table("test_table2")
    assert retrieved is not None
    assert retrieved.table_id == "test_table2"
    assert retrieved.drops[0].fragment_id == "test_frag2"


def test_drop_fragments():
    """Test that dropping fragments works."""
    drop = FragmentDrop(fragment_id="test_frag3", min_count=1, max_count=2, weight=100)
    table = FragmentDropTable(table_id="test_table3", quest_id="test_quest3", drops=[drop])
    register_fragment_drop_table(table)

    # Test with no flags (should drop)
    fragments = table.drop_fragments()
    assert isinstance(fragments, list)
    # Should have between 1 and 2 fragments
    assert 1 <= len(fragments) <= 2
    assert all(f == "test_frag3" for f in fragments)

    # Test with forbidden flag (should not drop)
    fragments_forbidden = table.drop_fragments(player_flags=["forbidden_flag"])
    # Since we didn't set forbidden_flags on the drop, it should still drop
    # Actually, we didn't set forbidden_flags, so it should drop.
    # Let's set a forbidden flag on the drop.
    drop2 = FragmentDrop(fragment_id="test_frag4", min_count=1, max_count=1, weight=100, forbidden_flags=["no_drop"])
    table2 = FragmentDropTable(table_id="test_table4", quest_id="test_quest4", drops=[drop2])
    register_fragment_drop_table(table2)
    fragments_forbidden = table2.drop_fragments(player_flags=["no_drop"])
    assert fragments_forbidden == []  # should be empty due to forbidden flag


if __name__ == "__main__":
    test_fragment_drop_table_creation()
    test_register_and_get_table()
    test_drop_fragments()
    print("All tests passed!")
