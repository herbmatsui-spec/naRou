# HDR Pipeline Architecture

## Overview

This document describes the HDR rendering pipeline for naRou, implementing full HDR rendering with ACES tonemapping, Kawase bloom, and pseudo-HDR fallback for tcod console.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
                        Game Engine
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
                        Compositor
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  HDRCompositor                       │   │
│  │  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌────────┐  │   │
│  │  │ Scene   │→ │ Bloom    │→ │ Tonemap│→ │ Output │  │   │
│  │  │ (HDR)   │  │ (Kawase) │  │ (ACES) │  │ (LDR)  │  │   │
│  │  └─────────┘  └──────────┘  └────────┘  └────────┘  │   │
│  │         │                                           │   │
│  │         ▼                                           │   │
│  │  ┌─────────────────┐                                │   │
│  │  │ AutoExposure    │                                │   │
│  │  └─────────────────┘                                │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
       ┌─────────────┐             ┌─────────────┐
       │ WebGL2/GPU  │             │ TCOD Console│
       │ (Full HDR)  │             │ (Pseudo-HDR)│
       └─────────────┘             └─────────────┘
```

## Core Components

### 1. HDRTarget (core/hdr.py)

Dual-buffer HDR render target for ping-pong bloom operations.

```python
target = HDRTarget(width=1920, height=1080)
# color_format: RG16F (2-channel 16-bit float)
# depth_format: DEPTH24_STENCIL8
```

Features:
- Two color buffers (A/B) for ping-pong
- Depth buffer for scene rendering
- `swap_buffers()` for bloom passes
- `resize()` for window changes

### 2. HDRCompositor (core/hdr.py)

Main HDR composition pipeline.

Pipeline stages:
1. **Scene Render** → HDR target (RG16F)
2. **Bright Extract** → Threshold-based luminance filter
3. **Downsample Pyramid** → 5-level mip chain (64→32→16→8→4)
4. **Kawase Upsample** → Blur + upsample at each level
5. **Bloom Composite** → Add bloom to HDR scene
6. **Auto Exposure** → Log-average luminance adaptation
7. **Tonemap** → ACES / Reinhard / Filmic
8. **Gamma Correction** → sRGB / P3 / Rec2020
9. **Output** → LDR (8-bit)

Configuration:
```python
comp = HDRCompositor(1920, 1080)
comp.set_bloom_params(threshold=1.0, intensity=1.0, radius=8, iterations=5)
comp.set_tonemap_mode("aces")  # "aces" | "reinhard" | "filmic"
comp.set_exposure(1.0)  # Manual override
```

### 3. AutoExposure (core/auto_exposure.py)

Automatic exposure control using log-average luminance.

```python
ae = AutoExposure(
    min_exposure=0.1,
    max_exposure=10.0,
    target_luminance=0.5,
    adaptation_speed=0.5,  # 0=instant, 1=frozen
)

# Per-frame update
exposure = ae.update(hdr_framebuffer)
```

Features:
- Log-average luminance (robust to bright outliers)
- Smooth temporal adaptation
- Configurable range and target
- Histogram-based variant available (`HistogramAutoExposure`)

### 4. Tonemapping Modes

#### ACES (Default)
Industry standard filmic curve (ACES RRT + ODT)
```glsl
// Approximation
num = x * (2.51 * x + 0.03)
den = x * (2.43 * x + 0.59) + 0.14
tonemapped = num / den
```

#### Reinhard
Simple photographic tonemap
```glsl
tonemapped = x / (1.0 + x)
```

#### Filmic (Unreal-style)
Full filmic curve with white point normalization
```glsl
// Unreal 4 filmic parameters
A=0.22, B=0.30, C=0.10, D=0.20, E=0.01, F=0.30, W=11.2
```

### 5. Kawase Bloom (shaders/bloom_kawase.frag)

Dual-filter separable blur for high-quality bloom.

Algorithm:
1. **Extract** bright pixels (> threshold)
2. **Downsample** 5× (box filter)
3. **Upsample + Blur** 5× (Kawase weights)
4. **Composite** add to scene

Kawase weights: `[0.227027, 0.194595, 0.121622, 0.054054, 0.016216]`
Offsets: `[0.0, 1.38, 3.23, 5.08, 7.0]`

Advantages over Gaussian:
- Fewer texture samples
- Better quality at large radii
- Natural "glow" falloff

### 6. Pseudo-HDR Fallback (core/compositor.py, core/tcod_hdr_fallback.py)

For tcod console backend without GPU shaders.

Implementation:
- **10-bit LUT** (1024 entries) for filmic tonemap
- **Separable Gaussian blur** (3×3 × 2 passes) for bloom approximation
- **LUT lookup** per pixel for tonemapping

```python
phdr = PseudoHDR()
phdr.apply(console, hdr_framebuffer)
```

Quality tradeoffs:
- ✅ Works on any terminal
- ✅ Deterministic
- ⚠️ Limited dynamic range (10-bit)
- ⚠️ Approximate bloom
- ⚠️ CPU only

## Shader Programs

### aces_tonemap.frag
Full-screen quad tonemapping with mode selection.

Uniforms:
- `u_hdr_texture` - HDR input
- `u_exposure` - Exposure multiplier
- `u_gamma` - Display gamma (2.2 default)
- `u_tonemap_mode` - 0=ACES, 1=Reinhard, 2=Filmic
- `u_color_space` - 0=sRGB, 1=P3, 2=Rec2020

### bloom_kawase.frag
Multi-pass bloom with pass selection.

Uniforms:
- `u_texture` - Input texture
- `u_resolution` / `u_inv_resolution` - Texture size
- `u_threshold` - Luminance threshold
- `u_intensity` - Bloom multiplier
- `u_pass` - 0=extract, 1=downsample, 2=upsample+blur, 3=composite

Pass sequence (executed by compositor):
```
Pass 0: Bright extract → bloom_bright
Pass 1: Downsample 1 → bloom_down_1
Pass 2: Downsample 2 → bloom_down_2
Pass 3: Downsample 3 → bloom_down_3
Pass 4: Downsample 4 → bloom_down_4
Pass 5: Downsample 5 → bloom_down_5
Pass 6: Upsample+Blur 5 → bloom_up_5
Pass 7: Upsample+Blur 4 → bloom_up_4
Pass 8: Upsample+Blur 3 → bloom_up_3
Pass 9: Upsample+Blur 2 → bloom_up_2
Pass 10: Upsample+Blur 1 → bloom_up_1
Pass 11: Composite bloom → hdr_bloomed
Pass 12: Tonemap → ldr_output
```

## Integration with RenderSystem

The existing `RenderSystem.render_all()` integrates with HDR pipeline:

```python
# In render_system.py
compositor = Compositor(VIEW_WIDTH, VIEW_HEIGHT)


