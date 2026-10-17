"""
Lighting System Test - Verifies G-Buffer, Light Volumes, and Tile Culling.
Step 23 of Visual Obsessive Implementation Plan.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from core.gbuffer import GBuffer, pack_material, pack_normal_xy, unpack_material, unpack_normal_xy
from core.lighting import LightVolume, MaterialSystem, ShadowAtlas, TileCulling


def test_gbuffer():
    """Test G-Buffer creation and packing."""
    print("Test 1: G-Buffer")

    gbuf = GBuffer(100, 100)
    assert gbuf.albedo.shape == (100, 100, 4)
    assert gbuf.normal.shape == (100, 100, 2)
    assert gbuf.material.shape == (100, 100, 4)
    assert gbuf.depth.shape == (100, 100)
    print("  PASS: Buffer shapes correct")

    # Test clear
    gbuf.clear()
    assert np.all(gbuf.albedo == 0)
    assert np.all(gbuf.depth == 1.0)
    print("  PASS: Clear works")

    # Test resize
    gbuf.resize(200, 150)
    assert gbuf.albedo.shape == (150, 200, 4)
    print("  PASS: Resize works")

    return True


def test_normal_packing():
    """Test normal packing/unpacking."""
    print("Test 2: Normal Packing")

    # Create test normals
    normals = np.array(
        [[[0.0, 0.0, 1.0], [1.0, 0.0, 0.0]], [[0.0, 1.0, 0.0], [-0.707, 0.0, 0.707]]],
        dtype=np.float32,
    )

    # Pack
    packed = pack_normal_xy(normals)
    assert packed.shape == (2, 2, 2)
    assert packed.dtype == np.float16
    print("  PASS: Packing shape correct")

    # Unpack
    unpacked = unpack_normal_xy(packed)
    assert unpacked.shape == (2, 2, 3)
    print("  PASS: Unpacking shape correct")

    # Check accuracy (Z should be reconstructed)
    for y in range(2):
        for x in range(2):
            orig = normals[y, x]
            recon = unpacked[y, x]
            # Check X, Y preserved
            assert abs(orig[0] - recon[0]) < 0.01
            assert abs(orig[1] - recon[1]) < 0.01
            # Check Z reconstructed correctly
            assert abs(orig[2] - recon[2]) < 0.02
    print("  PASS: Normal reconstruction accurate")

    return True


def test_material_packing():
    """Test material packing/unpacking."""
    print("Test 3: Material Packing")

    h, w = 10, 10
    roughness = np.full((h, w), 0.5, dtype=np.float32)
    metallic = np.full((h, w), 0.0, dtype=np.float32)
    emissive = np.full((h, w), 0.1, dtype=np.float32)
    ao = np.full((h, w), 0.9, dtype=np.float32)

    packed = pack_material(roughness, metallic, emissive, ao)
    assert packed.shape == (h, w, 4)
    assert packed.dtype == np.uint8
    print("  PASS: Packing shape correct")

    r, m, e, a = unpack_material(packed)
    assert np.allclose(r, 0.5, atol=1 / 255)
    assert np.allclose(m, 0.0, atol=1 / 255)
    assert np.allclose(e, 0.1, atol=1 / 255)
    assert np.allclose(a, 0.9, atol=1 / 255)
    print("  PASS: Unpacking accurate")

    return True


def test_shadow_atlas():
    """Test shadow atlas allocation."""
    print("Test 4: Shadow Atlas")

    atlas = ShadowAtlas(1024, 16)

    # Allocate some lights
    regions = []
    for i in range(10):
        region = atlas.allocate_light("point", 128)
        assert region is not None
        regions.append(region)
    print(f"  Allocated {len(regions)} lights")

    # Check regions don't overlap
    for i, (x1, y1, w1, h1) in enumerate(regions):
        for j, (x2, y2, w2, h2) in enumerate(regions):
            if i != j:
                overlap_x = not (x1 + w1 <= x2 or x2 + w2 <= x1)
                overlap_y = not (y1 + h1 <= y2 or y2 + h2 <= y1)
                assert not (overlap_x and overlap_y)
    print("  PASS: No overlapping regions")

    # Get region
    region = atlas.get_light_region(0)
    assert region is not None
    print("  PASS: Region retrieval works")

    return True


def test_tile_culling():
    """Test tile-based light culling."""
    print("Test 5: Tile Culling")

    culling = TileCulling(tile_size=16, max_lights_per_tile=32)

    # Create test lights
    lights = [
        LightVolume("point", (50, 50, 10), (1, 1, 1), 20, 1.0),
        LightVolume(
            "spot",
            (100, 100, 10),
            (1, 0.5, 0.2),
            30,
            2.0,
            direction=(0, -1, 0),
            inner_cone=0.5,
            outer_cone=1.0,
        ),
        LightVolume("point", (200, 50, 10), (0.2, 0.5, 1), 15, 0.5),
    ]

    # Identity view-proj
    view_proj = np.eye(4, dtype=np.float32)

    grid = culling.build_light_grid(256, 256, lights, view_proj)

    grid_h, grid_w, max_lights = grid.shape
    assert grid_h == 16  # 256/16
    assert grid_w == 16
    assert max_lights == 32
    print(f"  Grid shape: {grid.shape}")

    # Check some tiles have lights
    has_lights = np.any(grid != 0xFFFFFFFF)
    assert has_lights
    print("  PASS: Lights assigned to tiles")

    return True


def test_material_system():
    """Test material system."""
    print("Test 6: Material System")

    # Create temp material file
    import json
    import tempfile

    test_materials = {
        "test_floor": {
            "albedo": "floor",
            "roughness": 0.8,
            "metallic": 0.0,
            "emissive": 0.0,
            "ao": 1.0,
        },
        "test_metal": {
            "albedo": "metal",
            "roughness": 0.2,
            "metallic": 1.0,
            "emissive": 0.0,
            "ao": 1.0,
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_materials, f)
        temp_path = f.name

    try:
        ms = MaterialSystem(temp_path)

        # Test get_material
        mat = ms.get_material("test_floor")
        assert mat["roughness"] == 0.8
        assert mat["metallic"] == 0.0
        print("  PASS: Material lookup works")

        # Test default fallback
        mat = ms.get_material("nonexistent")
        assert mat["roughness"] == 0.5  # Default
        print("  PASS: Default fallback works")

        # Test array
        arr = ms.get_material_array(["test_floor", "test_metal"])
        assert arr.shape == (2, 4)
        print("  PASS: Array generation works")

    finally:
        Path(temp_path).unlink()

    return True


def test_light_volume():
    """Test LightVolume dataclass."""
    print("Test 7: Light Volume")

    # Point light
    point = LightVolume(
        light_type="point",
        position=(10.0, 20.0, 5.0),
        color=(1.0, 0.8, 0.6),
        radius=15.0,
        intensity=2.0,
    )
    assert point.light_type == "point"
    assert point.radius == 15.0
    print("  PASS: Point light created")

    # Spot light
    spot = LightVolume(
        light_type="spot",
        position=(0.0, 10.0, 5.0),
        color=(1.0, 1.0, 1.0),
        radius=20.0,
        intensity=3.0,
        direction=(0.0, -1.0, 0.0),
        inner_cone=0.5,
        outer_cone=0.8,
    )
    assert spot.light_type == "spot"
    assert spot.inner_cone == 0.5
    print("  PASS: Spot light created")

    # Decal
    decal = LightVolume(
        light_type="decal",
        position=(5.0, 5.0, 0.1),
        color=(0.1, 0.5, 1.0),
        radius=2.0,
        intensity=1.0,
        size=(4.0, 4.0),
        rotation=0.5,
    )
    assert decal.light_type == "decal"
    assert decal.size == (4.0, 4.0)
    print("  PASS: Decal created")

    return True


def run_all_tests():
    """Run all lighting tests."""
    tests = [
        test_gbuffer,
        test_normal_packing,
        test_material_packing,
        test_shadow_atlas,
        test_tile_culling,
        test_material_system,
        test_light_volume,
    ]

    print("=" * 50)
    print("Lighting System Tests")
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
    sys.exit(0 if success else 1)
