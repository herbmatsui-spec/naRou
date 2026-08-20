"""
Item Renderer Module - Handles item rendering with glow, hunger aura, and particle effects
"""

from __future__ import annotations

import random

import tcod

from constants import (
    CAT_FOOD,
    VIEW_HEIGHT,
    VIEW_WIDTH,
)
from render_context import RenderContext
from ui_fx_systems import DynamicLighting


class ItemRenderer:
    """アイテム描画専用クラス"""

    @classmethod
    def render(
        cls,
        console: tcod.console.Console,
        context: RenderContext,
        cam_x: int,
        cam_y: int,
        light_sources: list,
    ) -> None:
        """アイテム描画のメインエントリポイント"""
        is_starving = context.survival.hunger <= 2000
        tick = context.frame_count

        for itm in context.items_on_ground:
            if context.game_map.visible[itm.x][itm.y]:
                vx = itm.x - cam_x
                vy = itm.y - cam_y
                if (
                    0 <= vx < context.game_map.width
                    and 0 <= vy < context.game_map.height
                ):
                    # Note: VIEW_WIDTH and VIEW_HEIGHT are used for screen bounds, but we already checked visibility via game_map.visible
                    # However, the original code also checked 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT
                    # We'll keep the VIEW_* check to be safe.
                    if (
                        0 <= vx < context.game_map.width
                        and 0 <= vy < context.game_map.height
                    ):
                        # Convert to view coordinates using the same VIEW_WIDTH/HEIGHT as original
                        # Actually the original used VIEW_WIDTH, VIEW_HEIGHT for screen dimensions, not map dimensions.
                        # We'll compute using the same formula as in the original: vx = itm.x - cam_x, then check 0 <= vx < VIEW_WIDTH
                        # Let's recompute view coordinates based on camera and view size.
                        view_vx = itm.x - cam_x
                        view_vy = itm.y - cam_y
                        if 0 <= view_vx < VIEW_WIDTH and 0 <= view_vy < VIEW_HEIGHT:
                            # --- アイテム神々しい発光演出 (Proposal 5) ---
                            # レアアイテム（ここでは仮に色で判定、または特定のカテゴリ）にゴッドレイと粒子を付与
                            is_rare = itm.color in (
                                (255, 215, 0),
                                (200, 100, 255),
                                (100, 255, 220),
                            )
                            if is_rare:
                                # 1. ゴッドレイ（十字方向への微かな光の筋）
                                ray_col = (
                                    int(itm.color[0] * 0.5),
                                    int(itm.color[1] * 0.5),
                                    int(itm.color[2] * 0.5),
                                )
                                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                                    for dist in range(1, 3):
                                        rx, ry = (
                                            view_vx + dx * dist,
                                            view_vy + dy * dist,
                                        )
                                        if (
                                            0 <= rx < VIEW_WIDTH
                                            and 0 <= ry < VIEW_HEIGHT
                                        ):
                                            # ちらつき演出
                                            if (tick + dist) % 4 != 0:
                                                console.print(
                                                    x=rx, y=ry, string=" ", bg=ray_col
                                                )

                            # 2. 周囲に漂う光粒子
                            if tick % 2 == 0:
                                px, py = (
                                    view_vx + random.randint(-1, 1),
                                    view_vy + random.randint(-1, 1),
                                )
                                if 0 <= px < VIEW_WIDTH and 0 <= py < VIEW_HEIGHT:
                                    console.print(x=px, y=py, string="*", fg=itm.color)

                            # 飢餓連動演出: 食料のみ黄金のオーラを放つ
                            if is_starving and itm.category == CAT_FOOD:
                                itm_col = (255, 225, 60)
                            else:
                                base_itm_col = itm.color
                                lit_col, intensity = (
                                    DynamicLighting.calculate_tile_lighting(
                                        itm.x, itm.y, base_itm_col, light_sources
                                    )
                                )
                                # 光源が極端に遠い場合はシルエット化 (暗い灰色)
                                if intensity < 0.25:
                                    itm_col = (60, 65, 80)
                                else:
                                    itm_col = lit_col
                            console.print(
                                x=view_vx, y=view_vy, string=itm.char, fg=itm_col
                            )
