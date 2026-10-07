"""Tests for win condition (Step 19)."""

from __future__ import annotations

import game
from naRou.engine.game_state import GameStateMachine


class TestWinCondition:
    """Win condition tests."""

    def test_reaching_depth_boss_wins(self):
        """Test that reaching depth 20 triggers victory."""
        engine = game.Engine()
        # Set dungeon level to 20
        engine.dungeon_level = 20
        # Check win condition
        result = engine.check_win_condition()
        assert result is True
        assert engine.game_state_machine.current == "victory"
        assert engine.game_state_machine.is_terminal

    def test_win_condition_not_triggered_before_depth_20(self):
        """Test that win condition is not triggered before depth 20."""
        engine = game.Engine()
        engine.dungeon_level = 19
        result = engine.check_win_condition()
        assert result is False
        assert engine.game_state_machine.current == "playing"

    def test_win_condition_only_when_playing(self):
        """Test that win condition only triggers when playing."""
        engine = game.Engine()
        engine.dungeon_level = 20
        # Set to game_over first
        engine.game_state_machine.transition("game_over")
        result = engine.check_win_condition()
        assert result is False
        assert engine.game_state_machine.current == "game_over"

    def test_victory_transition_to_title(self):
        """Test that victory can transition to title."""
        gsm = GameStateMachine("playing")
        gsm.transition("victory")
        assert gsm.current == "victory"
        gsm.transition("title")
        assert gsm.current == "title"

    def test_victory_cannot_go_to_game_over(self):
        """Test that victory cannot transition to game_over."""
        gsm = GameStateMachine("playing")
        gsm.transition("victory")
        from pytest import raises
        with raises(ValueError):
            gsm.transition("game_over")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])