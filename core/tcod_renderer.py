from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np
import tcod
import tcod.tileset
import tcod.console

from core.renderer_base import (
    RendererBase, TileDrawCall, TextDrawCall, Viewport, EntityDrawCall,
    LightingDrawCall, ParticleDrawCall
)
from core.msdf_atlas import MSDFAtlas, GlyphMetrics
from core.tile_atlas import TileAtlas, AnimState, TileUV
from core.entity_renderer import EntityRenderer, calculate_facing, calculate_facing_to_target
from core.lighting import TerminalLightingSystem, TerminalParticleSystem


class TCODRenderer(RendererBase):
    def __init__(self, width: int, height: int, tileset_path: Optional[str] = None):
        self.width = width
        self.height = height
        
        # Initialize TileAtlas for unified tile management
        self.tile_atlas = TileAtlas(default_scale="32")
        
        # Load master tileset for tcod (32x32)
        if tileset_path and Path(tileset_path).exists():
            self.tileset = tcod.tileset.load_tilesheet(
                tileset_path, 32, 8, tcod.tileset.CHARMAP_TCOD
            )
        else:
            default_tileset = Path("assets/tiles/tileset_32x32.png")
            if default_tileset.exists():
                self.tileset = tcod.tileset.load_tilesheet(
                    default_tileset.as_posix(), 32, 8, tcod.tileset.CHARMAP_TCOD
                )
            else:
                self.tileset = tcod.tileset.procedural_block_elements()
        
        self.console = tcod.console.Console(width, height, order="F")
        self.context: Optional[tcod.context.Context] = None
        
        # Sub-image cache: (tile_id, variant, frame, direction, state) -> tcod.image.Image
        self._subimage_cache: Dict[Tuple[str, int, int, int, str], tcod.image.Image] = {}
        
        # Animation tracking: (x, y) -> AnimState
        self._tile_animations: Dict[Tuple[int, int], AnimState] = {}
        
        self._msdf_atlas: Optional[MSDFAtlas] = None
        self._msdf_texture_id: Optional[int] = None
        
        self._viewport = Viewport(0, 0, width, height)

        # EntityRenderer for entity animations
        self.entity_renderer = EntityRenderer(self.tile_atlas)

        # Lighting and Particle systems
        self.lighting = TerminalLightingSystem(width, height)
        self.particles = TerminalParticleSystem(width, height)

        # Performance monitoring
        self._frame_count = 0
        self._last_frame_time = 0.0
        self._fps = 0.0
        self._draw_calls = 0
        self._quality_reduced = False

    def _monitor_performance(self, dt: float) -> None:
        """Monitor and auto-adjust quality based on FPS."""
        self._frame_count += 1
        self._last_frame_time += dt
        if self._last_frame_time >= 1.0:
            self._fps = self._frame_count / self._last_frame_time
            self._frame_count = 0
            self._last_frame_time = 0.0
            
            if self._frame_count % 60 == 0:
                print(f"[TCOD] FPS: {self._fps:.1f}, Draw calls: {self._draw_calls}, Animations: {len(self._tile_animations)}")
            
            # Auto quality adjustment
            if self._fps < 20 and not self._quality_reduced:
                self._quality_reduced = True
                print("[TCOD] Performance low, reducing quality")
                # Reduce particle effects, limit animations
                # (particle system would need to be integrated)
            elif self._fps > 40 and self._quality_reduced:
                self._quality_reduced = False
                print("[TCOD] Performance recovered, restoring quality")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        return {
            "fps": self._fps,
            "draw_calls": self._draw_calls,
            "tile_animations": len(self._tile_animations),
            "entity_animations": len(self.entity_renderer.entity_anims),
            "cached_subimages": len(self._subimage_cache),
            "quality_reduced": self._quality_reduced
        }

    def initialize_context(self, sdl_window: bool = True) -> None:
        self.context = tcod.context.new(
            columns=self.width,
            rows=self.height,
            tileset=self.tileset,
            title="naRou",
            sdl_window=sdl_window,
        )

    def begin_frame(self) -> None:
        self.console.clear()
        self._draw_calls = 0
        # Update particle physics
        self.particles.update(1/60)

    def end_frame(self, dt: float = 0.016) -> None:
        # Sync quality settings
        if hasattr(self.particles, 'set_quality'):
            self.particles.set_quality(self._quality_reduced)
        self._monitor_performance(dt)
        if self.context:
            self.context.present(self.console)

    def draw_tile(self, call: TileDrawCall) -> None:
        """
        Draw a tile using TileAtlas for UV lookup.
        call.texture_id can be:
        - str: tile_id (uses defaults)
        - tuple: (tile_id, variant, frame, direction, state)
        """
        # Parse texture_id
        if isinstance(call.texture_id, str):
            tile_id = call.texture_id
            variant = frame = direction = 0
            state = "idle"
        elif isinstance(call.texture_id, tuple):
            tile_id = call.texture_id[0]
            variant = call.texture_id[1] if len(call.texture_id) > 1 else 0
            frame = call.texture_id[2] if len(call.texture_id) > 2 else 0
            direction = call.texture_id[3] if len(call.texture_id) > 3 else 0
            state = call.texture_id[4] if len(call.texture_id) > 4 else "idle"
        else:
            # Fallback
            self._draw_fallback_tile(call.x, call.y)
            return

        # Get sub-image from cache or create
        sub_image = self._get_cached_subimage(tile_id, variant, frame, direction, state)
        if sub_image:
            self.console.draw_semigraphics(sub_image, call.x, call.y)
            self._draw_calls += 1
        else:
            self._draw_fallback_tile(call.x, call.y)

    def _get_cached_subimage(
        self, 
        tile_id: str, 
        variant: int, 
        frame: int, 
        direction: int, 
        state: str
    ) -> Optional[tcod.image.Image]:
        """Get or create cached sub-image for a tile configuration."""
        key = (tile_id, variant, frame, direction, state)
        if key in self._subimage_cache:
            return self._subimage_cache[key]

        # Get UV from TileAtlas
        try:
            uv = self.tile_atlas.get_uv(tile_id, variant, frame, direction, state, scale="32")
        except KeyError:
            return None

        # Get master image path
        master_path = self.tile_atlas.get_master_image_path(tile_id, scale="32")
        if not master_path or not master_path.exists():
            return None

        # Load master image if not cached
        master_key = f"master_{master_path}"
        if not hasattr(self, '_master_images'):
            self._master_images = {}
        if master_key not in self._master_images:
            self._master_images[master_key] = tcod.image.Image(master_path.as_posix())
        master = self._master_images[master_key]

        # Extract sub-image (crop)
        sub = tcod.image.Image(uv.w, uv.h)
        # Use numpy for fast pixel copy
        try:
            master_arr = np.array(master)  # (H, W, 4) or (H, W, 3)
            sub_arr = master_arr[uv.y:uv.y+uv.h, uv.x:uv.x+uv.w]
            # Create new image from array
            sub = tcod.image.Image(sub_arr.shape[1], sub_arr.shape[0])
            # tcod.image.Image doesn't have direct array setter, use put_pixel
            # This is slow but only done once per unique tile config
            for py in range(uv.h):
                for px in range(uv.w):
                    rgba = sub_arr[py, px]
                    if rgba.shape[0] == 4:
                        sub.put_pixel(px, py, tuple(rgba))
                    else:
                        sub.put_pixel(px, py, (rgba[0], rgba[1], rgba[2], 255))
        except Exception:
            return None

        self._subimage_cache[key] = sub
        return sub

    def _draw_fallback_tile(self, x: int, y: int) -> None:
        """Draw a fallback tile (colored rectangle)."""
        # Simple fallback: draw a colored block
        self.console.draw_rect(x, y, 1, 1, 0, fg=(255, 0, 255), bg=(0, 0, 0))

    def update_animations(self, dt: float) -> None:
        """Update all running tile animations. Call once per frame."""
        for (tx, ty), anim in list(self._tile_animations.items()):
            if anim.update(dt):
                # Frame changed - mark for redraw (handled by game loop)
                pass
            if not anim.loop and anim.frame == 0 and anim.timer == 0:
                # One-shot animation finished
                del self._tile_animations[(tx, ty)]

    def draw_entity(self, call: EntityDrawCall) -> None:
        """Draw an entity with direction/state animation."""
        # Get sub-image from entity renderer cache
        sub_image = self._get_entity_subimage(
            call.tile_id, call.direction, call.state, call.frame
        )
        if sub_image:
            # Apply bounce offset
            draw_y = call.y + int(call.bounce)
            self.console.draw_semigraphics(sub_image, call.x, draw_y)
            self._draw_calls += 1
        else:
            self._draw_fallback_tile(call.x, call.y)

    def draw_lighting(self, call: LightingDrawCall) -> None:
        """Receive lighting data for this frame."""
        if call.light_map:
            self.lighting.light_map = call.light_map
        self.lighting.light_sources = call.light_sources
        self.lighting.enemy_cones = call.enemy_cones
        self.lighting.ambient_light = call.ambient_light
        self.lighting._time = call.time

    def draw_particles(self, call: ParticleDrawCall) -> None:
        """Receive particle data for this frame."""
        for p in call.particles:
            self.particles.emit({
                'type': p.type,
                'x': p.x,
                'y': p.y,
                'count': 1,
                'lifetime': p.life,
                'colors': [p.color],
                'chars': [p.char]
            })

    def _get_entity_subimage(
        self, 
        tile_id: str, 
        direction: int, 
        state: str, 
        frame: int
    ) -> Optional[tcod.image.Image]:
        """Get or create cached sub-image for an entity configuration."""
        key = (tile_id, frame, direction, state)
        if key in self._subimage_cache:
            return self._subimage_cache[key]

        # Get UV from TileAtlas
        try:
            uv = self.tile_atlas.get_uv(tile_id, variant=0, frame=frame, 
                                       direction=direction, state=state, scale="32")
        except KeyError:
            return None

        # Get master image path
        master_path = self.tile_atlas.get_master_image_path(tile_id, scale="32")
        if not master_path or not master_path.exists():
            return None

        # Load master image if not cached
        master_key = f"master_{master_path}"
        if not hasattr(self, '_master_images'):
            self._master_images = {}
        if master_key not in self._master_images:
            self._master_images[master_key] = tcod.image.Image(master_path.as_posix())
        master = self._master_images[master_key]

        # Extract sub-image (crop)
        sub = tcod.image.Image(uv.w, uv.h)
        try:
            master_arr = np.array(master)
            sub_arr = master_arr[uv.y:uv.y+uv.h, uv.x:uv.x+uv.w]
            sub = tcod.image.Image(sub_arr.shape[1], sub_arr.shape[0])
            for py in range(uv.h):
                for px in range(uv.w):
                    rgba = sub_arr[py, px]
                    if rgba.shape[0] == 4:
                        sub.put_pixel(px, py, tuple(rgba))
                    else:
                        sub.put_pixel(px, py, (rgba[0], rgba[1], rgba[2], 255))
        except Exception:
            return None

        self._subimage_cache[key] = sub
        return sub

    def start_tile_animation(
        self, 
        x: int, 
        y: int, 
        tile_id: str, 
        variant: int = 0,
        direction: int = 0,
        state: str = "idle",
        fps: int = None,
        loop: bool = True
    ) -> None:
        """Start an animation at a tile position."""
        anim = self.tile_atlas.create_anim_state(
            tile_id, variant=variant, direction=direction, 
            state=state, fps=fps, loop=loop
        )
        self._tile_animations[(x, y)] = anim

    def get_tile_animation_frame(self, x: int, y: int) -> Optional[Tuple[int, int, int, int]]:
        """Get current animation frame UV for a position."""
        anim = self._tile_animations.get((x, y))
        if not anim:
            return None
        uv = anim.get_uv(scale="32")
        return (uv.x, uv.y, uv.w, uv.h)

    def render_lighting_pass(
        self,
        cam_x: int,
        cam_y: int,
        view_w: int,
        view_h: int,
        visible: Optional[List[List[bool]]] = None,
        explored: Optional[List[List[bool]]] = None,
        time: float = 0.0
    ) -> None:
        """ライティング完全パス実行 (タイル描画前に呼び出し)"""
        self.lighting.render_pass(
            self.console, cam_x, cam_y, view_w, view_h,
            visible, explored, time
        )

    def render_particles_pass(self, cam_x: int, cam_y: int) -> None:
        """パーティクル描画パス実行 (最上層、全描画後に呼び出し)"""
        self.particles.draw(self.console, cam_x, cam_y)

    def draw_text(self, call: TextDrawCall) -> None:
        if self._msdf_atlas is None:
            self.console.print(
                x=call.x,
                y=call.y,
                string=call.text,
                fg=self._color_to_tuple(call.color),
            )
            return
        
        x = call.x
        y = call.y
        scale = call.font_size / self._msdf_atlas.font_size
        
        for ch in call.text:
            glyph = self._msdf_atlas.get_glyph(ch)
            if glyph and glyph.width > 0:
                self.console.print(
                    x=x,
                    y=y,
                    string=ch,
                    fg=self._color_to_tuple(call.color),
                )
                x += int(glyph.advance * scale)
            else:
                x += int(call.font_size * 0.5)

    def set_viewport(self, viewport: Viewport) -> None:
        self._viewport = viewport

    def get_viewport(self) -> Viewport:
        return self._viewport

    def create_texture(self, path: Path) -> int:
        if not path.exists():
            raise FileNotFoundError(f"Texture not found: {path}")
        
        image = tcod.image.Image(path.as_posix())
        texture_id = len(self._subimage_cache) + 1
        self._subimage_cache[texture_id] = image  # Reuse cache dict
        return texture_id

    def destroy_texture(self, texture_id: int) -> None:
        if texture_id in self._subimage_cache:
            del self._subimage_cache[texture_id]

    def get_texture_size(self, texture_id: int) -> Tuple[int, int]:
        if texture_id in self._subimage_cache:
            img = self._subimage_cache[texture_id]
            return (img.width, img.height)
        return (0, 0)

    def clear(self, color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)) -> None:
        r, g, b, a = [int(c * 255) for c in color]
        self.console.clear(fg=(r, g, b), bg=(0, 0, 0))

    def present(self) -> None:
        if self.context:
            self.context.present(self.console)

    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.console = tcod.console.Console(width, height, order="F")
        if self.context:
            self.context = tcod.context.new(
                columns=width,
                rows=height,
                tileset=self.tileset,
                title="naRou",
            )

    def get_framebuffer_size(self) -> Tuple[int, int]:
        return (self.width, self.height)

    def set_msdf_atlas(self, atlas: MSDFAtlas) -> None:
        self._msdf_atlas = atlas

    def _color_to_tuple(self, color: Tuple[float, float, float, float]) -> Tuple[int, int, int]:
        return tuple(int(c * 255) for c in color[:3])