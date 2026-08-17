"""
Render System Module - Handles map, UI, overlays, and windows rendering
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING
import tcod

from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, MAP_WIDTH, MAP_HEIGHT, VIEW_WIDTH, VIEW_HEIGHT,
    TILE_WALL, TILE_FLOOR, TILE_STAIRS_DOWN, TILE_STAIRS_UP, TILE_WATER,
    COLOR_WALL_DARK, COLOR_WALL_LIT, COLOR_FLOOR_DARK, COLOR_FLOOR_LIT, COLOR_ALTAR,
    COLOR_HP_GREEN, COLOR_MP_BLUE, COLOR_GOLD_YELLOW, COLOR_PET_PINK,
)
from entity import GodInfo
from item_system import Item, CAT_WEAPON, CAT_SHIELD, CAT_ARMOR, CAT_FOOD, CAT_POTION
from systems import STATUS_BLEEDING
from ui_fx_systems import (
    MiniMapRenderer, DynamicLighting, GaugeBar, HelpSystem, SkillTreeUI, JobUI,
    WeatherAtmosphereLayer, ScreenFilterManager, ItemInspectorUI, EmotionalUI,
    CinematicLogVisualizer
)

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
                        if (map_x, map_y) == engine.altar_pos:
                            lit_col, _ = DynamicLighting.calculate_tile_lighting(map_x, map_y, COLOR_ALTAR, light_sources)
                            console.print(x=vx, y=vy, string="_", fg=lit_col)
                        else:
                            t = engine.game_map.tiles[map_x][map_y]
                            base_col = COLOR_WALL_LIT if t == TILE_WALL else COLOR_FLOOR_LIT
                            
                            # Proposal 6: 世代・時間経過による環境変化 (焼け跡・苔むした壁)
                            # 座標のハッシュに基づく時間経過の自然表現
                            tile_seed = (map_x * 73856093 ^ map_y * 19349663) % 100
                            if t == TILE_WALL and tile_seed < 8:
                                # 苔の生えた古壁
                                base_col = (110, 140, 95)
                            elif t == TILE_FLOOR and tile_seed < 4:
                                # 過去の火災・焼け跡
                                base_col = (90, 75, 70)

                            lit_col, _ = DynamicLighting.calculate_tile_lighting(map_x, map_y, base_col, light_sources)
                            console.print(x=vx, y=vy, string=t, fg=lit_col)
                    elif engine.game_map.explored[map_x][map_y]:
                        if (map_x, map_y) == engine.altar_pos:
                            console.print(x=vx, y=vy, string="⛩️", fg=(80, 70, 30))
                        else:
                            t = engine.game_map.tiles[map_x][map_y]
                            console.print(x=vx, y=vy, string=t, fg=COLOR_WALL_DARK if t == TILE_WALL else COLOR_FLOOR_DARK)

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
                    base_ent_col = ent.color
                    lit_col, intensity = DynamicLighting.calculate_tile_lighting(ent.x, ent.y, base_ent_col, light_sources)
                    if not ent.is_player and not ent.is_pet and intensity < 0.3:
                        # 敵のシルエット表示（闇に潜む気配）
                        ent_col = (70, 70, 90)
                    else:
                        ent_col = lit_col
                    console.print(x=vx, y=vy, string=ent.char, fg=ent_col)

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
        console.print(x=lx+1, y=ly+5, string="?:キノコ $:鉱石", fg=(100, 255, 180))
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
            tip_text = f"💡 祭壇の上: [p]キーで神に祈りを捧げて回復・恩恵を受ける"
            console.print(x=2, y=ui_y+3, string=tip_text[:76], fg=(255, 220, 100))
        elif engine.game_map.tiles[p.x][p.y] == TILE_STAIRS_DOWN:
            tip_text = f"💡 下り階段の上: [>]キーで次の地下階層へ進む"
            console.print(x=2, y=ui_y+3, string=tip_text[:76], fg=(100, 255, 200))
        else:
            console.print(x=2, y=ui_y+3, string="🎮 [矢印]:移動 [Space]:便利行動 [l]:調査 [i]:荷物 [c]:能力 [Shift+T]:称号 [?]:ヘルプ", fg=(140, 180, 220))

        # 称号・実績獲得通知UI (Steps 70, 71)
        # TODO: Achievement notification
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

    @classmethod
    def _render_sub_screens(cls, console: tcod.console.Console, engine: Engine) -> None:
        """ヘルプ、インベントリ、会話、ステータス、各種UI画面のレンダリング"""
        # ヘルプガイド画面
        if engine.game_state == "help":
            bx, by, box_w, box_h = 4, 3, 72, 34
            console.draw_rect(x=bx, y=by, width=box_w, height=box_h, ch=0, bg=(15, 18, 28))
            tab_names = ["1.基本 & 心得", "2.キー操作", "3.画面凡例", "4.システム解説"]
            tab_header = " | ".join(f"[{t}]" if idx == engine.help_tab else f" {t} " for idx, t in enumerate(tab_names))
            console.draw_frame(x=bx, y=by, width=box_w, height=box_h, title=f" 📖 初心者冒険ガイド {tab_header} ", fg=(100, 255, 200))

            sec = HelpSystem.SECTIONS[engine.help_tab % len(HelpSystem.SECTIONS)]
            console.print(x=bx+3, y=by+2, string=f"【 {sec['title']} 】", fg=(255, 220, 100))

            for l_idx, line in enumerate(sec["lines"]):
                console.print(x=bx+3, y=by+4+l_idx*2, string=line, fg=(230, 240, 255))

            console.print(x=bx+3, y=by+box_h-2, string="[←/→/Tab]:タブ切替  [1-4]:直接選択  [Esc/?/h]:閉じる", fg=(140, 180, 220))

        # 会話ウィンドウ
        if engine.active_dialogue:
            speaker, text = engine.active_dialogue
            dw, dh = 60, 6
            dx, dy = 10, 15
            console.draw_rect(x=dx, y=dy, width=dw, height=dh, ch=0, bg=(15,20,35))
            console.draw_frame(x=dx, y=dy, width=dw, height=dh, title=f" {speaker} ", fg=(255,200,100))
            console.print(x=dx+2, y=dy+2, string=text[:dw-4], fg=(255,255,255))
            console.print(x=dx+dw-14, y=dy+dh-1, string="[Space]閉じる", fg=(180,180,180))

        elif engine.game_state == "inventory":
            is_pet = getattr(engine, "inventory_target", "player") == "pet"
            target_inv = engine.pet_inventory if is_pet else engine.inventory
            bx, by, box_w, box_h = 4, 4, 72, 29
            
            bg_col = (30, 20, 25) if is_pet else (20, 20, 30)
            fg_col = COLOR_PET_PINK if is_pet else (200, 200, 255)
            title_prefix = "妹分 シエルの所持品" if is_pet else "所持品"
            tabs = ["全て", "武器", "防具", "消費", "その他"]
            tab_str = " | ".join(f"[{t}]" if i == engine.inventory_tab else f" {t} " for i, t in enumerate(tabs))
            full_title = f" {title_prefix} {tab_str} "

            # Proposal 5: 感情同期型UIフレーム描画 (HPピンチ時の振動/危険色)
            hp_rat = engine.player.hp / max(1, engine.player.max_hp)
            tick = getattr(engine, "frame_count", 0) if hasattr(engine, "frame_count") else 0
            bx, by = EmotionalUI.draw_emotional_frame(
                console=console,
                x=bx, y=by, width=box_w, height=box_h,
                title=full_title,
                base_fg=fg_col,
                bg=bg_col,
                hp_ratio=hp_rat,
                frame_count=tick
            )

            # ペーパードール型 装備欄表示
            console.print(x=bx+2, y=by+2, string="【 装備スロット 】", fg=(255, 215, 0))
            slot_map = [
                ("頭  ", "head", "🪖"),
                ("首  ", "neck", "📿"),
                ("胴体", "body", "🥋"),
                ("右手", "main_hand", "🗡️"),
                ("左手", "off_hand", "🛡️"),
                ("指輪", "ring1", "💍"),
            ]
            for sidx, (label, sname, icon) in enumerate(slot_map):
                slot_obj = target_inv.get_slot(sname)
                eq_item = slot_obj.item if slot_obj else None
                eq_name = eq_item.display_name[:12] if eq_item else "── なし ──"
                console.print(x=bx+2, y=by+4+sidx*2, string=f"{icon} {label}:", fg=(180, 200, 255))
                console.print(x=bx+12, y=by+4+sidx*2, string=eq_name, fg=(120, 255, 150) if eq_item else (100, 100, 120))

            console.print(x=bx+27, y=by+2, string="│", fg=(60, 70, 90))
            for sep_y in range(by+3, by+box_h-3):
                console.print(x=bx+27, y=sep_y, string="│", fg=(60, 70, 90))

            # アイテム一覧
            filtered = cls.get_tabbed_items(engine)
            for idx, itm in enumerate(filtered[:18]):
                prefix = " ▶ " if idx == engine.inventory_cursor else "   "
                eq_tag = " [装]" if any(s.item is itm for s in target_inv.slots) else ""
                curse_tag = " 【呪】" if itm.cursed else ""
                line = f"{prefix}{chr(97+idx)}) {itm.display_name}{eq_tag}{curse_tag}"
                console.print(x=bx+29, y=by+3+idx, string=line[:box_w-32], fg=(255,255,180) if idx == engine.inventory_cursor else (200,200,200))

            help_txt = "重量:{}/{}s  (左右:タブ e:使 d:置 x:装備 g:渡)".format(target_inv.total_weight, target_inv.max_weight)
            console.print(x=bx+2, y=by+box_h-2, string=help_txt, fg=(130,255,130) if not is_pet else (255, 180, 200))

        # ルックモード
        elif engine.game_state == "look":
            lx, ly = engine.look_cursor.x, engine.look_cursor.y
            bx, by, box_w, box_h = 8, 10, 64, 10
            console.draw_rect(x=bx, y=by, width=box_w, height=box_h, ch=0, bg=(12, 18, 28))
            console.draw_frame(x=bx, y=by, width=box_w, height=box_h, title=" 🔍 ターゲット詳細調査 (Esc/Enter:閉じる) ", fg=(255, 255, 100))

            ent = engine.get_entity_at(lx, ly)
            items = [i for i in engine.items_on_ground if i.x == lx and i.y == ly]
            tile = engine.game_map.tiles[lx][ly] if engine.game_map.is_in_bounds(lx, ly) else "?"

            if ent:
                ent_hp_bar = GaugeBar.render(ent.hp, ent.max_hp, length=12)
                rel = "【味方/ペット】" if ent.is_pet else ("【あなた】" if ent.is_player else "【敵/中立】")
                console.print(x=bx+2, y=by+2, string=f"{rel} {ent.name}  (表示文字: '{ent.char}')", fg=(255, 220, 150))
                console.print(x=bx+2, y=by+3, string=f"生命力: [{ent_hp_bar}] {ent.hp}/{ent.max_hp}  速度: {ent.speed}", fg=COLOR_HP_GREEN)
                faction_str = getattr(ent, "faction", "不明")
                console.print(x=bx+2, y=by+4, string=f"所属組織: {faction_str}  座標: ({lx}, {ly})", fg=(180, 200, 255))
                if not ent.is_player and not ent.is_pet:
                    console.print(x=bx+2, y=by+6, string="💡 ヒント: 隣接して方向キーを押すと通常攻撃します。", fg=(255, 180, 140))
            elif items:
                itm = items[0]
                count_str = f" x{itm.count}" if itm.count > 1 else ""
                console.print(x=bx+2, y=by+2, string=f"【地面のアイテム】 {itm.display_name}{count_str}", fg=(255, 230, 100))
                console.print(x=bx+2, y=by+3, string=f"種別: {itm.category}  重量: {itm.weight}s  価値: {itm.value}G", fg=(200, 255, 200))
                if len(items) > 1:
                    console.print(x=bx+2, y=by+4, string=f"※ 他に {len(items)-1} 個のアイテムが重なっています", fg=(180, 180, 180))
                console.print(x=bx+2, y=by+6, string="💡 ヒント: このマスへ移動して [Space] または [g] で拾えます。", fg=(120, 255, 200))
                
                # Proposal 4: 超詳細なアイテム・インスペクターのクローズアップ表示
                appraisal_lvl = getattr(engine.player.attributes, "learning", 10) // 3
                ItemInspectorUI.render_inspection(console, itm, appraisal_level=appraisal_lvl, x=10, y=21)
            else:
                tname = "壁 (掘削可能: bキー)" if tile == TILE_WALL else ("水場" if tile == TILE_WATER else ("下り階段 (次の階層へ: >キー)" if tile == TILE_STAIRS_DOWN else ("上り階段 (<キー)" if tile == TILE_STAIRS_UP else "安全な床")))
                console.print(x=bx+2, y=by+2, string=f"【地形】 {tname}  (表示文字: '{tile}')", fg=(200, 220, 255))
                console.print(x=bx+2, y=by+3, string=f"座標: ({lx}, {ly})  視界内: {'可視' if engine.game_map.visible[lx][ly] else '記憶領域'}", fg=(160, 160, 180))
                
                # Proposal 8: プロシージャル・ディテール（壁画・血文字）の表示
                micro_det = engine.game_map.micro_details.get((lx, ly)) if hasattr(engine.game_map, "micro_details") else None
                if micro_det:
                    console.print(x=bx+2, y=by+5, string=f"🔍 発見: {micro_det['char']} 【{micro_det['title']}】", fg=(255, 215, 100))
                    console.print(x=bx+4, y=by+6, string=f"{micro_det['description']}", fg=(255, 230, 180))
                    console.print(x=bx+2, y=by+8, string="💡 矢印キーでカーソル移動 / Escで調査終了", fg=(140, 180, 220))
                else:
                    console.print(x=bx+2, y=by+6, string="💡 矢印キーでカーソル移動 / Escで調査終了", fg=(140, 180, 220))

        # コンテキストメニュー
        elif engine.game_state == "context":
            actions = engine.context_menu.actions
            bx, by, box_w, box_h = 16, 10, 48, len(actions) + 4
            console.draw_rect(x=bx, y=by, width=box_w, height=box_h, ch=0, bg=(20, 25, 40))
            console.draw_frame(x=bx, y=by, width=box_w, height=box_h, title=" ⚡ アクション選択 ", fg=(100, 220, 255))

            for idx, act in enumerate(actions):
                prefix = " ▶ " if idx == engine.context_menu.selected_index else "   "
                console.print(x=bx+2, y=by+2+idx, string=f"{prefix}{idx+1}. {act.label}", fg=(255, 255, 180) if idx == engine.context_menu.selected_index else (220, 220, 220))

            console.print(x=bx+2, y=by+box_h-1, string="[1-9/Enter]:実行 [Esc]:閉じる", fg=(120, 160, 200))

        # 称号画面
        elif engine.game_state == "titles":
            bx, by, box_w, box_h = 4, 3, 72, 34
            console.draw_rect(x=bx, y=by, width=box_w, height=box_h, ch=0, bg=(15, 18, 28))
            console.draw_frame(x=bx, y=by, width=box_w, height=box_h, title=" 🏷️ 称号一覧 ([T]閉じる) ", fg=(255, 215, 0))
            
            from title_system import REGISTRY
            REGISTRY.load()
            
            p = engine.player
            y = by + 2
            
            if p.equipped_title:
                title = REGISTRY.get(p.equipped_title)
                if title:
                    console.print(x=bx+2, y=y, string=f"▶ 現在表示: 《{title.epithet}》 {title.name}", fg=(255, 255, 100))
                    console.print(x=bx+2, y=y+1, string=f"   {title.description}", fg=(180, 220, 255))
                    y += 3
            else:
                console.print(x=bx+2, y=y, string="▶ 現在表示: (なし)", fg=(150, 150, 150))
                y += 2
            
            console.print(x=bx+2, y=y, string="━" * 68, fg=(60, 70, 90))
            y += 1
            
            console.print(x=bx+2, y=y, string="【 獲得済み称号 】", fg=(255, 215, 0))
            y += 1
            
            if not p.titles:
                console.print(x=bx+4, y=y, string="(称号を持っていません)", fg=(120, 120, 120))
                y += 1
            else:
                for tid in p.titles:
                    title = REGISTRY.get(tid)
                    if title:
                        is_equipped = (tid == p.equipped_title)
                        prefix = "▶ " if is_equipped else "  "
                        color = (255, 255, 100) if is_equipped else (200, 220, 255)
                        console.print(x=bx+4, y=y, string=f"{prefix}《{title.epithet}》 {title.name}", fg=color)
                        console.print(x=bx+6, y=y+1, string=f"   {title.description}", fg=(150, 180, 220))
                        y += 2
            
            y += 1
            console.print(x=bx+2, y=y, string="━" * 68, fg=(60, 70, 90))
            y += 1
            
            console.print(x=bx+2, y=y, string="【 未獲得称号 】", fg=(180, 180, 180))
            y += 1
            
            unearned = [t for t in REGISTRY.all() if t.id not in p.titles]
            for title in unearned[:8]:
                console.print(x=bx+4, y=y, string=f"  ??? 《{title.epithet}》 ???", fg=(100, 100, 120))
                console.print(x=bx+6, y=y+1, string=f"   条件: {title.condition_hint}", fg=(80, 80, 100))
                y += 2
            
            if len(unearned) > 8:
                console.print(x=bx+4, y=y, string=f"  ... 他 {len(unearned) - 8} 個", fg=(80, 80, 100))
            
            y = by + box_h - 2
            console.print(x=bx+2, y=y, string="[Enter]:装備/解除  [T/Esc]:閉じる", fg=(140, 180, 220))

        # スキルツリー画面
        elif engine.game_state == "skill_tree":
            bx, by, box_w, box_h = 4, 3, 72, 34
            console.draw_rect(x=bx, y=by, width=box_w, height=box_h, ch=0, bg=(15, 20, 30))
            console.draw_frame(x=bx, y=by, width=box_w, height=box_h, title=" 🌲 スキルツリー習得 ([S/Esc]閉じる) ", fg=(100, 255, 180))

            p = engine.player
            y = by + 2
            console.print(x=bx+2, y=y, string=f"保有スキルポイント(SP): {p.skill_points}  (累計獲得: {p.total_skill_points_earned})", fg=(255, 255, 100))
            y += 2

            for tree_id, tree in engine.skill_tree_registry.all().items():
                learned_list = p.skill_tree_progress.get(tree_id, [])
                summary = SkillTreeUI.format_tree_summary(tree_id, tree.name, len(tree.tiers), len(learned_list))
                console.print(x=bx+2, y=y, string=f"{tree.icon} {summary}", fg=(255, 220, 120))
                y += 1

                for tier in tree.tiers:
                    is_learned = tier.id in learned_list
                    can_learn = engine.skill_tree_manager.check_prerequisites(p, tier) and not is_learned
                    line_str = SkillTreeUI.format_tier_line(tier.name, tier.cost, is_learned, can_learn)
                    color = (100, 255, 100) if is_learned else ((255, 255, 200) if can_learn else (120, 120, 120))
                    console.print(x=bx+6, y=y, string=line_str, fg=color)
                    y += 1
                y += 1

            y = by + box_h - 2
            console.print(x=bx+2, y=y, string="[1-9]:スキル習得  [S/Esc]:閉じる", fg=(140, 180, 220))

        # ジョブ画面
        elif engine.game_state == "jobs":
            bx, by, box_w, box_h = 4, 3, 72, 34
            console.draw_rect(x=bx, y=by, width=box_w, height=box_h, ch=0, bg=(25, 18, 20))
            console.draw_frame(x=bx, y=by, width=box_w, height=box_h, title=" ⚔ 職業・ジョブシステム ([J/Esc]閉じる) ", fg=(255, 150, 100))

            p = engine.player
            y = by + 2
            cur_job = engine.job_registry.get(p.job)
            job_name = cur_job.name if cur_job else p.job
            summary = JobUI.format_job_summary(job_name, p.job_level, p.job_exp)
            console.print(x=bx+2, y=y, string=summary, fg=(255, 255, 120))
            y += 2

            console.print(x=bx+2, y=y, string="【 転職可能ジョブ一覧 】", fg=(255, 200, 100))
            y += 1

            avail_jobs = engine.job_manager.get_available_jobs(p)
            if not avail_jobs:
                console.print(x=bx+4, y=y, string="現在転職可能なジョブはありません（条件未達）。", fg=(150, 150, 150))
                y += 2
            else:
                for idx, j in enumerate(avail_jobs):
                    console.print(x=bx+4, y=y, string=f"[{idx+1}] {j.name} (Tier {j.tier}) - {j.description}", fg=(200, 255, 200))
                    y += 2

            console.print(x=bx+2, y=y, string="━" * 68, fg=(60, 70, 90))
            y += 1
            console.print(x=bx+2, y=y, string="【 習得済み専用スキル 】", fg=(200, 200, 255))
            y += 1
            excl_skills = p.mastered_exclusive_skills
            if not excl_skills:
                console.print(x=bx+4, y=y, string="(なし)", fg=(120, 120, 120))
            else:
                for s in excl_skills:
                    console.print(x=bx+4, y=y, string=f"★ {s}", fg=(150, 220, 255))
                    y += 1

            y = by + box_h - 2
            console.print(x=bx+2, y=y, string="[1-9]:転職実行  [J/Esc]:閉じる", fg=(140, 180, 220))

        # ギルド画面
        elif engine.game_state == "guild":
            bx, by, box_w, box_h = 4, 3, 72, 34
            console.draw_rect(x=bx, y=by, width=box_w, height=box_h, ch=0, bg=(18, 25, 30))
            console.draw_frame(x=bx, y=by, width=box_w, height=box_h, title=" 🏰 ギルド・派閥情報 ([G/Esc]閉じる) ", fg=(100, 220, 255))

            p = engine.player
            y = by + 2
            guild_info = engine.guild_manager.get_guild_info(p)
            if guild_info:
                console.print(x=bx+2, y=y, string=f"{guild_info.icon} 所属ギルド: 【{guild_info.name}】 (Rank: {p.guild_rank.upper()}  貢献度: {p.guild_contribution}pt)", fg=(255, 255, 120))
                y += 1
                console.print(x=bx+4, y=y, string=f"本部所在地: {guild_info.hall_location}  施設: {', '.join(guild_info.facilities)}", fg=(180, 220, 255))
                y += 2

                console.print(x=bx+2, y=y, string="【 受託可能なギルドクエスト 】", fg=(255, 200, 100))
                y += 1
                d_quests = engine.guild_quest_manager.get_available_quests(p, "daily")
                for q in d_quests:
                    prog = p.guild_quest_progress.get(q.id, 0)
                    status_str = "【完了可能!】" if prog >= 100 else f"進捗: {prog}%"
                    color = (100, 255, 100) if prog >= 100 else (220, 220, 220)
                    console.print(x=bx+4, y=y, string=f"● {q.name} ({status_str}) - {q.description}", fg=color)
                    y += 1
            else:
                console.print(x=bx+2, y=y, string="所属ギルド: (無所属)", fg=(180, 180, 180))
                y += 1
                console.print(x=bx+2, y=y, string="【 加入可能なギルド 】", fg=(255, 200, 100))
                y += 1
                for idx, (gid, g) in enumerate(engine.guild_registry.all().items()):
                    console.print(x=bx+4, y=y, string=f"[{idx+1}] {g.icon} {g.name} ({g.hall_location}) - {g.description}", fg=(200, 255, 200))
                    y += 2

            y += 1
            console.print(x=bx+2, y=y, string="━" * 68, fg=(60, 70, 90))
            y += 1
            console.print(x=bx+2, y=y, string="【 各勢力・派閥の影響力状況 】", fg=(255, 220, 150))
            y += 1
            for fid, f in engine.faction_war_registry.all().items():
                rep = p.faction_reputation.get(fid, 0)
                console.print(x=bx+4, y=y, string=f"・{f.name}: 影響力 {f.influence}%  (あなたの評判: {rep:+})", fg=(200, 220, 255))
                y += 1

            y = by + box_h - 2
            console.print(x=bx+2, y=y, string="[1-3]:ギルド加入  [G/Esc]:閉じる", fg=(140, 180, 220))

        # ステータス画面
        elif engine.game_state == "status":
            bx, by, box_w, box_h = 5, 3, 70, 34
            console.draw_rect(x=bx, y=by, width=box_w, height=box_h, ch=0, bg=(18,18,28))
            console.draw_frame(x=bx, y=by, width=box_w, height=box_h, title=" キャラクターシート ([C]閉じる) ", fg=(255,215,0))
            p = engine.player
            attrs = [
                ("筋力(STR)",   p.attributes.strength),
                ("耐久(END)",   p.attributes.endurance),
                ("器用(DEX)",   p.attributes.dexterity),
                ("感覚(PER)",   p.attributes.perception),
                ("習得(LEA)",   p.attributes.learning),
                ("意思(WIL)",   p.attributes.will),
                ("魔力(MAG)",   p.attributes.magic),
                ("魅力(CHA)",   p.attributes.charisma),
            ]
            for i, (aname, aval) in enumerate(attrs):
                console.print(x=bx+3, y=by+2+i, string=f"{aname}: {aval}", fg=(200,230,255))

            res = p.resistances
            console.print(x=bx+3, y=by+12, string=f"火炎耐性: {res.fire:+}", fg=(255,150,80))
            console.print(x=bx+3, y=by+13, string=f"冷気耐性: {res.cold:+}", fg=(80,180,255))
            console.print(x=bx+3, y=by+14, string=f"電撃耐性: {res.lightning:+}", fg=(255,255,80))
            console.print(x=bx+3, y=by+15, string=f"暗黒耐性: {res.darkness:+}", fg=(180,100,255))

            console.print(x=bx+25, y=by+2, string=f"レベル: {p.level}", fg=(255,215,0))
            console.print(x=bx+25, y=by+3, string=f"経験値: {p.exp}/{p.exp_next}", fg=(200,200,200))
            console.print(x=bx+25, y=by+4, string=f"HP: {p.hp}/{p.max_hp}", fg=COLOR_HP_GREEN)
            console.print(x=bx+25, y=by+5, string=f"MP: {p.mp}/{p.max_mp}", fg=COLOR_MP_BLUE)
            console.print(x=bx+25, y=by+6, string=f"速度: {p.speed}", fg=(180,255,180))

            s = engine.survival
            god_name = GodInfo.GODS[p.god_id]["name"]
            console.print(x=bx+25, y=by+8,  string=f"カルマ: {s.karma}", fg=(200,255,200) if s.karma >= 0 else (255,100,100))
            console.print(x=bx+25, y=by+9,  string=f"信仰: {god_name}", fg=(200,150,255))
            console.print(x=bx+25, y=by+10, string=f"信仰度: {p.piety}", fg=(200,150,255))
            console.print(x=bx+25, y=by+11, string=f"エーテル病: {s.ether_disease}/20000", fg=(100,255,200))
            console.print(x=bx+25, y=by+12, string=f"所持金: {s.gold}G / {s.platinum}P", fg=COLOR_GOLD_YELLOW)
            console.print(x=bx+25, y=by+13, string=f"転生回数: {getattr(p, 'reincarnation_count', 0)}周目  記憶の欠片: {len(getattr(p, 'collected_fragments', []))}個", fg=(255, 200, 100))

            if getattr(p, "cycle_modifiers", None):
                mod_names = " ".join([f"[{m.get('name', '')}]" for m in p.cycle_modifiers[:2] if isinstance(m, dict)])
                console.print(x=bx+25, y=by+14, string=f"特異点: {mod_names[:25]}", fg=(120, 220, 255))

            y_off = 0
            for sk_name, sk in list(p.skills.items())[:12]:
                console.print(x=bx+3, y=by+18+y_off, string=f"【{sk.name}】Lv{sk.level} (潜在:{sk.potential}%)", fg=(180,220,180))
                y_off += 1


        # デバッグコンソール
        elif engine.game_state == "debug":
            bx, by, box_w, box_h = 10, 20, 60, 8
            console.draw_rect(x=bx, y=by, width=box_w, height=box_h, ch=0, bg=(10,30,10))
            console.draw_frame(x=bx, y=by, width=box_w, height=box_h, title=" デバッグコンソール (Esc:閉) ", fg=(0,255,0))
            console.print(x=bx+2, y=by+2, string=f"> {engine.debug_input}_", fg=(0,255,0))
            console.print(x=bx+2, y=by+4, string="heal/levelup/gold/killall/item <名>/ether", fg=(0,180,0))

        # 実績一覧画面 (Step 72)
        elif engine.game_state == "achievements":
            bx, by, box_w, box_h = 4, 3, 72, 34
            console.draw_rect(x=bx, y=by, width=box_w, height=box_h, ch=0, bg=(18, 15, 25))
            console.draw_frame(x=bx, y=by, width=box_w, height=box_h, title=" 🏆 実績・トロフィー一覧 ([A/Esc]閉じる) ", fg=(255, 215, 0))

            from achievement_system import REGISTRY
            REGISTRY.load()
            p = engine.player
            unlocked = p.achievements
            all_achs = REGISTRY.all()

            y = by + 2
            console.print(x=bx+2, y=y, string=f"達成実績: {len(unlocked)} / {len(all_achs)}  (達成率: {int(len(unlocked)/max(1, len(all_achs))*100)}%)", fg=(255, 255, 120))
            y += 2

            console.print(x=bx+2, y=y, string="【 実績リスト 】", fg=(255, 200, 100))
            y += 1

            for aid, ach in list(all_achs.items())[:10]:
                is_done = aid in unlocked
                if ach.hidden and not is_done:
                    console.print(x=bx+4, y=y, string=f"❓ ？？？？？？ (隠し実績)", fg=(100, 100, 120))
                    console.print(x=bx+6, y=y+1, string=f"   条件: ？？？？？？", fg=(80, 80, 100))
                else:
                    icon = ach.icon if is_done else "🔒"
                    color = (100, 255, 100) if is_done else (200, 200, 200)
                    status_text = "【達成済】" if is_done else "【未達成】"
                    console.print(x=bx+4, y=y, string=f"{icon} {ach.name} {status_text}", fg=color)
                    console.print(x=bx+6, y=y+1, string=f"   {ach.description} (報酬: {ach.reward_gold}G / SP+{ach.reward_skill_points})", fg=(160, 180, 200))
                y += 2

            y = by + box_h - 2
            console.print(x=bx+2, y=y, string="[A/Esc]:閉じる", fg=(140, 180, 220))

        # 願い入力
        elif engine.game_state == "wish":
            bx, by, box_w, box_h = 10, 20, 60, 7
            console.draw_rect(x=bx, y=by, width=box_w, height=box_h, ch=0, bg=(10,10,30))
            console.draw_frame(x=bx, y=by, width=box_w, height=box_h, title=" ★願いの杖 - 何を望む？ ", fg=(100,255,255))
            console.print(x=bx+2, y=by+2, string=f"> {engine.wish_input}_", fg=(100,255,255))
            console.print(x=bx+2, y=by+4, string="sword/shield/potion/gold/skill/hp...など", fg=(80,200,200))
