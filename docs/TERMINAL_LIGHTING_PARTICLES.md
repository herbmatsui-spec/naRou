# Terminal Lighting & Particle Systems Documentation

## Overview

This document describes the terminal (tcod) implementations of dynamic lighting and particle systems, matching the Web (PixiJS) versions feature-for-feature.

## Architecture

### Core Components

1. **TerminalLightingSystem** (`core/lighting.py`)
   - Multiplicative blend for FOV darkness (via `console.tiles_rgb["bg"]`)
   - Additive blend for light sources (torch flicker)
   - Additive blend for enemy vision cones (pulse effect)
   - Ambient light for explored but not visible areas

2. **TerminalParticleSystem** (`core/lighting.py`)
   - 5 particle types: dust, spark, magic, heal, damage
   - Object pooling for performance
   - Physics: gravity, velocity, rotation
   - Foreground color alpha blending for pseudo-transparency
   - Preset effects: step, hit, magic_cast, heal, damage, level_up

3. **TCODRenderer Integration** (`core/tcod_renderer.py`)
   - `render_lighting_pass()` - Base + additive lighting
   - `render_particles_pass()` - Particle drawing (topmost)
   - Auto-quality adjustment based on FPS

## Data Structures

### LightSource
```python
@dataclass
class LightSource:
    x: int
    y: int
    radius: float = 7.5
    intensity: float = 1.0
    color: Tuple[int, int, int] = (255, 220, 140)
    seed: float = 0.0
    flicker: float = 1.0
    effective_radius: float = 0.0
    
    def update_flicker(self, time: float) -> None:
        """Update flicker based on time and position seed"""
```

### EnemyCone
```python
@dataclass
class EnemyCone:
    x: int
    y: int
    angle: float
    half_angle: float = 0.6
    range: float = 6.0
    color: Tuple[int, int, int] = (255, 60, 60)
    pulse: float = 0.12
    
    def update_pulse(self, time: float) -> None:
        """Update pulse intensity based on time"""
```

### LightMap
```python
@dataclass
class LightMap:
    intensity: List[List[float]]  # 0..1, -1=unexplored
    color: List[List[Tuple[int, int, int]]]  # RGB per tile
```

### Particle
```python
@dataclass
class Particle:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: float = 0.0
    max_life: float = 0.0
    char: str = "·"
    color: Tuple[int, int, int] = (255, 255, 255)
    alpha: float = 1.0
    gravity: float = 0.1
    rotation: float = 0.0
    rotation_speed: float = 0.0
    active: bool = False
    type: str = "dust"
```

## Particle Types

| Type | Chars | Colors | Gravity | Speed | Lifetime |
|------|-------|--------|---------|-------|----------|
| dust | · ∘ ○ | Cool blues | 0.05 | 0.5 | 1.5s |
| spark | ✦ ⋆ ✧ | Oranges/reds | 0.2 | 1.5 | 0.8s |
| magic | ✦ ✧ ⋆ | Purples/cyans/greens | -0.05 | 0.8 | 1.2s |
| heal | ✧ ⋆ ✦ | Greens | -0.1 | 0.6 | 1.5s |
| damage | ◆ ■ ▲ | Reds | 0.0 | 1.0 | 0.6s |

## Preset Effects

| Effect | Type | Count | Speed | Lifetime |
|--------|------|-------|-------|----------|
| step | dust | 5 | 0.3 | 0.8s |
| hit | spark | 10 | 1.0 | 0.4s |
| magic_cast | magic | 15 | 0.5 | 1.0s |
| heal | heal | 10 | 0.4 | 1.2s |
| damage | damage | 5 | 0.8 | 0.5s |
| level_up | magic | 20 | 1.0 | 2.0s |

## Rendering Pipeline

### Correct Order (Critical!)

```
1. begin_frame() - Clear console, update particles
2. render_lighting_pass() - 
   a) Multiplicative: FOV darkness (console.tiles_rgb["bg"])
   b) Additive: Light source halos
   c) Additive: Enemy vision cones
3. RenderSystem.render_all() - Map, items, entities (draw on lit background)
4. render_particles_pass() - Particles (topmost, pseudo-alpha)
5. end_frame() - Present
```

### Lighting Pass Details

#### 1. Multiplicative Blend (FOV)
```python
# For each visible tile:
if intensity <= 0.001:
    # Explored but not visible: Fog of War
    r, g, b = base_color * ambient_light(0.08)
elif intensity > 0:
    # Visible: Multiplicative
    r, g, b = base_color * intensity
# console.tiles_rgb["bg"][vx, vy] = (r, g, b)
```

#### 2. Additive Blend - Light Sources
```python
# Concentric circles with decreasing alpha
for i in range(steps, 0, -1):
    t = i / steps
    radius = int(effective_radius * t)
    alpha = (intensity / steps) * 0.18 * (1 - t * 0.6)
    # Draw circle at radius with additive color
```

#### 3. Additive Blend - Enemy Cones
```python
# Pulsing sector
pulse = 0.12 + 0.06 * (0.5 + 0.5 * sin(time * 4 + x * 24))
# Draw sector with additive color
```

### Particle Pass Details

```python
# Pseudo-alpha via foreground blend
bg = console.tiles_rgb["bg"][tx, ty]
ratio = life / max_life
fg_r = int(particle_color[0] * ratio + bg[0] * (1 - ratio))
fg_g = int(particle_color[1] * ratio + bg[1] * (1 - ratio))
fg_b = int(particle_color[2] * ratio + bg[2] * (1 - ratio))

console.tiles_rgb["fg"][tx, ty] = (fg_r, fg_g, fg_b)
console.tiles_rgb["ch"][tx, ty] = ord(particle.char)
```

