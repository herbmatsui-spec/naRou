"""Coverage tests for skill_eater_env_puzzles (EnvironmentalPuzzleManager)."""

from __future__ import annotations

import pytest

from skill_eater_env_puzzles import EnvironmentalPuzzleManager


@pytest.fixture
def mgr() -> EnvironmentalPuzzleManager:
    return EnvironmentalPuzzleManager()


class TestDefaults:
    def test_two_puzzles_defined(self, mgr: EnvironmentalPuzzleManager) -> None:
        assert set(mgr.puzzles) == {"neon_security_gate", "toxic_steam_vent"}
        assert mgr.solved_puzzles == set()

    def test_puzzle_fields(self, mgr: EnvironmentalPuzzleManager) -> None:
        gate = mgr.puzzles["neon_security_gate"]
        assert gate["required_power"] == 50
        assert gate["failure_trap_damage"] == 35
        assert gate["is_solved"] is False
        assert len(gate["required_skills"]) == 2


class TestInspect:
    def test_inspect_known_puzzle(self, mgr: EnvironmentalPuzzleManager) -> None:
        res = mgr.inspect_puzzle("toxic_steam_vent")
        assert res["puzzle_id"] == "toxic_steam_vent"
        assert res["name"] == "腐食性魔導蒸気弁"
        assert res["required_skills"] == ["Dimensional Storage", "Frost Magic"]
        assert res["is_solved"] is False

    def test_inspect_unknown_puzzle(self, mgr: EnvironmentalPuzzleManager) -> None:
        assert mgr.inspect_puzzle("nope") == {"error": "Puzzle not found"}


class TestAttemptSolve:
    def test_unknown_puzzle_fails(self, mgr: EnvironmentalPuzzleManager) -> None:
        res = mgr.attempt_solve_puzzle("nope", [], 999)
        assert res["success"] is False
        assert res["message"] == "Puzzle does not exist."

    def test_solve_with_all_skills_and_power(self, mgr: EnvironmentalPuzzleManager) -> None:
        res = mgr.attempt_solve_puzzle(
            "neon_security_gate",
            ["Lightning Magic", "Network Hacking", "Extra"],
            50,
        )
        assert res["success"] is True
        assert res["opened_gate"] is True
        assert res["secret_reward"] == "Hidden Storage Room: 500 Junk & Rare Core"
        assert "SOLVED" in res["message"]
        assert mgr.solved_puzzles == {"neon_security_gate"}
        assert mgr.puzzles["neon_security_gate"]["is_solved"] is True

    def test_power_boundary_exact(self, mgr: EnvironmentalPuzzleManager) -> None:
        res = mgr.attempt_solve_puzzle(
            "neon_security_gate", ["Lightning Magic", "Network Hacking"], 49
        )
        assert res["success"] is False
        assert res["power_sufficient"] is False

    def test_enough_power_but_missing_skills(self, mgr: EnvironmentalPuzzleManager) -> None:
        res = mgr.attempt_solve_puzzle("neon_security_gate", ["Lightning Magic"], 100)
        assert res["success"] is False
        assert res["trap_damage"] == 35
        assert res["missing_skills"] == ["Network Hacking"]
        assert res["power_sufficient"] is True

    def test_all_skills_but_not_enough_power(self, mgr: EnvironmentalPuzzleManager) -> None:
        res = mgr.attempt_solve_puzzle(
            "toxic_steam_vent", ["Dimensional Storage", "Frost Magic"], 10
        )
        assert res["success"] is False
        assert res["trap_damage"] == 50
        assert res["missing_skills"] == []
        assert res["power_sufficient"] is False

    def test_failed_attempt_does_not_mark_solved(self, mgr: EnvironmentalPuzzleManager) -> None:
        mgr.attempt_solve_puzzle("neon_security_gate", [], 0)
        assert mgr.solved_puzzles == set()
        assert mgr.puzzles["neon_security_gate"]["is_solved"] is False

    def test_already_solved_returns_short_circuit(self, mgr: EnvironmentalPuzzleManager) -> None:
        mgr.attempt_solve_puzzle(
            "neon_security_gate", ["Lightning Magic", "Network Hacking"], 100
        )
        res = mgr.attempt_solve_puzzle("neon_security_gate", [], 0)
        assert res["success"] is True
        assert res["already_open"] is True
        assert "already solved" in res["message"]

    def test_inspect_reflects_solved_state(self, mgr: EnvironmentalPuzzleManager) -> None:
        mgr.attempt_solve_puzzle(
            "neon_security_gate", ["Lightning Magic", "Network Hacking"], 100
        )
        assert mgr.inspect_puzzle("neon_security_gate")["is_solved"] is True

    def test_puzzles_solve_independently(self, mgr: EnvironmentalPuzzleManager) -> None:
        mgr.attempt_solve_puzzle(
            "toxic_steam_vent", ["Dimensional Storage", "Frost Magic"], 40
        )
        assert mgr.solved_puzzles == {"toxic_steam_vent"}
        assert mgr.puzzles["neon_security_gate"]["is_solved"] is False
