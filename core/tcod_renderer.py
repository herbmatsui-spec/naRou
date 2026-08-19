from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple, Dict
import numpy as np
import tcod
import tcod.tileset
import tcod.console

from core.renderer_base import (
    RendererBase, TileDrawCall, TextDrawCall, Viewport
)
from core.msdf_atlas import MSDFAtlas, GlyphMetrics


class TCODRenderer(RendererBase):
    def __init__(self, width: int, height: int, tileset_path: Optional[str] = None):
        self.width = width
        self.height = height
        
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
        
        self._texture_cache: Dict[int, tcod.image.Image] = {}
        self._next_texture_id = 1
        
        self._msdf_atlas: Optional[MSDFAtlas] = None
        self._msdf_texture_id: Optional[int] = None
        
        self._viewport = Viewport(0, 0, width, height)

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

    def end_frame(self) -> None:
        if self.context:
            self.context.present(self.console)

    def draw_tile(self, call: TileDrawCall) -> None:
        if call.texture_id in self._texture_cache:
            image = self._texture_cache[call.texture_id]
            self.console.draw_semigraphics(
                image,
                call.x,
                call.y,
            )

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
        texture_id = self._next_texture_id
        self._next_texture_id += 1
        self._texture_cache[texture_id] = image
        return texture_id

    def destroy_texture(self, texture_id: int) -> None:
        if texture_id in self._texture_cache:
            del self._texture_cache[texture_id]

    def get_texture_size(self, texture_id: int) -> Tuple[int, int]:
        if texture_id in self._texture_cache:
            img = self._texture_cache[texture_id]
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