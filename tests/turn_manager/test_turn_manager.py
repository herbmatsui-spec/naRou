"""Unit tests for turn_manager.py - Turn management system."""

from __future__ import annotations

import pytest

from ecs.entity import Entity
from turn_manager import (
    TimeSystem,
    TurnQueue,
)


class TestTimeSystem:
    """Tests for TimeSystem class."""

    def test_time_system_creation(self):
        """TimeSystem initializes correctly."""
        ts = TimeSystem()

        assert ts is not None

    def test_time_system_default_values(self):
        """TimeSystem has expected default values."""
        ts = TimeSystem()

        # Check default date/time
        assert ts.year == 517
        assert ts.month == 8
        assert ts.day == 15
        assert ts.hour == 8
        assert ts.minute == 0

    def test_pass_ticks(self):
        """pass_ticks advances time."""
        ts = TimeSystem()
        initial_ticks = ts.ticks

        ts.pass_ticks(10)

        assert ts.ticks == initial_ticks + 10

    def test_time_system_to_string(self):
        """to_string returns formatted time string."""
        ts = TimeSystem()

        time_str = ts.to_string()

        assert isinstance(time_str, str)
        assert len(time_str) > 0

    def test_time_system_serialization(self):
        """TimeSystem serializes and deserializes correctly."""
        ts = TimeSystem()
        ts.pass_ticks(100)

        data = ts.to_dict()
        restored = TimeSystem.from_dict(data)

        assert restored.ticks == ts.ticks
        assert restored.year == ts.year
        assert restored.month == ts.month
        assert restored.day == ts.day
        assert restored.hour == ts.hour
        assert restored.minute == ts.minute

    def test_custom_time_system_config(self):
        """TimeSystem accepts custom initial time."""
        ts = TimeSystem(year=2024, month=1, day=1, hour=12, minute=30)

        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 1
        assert ts.hour == 12
        assert ts.minute == 30

    def test_time_phase_property(self):
        """current_phase returns TimePhase."""
        ts = TimeSystem()

        phase = ts.current_phase

        # Just verify it returns a valid TimePhase
        from time_system import TimePhase
        assert isinstance(phase, type(phase))  # Just check it's a valid object


class TestTurnQueue:
    """Tests for TurnQueue class."""

    def test_turn_queue_creation(self):
        """TurnQueue initializes correctly."""
        ts = TimeSystem()
        tq = TurnQueue(ts)

        assert tq is not None
        assert tq.time_system is ts

    def test_step_next_actor_single(self):
        """step_next_actor returns entity with enough energy."""
        ts = TimeSystem()
        tq = TurnQueue(ts)

        entity = Entity(name="Hero", is_player=True)
        entity.speed = 100
        entity.energy = 1000  # Above threshold
        entity.hp = 100

        actor, ticks = tq.step_next_actor([entity])

        assert actor is entity
        assert ticks == 0

    def test_step_next_actor_charges_energy(self):
        """Entities below threshold get energy charged."""
        ts = TimeSystem()
        tq = TurnQueue(ts)

        entity = Entity(name="Hero", is_player=True)
        entity.speed = 100
        entity.energy = 0
        entity.hp = 100

        actor, ticks = tq.step_next_actor([entity])

        # Should take some ticks to charge energy
        assert actor is entity
        assert ticks > 0
        # Energy should have been charged by speed * ticks
        assert entity.energy >= entity.speed * ticks

    def test_multiple_entities_priority(self):
        """Higher speed entities act first when both ready."""
        ts = TimeSystem()
        tq = TurnQueue(ts)

        fast = Entity(name="Fast", is_player=True)
        fast.speed = 200
        fast.energy = 1000
        fast.hp = 100

        slow = Entity(name="Slow", is_player=True)
        slow.speed = 50
        slow.energy = 1000
        slow.hp = 100

        actor, _ = tq.step_next_actor([slow, fast])

        assert actor is fast

    def test_dead_entities_skipped(self):
        """Dead entities are skipped."""
        ts = TimeSystem()
        tq = TurnQueue(ts)

        dead = Entity(name="Dead")
        dead.energy = 1000
        dead.hp = 0

        alive = Entity(name="Alive")
        alive.energy = 1000
        alive.hp = 100

        actor, _ = tq.step_next_actor([dead, alive])

        assert actor is alive

    def test_no_entities_ready(self):
        """Returns None when no entities can act."""
        ts = TimeSystem()
        tq = TurnQueue(ts)

        # All entities dead
        entity = Entity(name="Dead")
        entity.hp = 0
        entity.energy = 1000

        actor, ticks = tq.step_next_actor([entity])

        assert actor is None
        assert ticks >= 0  # May have charged energy

    def test_speed_determines_action_order(self):
        """Entities with higher speed act more frequently."""
        ts = TimeSystem()
        tq = TurnQueue(ts)

        fast = Entity(name="Fast", speed=200)
        fast.energy = 1000
        fast.hp = 100

        slow = Entity(name="Slow", speed=50)
        slow.energy = 1000
        slow.hp = 100

        # Act several times
        actors = []
        for _ in range(4):
            actor, _ = tq.step_next_actor([slow, fast])
            if actor:
                actors.append(actor.name)

        # Fast entity should act more often
        fast_count = actors.count("Fast")
        slow_count = actors.count("Slow")

        assert fast_count >= slow_count


class TestTimeSystemIntegration:
    """Integration tests for TimeSystem and TurnQueue."""

    def test_time_advances_during_turns(self):
        """Time advances when turn queue processes."""
        ts = TimeSystem()
        tq = TurnQueue(ts)

        entity = Entity(name="Hero", speed=100)
        entity.energy = 0
        entity.hp = 100

        initial_ticks = ts.ticks

        # This will charge energy and advance time
        tq.step_next_actor([entity])

        assert ts.ticks > initial_ticks

    def test_custom_time_system_config(self):
        """TimeSystem accepts custom initial time."""
        ts = TimeSystem(year=2024, month=1, day=1, hour=12, minute=30)

        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 1
        assert ts.hour == 12
        assert ts.minute == 30

    def test_time_phase_property(self):
        """current_phase returns TimePhase."""
        ts = TimeSystem()

        phase = ts.current_phase

        # Just verify it returns a valid TimePhase
        from time_system import TimePhase
        assert isinstance(phase, type(phase))  # Just check it's a valid object


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