## Game Loop Integration

### In Engine.render() (game.py)

```python
def render(self, console):
    # ... state checks ...

    # Use new TCODRenderer
    from core.tcod_renderer import TCODRenderer

    if not hasattr(self, "_tcod_renderer"):
        self._tcod_renderer = TCODRenderer(console.width, console.height)
        self._tcod_renderer.initialize_context(sdl_window=False)
        self._tcod_renderer.console = console

    renderer = self._tcod_renderer
    frame_time = 1 / 60

    renderer.begin_frame()  # Updates particles

    # Camera
    cam_x = max(0, min(MAP_WIDTH - VIEW_WIDTH, player.x - VIEW_WIDTH // 2))
    cam_y = max(0, min(MAP_HEIGHT - VIEW_HEIGHT, player.y - VIEW_HEIGHT // 2))

    # Build lighting data
    # ... create LightMap, LightSource[], EnemyCone[] ...

    # Send to renderer
    renderer.draw_lighting(LightingDrawCall(...))
    renderer.draw_particles(ParticleDrawCall(...))

    # RENDER PASSES IN ORDER:
    # 1. Lighting (base + additive)
    renderer.render_lighting_pass(
        cam_x,
        cam_y,
        VIEW_WIDTH,
        VIEW_HEIGHT,
        visible=game_map.visible,
        explored=game_map.explored,
        time=render_time,
    )

    # 2. Standard rendering (map, items, entities)
    RenderSystem.render_all(console, render_context)

    # 3. Particles (topmost)
    renderer.render_particles_pass(cam_x, cam_y)

    renderer.end_frame(1 / 60)
```

### Web Server Data Transmission (web_server.py)

The server already sends:
- `light_sources`: `[{x, y, radius, color, intensity}, ...]`
- `enemy_cones`: `[{x, y, angle, half_angle, range, color}, ...]`
- `particles`: `[{char, x, y, color, life}, ...]`

## Performance Optimization

### Auto Quality Adjustment

```python
# In TCODRenderer._monitor_performance():
if fps < 20 and not quality_reduced:
    quality_reduced = True
    particles.set_quality(True)  # max_particles = 250
elif fps > 40 and quality_reduced:
    quality_reduced = False
    particles.set_quality(False)  # max_particles = 500
```

### Particle Pooling

```python
# Reuse dead particles instead of creating new ones
def _return_to_pool(self, particle):
    particle.reset()
    self.pools[particle.type].append(particle)


def _get_from_pool(self, ptype):
    pool = self.pools[ptype]
    return pool.pop() if pool else None
```

### Hard Limits

- Max particles: 500 (250 in reduced quality)
- Auto-eviction when limit exceeded (oldest removed first)
- Per-frame update: O(active_particles) only

## Web/Terminal Parity

| Feature | Web (PixiJS) | Terminal (tcod) |
|---------|-------------|-----------------|
| Multiplicative darkness | MULTIPLY blend | `tiles_rgb["bg"]` *= intensity |
| Light source halos | ADD blend | `tiles_rgb["bg"]` += color |
| Enemy cones | ADD blend | `tiles_rgb["bg"]` += color |
| Torch flicker | `sin(time * 9 + seed)` | Same formula |
| Cone pulse | `sin(time * 4 + x)` | Same formula |
| Particle physics | PixiJS ticker | Manual `update(dt)` |
| Particle alpha | Real alpha | FG/BG blend pseudo-alpha |
| Particle pooling | PixiJS pool | Python list pool |
| Quality scaling | bloom/particle limit | max_particles limit |

## Testing

### Unit Tests

```bash
# Lighting tests
python tools/test_lighting.py

# Particle tests  
python tools/test_particles.py

# Both
python tools/test_lighting.py && python tools/test_particles.py
```

### Visual Regression

```bash
# Generate reference images
python tools/visual_regression.py --generate

# Compare current rendering
python tools/visual_regression.py --compare
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Background not darkening | Light map not applied | Call `render_lighting_pass()` before map rendering |
| Light sources not visible | Additive blend not working | Check `render_lighting_pass()` order |
| Particles not showing | Draw order wrong | Call `render_particles_pass()` last |
| FPS too low | Too many particles | Auto quality reduces to 250 |
| Torch not flickering | Time not passed | Pass `time` to `render_pass()` |
| Overflow warnings | Additive blend clamps | Expected, `min(255, ...)` handles it |

## Migration Notes

### From Old Rendering

**Before:**
```python
# MapRenderer handled lighting internally
MapRenderer.render(console, context, cam_x, cam_y, light_sources)
```

**After:**
```python
# 1. Lighting pass FIRST
renderer.render_lighting_pass(cam_x, cam_y, ...)

# 2. Then standard rendering
RenderSystem.render_all(console, context)

# 3. Particles LAST
renderer.render_particles_pass(cam_x, cam_y)
```

### Adding New Light Sources

1. Create `LightSource(x, y, radius, intensity, color)`
2. Add to `light_sources` list in render()
3. System handles flicker automatically

### Adding New Particle Effects

1. Add to `PARTICLE_EFFECTS` dict in `core/lighting.py`
2. Or call `particles.emit()` with custom config
3. System handles pooling, physics, drawing

## Future Enhancements

- [ ] Screen-space ambient occlusion (SSAO)
- [ ] Light propagation through doors/walls
- [ ] Dynamic weather lighting (rain, fog)
- [ ] Particle collision with walls
- [ ] Emitter components for continuous effects
- [ ] GPU-accelerated particle compute (if porting to Vulkan/Metal)