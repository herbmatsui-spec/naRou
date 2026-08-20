"""
Render System Module - Handles map, UI, overlays, and windows rendering
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional
import math
import tcod

from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, MAP_WIDTH, MAP_HEIGHT, VIEW_WIDTH, VIEW_HEIGHT,
    TILE_STAIRS_DOWN, COLOR_WALL_DARK, COLOR_WALL_LIT, COLOR_FLOOR_DARK, COLOR_FLOOR_LIT, COLOR_ALTAR,
    COLOR_HP_GREEN, COLOR_MP_BLUE, COLOR_GOLD_YELLOW, COLOR_PET_PINK,
)
from entity import GodInfo
from item_system import Item, CAT_WEAPON, CAT_SHIELD, CAT_ARMOR, CAT_FOOD, CAT_POTION
from systems import STATUS_BLEEDING
from ui_fx_systems import (
    MiniMapRenderer, DynamicLighting, GaugeBar, WeatherAtmosphereLayer, ScreenFilterManager, CinematicLogVisualizer
)
from render_context import RenderContext
from crafting_system import ResourceNode
from map_engine import TILE_REGISTRY
from map_renderer import MapRenderer
from item_renderer import ItemRenderer
from entity_renderer import EntityRenderer
from particle_renderer import ParticleRenderer
from uirenderer import UIRenderer

if TYPE_CHECKING:
    from game import Engine


class RenderSystem:
    """描画専用システム"""

    @staticmethod
    def get_tabbed_items(context: RenderContext) -> List[Item]:
        """タブに応じてフィルタされたアイテムリスト"""
        target_inv = context.pet_inventory if context.inventory_target == "pet" else context.inventory
        items = target_inv.items
        tab = context.inventory_tab
        if tab == 1:
            return [i for i in items if i.category in (CAT_WEAPON,)]
        elif tab == 2:
            return [i for i in items if i.category in (CAT_SHIELD, CAT_ARMOR)]
        elif tab == 3:
            return [i for i in items if i.category in (CAT_POTION, CAT_FOOD)]
        elif tab == 4:
            return [i for i in items if i.category not in (CAT_WEAPON, CAT_SHIELD, CAT_ARMOR, CAT_POTION, CAT_FOOD)]
        return items

    @classmethod
    def render_all(cls, console: tcod.console.Console, context: RenderContext) -> None:
        # Compute camera offset and lighting once for all rendering passes
        p = context.player
        s = context.survival
        ui_y = VIEW_HEIGHT
        is_starving = s.hunger <= 2000
        cam_x = max(0, min(MAP_WIDTH - VIEW_WIDTH, p.x - VIEW_WIDTH // 2))
        cam_y = max(0, min(MAP_HEIGHT - VIEW_HEIGHT, p.y - VIEW_HEIGHT // 2))
        light_sources = DynamicLighting.get_light_sources_for_engine(context)
        
        # Delegate map rendering to MapRenderer
        MapRenderer.render(console, context, cam_x, cam_y, light_sources)

        # 2. 採取ポイント表示 (状況適応型ライティング適用)
        for node in context.resource_nodes:
            if context.game_map.visible[node.x][node.y] and not node.depleted:
                vx = node.x - cam_x
                vy = node.y - cam_y
                if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                    char_map = {"herb": "%", "mushroom": "?", "ore_vein": "$"}
                    node_char = char_map.get(node.node_type, "*")
                    node_col, _ = DynamicLighting.calculate_tile_lighting(node.x, node.y, (100, 255, 180), light_sources)
                    console.print(x=vx, y=vy, string=node_char, fg=node_col)

        # 3. アイテム (光が届かない場所はシルエット/暗転表示、飢餓時は食料が黄金に輝く)
        ItemRenderer.render(console, context, cam_x, cam_y, light_sources)

        # 4. Entity (光が届かない場所の敵はシルエット化、光源が近づくと鮮明化)
        EntityRenderer.render(console, context, cam_x, cam_y, light_sources)

        # 5. パーティクル
        ParticleRenderer.render(console, context, cam_x, cam_y)

        # 5.5 動的レイヤー・環境エフェクト (Proposal 1: 霧・陽炎・空気感)
        tick = context.frame_count
        
        # --- 魔法演出レイヤー (Proposal: 動的魔方陣) ---
        if context.casting_spell:
            spell = context.casting_spell
            # 詠唱中の魔方陣描画
            # プレイヤーの足元を中心に回転する幾何学模様をシミュレート
            circle_radius = 2
            angle_offset = tick * 0.2
            for r in range(1, circle_radius + 1):
                for a in range(0, 360, 45):
                    rad = math.radians(a + angle_offset * (1 if r % 2 == 0 else -1))
                    vx = int(p.x - cam_x + math.cos(rad) * r)
                    vy = int(p.y - cam_y + math.sin(rad) * r)
                    if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                        # 詠唱が進むにつれて色を白く、輝きを強くする
                        cast_progress = getattr(spell, "progress", 0) / 100.0
                        color = (
                            int(150 + 105 * cast_progress),
                            int(100 + 155 * cast_progress),
                            int(200 + 55 * cast_progress)
                        )
                        char = "✧" if r == circle_radius else "·"
                        console.print(x=vx, y=vy, string=char, fg=color)

        WeatherAtmosphereLayer.apply_atmosphere(
            console=console,
            cam_x=cam_x,
            cam_y=cam_y,
            view_w=VIEW_WIDTH,
            view_h=VIEW_HEIGHT,
            weather=context.current_weather,
            tick=tick,
            player_speed=getattr(p, "speed", 70),
            sanity_ratio=1.0
        )

        UIRenderer.render(console, context, cam_x, cam_y)

        # Proposal 9: 究極のログ・ビジュアライザー (文字別アニメーション・衝撃波・発光)
        tick = context.frame_count
        CinematicLogVisualizer.render_cinematic_logs(
            console=console,
            msg_log=context.msg_log,
            start_x=2,
            start_y=ui_y + 7,
            count=4,
            frame_count=tick
        )

# 10. モーダル・サブウィンドウ描画
        cls._render_sub_screens(console, context)
        
        # 11. 全画面ポストプロセッシング・状態デグラデーション (Proposal 3, 7)
        is_poisoned = any(getattr(e, "name", "") == "毒" for e in getattr(p, "status_effects", []))
        glitch_dur = context.fx_manager.glitch_duration
        tick = context.frame_count
        ScreenFilterManager.apply_post_processing(
            console=console,
            hp=p.hp,
            max_hp=p.max_hp,
            is_poisoned=is_poisoned,
            is_starving=is_starving,
            glitch_duration=glitch_dur,
            frame_count=tick
        )

        # TODO: Achievement notification
        # Render achievement_notifications and achievements screen when active
        if getattr(context, "achievement_notifications", None):
            pass