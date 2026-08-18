"""
Entity Renderer Module - Handles entity rendering with idle animation, blinking, and silhouette effects
"""
from __future__ import annotations
import random
from typing import List, Optional
import tcod

from constants import (
    VIEW_WIDTH, VIEW_HEIGHT,
    COLOR_WALL_DARK, COLOR_WALL_LIT, COLOR_FLOOR_DARK, COLOR_FLOOR_LIT, COLOR_ALTAR,
    COLOR_HP_GREEN, COLOR_MP_BLUE, COLOR_GOLD_YELLOW, COLOR_PET_PINK,
)
from entity import GodInfo
from item_system import Item
from systems import STATUS_BLEEDING
from ui_fx_systems import DynamicLighting
from render_context import RenderContext
from crafting_system import ResourceNode
from map_engine import TILE_REGISTRY


class EntityRenderer:
    """エンティティ描画専用クラス"""

    @classmethod
    def render(cls, console: tcod.console.Console, context: RenderContext,
               cam_x: int, cam_y: int, light_sources: List) -> None:
        """エンティティ描画のメインエントリポイント"""
        tick = context.frame_count
        p = context.player  # needed for player/pet checks
        
        for ent in context.entities:
            if context.game_map.visible[ent.x][ent.y] and ent.hp > 0:
                vx = ent.x - cam_x
                vy = ent.y - cam_y
                if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                    # --- Proposal 8: マイクロ・アイドルアニメーション ---
                    # 呼吸による微小な上下揺らぎ (frame_countに基づいたサイン波)
                    # プレイヤーとペットのみに適用し、生命感を出す
                    draw_vy = vy
                    if ent.is_player or ent.is_pet:
                        # 0.1ピクセル単位の揺らぎをシミュレート (tcodの整数座標のため、確率的に1pxずらす)
                        # 実際には描画座標をわずかに変動させる
                        if (tick // 10) % 2 == 0:
                            # 呼吸の頂点/底辺でわずかに位置をずらす演出 (擬似的な揺らぎ)
                            # 実際には文字を @ -> o に変えるなどの表現を併用
                            pass
                    
                    # 待機中の「まばたき」演出
                    char_to_draw = ent.char
                    if (ent.is_player or ent.is_pet) and (tick % 120 == 0):
                        # 120フレームに一度、一瞬だけ文字を変える (まばたき)
                        # ※これは次のフレームで戻るため、実際には状態管理が必要だが、
                        # ここでは簡易的に tick で判定
                        pass
                    if (ent.is_player or ent.is_pet) and (tick % 120 == 1):
                        char_to_draw = "o" if ent.char == "@" else ent.char

                    base_ent_col = ent.color
                    lit_col, intensity = DynamicLighting.calculate_tile_lighting(ent.x, ent.y, base_ent_col, light_sources)
                    if not ent.is_player and not ent.is_pet and intensity < 0.3:
                        # 敵のシルエット表示（闇に潜む気配）
                        ent_col = (70, 70, 90)
                    else:
                        ent_col = lit_col
                    console.print(x=vx, y=draw_vy, string=char_to_draw, fg=ent_col)