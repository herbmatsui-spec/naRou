# Entity Rendering System Documentation

## Overview

This document describes the unified entity rendering system for naRou, implementing direction/state-based animated sprites for both terminal (tcod) and web (PixiJS) renderers.

## Architecture

### Core Components

1. **TileAtlas** (`core/tile_atlas.py`, `demos/lib/TileAtlas.js`)
   - Unified tile definition loader
   - UV coordinate calculation for tile_id + variant + frame + direction + state
   - Autotile support (4-bit neighbor mask → 16 variants)
   - Animation state management

2. **EntityAnimState** (`core/entity_renderer.py`)
   - Per-entity animation state tracking
   - Frame advancement with configurable FPS
   - Loop/one-shot animation support
   - Attack timer for synchronized attack animations

3. **EntityRenderer** (`core/entity_renderer.py`, `entity_renderer.py`)
   - Terminal: Sub-image extraction and caching
   - Web: PIXI.AnimatedSprite creation and management
   - Shared logic for facing calculation and state transitions

4. **TCODRenderer** (`core/tcod_renderer.py`)
   - Implements `draw_entity(EntityDrawCall)`
   - Sub-image extraction from master atlas
   - Performance monitoring

5. **Web Renderer** (`web_game_client.html`)
   - TileAtlas initialization
   - Entity sprite rendering loop
   - Attack timer synchronization

### Data Flow

```
tileset_def.json + atlas metadata
         ↓
    TileAtlas (UV lookup)
         ↓
┌────────┴────────┐
Terminal          Web
   ↓               ↓
EntityRenderer   TileAtlas.createAnimatedSprite
   ↓               ↓
TCODRenderer     web_game_client.html
```

## Tile Definition Schema

```json
{
  "TILE_ID": {
    "file": "ATLAS_KEY",           // Key in atlas metadata
    "variants": 1,                  // Number of variants (for autotile)
    "animated": true,               // Has animation frames
    "frames": 4,                    // Number of animation frames
    "fps": 8,                       // Animation frames per second
    "directions": 4,                // Directional sprites (0=down,1=left,2=right,3=up)
    "states": ["idle","walk","attack"], // Animation states
    "autotile": false,              // Uses 4-bit neighbor mask
    "atlas_scale": "16",            // Source atlas scale
    "frame_width": 16,              // Frame width in pixels
    "anchor_x": 0.5,                // Sprite anchor (0-1)
    "anchor_y": 1.0
  }
}
```

## Direction Convention

```
0 = Down (South)  - Default
1 = Left (West)
2 = Right (East)
3 = Up (North)
```

Calculated from movement vector:
```python
def calculate_facing(dx, dy):
    if abs(dx) > abs(dy):
        return 2 if dx > 0 else 1  # Right or Left
    else:
        return 0 if dy > 0 else 3  # Down or Up
```

## Animation States

| State  | Description                    | Loop  | Typical FPS |
|--------|--------------------------------|-------|-------------|
| idle   | Standing still                 | Yes   | 8-10        |
| walk   | Moving                         | Yes   | 8-10        |
| attack | Attacking (one-shot)           | No    | 12          |
| dead   | Death animation (one-shot)     | No    | 4           |

## Attack Animation Synchronization

### Server → Client Protocol

Server includes in entity state:
```json
{
  "facing": 2,
  "state": "attack",
  "attack_timer": 0.5,
  "moving": false
}
```

### Client Processing (Web)

```javascript
// Server sends attack_timer > 0 → client starts local timer
if (ent.attack_timer > 0) {
    entityAttackTimers.set(id, { timer: ent.attack_timer, duration: 0.5 });
}

// Client counts down local timer
if (attack_timer > 0) {
    attack_timer -= dt;
    state = "attack";
    if (attack_timer <= 0) state = "idle";
}
```

### Terminal Processing

```python
# In EntityAnimState.update()
elif is_attacking:
    self.state = "attack"
    self.attack_timer = 0.5
    self.loop = False
elif self.attack_timer > 0:
    self.attack_timer -= dt
    if self.attack_timer <= 0 and self.state == "attack":
        self.state = "idle"
        self.loop = True
```

## Autotiling

4-bit neighbor mask (bit0=up, bit1=right, bit2=down, bit3=left) maps to 16 variants:

```python
AUTOTILE_MAP = {
    0b0000: 0,
    0b0001: 1,
    0b0010: 2,
    0b0100: 4,
    0b1000: 8,
    0b0011: 3,
    0b0110: 6,
    0b1100: 12,
    0b1001: 9,
    0b0101: 5,
    0b1010: 10,
    0b0111: 7,
    0b1110: 14,
    0b1101: 13,
    0b1011: 11,
    0b1111: 15,
}
```

## API Reference

### TileAtlas (Python)

```python
atlas = TileAtlas()

# UV lookup
uv = atlas.get_uv("PLAYER", direction=1, frame=2, state="walk", scale="32")
# Returns TileUV(x, y, w, h, scale)

# Autotile
variant = atlas.get_autotile_variant("TILE_WALL", neighbor_mask)
mask = atlas.calculate_neighbor_mask(tile_map, x, y, "TILE_WALL")

# Animation
anim = atlas.create_anim_state("TILE_WATER", fps=5)
anim.update(dt)  # Returns True if frame changed
uv = anim.get_uv("32")
```

