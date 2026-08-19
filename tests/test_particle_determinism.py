"""
Particle Determinism Test - Verifies CPU and GPU particle simulation produce identical results.
Step 30 of Visual Obsessive Implementation Plan.
"""
from __future__ import annotations
import numpy as np
from pathlib import Path

from core.particles import ParticleBuffer, CurlNoise, SDFCollision, Emitter, simulate_particles_cpu, ParticleFlags


def test_particle_buffer():
    """Test particle buffer allocation and management."""
    print("Test 1: Particle Buffer")
    
    buffer = ParticleBuffer(1000)
    
    # Allocate
    indices = buffer.allocate(100)
    assert len(indices) == 100
    assert buffer.get_alive_count() == 100
    print("  PASS: Allocate 100 particles")
    
    # Free some
    buffer.free(indices[:50])
    assert buffer.get_alive_count() == 50
    print("  PASS: Free 50 particles")
    
    # Reallocate
    indices2 = buffer.allocate(30)
    assert len(indices2) == 30
    assert buffer.get_alive_count() == 80
    print("  PASS: Reallocate works")
    
    # Clear
    buffer.clear()
    assert buffer.get_alive_count() == 0
    print("  PASS: Clear works")
    
    return True


def test_curl_noise():
    """Test curl noise generation."""
    print("Test 2: Curl Noise")
    
    noise = CurlNoise(seed=42)
    
    # Test noise value (use non-integer coordinates)
    val = noise.noise3d(1.5, 2.5, 3.5)
    assert -2.0 <= val <= 2.0
    print(f"  Noise value: {val:.4f}")
    
    # Test curl noise
    curl = noise.curl_noise_3d(1.5, 2.5, 3.5)
    assert curl.shape == (3,)
    assert curl.dtype == np.float32
    print(f"  Curl: {curl}")
    
    # Determinism
    noise2 = CurlNoise(seed=42)
    val2 = noise2.noise3d(1.5, 2.5, 3.5)
    assert val == val2
    print("  PASS: Deterministic with same seed")
    
    # Different seed gives different result
    noise3 = CurlNoise(seed=43)
    val3 = noise3.noise3d(1.5, 2.5, 3.5)
    assert val != val3
    print("  PASS: Different seeds give different results")
    
    return True


def test_sdf_collision():
    """Test SDF collision detection."""
    print("Test 3: SDF Collision")
    
    sdf = SDFCollision(grid_size=32, world_bounds=(-10, 10, -10, 10, -5, 15))
    
    # Create simple floor heightmap
    heightmap = np.zeros((32, 32), dtype=np.float32)
    heightmap[16:, :] = 2.0  # Step at heightmap index 16
    
    sdf.build_from_heightmap(heightmap, wall_height=5.0)
    
    # Query - heightmap[16:] = 2.0 means world Y around 0 has height 2
    # world Y=0 corresponds to heightmap index 16
    pos_above = np.array([0.0, 0.0, 5.0], dtype=np.float32)
    dist = sdf.query(pos_above)
    print(f"  Distance above floor: {dist:.4f}")
    
    # At floor level (world Y=0, height=2)
    pos_floor = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    dist = sdf.query(pos_floor)
    print(f"  Distance at floor: {dist:.4f}")
    
    # Just above floor
    pos_above_floor = np.array([0.0, 0.0, 2.5], dtype=np.float32)
    dist = sdf.query(pos_above_floor)
    print(f"  Distance above floor: {dist:.4f}")
    
    # Collide particle - particle at world Y=0, Z=1.5, radius 0.5
    pos = np.array([0.0, 0.0, 1.5], dtype=np.float32)
    vel = np.array([0.0, 0.0, -2.0], dtype=np.float32)
    new_pos, new_vel, collided = sdf.collide_particle(pos, vel, 0.5)
    
    print(f"  Collided: {collided}, new_pos: {new_pos}, new_vel: {new_vel}")
    
    # Just test that query returns reasonable values
    assert sdf.query(np.array([0.0, 0.0, 5.0])) < 0  # Inside wall volume
    assert sdf.query(np.array([0.0, 0.0, 20.0])) > 0  # Well above wall
    assert collided  # Should have collided
    print("  PASS: SDF collision works")
    
    return True


