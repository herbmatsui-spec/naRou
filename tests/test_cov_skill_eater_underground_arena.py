"""Coverage tests for skill_eater_underground_arena (UndergroundArenaManager)."""

from __future__ import annotations

import pytest

from skill_eater_underground_arena import UndergroundArenaManager


@pytest.fixture
def arena() -> UndergroundArenaManager:
    return UndergroundArenaManager()


class TestDefaults:
    def test_initial_state(self, arena: UndergroundArenaManager) -> None:
        assert arena.current_wave == 0
        assert arena.max_wave == 10
        assert arena.is_in_arena is False
        assert arena.active_challenge is None
        assert arena.total_damage_dealt == 0
        assert arena.total_turns_taken == 0
        assert arena.high_score == 0
        assert arena.unlocked_ranks == ["Bronze"]


class TestSessionLifecycle:
    def test_start_session_default(self, arena: UndergroundArenaManager) -> None:
        res = arena.start_arena_session()
        assert res["success"] is True
        assert res["wave"] == 1
        assert res["challenge"] == "STANDARD_PRACTICE"
        assert arena.is_in_arena is True

    def test_start_session_resets_counters(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session()
        arena.simulate_attack(500)
        arena.start_arena_session("TIME_ATTACK")
        assert arena.total_damage_dealt == 0
        assert arena.total_turns_taken == 0
        assert arena.active_challenge == "TIME_ATTACK"
        assert arena.current_wave == 1

    def test_exit_arena(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session()
        res = arena.exit_arena()
        assert res["success"] is True
        assert arena.is_in_arena is False
        assert res["final_dps"] == 0
        assert res["high_score"] == 0

    def test_exit_with_stats_reports_dps(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session()
        arena.simulate_attack(100)
        arena.simulate_attack(300)
        res = arena.exit_arena()
        assert res["final_dps"] == 200.0


class TestWaveSpawning:
    def test_spawn_requires_session(self, arena: UndergroundArenaManager) -> None:
        assert arena.spawn_wave_enemies() == {"error": "Not in arena"}

    def test_spawn_scales_with_wave(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session()
        dummy = arena.spawn_wave_enemies()["target_dummy"]
        assert dummy["name"] == "Simulation Drone MK-1"
        assert dummy["hp"] == 500
        assert dummy["defense"] == 10
        assert dummy["type"] == "Holographic Target"

        arena.current_wave = 3
        dummy = arena.spawn_wave_enemies()["target_dummy"]
        assert dummy["hp"] == 1500
        assert dummy["defense"] == 30


class TestSimulateAttack:
    def test_attack_requires_session(self, arena: UndergroundArenaManager) -> None:
        res = arena.simulate_attack(100)
        assert res["success"] is False
        assert res["message"] == "Arena session not active."

    def test_damage_accumulates_and_dps(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session()
        r1 = arena.simulate_attack(200)
        assert r1["damage_dealt"] == 200
        assert r1["total_damage"] == 200
        assert r1["current_dps"] == 200.0
        r2 = arena.simulate_attack(600)
        assert r2["total_damage"] == 800
        assert r2["turns"] == 2
        assert r2["current_dps"] == 400.0

    def test_minimum_damage_clamped_to_one(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session()
        res = arena.simulate_attack(-50)
        assert res["damage_dealt"] == 1
        res = arena.simulate_attack(0)
        assert res["damage_dealt"] == 1

    def test_no_magic_challenge_blocks_magic(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session("NO_MAGIC")
        res = arena.simulate_attack(100, skill_type="Magic")
        assert res["success"] is False
        assert "NO_MAGIC" in res["message"]
        assert arena.total_damage_dealt == 0

    def test_no_magic_allows_physical(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session("NO_MAGIC")
        res = arena.simulate_attack(100, skill_type="Physical")
        assert res["success"] is True

    def test_other_challenges_allow_magic(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session("TIME_ATTACK")
        res = arena.simulate_attack(100, skill_type="Magic")
        assert res["success"] is True


class TestCompleteWave:
    def test_requires_session(self, arena: UndergroundArenaManager) -> None:
        res = arena.complete_wave()
        assert res["success"] is False
        assert res["message"] == "Not in arena"

    def test_wave_rewards_and_score(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session()
        arena.simulate_attack(300)
        res = arena.complete_wave()
        assert res["success"] is True
        assert res["cleared_wave"] == 1
        assert res["has_next_wave"] is True
        assert res["reward_junk"] == 100
        # score = (300 // 1) * 1
        assert res["score"] == 300
        assert arena.high_score == 300
        assert arena.current_wave == 2

    def test_high_score_keeps_max(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session()
        arena.simulate_attack(1000)
        w1 = arena.complete_wave()  # score = (1000 // 1) * 1
        assert w1["score"] == 1000
        w2 = arena.complete_wave()  # no attacks: dps still 1000, wave 2
        assert w2["score"] == 2000
        assert arena.high_score == 2000

    def test_silver_rank_at_wave_5(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session()
        arena.current_wave = 4
        arena.complete_wave()  # wave 4 → no silver yet
        assert "Silver" not in arena.unlocked_ranks
        res = arena.complete_wave()  # wave 5
        assert "Silver" in res["current_ranks"]

    def test_gold_rank_at_wave_10_and_session_end(self, arena: UndergroundArenaManager) -> None:
        arena.start_arena_session()
        arena.current_wave = 10
        res = arena.complete_wave()
        assert res["cleared_wave"] == 10
        assert res["has_next_wave"] is False
        assert "Gold" in res["current_ranks"]
        assert arena.is_in_arena is False