### TileAtlas (JavaScript)

```javascript
const data = await TileAtlas.loadAll(["16", "32", "64"]);
const tileAtlas = new TileAtlas(data.baseTextures, data.metadatas, data.defs);

// Static sprite
const sprite = tileAtlas.createSprite("TILE_WALL", { variant: 3, scale: "32" });

// Animated sprite
const anim = tileAtlas.createAnimatedSprite("TILE_WATER", {
    direction: 0, state: "idle", fps: 5, loop: true
});

// Autotile
const variant = tileAtlas.getAutotileVariant("TILE_WALL", mask);
const mask = tileAtlas.calculateNeighborMask(tileMap, x, y, "TILE_WALL");
```

### EntityRenderer (Python)

```python
renderer = EntityRenderer(tile_atlas)

# Register entity
eid = renderer.register_entity("PLAYER", x=10, y=10, direction=0, state="idle")

# Update per frame
renderer.update_entity(eid, x=10, y=10, direction=2, state="walk", dt=1 / 60)

# Get subimage for rendering
sub_image = renderer.get_subimage(eid)
console.draw_semigraphics(sub_image, x, y)
```

## Testing

### Entity Parity Test
```bash
python tools/test_entity_parity.py
```
Verifies UV consistency across scales, autotile mapping, facing calculation, and animation state machines.

### Attack Animation Sync Test
```bash
python tools/test_attack_anim.py
```
Verifies attack timer synchronization, rapid trigger handling, movement interruption, death override, and web-side timer simulation.

### Visual Regression
```bash
# Generate reference images
python tools/visual_regression.py --generate

# Compare current rendering with references
python tools/visual_regression.py --compare
```

## Performance

### Caching Strategy

- **TileAtlas**: UV lookups are O(1) dictionary lookups
- **EntityRenderer**: Sub-image cache keyed by (tile_id, frame, direction, state)
- **Web**: AnimatedSprite prototypes cached by (tile_id, direction, state, fps, loop)

### Auto Quality Adjustment

Both renderers monitor FPS and automatically reduce quality:
- **Terminal**: Reduces particle effects, limits animations
- **Web**: Reduces particle count, disables bloom, halves animation speed

## Asset Requirements

### Atlas Images
- `assets/tiles/tileset_16x16.png` + `.json`
- `assets/tiles/tileset_32x32.png` + `.json`
- `assets/tiles/tileset_64x64.png` + `.json`

### Source Assets
- `assets/src/terrain/*.ase` (Aseprite files)
- `assets/src/entities/*.ase`
- `assets/src/effects/*.ase`
- `assets/src/objects/*.ase`

### Build Pipeline
```bash
python tools/build_assets.py
```
Processes Aseprite files → generates atlas PNG/JSON → updates tileset_def.json

## Migration Notes

### From Placeholder Rendering

**Before** (web_game_client.html):
```javascript
// Placeholder colored rectangles
entityGraphics.beginFill(0xff0000);
entityGraphics.drawCircle(0, 0, TILE_SIZE * 0.4);
```

**After**:
```javascript
// Real animated sprites
const animKey = `${tileId}_${dir}_${state}`;
if (!entityAnimCache[animKey]) {
    entityAnimCache[animKey] = tileAtlas.createAnimatedSprite(tileId, {
        direction: dir, state, fps: 10, loop: state !== "attack"
    });
}
const sprite = entityAnimCache[animKey];
sprite.x = px; sprite.y = py + bounce;
entityLayer.addChild(sprite);
```

### Adding New Entity Types

1. Add Aseprite source to `assets/src/entities/`
2. Run `python tools/build_assets.py`
3. Update `tileset_def.json` with new tile definition
4. Add entity type mapping in `getEntityTileId()` (web) and `_get_tile_id()` (terminal)
5. Run visual regression tests to generate references

## Troubleshooting

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Entity invisible | UV out of bounds | Check frame count vs atlas width |
| Wrong direction | Facing calculation error | Verify `calculate_facing(dx, dy)` |
| Attack loops | `loop=False` not set | Ensure attack state sets `loop=False` |
| Death doesn't animate | `loop=True` on death | Register with `state="dead"` |
| Web/WebGL errors | Atlas not loaded | Ensure `TileAtlas.loadAll()` completes |

### Debug Commands

```bash
# Test TileAtlas UV lookup
python -c "from core.tile_atlas import TileAtlas; a=TileAtlas(); print(a.get_uv('PLAYER', direction=1, frame=2))"

# Test entity animation
python -c "from core.entity_renderer import EntityRenderer; from core.tile_atlas import TileAtlas; a=TileAtlas(); r=EntityRenderer(a); e=r.register_entity('PLAYER',0,0); r.update_entity(e,0,0,2,'attack',True,1/60); print(r.entity_anims[e].state)"

# Run all tests
python tools/test_entity_parity.py && python tools/test_attack_anim.py
python tools/visual_regression.py --compare
```
