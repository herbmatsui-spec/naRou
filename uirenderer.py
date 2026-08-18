"""
UI Renderer Module - Handles inline UI drawing: popup text, look cursor, map legend, bottom UI
"""
from __future__ import annotations
from typing import List, Optional
import tcod

from constants import (
    VIEW_WIDTH, VIEW_HEIGHT,
    COLOR_WALL_DARK, COLOR_WALL_LIT, COLOR_FLOOR_DARK, COLOR_FLOOR_LIT, COLOR_ALTAR,
    COLOR_HP_GREEN, COLOR_MP_BLUE, COLOR_GOLD_YELLOW, COLOR_PET_PINK,
    TILE_STAIRS_DOWN,
)
from entity import GodInfo
from item_system import Item
from systems import STATUS_BLEEDING
from render_context import RenderContext
from crafting_system import ResourceNode
from map_engine import TILE_REGISTRY


class UIRenderer:
    """UI描画専用クラス (インラインUI描画担当)"""

    @classmethod
    def render(cls, console: tcod.console.Console, context: RenderContext,
               cam_x: int, cam_y: int) -> None:
        """UI描画のメインエントリポイント"""
        # 6. ポップアップテキスト
        for ft in context.floating_texts:
            vx = int(ft.x) - cam_x
            vy = int(ft.y) - cam_y
            if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                console.print(x=vx, y=vy, string=ft.text, fg=ft.color)

        # 7. ルックモードカーソル
        if context.game_state == "look":
            vx = context.look_cursor.x - cam_x
            vy = context.look_cursor.y - cam_y
            if 0 <= vx < VIEW_WIDTH and 0 <= vy < VIEW_HEIGHT:
                console.print(x=vx, y=vy, string="🎯", fg=(255, 255, 0))

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

        p = context.player
        s = context.survival
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
        pet_hp_bar = GaugeBar.render(context.pet.hp, context.pet.max_hp, length=6) if context.pet.hp > 0 else " DEAD "
        pet_str = f"HP:[{pet_hp_bar}] {context.pet.hp}/{context.pet.max_hp}" if context.pet.hp > 0 else "死亡"
        console.print(x=2,  y=ui_y+2, string=f"【仲間】シエル {pet_str}", fg=COLOR_PET_PINK)
        console.print(x=34, y=ui_y+2, string=f"信仰:{god_name}({p.piety})", fg=(200,150,255))
        console.print(x=54, y=ui_y+2, string=f"{context.time_system.to_string()} B{context.dungeon_level}F", fg=(170,170,170))

        # 行3: リアルタイム・ツールチップ
        ground_itms = [i for i in context.items_on_ground if i.x == p.x and i.y == p.y]
        if ground_itms:
            tip_text = f"💡 足元: [{ground_itms[0].display_name}] がある ([Space]または[g]で拾う)"
            console.print(x=2, y=ui_y+3, string=tip_text[:76], fg=(255, 255, 120))
        elif (p.x, p.y) == context.altar_pos:
            tip_text = "💡 祭壇の上: [p]キーで神に祈りを捧げて回復・恩恵を受ける"
            console.print(x=2, y=ui_y+3, string=tip_text[:76], fg=(255, 220, 100))
        elif context.game_map.tiles[p.x][p.y] == TILE_STAIRS_DOWN:
            tip_text = "💡 下り階段の上: [>]キーで次の地下階層へ進む"
            console.print(x=2, y=ui_y+3, string=tip_text[:76], fg=(100, 255, 200))
        else:
            console.print(x=2, y=ui_y+3, string="🎮 [矢印]:移動 [Space]:便利行動 [l]:調査 [i]:荷物 [c]:能力 [Shift+T]:称号 [?]:ヘルプ", fg=(140, 180, 220))

        # 称号・実績獲得通知UI (Steps 70, 71)
        # TODO: Achievement notification
        # achievements
        if hasattr(context.player, 'achievement_notifications') and context.player.achievement_notifications:
            for i, notif in enumerate(context.player.achievement_notifications[:3]):
                console.print(x=2, y=ui_y+5+i, string=f"{notif}", fg=(255, 220, 100))

        # フローティング重要通知表示 (Step 2.2)
        latest_notif = context.notification_manager.get_latest()
        if latest_notif:
            notif_box_w = min(70, len(latest_notif.message) + len(latest_notif.title) + 6)
            nbx = max(2, (SCREEN_WIDTH - notif_box_w) // 2)
            nby = 2
            console.draw_rect(x=nbx, y=nby, width=notif_box_w, height=3, ch=0, bg=(20, 25, 40))
            console.draw_frame(x=nbx, y=nby, width=notif_box_w, height=3, title=f" {latest_notif.title} ", fg=latest_notif.color)
            console.print(x=nbx+2, y=nby+1, string=latest_notif.message[:notif_box_w-4], fg=(255, 255, 255))