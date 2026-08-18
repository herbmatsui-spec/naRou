"""
Particle Renderer Module - Handles particle rendering
"""
from __future__ import annotations
from typing import List, Optional
import tcod

from constants import VIEW_WIDTH, VIEW_HEIGHT
from render_context import RenderContext


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
                console.print(x=vx, y=vy, string=pt.char, fg=pt.color)