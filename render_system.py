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
from map_engine import TILE_REGISTRY

if TYPE_CHECKING:
    from game import Engine


class RenderSystem:
    """描画専用システム"""

    @staticmethod
    def get_tabbed_items(engine: Engine) -> List[Item]:
        """タブに応じてフィルタされたアイテムリスト"""
        target_inv = engine.pet_inventory if getattr(engine, "inventory_target", "player") == "pet" else engine.inventory
        items = target_inv.items
        tab = engine.inventory_tab
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
    def render_all(cls, console: tcod.console.Console, engine: Engine) -> None:
        """ゲーム画面全体の描画"""
        # Load atlas textures if using pixel art
        atlas_16: Optional[tcod.image.Image] = None
        atlas_32: Optional[tcod.image.Image] = None
        if engine.game_map.use_pixel_art:
            try:
                atlas_16 = tcod.image.Image.load("assets/tiles/tileset_16x16.png")
                atlas_32 = tcod.image.Image.load("assets/tiles/tileset_32x32.png")
            except Exception:
                # Fallback to emoji mode if atlas loading fails
                engine.game_map.use_pixel_art = False

        # カメラオフセット計算 (プレイヤー追従)
        cam_x = max(0, min(MAP_WIDTH - VIEW_WIDTH, engine.player.x - VIEW_WIDTH // 2))
        cam_y = max(0, min(MAP_HEIGHT - VIEW_HEIGHT, engine.player.y - VIEW_HEIGHT // 2))

        # 1. マップ描画 (状況適応型ダイナミック・ライティング & 複数光源 + 影・環境光)
        light_sources = DynamicLighting.get_light_sources_for_engine(engine)
        p = engine.player

        for vx in range(VIEW_WIDTH):
            for vy in range(VIEW_HEIGHT):
                map_x = cam_x + vx
                map_y = cam_y + vy
                if 0 <= map_x < MAP_WIDTH and 0 <= map_y < MAP_HEIGHT:
                    if engine.game_map.visible[map_x][map_y]:
                        if engine.game_map.use_pixel_art and atlas_16 is not None:
                            # Pixel art rendering using atlas
                            tile_id = engine.game_map.tiles[map_x][map_y]
                            
                            # Get variant for autotiling/animation
                            variant = engine.game_map.tile_variants.get((map_x, map_y), 0)
                            
                            # Get animation frame if applicable
                            frame = 0
                            if (map_x, map_y) in engine.game_map.tile_animations:
                                anim = engine.game_map.tile_animations[(map_x, map_y)]
                                frame = anim.get("frame", 0)
                            
                            # Determine scale (could be made configurable)
                            scale = "16"  # Default to 16x16
                            tile_size = 16 if scale == "16" else 32
                            
                            # Get UV coordinates from atlas
                            if engine.game_map.tile_animations.get((map_x, map_y)):
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
                            _t = engine.game_map.tiles[map_x][map_y]
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
                            if (map_x, map_y) == engine.altar_pos:
                                lit_col, _ = DynamicLighting.calculate_tile_lighting(map_x, map_y, COLOR_ALTAR, light_sources)
                                console.print(x=vx, y=vy, string="_", fg=lit_col)
                            else:
                                t = engine.game_map.tiles[map_x][map_y]
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
                    elif engine.game_map.explored[map_x][map_y]:
                        if engine.game_map.use_pixel_art and atlas_16 is not None:
                            # Pixel art rendering for explored tiles
                            tile_id = engine.game_map.tiles[map_x][map_y]
                            variant = engine.game_map.tile_variants.get((map_x, map_y), 0)
                            
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
                            if (map_x, map_y) == engine.altar_pos:
                                console.print(x=vx, y=vy, string="⛩️", fg=(80, 70, 30))
                            else:
                                t = engine.game_map.tiles[map_x][map_y]
                                console.print(x=vx, y=vy, string=t, fg=COLOR_WALL_DARK if t == "TILE_WALL" else COLOR_FLOOR_DARK)

        # 2. 採取ポイント表示 (状況適応型ライティング適用)
        for node in engine.resource_nodes:
            if engine.game_map.visible[node.x][node.y] and not node.depleted:
                vx = node.x - cam_x
                vy = node.y - cam_y
                if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                    char_map = {"herb": "%", "mushroom": "?", "ore_vein": "$"}
                    node_char = char_map.get(node.node_type, "*")
                    node_col, _ = DynamicLighting.calculate_tile_lighting(node.x, node.y, (100, 255, 180), light_sources)
                    console.print(x=vx, y=vy, string=node_char, fg=node_col)

        # 3. アイテム (光が届かない場所はシルエット/暗転表示、飢餓時は食料が黄金に輝く)
        is_starving = hasattr(engine, "survival") and engine.survival.hunger <= 2000
        tick = getattr(engine, "frame_count", 0) if hasattr(engine, "frame_count") else 0
        for itm in engine.items_on_ground:
            if engine.game_map.visible[itm.x][itm.y]:
                vx = itm.x - cam_x
                vy = itm.y - cam_y
                if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                    # --- アイテム神々しい発光演出 (Proposal 5) ---
                    # レアアイテム（ここでは仮に色で判定、または特定のカテゴリ）にゴッドレイと粒子を付与
                    is_rare = itm.color in ((255, 215, 0), (200, 100, 255), (100, 255, 220))
                    if is_rare:
                        # 1. ゴッドレイ（十字方向への微かな光の筋）
                        ray_col = (int(itm.color[0]*0.5), int(itm.color[1]*0.5), int(itm.color[2]*0.5))
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            for dist in range(1, 3):
                                rx, ry = vx + dx * dist, vy + dy * dist
                                if 0 <= rx < VIEW_WIDTH and 0 <= ry < VIEW_HEIGHT:
                                    # ちらつき演出
                                    if (tick + dist) % 4 != 0:
                                        console.print(x=rx, y=ry, string=" ", bg=ray_col)
                    
                    # 2. 周囲に漂う光粒子
                    if tick % 2 == 0:
                        import random
                        px, py = vx + random.randint(-1, 1), vy + random.randint(-1, 1)
                        if 0 <= px < VIEW_WIDTH and 0 <= py < VIEW_HEIGHT:
                            console.print(x=px, y=py, string="*", fg=itm.color)

                    # 飢餓連動演出: 食料のみ黄金のオーラを放つ
                    if is_starving and itm.category == CAT_FOOD:
                        itm_col = (255, 225, 60)
                    else:
                        base_itm_col = itm.color
                        lit_col, intensity = DynamicLighting.calculate_tile_lighting(itm.x, itm.y, base_itm_col, light_sources)
                        # 光源が極端に遠い場合はシルエット化 (暗い灰色)
                        if intensity < 0.25:
                            itm_col = (60, 65, 80)
                        else:
                            itm_col = lit_col
                    console.print(x=vx, y=vy, string=itm.char, fg=itm_col)

        # 4. Entity (光が届かない場所の敵はシルエット化、光源が近づくと鮮明化)
        for ent in engine.entities:
            if engine.game_map.visible[ent.x][ent.y] and ent.hp > 0:
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

        # 5. パーティクル
        for pt in engine.particles:
            vx = int(pt.x) - cam_x
            vy = int(pt.y) - cam_y
            if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                console.print(x=vx, y=vy, string=pt.char, fg=pt.color)

        # 5.5 動的レイヤー・環境エフェクト (Proposal 1: 霧・陽炎・空気感)
        tick = getattr(engine, "frame_count", 0) if hasattr(engine, "frame_count") else 0
        
        # --- 魔法演出レイヤー (Proposal: 動的魔方陣) ---
        if hasattr(engine, "casting_spell") and engine.casting_spell:
            spell = engine.casting_spell
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
            weather=getattr(engine, "current_weather", "fog"),
            tick=tick,
            player_speed=getattr(p, "speed", 70),
            sanity_ratio=1.0
        )

        # 6. ポップアップテキスト
        for ft in engine.floating_texts:
            vx = int(ft.x) - cam_x
            vy = int(ft.y) - cam_y
            if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                console.print(x=vx, y=vy, string=ft.text, fg=ft.color)

        # 7. ルックモードカーソル
        if engine.game_state == "look":
            vx = engine.look_cursor.x - cam_x
            vy = engine.look_cursor.y - cam_y
            if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                console.print(x=vx, y=vy, string="🎯", fg=(255, 255, 0))

        # 8. ミニマップ (画面右上)
        MiniMapRenderer.render(
            console=console, start_x=SCREEN_WIDTH - 21, start_y=1,
            game_map=engine.game_map, player=engine.player, pet=engine.pet, entities=engine.entities
        )

        # 8.5 マップ凡例ガイド
        lx, ly = SCREEN_WIDTH - 21, 13
        console.draw_rect(x=lx, y=ly, width=20, height=8, ch=0, bg=(12, 16, 24))
        console.draw_frame(x=lx, y=ly, width=20, height=8, title=" [凡例] ", fg=(100, 180, 255))
        console.print(x=lx+1, y=ly+1, string="@:自分  p:仲間", fg=(200, 240, 255))
        console.print(x=lx+1, y=ly+2, string="#:壁    .:床", fg=(180, 180, 180))
        console.print(x=lx+1, y=ly+3, string=">:階段下 <:階段上", fg=(255, 220, 100))
        console.print(x=lx+1, y=ly+4, string="_:祭壇  %:薬草", fg=(255, 215, 0))
        console.print(x=lx+1, y=lx+5, string="?:キノコ $:鉱石", fg=(100, 255, 180))
        console.print(x=lx+1, y=ly+6, string="x:敵(赤) !:薬品", fg=(255, 120, 120))

        # 9. 下部UI
        ui_y = VIEW_HEIGHT
        console.draw_rect(x=0, y=ui_y, width=SCREEN_WIDTH, height=SCREEN_HEIGHT-ui_y, ch=0, bg=(10,12,16))
        console.print(x=1, y=ui_y, string="━"*78, fg=(60,70,90))

        p = engine.player
        s = engine.survival
        god_name = GodInfo.GODS[p.god_id]["name"].split(" ")[0]
        hunger_str = "満腹" if s.hunger > 7000 else ("普通" if s.hunger > 2000 else "★飢餓")
        bleed_tag = " [出血]" if any(e.name == STATUS_BLEEDING for e in getattr(p, "status_effects", [])) else ""

        # 行1: プレイヤー情報 & HP/MPバー
        hp_bar = GaugeBar.render(p.hp, p.max_hp, length=8)
        mp_bar = GaugeBar.render(p.mp, p.max_mp, length=6)
        console.print(x=2,  y=ui_y+1, string=f"{p.name} [{hunger_str}{bleed_tag}]", fg=(255,255,160))
        console.print(x=22, y=ui_y+1, string=f"HP:[{hp_bar}] {p.hp}/{p.max_hp}", fg=COLOR_HP_GREEN)
        console.print(x=46, y=ui_y+1, string=f"MP:[{mp_bar}] {p.mp}/{p.max_mp}", fg=COLOR_MP_BLUE)
        console.print(x=66, y=ui_y+1, string=f"Lv.{p.level} {s.gold}G", fg=COLOR_GOLD_YELLOW)

        # 行2: ペット情報 & 環境情報
        pet_hp_bar = GaugeBar.render(engine.pet.hp, engine.pet.max_hp, length=6) if engine.pet.hp > 0 else " DEAD "
        pet_str = f"HP:[{pet_hp_bar}] {engine.pet.hp}/{engine.pet.max_hp}" if engine.pet.hp > 0 else "死亡"
        console.print(x=2,  y=ui_y+2, string=f"【仲間】シエル {pet_str}", fg=COLOR_PET_PINK)
        console.print(x=34, y=ui_y+2, string=f"信仰:{god_name}({p.piety})", fg=(200,150,255))
        console.print(x=54, y=ui_y+2, string=f"{engine.time_system.to_string()} B{engine.dungeon_level}F", fg=(170,170,170))

        # 行3: リアルタイム・ツールチップ
        ground_itms = [i for i in engine.items_on_ground if i.x == p.x and i.y == p.y]
        if ground_itms:
            tip_text = f"💡 足元: [{ground_itms[0].display_name}] がある ([Space]または[g]で拾う)"
            console.print(x=2, y=ui_y+3, string=tip_text[:76], fg=(255, 255, 120))
        elif (p.x, p.y) == engine.altar_pos:
            tip_text = "💡 祭壇の上: [p]キーで神に祈りを捧げて回復・恩恵を受ける"
            console.print(x=2, y=ui_y+3, string=tip_text[:76], fg=(255, 220, 100))
        elif engine.game_map.tiles[p.x][p.y] == TILE_STAIRS_DOWN:
            tip_text = "💡 下り階段の上: [>]キーで次の地下階層へ進む"
            console.print(x=2, y=ui_y+3, string=tip_text[:76], fg=(100, 255, 200))
        else:
            console.print(x=2, y=ui_y+3, string="🎮 [矢印]:移動 [Space]:便利行動 [l]:調査 [i]:荷物 [c]:能力 [Shift+T]:称号 [?]:ヘルプ", fg=(140, 180, 220))

        # 称号・実績獲得通知UI (Steps 70, 71)
        # TODO: Achievement notification
        # achievements
        if hasattr(engine.player, 'achievement_notifications') and engine.player.achievement_notifications:
            for i, notif in enumerate(engine.player.achievement_notifications[:3]):
                console.print(x=2, y=ui_y+5+i, string=f"{notif}", fg=(255, 220, 100))

        # フローティング重要通知表示 (Step 2.2)
        if hasattr(engine, 'notification_manager'):
            latest_notif = engine.notification_manager.get_latest()
            if latest_notif:
                notif_box_w = min(70, len(latest_notif.message) + len(latest_notif.title) + 6)
                nbx = max(2, (SCREEN_WIDTH - notif_box_w) // 2)
                nby = 2
                console.draw_rect(x=nbx, y=nby, width=notif_box_w, height=3, ch=0, bg=(20, 25, 40))
                console.draw_frame(x=nbx, y=nby, width=notif_box_w, height=3, title=f" {latest_notif.title} ", fg=latest_notif.color)
                console.print(x=nbx+2, y=nby+1, string=latest_notif.message[:notif_box_w-4], fg=(255, 255, 255))

        # Proposal 9: 究極のログ・ビジュアライザー (文字別アニメーション・衝撃波・発光)
        tick = getattr(engine, "frame_count", 0) if hasattr(engine, "frame_count") else 0
        CinematicLogVisualizer.render_cinematic_logs(
            console=console,
            msg_log=engine.msg_log,
            start_x=2,
            start_y=ui_y + 7,
            count=4,
            frame_count=tick
        )

        # 10. モーダル・サブウィンドウ描画
        cls._render_sub_screens(console, engine)

        # 11. 全画面ポストプロセッシング・状態デグラデーション (Proposal 3, 7)
        is_poisoned = any(getattr(e, "name", "") == "毒" for e in getattr(p, "status_effects", []))
        glitch_dur = getattr(engine.fx_manager, "glitch_duration", 0) if hasattr(engine, "fx_manager") else 0
        tick = getattr(engine, "frame_count", 0) if hasattr(engine, "frame_count") else 0
        ScreenFilterManager.apply_post_processing(
            console=console,
            hp=p.hp,
            max_hp=p.max_hp,
            is_poisoned=is_poisoned,
            is_starving=is_starving,
            glitch_duration=glitch_dur,
            frame_count=tick
        )