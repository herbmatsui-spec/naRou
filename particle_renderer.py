"""
Particle Renderer Module - Handles particle rendering
"""
from __future__ import annotations
from typing import List, Optional
import tcod

from constants import VIEW_WIDTH, VIEW_HEIGHT
from render_context import RenderContext
from map_engine import TILE_REGISTRY


class ParticleRenderer:
    """パーティクル描画専用クラス"""

    @classmethod
    def render(cls, console: tcod.console.Console, context: RenderContext,
               cam_x: int, cam_y: int) -> None:
        """パーティクル描画のメインエントリポイント"""
        for pt in context.particles:
            vx = int(pt.x) - cam_x
            vy = int(pt.y) - cam_y
            if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                # Check if particle has a tile_id for Tiny Rogue tile rendering
                if getattr(pt, 'tile_id', None):
                    # Render using tile atlas
                    uv = TILE_REGISTRY.get_uv(pt.tile_id, scale="tiny_rogue_16")
                    # Draw semigraphics using the tile
                    # For now, fall back to character if tile rendering not available
                    console.print(x=vx, y=vy, string=pt.char or "•", fg=pt.color)
                else:
                    console.print(x=vx, y=vy, string=pt.char, fg=pt.color)