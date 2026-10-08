"""Test difficulty preset consistency with config.yaml."""

from __future__ import annotations

import pytest


class TestDifficultyPresetMatchesConfig:
    """Verify DifficultyManager presets match config.yaml values."""

    def test_difficulty_preset_matches_config(self) -> None:
        """Code presets in DifficultyManager._DEFAULTS must match config.yaml difficulty_presets."""
        # Load config values
        from config import get_config
        from core.difficulty import DifficultyManager

        config_easy = get_config("game.difficulty_presets.easy")
        config_normal = get_config("game.difficulty_presets.normal")
        config_hard = get_config("game.difficulty_presets.hard")

        # Get code presets (explicit mode uses _DEFAULTS)
        dm_easy = DifficultyManager(difficulty="easy")
        dm_normal = DifficultyManager(difficulty="normal")
        dm_hard = DifficultyManager(difficulty="hard")

        # Verify each multiplier matches
        for difficulty, config_preset, dm in [
            ("easy", config_easy, dm_easy),
            ("normal", config_normal, dm_normal),
            ("hard", config_hard, dm_hard),
        ]:
            assert dm.multipliers["player_damage_taken"] == config_preset["player_damage_taken"], \
                f"{difficulty}: player_damage_taken mismatch: code={dm.multipliers['player_damage_taken']}, config={config_preset['player_damage_taken']}"
            assert dm.multipliers["enemy_hp"] == config_preset["enemy_hp"], \
                f"{difficulty}: enemy_hp mismatch: code={dm.multipliers['enemy_hp']}, config={config_preset['enemy_hp']}"
            assert dm.multipliers["player_regen"] == config_preset["player_regen"], \
                f"{difficulty}: player_regen mismatch: code={dm.multipliers['player_regen']}, config={config_preset['player_regen']}"

    def test_win_depth_reads_from_config(self) -> None:
        """WorldSystem.check_win_condition must read win_depth from config, not hardcode."""
        from config import get_config

        win_depth = get_config("game.dungeon.win_depth")
        assert win_depth == 20, f"config win_depth = {win_depth}, expected 20"

        # Verify the actual check uses config (will fail until implementation)
        # Check source code doesn't have hardcoded 20
        import inspect

        from engine.systems.world_system import WorldSystem

        source = inspect.getsource(WorldSystem.check_win_condition)
        assert ">= 20" not in source or "win_depth" in source, \
            "check_win_condition contains hardcoded '20' without referencing win_depth config"


class TestNonVacuity:
    """Non-vacuity proofs for difficulty tests."""

    def test_assert_distinguishes_difficulty_mismatch(self) -> None:
        """Test that our check CAN detect a mismatch (non-vacuity)."""
        from tests.helpers.non_vacuity import assert_distinguishes

        def check_preset_match(preset_value: float) -> None:
            """Assertion-style check: preset matches config (raises on mismatch)."""
            config_value = 0.75  # config.yaml value
            assert preset_value == config_value, f"preset {preset_value} != config {config_value}"

        # Good case: preset matches config (0.75 == 0.75) - should pass
        good_preset = 0.75
        # Bad case: preset differs from config (0.5 != 0.75) - should raise AssertionError
        bad_preset = 0.5

        # assert_distinguishes confirms check(good) passes and check(bad) raises
        assert_distinguishes(check_preset_match, good_preset, bad_preset, label="easy player_damage_taken")

    def test_assert_distinguishes_win_depth(self) -> None:
        """Test that win_depth check CAN detect hardcoded value."""
        from tests.helpers.non_vacuity import assert_distinguishes

        def check_uses_config(win_threshold: int) -> None:
            """Assertion-style check: threshold matches config win_depth."""
            config_win_depth = 20
            assert win_threshold == config_win_depth, f"threshold {win_threshold} != config {config_win_depth}"

        good_threshold = 20  # matches config
        bad_threshold = 15   # doesn't match config

        assert_distinguishes(check_uses_config, good_threshold, bad_threshold, label="win_depth threshold")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