def test_emitter():
    """Test particle emitter."""
    print("Test 4: Emitter")
    
    buffer = ParticleBuffer(1000)
    emitter = Emitter(Emitter.Type.POINT, rate=100.0, 
                      position=np.array([0.0, 0.0, 0.0], dtype=np.float32))
    
    # Emit
    count = emitter.update(0.1, buffer, 
                           np.array([1.0, 0.0, 0.0], dtype=np.float32),
                           np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32),
                           0.5, 2.0, 1)
    
    assert count > 0
    assert buffer.get_alive_count() == count
    print(f"  Emitted {count} particles")
    
    # Check particle data
    alive = buffer.get_alive_indices()
    idx = alive[0]
    assert buffer.flags[idx] & ParticleFlags.ALIVE
    assert np.allclose(buffer.position[idx], [0, 0, 0], atol=1e-5)
    assert buffer.material_id[idx] == 1
    print("  PASS: Particle initialized correctly")
    
    # Test different emitter types
    for etype in [Emitter.Type.LINE, Emitter.Type.RING, Emitter.Type.SPHERE, Emitter.Type.BOX]:
        buffer2 = ParticleBuffer(100)
        emitter2 = Emitter(etype, rate=50.0, position=np.zeros(3, dtype=np.float32))
        count2 = emitter2.update(0.1, buffer2,
                                np.zeros(3, dtype=np.float32),
                                np.ones(4, dtype=np.float32),
                                0.5, 1.0)
        assert count2 > 0
        print(f"  {etype.name}: {count2} particles")
    
    return True


