# Renderer Architecture

## Overview

This document describes the renderer architecture for naRou, implementing a dual-backend rendering system supporting both traditional terminal (tcod) and modern WebGL/WebGPU clients.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Game Engine                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    RendererBase (Abstract)                  │
│  • begin_frame()          • draw_tile()                     │
│  • end_frame()            • draw_text()                     │
│  • set_viewport()         • create_texture()                │
│  • get_viewport()         • destroy_texture()               │
│  • clear()                • get_texture_size()              │
│  • present()              • resize()                        │
│  • get_framebuffer_size()                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│     TCODRenderer        │   │     WebGLRenderer       │
│  (core/tcod_renderer.py)│   │   (webgl/renderer.ts)   │
└─────────────────────────┘   └─────────────────────────┘
              │                           │
              ▼                           ▼
       ┌─────────────┐             ┌─────────────┐
       │ libtcod     │             │ WebGL2 /    │
       │ Console API │             │ WebGPU      │
       └─────────────┘             └─────────────┘
```

## Core Components

### 1. RendererBase (core/renderer_base.py)

Abstract base class defining the renderer interface. All backend renderers must implement this interface.

Key methods:
- `begin_frame()` / `end_frame()`: Frame lifecycle
- `draw_tile()`: Draw a textured quad
- `draw_text()`: Draw MSDF-rendered text
- `set_viewport()` / `get_viewport()`: Viewport management
- Texture management: `create_texture()`, `destroy_texture()`, `get_texture_size()`
- `resize()`: Handle window resize

### 2. TCODRenderer (core/tcod_renderer.py)

Terminal-based renderer using libtcod.

Features:
- Uses `tcod.console.Console` for character-cell rendering
- Supports MSDF font atlas for high-quality text
- Integrates with existing tileset system (assets/tiles/tileset_32x32.png)
- Fallback to procedural block elements if tileset missing

Integration points:
- `initialize_context()`: Creates tcod context with SDL window
- `set_msdf_atlas()`: Injects MSDF atlas for text rendering

### 3. WebGLRenderer (webgl/renderer.ts)

Modern GPU-accelerated renderer for web clients.

Features:
- WebGL2 with fallback to WebGPU
- MSDF text rendering via custom shaders
- Instanced drawing for tile batches
- Subpixel positioning via vertex shader
- Texture atlas management

Shader programs:
- `tile_program`: Textured quad rendering
- `text_program`: MSDF text with smoothstep alpha

### 4. MSDF Atlas (core/msdf_atlas.py)

Multi-channel Signed Distance Field font atlas generator.

Features:
- Generates SDF from TTF fonts using PIL
- Packs glyphs into power-of-2 atlas texture
- Exports glyph metrics (advance, bearing, UV coordinates)
- JSON serialization for caching

### 5. Pixel Perfect Utilities (core/pixel_perfect.py)

Coordinate conversion utilities for subpixel positioning.

Functions:
- `logical_to_physical()`: Logical → physical with subpixel
- `get_css_transform()`: CSS transform string for web
- `calculate_optimal_scale()`: Integer scale calculation
- `lerp_subpixel()`: Smooth interpolation

## Data Flow

### Frame Rendering

```
Game Engine
    │
    ▼
RendererBase.begin_frame()
    │
    ├─▶ Clear screen
    ├─▶ Draw map tiles (TileDrawCall[])
    ├─▶ Draw entities (TileDrawCall[])
    ├─▶ Draw UI (TileDrawCall[] + TextDrawCall[])
    ├─▶ Draw particles (TileDrawCall[])
    │
    ▼
RendererBase.end_frame()
    │
    ├─▶ TCOD: context.present(console)
    └─▶ WebGL: Swap buffers
```

### Text Rendering Pipeline

```
TextDrawCall
    │
    ▼
MSDFAtlas.get_glyph(ch)
    │
    ├─▶ Returns GlyphMetrics (UV coords, advance, bearing)
    │
    ▼
Renderer.draw_text()
    │
    ├─▶ TCOD: console.print() with MSDF texture
    └─▶ WebGL: Instanced quad + MSDF fragment shader
```

### Texture Management

```
create_texture(path)
    │
    ├─▶ TCOD: tcod.image.Image → texture_id
    └─▶ WebGL: gl.createTexture() + Image.onload → texture_id
    
destroy_texture(id)
    │
    ├─▶ TCOD: del cache[id]
    └─▶ WebGL: gl.deleteTexture() + del cache[id]
```

## Integration with Game Systems

### RenderSystem (render_system.py)

The existing `RenderSystem.render_all()` is the main entry point. It:
1. Computes camera offset
2. Delegates to specialized renderers:
   - `MapRenderer` → tiles
   - `EntityRenderer` → entities
   - `ItemRenderer` → items
   - `ParticleRenderer` → particles
   - `UIRenderer` → UI panels
3. Applies post-processing via `ScreenFilterManager`

### Migration Path

To integrate new renderers:
1. Implement `RendererBase` for new backend
2. Update `RenderSystem` to accept `RendererBase` instance
3. Convert existing draw calls to `TileDrawCall`/`TextDrawCall`
4. Add backend-specific shaders/assets

## Configuration

### Design Tokens (design_tokens.json)

Accessibility and theming:
```json
{
  "accessibility": {
    "colorBlind": { "protan": {...}, "deutan": {...}, "tritan": {...} },
    "highContrast": { ... },
    "fontScale": { "minimum": 0.8, "maximum": 2.0, "step": 0.1 }
  }
}
```

### Asset Paths

- Tilesets: `assets/tiles/tileset_{16,32,64}x{16,32,64}.png`
- Fonts: System fonts or `assets/fonts/`
- Shaders: `shaders/` (GLSL) / `webgl/` (WGSL)

## Testing

### Renderer Parity Test (tests/test_renderer_parity.py)

Verifies both backends implement the same interface:
- begin_frame / end_frame
- draw_tile
- draw_text
- viewport management
- clear / resize

Run: `pytest tests/test_renderer_parity.py -q`

### Visual Regression

Future: Screenshot comparison between backends using pixelmatch.

## Performance Considerations

### TCOD Backend
- Character-cell based, low GPU overhead
- Suitable for terminal/SSH environments
- Limited to grid-aligned rendering

### WebGL Backend
- GPU-accelerated, supports effects
- Subpixel positioning for smooth animation
- Batch rendering via instancing
- Target: 60 FPS at 1920×1080

## Future Extensions

1. **WebGPU Renderer**: Modern GPU API with compute shaders
2. **Vulkan/Metal Renderer**: Native desktop GPU acceleration
3. **Headless Renderer**: For CI/testing without display
4. **Shader Hot-Reload**: Development iteration speed

## References

- [libtcod Documentation](https://libtcod.readthedocs.io/)
- [MSDF Font Rendering](https://github.com/Chlumsky/msdfgen)
- [WebGL2 Specification](https://www.khronos.org/registry/webgl/specs/latest/2.0/)
- [WebGPU Specification](https://gpuweb.github.io/gpuweb/)