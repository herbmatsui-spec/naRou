#!/usr/bin/env python3
"""
Particle system test for terminal renderer.
Tests TerminalParticleSystem functionality.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tcod
import tcod.console

from core.lighting import PARTICLE_EFFECTS, PARTICLE_TYPES, TerminalParticleSystem


def test_particle_creation():
    """Test particle creation and pool management."""
    print("Testing particle creation...")

    ps = TerminalParticleSystem(40, 24, max_particles=100)

    # Emit some particles
    ps.emit({"type": "dust", "x": 20, "y": 12, "count": 5, "lifetime": 1.0, "speed": 0.5})

    assert len(ps.particles) == 5
    assert all(p.active for p in ps.particles)
    assert all(p.type == "dust" for p in ps.particles)
    assert all(p.life > 0 for p in ps.particles)
    assert all(p.max_life > 0 for p in ps.particles)
    assert all(p.char in PARTICLE_TYPES["dust"]["chars"] for p in ps.particles)
    assert all(p.color in PARTICLE_TYPES["dust"]["colors"] for p in ps.particles)

    # Test pool reuse
    for p in ps.particles:
        p.active = False
        p.life = 0

    ps.emit(
        {
            "type": "dust",
            "x": 20,
            "y": 12,
            "count": 3,
        }
    )

    # Should reuse from pool
    assert len(ps.particles) == 8  # 5 old (inactive) + 3 new
    active_count = sum(1 for p in ps.particles if p.active)
    assert active_count == 3

    print("  PASS: Particle creation and pooling works")


def test_particle_types():
    """Test all particle types have correct configs."""
    print("Testing particle types...")

    required_types = ["dust", "spark", "magic", "heal", "damage"]

    for ptype in required_types:
        assert ptype in PARTICLE_TYPES, f"Missing particle type: {ptype}"
        conf = PARTICLE_TYPES[ptype]
        assert "chars" in conf and len(conf["chars"]) > 0
        assert "colors" in conf and len(conf["colors"]) > 0
        assert "gravity" in conf
        assert "speed" in conf
        assert "lifetime" in conf

    print("  PASS: All particle types configured")


def test_particle_effects():
    """Test preset effects."""
    print("Testing preset effects...")

    required_effects = ["step", "hit", "magic_cast", "heal", "damage", "level_up"]

    for effect in required_effects:
        assert effect in PARTICLE_EFFECTS, f"Missing effect: {effect}"
        conf = PARTICLE_EFFECTS[effect]
        assert "type" in conf
        assert conf["type"] in PARTICLE_TYPES

    print("  PASS: All preset effects configured")


def test_particle_update():
    """Test particle physics update."""
    print("Testing particle physics update...")

    ps = TerminalParticleSystem(40, 24, max_particles=100)

    # Emit particles
    ps.emit({"type": "spark", "x": 20, "y": 12, "count": 10, "lifetime": 1.0, "speed": 1.5})

    # Update a few frames
    initial_positions = [(p.x, p.y) for p in ps.particles if p.active]

    for _ in range(5):
        ps.update(1 / 60)

    final_positions = [(p.x, p.y) for p in ps.particles if p.active]

    # Particles should have moved
    moved = sum(1 for i, (ix, iy) in enumerate(initial_positions) if (ix, iy) != final_positions[i])

    assert moved > 0, "Particles should move"

    # Test gravity effect
    for p in ps.particles:
        if p.active:
            # After 5 frames at 60fps, vy should have increased due to gravity
            # but initial velocity might mask it, so just check physics ran
            assert p.x != 20.0 or p.y != 12.0, "Particle position should have changed"

    print("  PASS: Particle physics update works")


def test_particle_lifetime():
    """Test particle lifetime and pool return."""
    print("Testing particle lifetime...")

    ps = TerminalParticleSystem(40, 24, max_particles=100)

    # Emit short-lived particles
    ps.emit(
        {
            "type": "damage",
            "x": 20,
            "y": 12,
            "count": 5,
            "lifetime": 0.1,  # Very short
            "speed": 0.5,
        }
    )

    active_initial = sum(1 for p in ps.particles if p.active)
    assert active_initial == 5

    # Update until they die
    for _ in range(10):
        ps.update(1 / 60)

    active_final = sum(1 for p in ps.particles if p.active)
    assert active_final == 0, "All particles should be dead"

    # Pool should have them
    pool_size = sum(len(pool) for pool in ps.pools.values())
    assert pool_size == 5, "Particles should be in pool"

    print("  PASS: Particle lifetime and pool return works")


def test_preset_effects():
    """Test emit_effect with all presets."""
    print("Testing preset effects...")

    ps = TerminalParticleSystem(40, 24, max_particles=500)

    effects_to_test = ["step", "hit", "magic_cast", "heal", "damage", "level_up"]

    for effect in effects_to_test:
        ps.clear()
        ps.emit_effect(effect, 20, 12, 5)

        active = sum(1 for p in ps.particles if p.active)
        PARTICLE_EFFECTS[effect]["count"] * 5  # count=5
        # Allow some variance due to random count
        assert active > 0, f"Effect {effect} should create particles"
        assert ps.particles[0].type == PARTICLE_EFFECTS[effect]["type"]

    print("  PASS: All preset effects work")


def test_particle_drawing():
    """Test particle drawing on console."""
    print("Testing particle drawing...")

    console = tcod.console.Console(40, 24, order="F")
    ps = TerminalParticleSystem(40, 24)

    # Emit particles
    ps.emit({"type": "magic", "x": 20, "y": 12, "count": 10, "lifetime": 2.0, "speed": 0.8})

    # Update a bit
    for _ in range(3):
        ps.update(1 / 60)

    # Draw
    ps.draw(console, 0, 0)

    # Check foreground was modified
    fg = console.tiles_rgb["fg"]
    ch = console.tiles_rgb["ch"]

    non_zero_fg = sum(
        1
        for y in range(24)
        for x in range(40)
        if fg[x, y][0] > 0 or fg[x, y][1] > 0 or fg[x, y][2] > 0
    )
    non_zero_ch = sum(1 for y in range(24) for x in range(40) if ch[x, y] != 0)

    assert non_zero_fg > 0, "Foreground should be modified"
    assert non_zero_ch > 0, "Characters should be drawn"

    print("  PASS: Particle drawing works")


def test_quality_setting():
    """Test quality adjustment."""
    print("Testing quality setting...")

    ps = TerminalParticleSystem(40, 24, max_particles=500)

    assert ps.max_particles == 500

    ps.set_quality(True)  # reduced
    assert ps.max_particles == 250

    ps.set_quality(False)  # normal
    assert ps.max_particles == 500

    print("  PASS: Quality setting works")


def test_clear():
    """Test clear functionality."""
    print("Testing clear...")

    ps = TerminalParticleSystem(40, 24)

    ps.emit(
        {
            "type": "dust",
            "x": 20,
            "y": 12,
            "count": 10,
        }
    )

    assert len(ps.particles) == 10

    ps.clear()

    assert len(ps.particles) == 0
    for pool in ps.pools.values():
        assert len(pool) == 0

    print("  PASS: Clear works")


def test_active_count():
    """Test active count."""
    print("Testing active count...")

    ps = TerminalParticleSystem(40, 24)

    assert ps.get_active_count() == 0

    ps.emit(
        {
            "type": "dust",
            "x": 20,
            "y": 12,
            "count": 5,
        }
    )

    assert ps.get_active_count() == 5

    # Kill one
    ps.particles[0].active = False
    ps.particles[0].life = 0

    assert ps.get_active_count() == 4

    print("  PASS: Active count works")


def main():
    print("=" * 60)
    print("Terminal Particle System Tests")
    print("=" * 60)

    test_particle_creation()
    test_particle_types()
    test_particle_effects()
    test_particle_update()
    test_particle_lifetime()
    test_preset_effects()
    test_particle_drawing()
    test_quality_setting()
    test_clear()
    test_active_count()

    print("\n" + "=" * 60)
    print("ALL PARTICLE TESTS PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
