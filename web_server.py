"""
Elona Roguelike - Web Dual-Engine Server (Masterpiece Edition v2.0)
Provides HTTP server and REST/JSON API for HTML5 Canvas interactive rendering & WebAudio engine.
"""

from __future__ import annotations
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any, TYPE_CHECKING
import os

if TYPE_CHECKING:
    from game import Engine

_ENGINE_INSTANCE: Optional["Engine"] = None

class GameHTTPRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_GET(self):
        global _ENGINE_INSTANCE
        if self.path == "/api/state":
            if _ENGINE_INSTANCE is None:
                self._set_headers()
                self.wfile.write(json.dumps({"error": "Engine not initialized"}).encode('utf-8'))
                return

            state = self._serialize_engine_state(_ENGINE_INSTANCE)
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(state, ensure_ascii=False).encode('utf-8'))
        elif self.path == "/" or self.path.endswith(".html") or self.path == "/index.html":
            html_path = os.path.join(os.path.dirname(__file__), "web_game_client.html")
            if os.path.exists(html_path):
                with open(html_path, "rb") as f:
                    content = f.read()
                self._set_headers("text/html; charset=utf-8")
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global _ENGINE_INSTANCE
        if self.path == "/api/action":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}

            action = data.get("action")
            result_msg = "OK"

            if _ENGINE_INSTANCE and action:
                result_msg = self._handle_web_action(_ENGINE_INSTANCE, action, data)

            state = self._serialize_engine_state(_ENGINE_INSTANCE) if _ENGINE_INSTANCE else {}
            state["action_result"] = result_msg

            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(state, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def _serialize_engine_state(self, engine: "Engine") -> Dict[str, Any]:
        """Canvas 2DおよびWebAudio向けに完全なゲーム状態をJSONシリアライズ"""
        p = engine.player
        pet = engine.pet
        s = engine.survival

        # Webビューポート（プレイヤー追従カメラ）
        view_w = 40
        view_h = 24
        cam_x = max(0, min(engine.game_map.width - view_w, p.x - view_w // 2))
        cam_y = max(0, min(engine.game_map.height - view_h, p.y - view_h // 2))

        # マップデータ & タイル詳細情報
        visible_tiles = []
        raw_tiles = []
        light_map = []

        for vy in range(view_h):
            row = []
            raw_row = []
            light_row = []
            for vx in range(view_w):
                mx = cam_x + vx
                my = cam_y + vy
                if 0 <= mx < engine.game_map.width and 0 <= my < engine.game_map.height:
                    is_vis = engine.game_map.visible[mx][my]
                    is_exp = engine.game_map.explored[mx][my]
                    raw_tile = engine.game_map.tiles[mx][my]
                    raw_row.append(raw_tile if (is_vis or is_exp) else " ")

                    if is_vis:
                        if (mx, my) == getattr(engine, "altar_pos", (-1, -1)):
                            row.append("⛩️")
                        else:
                            row.append(raw_tile)
                        # プレイヤー周辺ライティング強度
                        dist_sq = (mx - p.x) ** 2 + (my - p.y) ** 2
                        intensity = max(0.15, 1.0 - (dist_sq / 64.0))
                        light_row.append(round(intensity, 2))
                    elif is_exp:
                        row.append(raw_tile)
                        light_row.append(0.0) # 探索済みだが視界外 (Fog of war)
                    else:
                        row.append(" ")
                        light_row.append(-1.0) # 未探索
                else:
                    row.append(" ")
                    raw_row.append(" ")
                    light_row.append(-1.0)
            visible_tiles.append(row)
            raw_tiles.append(raw_row)
            light_map.append(light_row)

        entities_data = []
        for e in engine.entities:
            if engine.game_map.visible[e.x][e.y] and e.hp > 0:
                vx = e.x - cam_x
                vy = e.y - cam_y
                if 0 <= vx < view_w and 0 <= vy < view_h:
                    entities_data.append({
                        "name": e.name,
                        "char": e.char,
                        "x": vx,
                        "y": vy,
                        "world_x": e.x,
                        "world_y": e.y,
                        "hp": e.hp,
                        "max_hp": e.max_hp,
                        "is_player": e.is_player,
                        "is_pet": getattr(e, "is_pet", False),
                        "faction": getattr(e, "faction", "neutral"),
                        "status_effects": [st.name for st in getattr(e, "status_effects", [])]
                    })

        items_data = []
        for itm in engine.items_on_ground:
            if engine.game_map.visible[itm.x][itm.y]:
                vx = itm.x - cam_x
                vy = itm.y - cam_y
                if 0 <= vx < view_w and 0 <= vy < view_h:
                    items_data.append({
                        "name": itm.display_name,
                        "raw_name": itm.name,
                        "char": itm.char,
                        "category": itm.category,
                        "quality": itm.quality,
                        "x": vx,
                        "y": vy
                    })

        # 浮遊テキスト
        floating_data = []
        if hasattr(engine, "floating_texts"):
            for ft in engine.floating_texts:
                vx = ft.x - cam_x
                vy = ft.y - cam_y
                if 0 <= vx < view_w and 0 <= vy < view_h:
                    floating_data.append({
                        "text": ft.text,
                        "x": vx,
                        "y": vy,
                        "color": list(ft.color),
                        "life": getattr(ft, "life", 10)
                    })

        # パーティクル
        particle_data = []
        if hasattr(engine, "particles"):
            for pt in engine.particles:
                vx = pt.x - cam_x
                vy = pt.y - cam_y
                if 0 <= vx < view_w and 0 <= vy < view_h:
                    particle_data.append({
                        "char": pt.char,
                        "x": vx,
                        "y": vy,
                        "color": list(pt.color),
                        "life": getattr(pt, "life", 5)
                    })

        inv_items = [
            {
                "id": itm.item_id,
                "name": itm.display_name,
                "raw_name": itm.name,
                "category": itm.category,
                "char": itm.char,
                "quality": itm.quality,
                "weight": itm.weight,
                "value": itm.value,
                "count": itm.count,
                "cursed": itm.cursed,
                "equipped": any(slot.item is itm for slot in engine.inventory.slots)
            }
            for itm in engine.inventory.items
        ]

        pet_inv_items = [
            {
                "id": itm.item_id,
                "name": itm.display_name,
                "category": itm.category,
                "char": itm.char,
                "weight": itm.weight,
                "count": itm.count,
                "equipped": any(slot.item is itm for slot in engine.pet_inventory.slots)
            }
            for itm in engine.pet_inventory.items
        ] if hasattr(engine, "pet_inventory") else []

        logs = [
            {
                "text": entry.text if hasattr(entry, 'text') else str(entry),
                "level": getattr(entry, 'level', 'INFO'),
                "color": getattr(entry, 'color', (230, 230, 230))
            }
            for entry in engine.msg_log.history[-12:]
        ]

        quests = [
            {
                "title": q.title,
                "target": q.target_monster,
                "current": q.current_count,
                "needed": q.target_count,
                "reward_gold": q.reward_gold,
                "completed": q.completed
            }
            for q in getattr(engine, "quests", [])
        ]

        popup_tutorial = getattr(p, "pending_tutorial_popup", None)
        if popup_tutorial:
            p.pending_tutorial_popup = None

        screen_shake = engine.screen_shake.is_active if hasattr(engine, "screen_shake") else False

        # プレイヤー属性
        attrs = {
            "str": p.attributes.strength,
            "end": p.attributes.endurance,
            "dex": p.attributes.dexterity,
            "per": p.attributes.perception,
            "ler": p.attributes.learning,
            "wil": p.attributes.will,
            "mag": p.attributes.magic,
            "cha": p.attributes.charisma,
        }

        # 光源リスト (Canvas Dynamic Lighting用)
        light_sources = [
            {"x": p.x - cam_x, "y": p.y - cam_y, "radius": 7.5, "color": [255, 220, 140], "intensity": 1.0}
        ]
        if hasattr(engine, "altar_pos"):
            ax, ay = engine.altar_pos
            if engine.game_map.visible[ax][ay]:
                light_sources.append({
                    "x": ax - cam_x, "y": ay - cam_y, "radius": 4.0, "color": [100, 200, 255], "intensity": 0.8
                })

        return {
            "player": {
                "name": p.name,
                "level": getattr(p, "level", 1),
                "exp": getattr(p, "exp", 0),
                "hp": p.hp,
                "max_hp": p.max_hp,
                "mp": p.mp,
                "max_mp": p.max_mp,
                "gold": s.gold,
                "platinum": s.platinum,
                "hunger": s.hunger,
                "karma": s.karma,
                "turns": engine.turns,
                "job": getattr(p, "job", "冒険者"),
                "job_level": getattr(p, "job_level", 1),
                "god": getattr(p, "god_id", "jure"),
                "piety": getattr(p, "piety", 0),
                "attributes": attrs,
                "skill_points": getattr(p, "skill_points", 0)
            },
            "pet": {
                "name": pet.name if pet else "",
                "hp": pet.hp if pet else 0,
                "max_hp": pet.max_hp if pet else 0,
                "tactic": getattr(pet, "tactic", "balanced") if pet else "balanced"
            },
            "map": visible_tiles,
            "raw_tiles": raw_tiles,
            "light_map": light_map,
            "light_sources": light_sources,
            "camera": {"cam_x": cam_x, "cam_y": cam_y, "view_w": view_w, "view_h": view_h},
            "map_size": {"width": engine.game_map.width, "height": engine.game_map.height},
            "entities": entities_data,
            "items": items_data,
            "floating_texts": floating_data,
            "particles": particle_data,
            "inventory": inv_items,
            "pet_inventory": pet_inv_items,
            "quests": quests,
            "logs": logs,
            "dungeon_level": engine.dungeon_level,
            "game_state": getattr(engine, "game_state", "play"),
            "tutorial_popup": popup_tutorial,
            "floating_notification": {
                "title": latest_notif.title,
                "message": latest_notif.message,
                "category": latest_notif.category,
                "color": list(latest_notif.color)
            } if (latest_notif := getattr(engine, "notification_manager", None) and engine.notification_manager.get_latest()) else None,
            "screen_shake": screen_shake
        }

    def _handle_web_action(self, engine: "Engine", action: str, data: Dict[str, Any]) -> str:
        """Webからのキー入力・アクションディスパッチ"""
        dx, dy = 0, 0
        if action == "up": dy = -1
        elif action == "down": dy = 1
        elif action == "left": dx = -1
        elif action == "right": dx = 1
        elif action == "up_left": dx, dy = -1, -1
        elif action == "up_right": dx, dy = 1, -1
        elif action == "down_left": dx, dy = -1, 1
        elif action == "down_right": dx, dy = 1, 1
        elif action == "wait":
            engine.player.energy -= 100
            engine.advance_world()
            return "1ターン待機しました"
        elif action == "pickup":
            px, py = engine.player.x, engine.player.y
            items = [itm for itm in engine.items_on_ground if itm.x == px and itm.y == py]
            if items:
                itm = items[0]
                ok, msg = engine.inventory.add_item(itm)
                if ok:
                    engine.items_on_ground.remove(itm)
                    engine.log(msg, (100, 255, 100), level="SUCCESS")
                    engine.advance_world()
                    return msg
            return "足元にアイテムはありません"
        elif action == "pray":
            engine.log(f"神【{getattr(engine.player, 'god_id', '神')}】に祈りを捧げた…… 神の恩寵が全身を満たす！", (255, 215, 0), level="SUCCESS")
            engine.player.hp = engine.player.max_hp
            engine.player.mp = engine.player.max_mp
            engine.advance_world()
            return "神に祈りを捧げました"
        elif action == "cast_fireball":
            if engine.player.mp >= 12:
                engine.player.mp -= 12
                engine.log("💥 火炎球（ファイアボール）の呪文を放った！", (255, 120, 50), level="SUCCESS")
                from ui_fx_systems import Particle
                for e in list(engine.entities):
                    if e.faction == "monster" and e.hp > 0:
                        dist = abs(e.x - engine.player.x) + abs(e.y - engine.player.y)
                        if dist <= 5:
                            e.hp -= 25
                            engine.particles.append(Particle("💥", e.x, e.y, (255, 100, 50), life=4))
                            if e.hp <= 0:
                                engine._on_kill(e)
                engine.advance_world()
                return "ファイアボールを詠唱しました"
            return "MPが足りません"
        elif action == "use_potion":
            potions = [i for i in engine.inventory.items if i.category == "potion"]
            if potions:
                pot = potions[0]
                heal = getattr(pot, "heal_amount", 40)
                engine.player.hp = min(engine.player.max_hp, engine.player.hp + heal)
                engine.inventory.remove_item(pot, 1)
                engine.log(f"🧪 {pot.display_name} を飲み、体力が回復した！ (+{heal} HP)", (100, 255, 150))
                engine.advance_world()
                return f"{pot.display_name} を使用しました"
            return "ポーションを持っていません"
        elif action == "set_pet_tactic":
            tactic = data.get("tactic", "balanced")
            if engine.pet:
                setattr(engine.pet, "tactic", tactic)
                engine.log(f"シエルへの戦術指示を【{tactic}】に変更しました。", (255, 180, 220))
                return f"戦術指示: {tactic}"

        if dx != 0 or dy != 0:
            acted = engine.player_act(dx, dy)
            if acted:
                engine.advance_world()
            return "移動/攻撃を行いました"
        return "Action processed"

    def log_message(self, format, *args):
        return


def start_web_server(engine: "Engine", port: int = 8080) -> Optional[HTTPServer]:
    global _ENGINE_INSTANCE
    _ENGINE_INSTANCE = engine

    try:
        server = HTTPServer(("0.0.0.0", port), GameHTTPRequestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server
    except Exception as e:
        print(f"Web server failed to bind on port {port}: {e}")
        return None
