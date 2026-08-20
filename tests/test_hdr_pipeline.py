"""
HDR Pipeline Test - Verifies HDR rendering, bloom, and tonemapping.
Step 15 of Visual Obsessive Implementation Plan.
"""

from __future__ import annotations

import numpy as np

from core.compositor import Compositor, PseudoHDR
from core.hdr import AutoExposure, HDRCompositor, HDRTarget


def test_hdr_target():
    """Test HDR target creation and buffer management."""
    print("Test 1: HDR Target")

    target = HDRTarget(100, 100)
    assert target.color_a.shape == (100, 100, 2)
    assert target.color_b.shape == (100, 100, 2)
    assert target.depth.shape == (100, 100)
    print("  PASS: Buffer shapes correct")

    # Test swap
    read_before = target.get_read_texture()
    target.swap_buffers()
    read_after = target.get_read_texture()
    assert read_after is target.color_b
    print("  PASS: Buffer swap works")

    # Test resize
    target.resize(200, 150)
    assert target.color_a.shape == (150, 200, 2)
    print("  PASS: Resize works")

    return True


def test_auto_exposure():
    """Test automatic exposure control."""
    print("Test 2: Auto Exposure")

    ae = AutoExposure(min_exposure=0.1, max_exposure=10.0, target_luminance=0.5)

    # Dark scene
    dark_hdr = np.full((100, 100, 3), 0.1, dtype=np.float32)
    exp = ae.update(dark_hdr)
    assert exp > 1.0  # Should increase exposure
    print(f"  Dark scene exposure: {exp:.3f}")

    # Bright scene
    bright_hdr = np.full((100, 100, 3), 5.0, dtype=np.float32)
    ae.current_exposure = 1.0  # Reset
    exp = ae.update(bright_hdr)
    assert exp < 1.0  # Should decrease exposure
    print(f"  Bright scene exposure: {exp:.3f}")

    # Clamping
    ae.set_exposure_range(0.5, 2.0)
    ae.current_exposure = 0.1
    exp = ae.update(dark_hdr)
    assert exp >= 0.5
    print(f"  Clamped exposure: {exp:.3f}")

    return True


def test_tonemapping():
    """Test tonemapping modes."""
    print("Test 3: Tonemapping")

    comp = HDRCompositor(64, 64)

    # Test HDR values
    hdr = np.array([[[0.5, 0.5]], [[2.0, 2.0]], [[10.0, 10.0]]], dtype=np.float32)
    hdr = np.broadcast_to(hdr, (3, 1, 2)).copy()

    # ACES
    comp.tonemap_mode = "aces"
    ldr_aces = comp.apply_tonemap(hdr)
    assert np.all(ldr_aces >= 0) and np.all(ldr_aces <= 1)
    print(f"  ACES: {ldr_aces.flatten()}")

    # Reinhard
    comp.tonemap_mode = "reinhard"
    ldr_reinhard = comp.apply_tonemap(hdr)
    assert np.all(ldr_reinhard >= 0) and np.all(ldr_reinhard <= 1)
    print(f"  Reinhard: {ldr_reinhard.flatten()}")

    # Filmic
    comp.tonemap_mode = "filmic"
    ldr_filmic = comp.apply_tonemap(hdr)
    assert np.all(ldr_filmic >= 0) and np.all(ldr_filmic <= 1)
    print(f"  Filmic: {ldr_filmic.flatten()}")

    return True


def test_bloom_extract():
    """Test bright pixel extraction for bloom."""
    print("Test 4: Bloom Extraction")

    comp = HDRCompositor(64, 64)
    comp.bloom_threshold = 1.0
    comp.bloom_intensity = 1.0

    # Create test HDR with bright and dark regions
    hdr = np.zeros((64, 64, 2), dtype=np.float16)
    hdr[10:20, 10:20] = [2.0, 2.0]  # Bright
    hdr[30:40, 30:40] = [0.5, 0.5]  # Dark

    comp.hdr_target.color_a = hdr.copy()
    comp.hdr_target.read_buffer = 0

    bright = comp._extract_bright_pixels()

    # Bright region should be preserved
    assert np.any(bright[10:20, 10:20] > 0)
    # Dark region should be zero
    assert np.all(bright[30:40, 30:40] == 0)
    print("  PASS: Bright extraction works")

    return True


