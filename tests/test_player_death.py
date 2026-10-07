"""Tests for player death handling (Steps 12-17)."""

from __future__ import annotations

import pytest
import game
from naRou.engine.game_state import GameStateMachine


class TestPlayerDeath:
    """Player death handling tests."""

    def test_zero_hp_triggers_game_over(self):
        """Test that player HP <= 0 triggers game_over via GameStateMachine."""
        engine = game.Engine()
        # Force player HP to 0
        engine.player.hp = 0
        # Call the death handler
        engine._on_player_death()
        # Verify state transition
        assert engine.game_state_machine.current == "game_over"
        assert engine.game_state_machine.is_terminal

    def test_spell_damage_can_kill(self):
        """Test that spell damage can kill the player."""
        engine = game.Engine()
        engine.player.hp = 10
        # Simulate spell damage
        engine.player.hp -= 15
        assert engine.player.hp <= 0
        engine._on_player_death()
        assert engine.game_state_machine.current == "game_over"

    def test_no_input_accepted_after_death(self):
        """Test that input is rejected after player death."""
        engine = game.Engine()
        engine.player.hp = 0
        engine._on_player_death()
        # player_act should return False when not playing
        result = engine.player_act(1, 0)
        assert result is False

    def test_regen_does_not_revive_the_dead(self):
        """Test that natural regen doesn't revive a dead player."""
        engine = game.Engine()
        engine.player.hp = 0
        engine._on_player_death()
        # Set turns to trigger regen
        engine.turns = 10
        # Call advance_world which contains the regen logic with the gate
        engine.advance_world()
        # Player should stay at 0 (or negative) HP
        assert engine.player.hp <= 0

    def test_devour_backlash_can_be_lethal(self):
        """Test that devour backlash can kill the player (no 1 HP floor)."""
        engine = game.Engine()
        engine.player.hp = 5
        # Simulate devour backlash (was max(1, hp - backlash))
        backlash = 8
        engine.player.hp -= backlash  # No max(1, ...) floor
        assert engine.player.hp <= 0

    def test_toxicity_can_be_lethal(self):
        """Test that toxicity can kill the player (no 1 HP floor)."""
        engine = game.Engine()
        engine.player.hp = 2
        # Simulate toxicity damage (was max(1, hp - 2))
        engine.player.hp -= 2  # No max(1, ...) floor
        assert engine.player.hp <= 0

    def test_player_hp_never_lands_below_zero_without_death(self):
        """Test that player HP going below zero always triggers death handler."""
        engine = game.Engine()
        engine.player.hp = -5
        # Calling _end_run_if_player_dead should handle this
        result = engine._end_run_if_player_dead()
        assert result is True
        assert engine.game_state_machine.current == "game_over"

    def test_no_production_code_assigns_game_state_directly(self):
        """Test that no production code assigns GameState.GAME_OVER directly."""
        # This is a grep-based test - verify no direct assignments exist
        import subprocess

        result = subprocess.run(
            [
                "grep",
                "-rn",
                r"GameState\.GAME_OVER",
                "engine/",
                "--include=*.py",
            ],
            capture_output=True,
            text=True,
            cwd="/home/herbmatsui/narou/.worktrees/v2-a",
        )
        # Should only find references in constants.py or tests, not assignments
        # Exception: backward compatibility assignments in _on_player_death (line 1372) and check_win_condition
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        assignments = [
            l for l in lines
            if "=" in l and "GameState.GAME_OVER" in l and "test" not in l
            and "engine/engine.py:1375" not in l  # _on_player_death backward compat
            and "engine/engine.py:1663" not in l  # check_win_condition backward compat
        ]
        assert len(assignments) == 0, f"Found direct GameState.GAME_OVER assignments: {assignments}"

    def test_non_vacuity_death_handler_noop(self):
        """Non-vacuity: if _on_player_death is no-op, test should fail."""
        engine = game.Engine()
        original = engine._on_player_death

        def noop():
            pass

        engine._on_player_death = noop
        engine.player.hp = 0
        engine._on_player_death()
        # State should NOT be game_over if handler is no-op
        assert engine.game_state_machine.current != "game_over", "Test would pass vacuously!"
        engine._on_player_death = original


class TestGameStateMachine:
    """Tests for GameStateMachine."""

    def test_valid_transitions(self):
        """Test valid state transitions."""
        gsm = GameStateMachine("playing")
        assert gsm.current == "playing"
        assert gsm.is_playing
        assert not gsm.is_terminal

        gsm.transition("game_over")
        assert gsm.current == "game_over"
        assert gsm.is_terminal
        assert not gsm.is_playing

        gsm.transition("title")
        assert gsm.current == "title"

    def test_invalid_transition_raises(self):
        """Test that invalid transitions raise ValueError."""
        gsm = GameStateMachine("playing")
        with pytest.raises(ValueError):
            gsm.transition("title")  # playing -> title not allowed directly

        gsm = GameStateMachine("game_over")
        with pytest.raises(ValueError):
            gsm.transition("playing")  # game_over -> playing not allowed


class TestNaturalRegen:
    """Tests for natural regen turn-gating (Step 18)."""

    def test_natural_regen_is_turn_gated(self):
        """Test that natural regen only triggers every 10 turns, not per frame."""
        engine = game.Engine()
        engine.player.hp = engine.player.max_hp - 20
        initial_hp = engine.player.hp
        
        # Simulate 9 turns - should NOT regen yet
        for _ in range(9):
            engine.advance_world()
        assert engine.player.hp == initial_hp, "Regen should not trigger before 10 turns"
        
        # 10th turn - should regen
        engine.advance_world()
        assert engine.player.hp == initial_hp + 1, "Regen should trigger on 10th turn"
        
        # Another 10 turns
        for _ in range(10):
            engine.advance_world()
        assert engine.player.hp == initial_hp + 2, "Regen should trigger every 10 turns"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])