def render_all(console, context):
    compositor.begin_frame()

    # Render scene to HDR (via renderers)
    MapRenderer.render_to_hdr(compositor.hdr_compositor, ...)
    EntityRenderer.render_to_hdr(compositor.hdr_compositor, ...)
    ParticleRenderer.render_to_hdr(compositor.hdr_compositor, ...)

    # Execute HDR pipeline
    ldr = compositor.end_frame()

    # Present LDR to console
    present_to_console(console, ldr)
```

## Configuration

### Design Tokens (design_tokens.json)
```json
{
  "hdr": {
    "enabled": true,
    "bloom": {
      "threshold": 1.0,
      "intensity": 1.0,
      "radius": 8,
      "iterations": 5
    },
    "tonemap": "aces",
    "exposure": {
      "auto": true,
      "min": 0.1,
      "max": 10.0,
      "target": 0.5,
      "speed": 0.5
    },
    "gamma": 2.2
  }
}
```

### ConfigManager Access
```python
config = ConfigManager.get()
hdr_config = config.get("hdr", {})
bloom_threshold = hdr_config.get("bloom", {}).get("threshold", 1.0)
```

## Testing

### Unit Tests (tests/test_hdr_pipeline.py)
- HDRTarget buffer management
- AutoExposure adaptation
- Tonemapping modes (ACES/Reinhard/Filmic)
- Bloom extraction
- Downsample/upsample pyramid
- Pseudo-HDR LUT
- Compositor pass configuration
- Full frame integration

Run:
```bash
pytest tests/test_hdr_pipeline.py -q
```

### Visual Verification
Debug passes via compositor:
```python
comp.set_debug_pass(0)  # Show bright extract
comp.set_debug_pass(5)  # Show downsample level 3
comp.set_debug_pass(11)  # Show bloom composite
```

## Performance

| Component | Cost (1080p) | Notes |
|-----------|--------------|-------|
| HDR Scene | ~2ms | Geometry + lighting |
| Bright Extract | ~0.1ms | Single pass |
| Downsample (5×) | ~0.3ms | Box filter |
| Kawase Upsample (5×) | ~0.8ms | 4 dirs × 5 weights |
| Tonemap | ~0.1ms | Full-screen |
| **Total** | **~3.3ms** | GPU (RTX 3060) |

CPU fallback (tcod): ~5-10ms depending on resolution

## Future Extensions

1. **WebGPU Compute** - Move bloom to compute shaders
2. **Temporal AA** - Jitter + history for bloom stability
3. **Lens Dirt** - Texture-based bloom artifacts
4. **Chromatic Aberration** - Per-channel bloom offset
5. **Volumetric Bloom** - 3D light scattering

## References

- [ACES Filmic Tone Mapping Curve](https://github.com/TheRealMJP/BakingLab/blob/master/ACES.hlsl)
- [Kawase Blur - Practical Post-Process DOF](https://www.gdcvault.com/play/1024421/Practical-Post-Process-Depth-of)
- [Filmic Tonemapping - Unreal Engine](https://www.unrealengine.com/en-US/blog/filmic-tonemapping-with-piecewise-power-curves)
- [Auto Exposure - GPU Gems 3](https://developer.nvidia.com/gpugems/gpugems3/part-iv-image-effects/chapter-24-auto-exposure)