def test_downsample_upsample():
    """Test mip pyramid downsample/upsample."""
    print("Test 5: Downsample/Upsample")

    comp = HDRCompositor(64, 64)
    comp.bloom_iterations = 4

    # Create test image
    bright = np.zeros((64, 64, 2), dtype=np.float16)
    bright[20:40, 20:40] = [1.0, 1.0]

    pyramid = comp._downsample_pyramid(bright)

    assert len(pyramid) >= 2
    assert pyramid[0].shape == (64, 64, 2)
    assert pyramid[1].shape[0] <= 32
    assert pyramid[1].shape[1] <= 32
    print(f"  Pyramid levels: {[p.shape[:2] for p in pyramid]}")

    # Upsample
    bloom = comp._upsample_kawase(pyramid)
    assert bloom.shape == (64, 64, 2)
    print("  PASS: Upsample works")

    return True


def test_pseudo_hdr():
    """Test pseudo-HDR fallback."""
    print("Test 6: Pseudo-HDR Fallback")

    phdr = PseudoHDR()

    # Check LUT generated
    assert phdr.lut is not None
    assert len(phdr.lut) == 1024
    print("  PASS: LUT generated")

    # Test exposure change
    phdr.set_exposure(2.0)
    assert phdr.exposure == 2.0
    print("  PASS: Exposure change works")

    # Test gamma change
    phdr.set_gamma(1.8)
    assert phdr.gamma == 1.8
    print("  PASS: Gamma change works")

    return True


def test_compositor():
    """Test full compositor pipeline."""
    print("Test 7: Compositor")

    comp = Compositor(64, 64)

    # Check passes
    passes = comp.get_pass_names()
    assert "scene" in passes
    assert "tonemap" in passes
    assert "bloom_composite" in passes
    print(f"  Passes: {len(passes)}")

    # Test bloom params
    comp.set_bloom_params(threshold=0.5, intensity=2.0, radius=4, iterations=3)
    assert comp.hdr_compositor.bloom_threshold == 0.5
    assert comp.hdr_compositor.bloom_intensity == 2.0
    print("  PASS: Bloom params")

    # Test tonemap mode
    comp.set_tonemap_mode("filmic")
    assert comp.hdr_compositor.tonemap_mode == "filmic"
    print("  PASS: Tonemap mode")

    # Test debug
    comp.set_debug_pass(2)
    assert comp.debug_mode
    comp.set_debug_pass(-1)
    assert not comp.debug_mode
    print("  PASS: Debug mode")

    # Test resize
    comp.resize(128, 96)
    assert comp.hdr_compositor.hdr_target.color_a.shape == (96, 128, 2)
    print("  PASS: Resize")

    return True


def test_integration():
    """Integration test: full frame simulation."""
    print("Test 8: Integration")

    comp = Compositor(32, 32)
    comp.set_bloom_params(threshold=1.0, intensity=1.0)

    # Simulate a frame - write directly to HDR write texture
    comp.begin_frame()

    # Add some "scene" data to HDR buffer manually
    write_tex = comp.hdr_compositor.hdr_target.get_write_texture()
    write_tex[5:10, 5:10] = [3.0, 3.0]  # Bright light
    write_tex[15:20, 15:20] = [0.3, 0.3]  # Dim

    # Execute pipeline
    ldr = comp.end_frame()

    assert ldr.shape == (32, 32, 2)
    assert np.all(ldr >= 0) and np.all(ldr <= 1)
    print(f"  Output range: [{np.min(ldr):.3f}, {np.max(ldr):.3f}]")

    return True


def run_all_tests():
    """Run all HDR pipeline tests."""
    tests = [
        test_hdr_target,
        test_auto_exposure,
        test_tonemapping,
        test_bloom_extract,
        test_downsample_upsample,
        test_pseudo_hdr,
        test_compositor,
        test_integration,
    ]

    print("=" * 50)
    print("HDR Pipeline Tests")
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
