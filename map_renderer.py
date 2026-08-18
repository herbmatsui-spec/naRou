"""
Map Renderer Module - Handles map tile rendering with pixel art and fallback
"""
from __future__ import annotations
from typing import Optional
import tcod

from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, MAP_WIDTH, MAP_HEIGHT, VIEW_WIDTH, VIEW_HEIGHT,
    TILE_STAIRS_DOWN, COLOR_WALL_DARK, COLOR_WALL_LIT, COLOR_FLOOR_DARK, COLOR_FLOOR_LIT, COLOR_ALTAR,
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


class MapRenderer:
    """マップ描画専用クラス"""
    # Cached atlases to avoid reloading each frame
    _atlas_16: Optional[tcod.image.Image] = None
    _atlas_32: Optional[tcod.image.Image] = None

    @classmethod
    def _load_atlases(cls) -> None:
        """アトラス画像をロードし、クラス変数にキャッシュする"""
        if cls._atlas_16 is None or cls._atlas_32 is None:
            try:
                cls._atlas_16 = tcod.image.Image.load("assets/tiles/tileset_16x16.png")
                cls._atlas_32 = tcod.image.Image.load("assets/tiles/tileset_32x32.png")
            except Exception:
                # ロードに失敗した場合はピクセルアートモードを無効にする
                # 注意: これはゲームマップの use_pixel_art フラグに変更を加えるわけではない
                # ここでフラグを変更すると副作用があるため、呼び出し側で判断する
                pass

    @classmethod
    def render(cls, console: tcod.console.Console, context: RenderContext, 
               cam_x: Optional[int] = None, cam_y: Optional[int] = None, 
               light_sources: Optional[List] = None) -> None:
        """マップ描画のメインエントリポイント"""
        # ピクセルアートが有効かつアトラスがロード可能な場合のみアトラスを使用
        use_pixel_art = context.game_map.use_pixel_art
        atlas_16: Optional[tcod.image.Image] = None
        atlas_32: Optional[tcod.image.Image] = None
        if use_pixel_art:
            cls._load_atlases()
            atlas_16 = cls._atlas_16
            atlas_32 = cls._atlas_32
            # アトラスロードに失敗した場合はフォールバック
            if atlas_16 is None or atlas_32 is None:
                use_pixel_art = False

        # カメラオフセット計算 (プレイヤー追従) - 呼び出し側から提供されない場合は内部で計算
        if cam_x is None or cam_y is None:
            cam_x = max(0, min(MAP_WIDTH - VIEW_WIDTH, context.player.x - VIEW_WIDTH // 2))
            cam_y = max(0, min(MAP_HEIGHT - VIEW_HEIGHT, context.player.y - VIEW_HEIGHT // 2))

        # 動的ライティング用光源取得 - 呼び出し側から提供されない場合は内部で計算
        if light_sources is None:
            light_sources = DynamicLighting.get_light_sources_for_engine(context)

        for vx in range(VIEW_WIDTH):
            for vy in range(VIEW_HEIGHT):
                map_x = cam_x + vx
                map_y = cam_y + vy
                if 0 <= map_x < MAP_WIDTH and 0 <= map_y < MAP_HEIGHT:
                    if context.game_map.visible[map_x][map_y]:
                        if use_pixel_art and atlas_16 is not None and atlas_32 is not None:
                            # Pixel art rendering using atlas
                            tile_id = context.game_map.tiles[map_x][map_y]
                            
                            # Get variant for autotiling/animation
                            variant = context.game_map.tile_variants.get((map_x, map_y), 0)
                            
                            # Get animation frame if applicable
                            frame = 0
                            if (map_x, map_y) in context.game_map.tile_animations:
                                anim = context.game_map.tile_animations[(map_x, map_y)]
                                frame = anim.get("frame", 0)
                            
                            # Determine scale (could be made configurable)
                            scale = "16"  # Default to 16x16
                            tile_size = 16 if scale == "16" else 32
                            
                            # Get UV coordinates from atlas
                            if context.game_map.tile_animations.get((map_x, map_y)):
                                # Animated tile
                                ux, uy, uw, uh = TILE_REGISTRY.get_animation_frame(tile_id, frame, scale)
                            else:
                                # Static tile
                                ux, uy, uw, uh = TILE_REGISTRY.get_uv(tile_id, variant, scale)
                            
                            # Blit from atlas
                            atlas_source = atlas_16 if scale == "16" else atlas_32
                            atlas_source.blit(
                                console,
                                vx * tile_size, vy * tile_size,  # destination x, y
                                ux, uy, uw, uh  # source x, y, width, height
                            )
                            
                            # ピクセルアート描画時も照明色を算出してから照明オーバーレイを適用
                            _t = context.game_map.tiles[map_x][map_y]
                            _base = COLOR_WALL_LIT if _t == "TILE_WALL" else COLOR_FLOOR_LIT
                            lit_col, _ = DynamicLighting.calculate_tile_lighting(map_x, map_y, _base, light_sources)

                            # Apply lighting as a simple brightness adjustment
                            # Calculate average brightness of light color
                            brightness = (lit_col[0] + lit_col[1] + lit_col[2]) / (3 * 255.0)
                            # Apply as a multiply blend (darken if dark, brighten if bright)
                            # For simplicity, we'll just draw a tinted rectangle with adjusted alpha
                            # This gives a basic lighting effect
                            if brightness > 0.5:  # Bright light - additively blend
                                blend_factor = min(1.0, brightness * 0.5)
                                r = min(255, int(255 * blend_factor + lit_col[0] * (1 - blend_factor)))
                                g = min(255, int(255 * blend_factor + lit_col[1] * (1 - blend_factor)))
                                b = min(255, int(255 * blend_factor + lit_col[2] * (1 - blend_factor)))
                                console.draw_rect(
                                    vx * tile_size, vy * tile_size, tile_size, tile_size,
                                    ch=0,
                                    fg=(r, g, b)
                                )
                            else:  # Dim light or dark - just show the tile as-is (already blended in atlas if needed)
                                pass
                            
                        else:
                            # Fallback to emoji/character rendering
                            if (map_x, map_y) == context.altar_pos:
                                lit_col, _ = DynamicLighting.calculate_tile_lighting(map_x, map_y, COLOR_ALTAR, light_sources)
                                console.print(x=vx, y=vy, string="_", fg=lit_col)
                            else:
                                t = context.game_map.tiles[map_x][map_y]
                                base_col = COLOR_WALL_LIT if t == "TILE_WALL" else COLOR_FLOOR_LIT
                                
                                # Proposal 6: 世代・時間経過による環境変化 (焼け跡・苔むした壁)
                                # 座標のハッシュに基づく時間経過の自然表現
                                tile_seed = (map_x * 73856093 ^ map_y * 19349663) % 100
                                if t == "TILE_WALL" and tile_seed < 8:
                                    # 苔の生えた古壁
                                    base_col = (110, 140, 95)
                                elif t == "TILE_FLOOR" and tile_seed < 4:
                                    # 過去の火災・焼け跡
                                    base_col = (90, 75, 70)
                                
                                lit_col, _ = DynamicLighting.calculate_tile_lighting(map_x, map_y, base_col, light_sources)
                                console.print(x=vx, y=vy, string=t, fg=lit_col)
                    elif context.game_map.explored[map_x][map_y]:
                        if use_pixel_art and atlas_16 is not None and atlas_32 is not None:
                            # Pixel art rendering for explored tiles
                            tile_id = context.game_map.tiles[map_x][map_y]
                            variant = context.game_map.tile_variants.get((map_x, map_y), 0)
                            
                            # Determine scale
                            scale = "16"
                            tile_size = 16 if scale == "16" else 32
                            
                            # Get UV coordinates from atlas
                            ux, uy, uw, uh = TILE_REGISTRY.get_uv(tile_id, variant, scale)
                            
                            # Blit explored tile from atlas
                            atlas_source = atlas_16 if scale == "16" else atlas_32
                            atlas_source.blit(
                                console,
                                vx * tile_size, vy * tile_size,  # destination x, y
                                ux, uy, uw, uh  # source x, y, width, height
                            )
                            
                            # Apply explored tile darkness (dimmed version)
                            console.draw_rect(
                                vx * tile_size, vy * tile_size, tile_size, tile_size,
                                ch=0,
                                fg=(40, 40, 40)  # Dark gray for explored tiles
                            )
                            
                        else:
                            # Fallback to emoji/character rendering
                            if (map_x, map_y) == context.altar_pos:
                                console.print(x=vx, y=vy, string="⛩️", fg=(80, 70, 30))
                            else:
                                t = context.game_map.tiles[map_x][map_y]
                                console.print(x=vx, y=vy, string=t, fg=COLOR_WALL_DARK if t == "TILE_WALL" else COLOR_FLOOR_DARK)