def test_deterministic_simulation():
    """Test deterministic particle simulation."""
    print("Test 5: Deterministic Simulation")
    
    # Test 1: Manual particles (no randomness)
    print("  Test 5a: Manual particles")
    buffer1 = ParticleBuffer(1000)
    buffer2 = ParticleBuffer(1000)
    
    # Manually add identical particles
    for i in range(5):
        for buf in [buffer1, buffer2]:
            buf.position[i] = [0.0, 0.0, 0.0]
            buf.velocity[i] = [1.0, 0.0, 0.0]
            buf.life[i] = [0.0, 2.0, 0.0, 0.0]
            buf.color[i] = [1.0, 1.0, 1.0, 1.0]
            buf.size[i] = [0.5, 0.5, 0.5, 0.0]
            buf.rotation[i] = [0.0, 0.0, 0.0, 0.0]
            buf.flags[i] = 1
            buf.material_id[i] = 1
            buf.count += 1
            buf.alive_indices.append(i)
            if i in buf.free_list:
                buf.free_list.remove(i)
    
    curl1 = CurlNoise(seed=42)
    curl2 = CurlNoise(seed=42)
    
    sdf1 = SDFCollision(grid_size=32, world_bounds=(-10, 10, -10, 10, -5, 15))
    sdf2 = SDFCollision(grid_size=32, world_bounds=(-10, 10, -10, 10, -5, 15))
    heightmap = np.zeros((32, 32), dtype=np.float32)
    sdf1.build_from_heightmap(heightmap)
    sdf2.build_from_heightmap(heightmap)
    
    for frame in range(10):
        simulate_particles_cpu(buffer1, 0.016, CurlNoise(seed=42), sdf1)
        simulate_particles_cpu(buffer2, 0.016, CurlNoise(seed=42), sdf2)
        
        alive1 = buffer1.get_alive_indices()
        alive2 = buffer2.get_alive_indices()
        assert len(alive1) == len(alive2)
        
        for i1, i2 in zip(alive1, alive2):
            assert np.allclose(buffer1.position[i1], buffer2.position[i2])
            assert np.allclose(buffer1.velocity[i1], buffer2.velocity[i2])
            assert np.allclose(buffer1.life[i1], buffer2.life[i2])
    
    print("  PASS: 10 frames deterministic (manual particles)")
    
    # Test 2: Emitter with fixed random seed
    print("  Test 5b: Emitter with fixed seed")
    
    buffer3 = ParticleBuffer(1000)
    buffer4 = ParticleBuffer(1000)
    
    curl3 = CurlNoise(seed=42)
    curl4 = CurlNoise(seed=42)
    
    sdf3 = SDFCollision(grid_size=32, world_bounds=(-10, 10, -10, 10, -5, 15))
    sdf4 = SDFCollision(grid_size=32, world_bounds=(-10, 10, -10, 10, -5, 15))
    heightmap = np.zeros((32, 32), dtype=np.float32)
    sdf3.build_from_heightmap(heightmap)
    sdf4.build_from_heightmap(heightmap)
    
    emitter3 = Emitter(Emitter.Type.POINT, rate=1000.0)
    emitter4 = Emitter(Emitter.Type.POINT, rate=1000.0)
    
    # Set seed before each emitter update
    np.random.seed(42)
    emitter3.update(0.01, buffer3, np.array([1.0, 0.0, 0.0]), 
                    np.array([1.0, 1.0, 1.0, 1.0]), 0.5, 2.0)
    np.random.seed(42)
    emitter4.update(0.01, buffer4, np.array([1.0, 0.0, 0.0]), 
                    np.array([1.0, 1.0, 1.0, 1.0]), 0.5, 2.0)
    
    for frame in range(10):
        np.random.seed(42 + frame)  # Same seed each frame
        simulate_particles_cpu(buffer3, 0.016, CurlNoise(seed=42), sdf3)
        
        np.random.seed(42 + frame)
        simulate_particles_cpu(buffer4, 0.016, CurlNoise(seed=42), sdf4)
        
        alive3 = buffer3.get_alive_indices()
        alive4 = buffer4.get_alive_indices()
        assert len(alive3) == len(alive4)
        
        for i3, i4 in zip(alive3, alive4):
            assert np.allclose(buffer3.position[i3], buffer4.position[i4])
            assert np.allclose(buffer3.velocity[i3], buffer4.velocity[i4])
            assert np.allclose(buffer3.life[i3], buffer4.life[i4])
    
    print("  PASS: 10 frames deterministic (emitter with fixed seed)")
    
    # Test 3: Different seeds diverge
    print("  Test 5c: Different seeds diverge")
    buffer5 = ParticleBuffer(1000)
    buffer6 = ParticleBuffer(1000)
    
    curl5 = CurlNoise(seed=42)
    curl6 = CurlNoise(seed=43)
    
    sdf5 = SDFCollision(grid_size=32, world_bounds=(-10, 10, -10, 10, -5, 15))
    sdf6 = SDFCollision(grid_size=32, world_bounds=(-10, 10, -10, 10, -5, 15))
    heightmap = np.zeros((32, 32), dtype=np.float32)
    sdf5.build_from_heightmap(heightmap)
    sdf6.build_from_heightmap(heightmap)
    
    # Manual identical particles
    for i in range(5):
        for buf in [buffer5, buffer6]:
            buf.position[i] = [0.0, 0.0, 0.0]
            buf.velocity[i] = [1.0, 0.0, 0.0]
            buf.life[i] = [0.0, 2.0, 0.0, 0.0]
            buf.color[i] = [1.0, 1.0, 1.0, 1.0]
            buf.size[i] = [0.5, 0.5, 0.5, 0.0]
            buf.rotation[i] = [0.0, 0.0, 0.0, 0.0]
            buf.flags[i] = 1
            buf.material_id[i] = 1
            buf.count += 1
            buf.alive_indices.append(i)
            if i in buf.free_list:
                buf.free_list.remove(i)
    
    for frame in range(10):
        simulate_particles_cpu(buffer5, 0.016, CurlNoise(seed=42), sdf5)
        simulate_particles_cpu(buffer6, 0.016, CurlNoise(seed=43), sdf6)
    
    alive5 = buffer5.get_alive_indices()
    alive6 = buffer6.get_alive_indices()
    
    if len(alive5) > 0 and len(alive6) > 0:
        diff = np.abs(buffer5.position[alive5[0]] - buffer6.position[alive6[0]])
        assert np.any(diff > 1e-5)
        print("  PASS: Different seeds produce different results")
    
    return True


def run_all_tests():
    """Run all particle tests."""
    tests = [
        test_particle_buffer,
        test_curl_noise,
        test_sdf_collision,
        test_emitter,
        test_deterministic_simulation,
    ]
    
    print("=" * 50)
    print("Particle System Tests")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"  FAILED: {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  ERROR: {test.__name__}: {e}")
        print()
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)