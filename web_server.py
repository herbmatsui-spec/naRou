"""
Elona Roguelike - Web Dual-Engine Server (Masterpiece Edition v2.0)
Provides HTTP server and REST/JSON API for HTML5 Canvas interactive rendering & WebAudio engine.
"""

from __future__ import annotations
import json
import math
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any, TYPE_CHECKING
import os

from ui_event_panel import get_current_event_info, get_event_ranking, get_player_event_score
from ui_ranking_panel import get_all_event_rankings

# Dynamic-lighting foundation (Phase 2-A). Import is optional so the server still
# runs if fov.py is unavailable.
try:
    from fov import compute_light_map as _compute_light_map
    _FOV_AVAILABLE = True
except Exception:  # pragma: no cover
    _FOV_AVAILABLE = False

if TYPE_CHECKING:
    from game import Engine

_ENGINE_INSTANCE: Optional["Engine"] = None
_ENGINE_LOCK: threading.Lock = threading.Lock()

# 開発環境ではlocalhostを許可、本番環境では適切なドメインに制限する
ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    # 本番環境ではここに実際のドメインを追加
]

def _is_origin_allowed(origin: str) -> bool:
    """オリジンが許可リストに含まれているかチェック"""
    return origin in ALLOWED_ORIGINS


# レート制限のスケルトン実装（本番では適切なストレージに置き換える）
_REQUEST_HISTORY: Dict[str, list] = {}
_RATE_LIMIT_WINDOW = 60  # 1分間隔
_RATE_LIMIT_MAX_REQUESTS = 100  # 窓内最大リクエスト数


def _is_rate_allowed(client_ip: str) -> bool:
    """レート制限チェックのスケルトン実装"""
    import time
    now = time.time()
    
    if client_ip not in _REQUEST_HISTORY:
        _REQUEST_HISTORY[client_ip] = []
    
    # 古いリクエストを削除
    _REQUEST_HISTORY[client_ip] = [
        req_time for req_time in _REQUEST_HISTORY[client_ip]
        if now - req_time < _RATE_LIMIT_WINDOW
    ]
    
    # リクエスト数をチェック
    if len(_REQUEST_HISTORY[client_ip]) >= _RATE_LIMIT_MAX_REQUESTS:
        return False
    
    # 現在のリクエストを記録
    _REQUEST_HISTORY[client_ip].append(now)
    return True


class GameHTTPRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, content_type="application/json"):
        self.send_response(200)
        # セキュリティ強化: オリジンチェックを実装
        origin = self.headers.get('Origin')
        if origin and _is_origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            # デフォルトは同一オリジンポリシー（何も送信しない）
            pass
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()
    def do_GET(self):
        # レート制限チェック
        client_ip = self.client_address[0]
        if not _is_rate_allowed(client_ip):
            self.send_response(429)  # Too Many Requests
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Rate limit exceeded"}).encode('utf-8'))
            return

        global _ENGINE_INSTANCE, _ENGINE_LOCK
        if self.path == "/api/state":
            if _ENGINE_INSTANCE is None:
                self._set_headers()
                self.wfile.write(json.dumps({"error": "Engine not initialized"}).encode('utf-8'))
                return

            with _ENGINE_LOCK:
                state = self._serialize_engine_state(_ENGINE_INSTANCE)
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(state, ensure_ascii=False).encode('utf-8'))
        elif self.path == "/api/event/info":
            # イベント情報を取得
            query = self.path.split('?', 1)[1] if '?' in self.path else ''
            params = dict(qc.split('=') for qc in query.split('&') if qc)
            turn = int(params.get('turn', 0))
            info = get_current_event_info(turn)
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(info, ensure_ascii=False).encode('utf-8'))
        elif self.path == "/api/event/ranking":
            query = self.path.split('?', 1)[1] if '?' in self.path else ''
            params = dict(qc.split('=') for qc in query.split('&') if qc)
            event_id = params.get('event_id', '')
            top_n = int(params.get('top_n', 10))
            ranking = get_event_ranking(event_id, top_n)
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(ranking, ensure_ascii=False).encode('utf-8'))
        elif self.path == "/api/event/score":
            query = self.path.split('?', 1)[1] if '?' in self.path else ''
            params = dict(qc.split('=') for qc in query.split('&') if qc)
            event_id = params.get('event_id', '')
            player_id = params.get('player_id', '')
            score = get_player_event_score(event_id, player_id)
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({"score": score}, ensure_ascii=False).encode('utf-8'))
        elif self.path == "/api/event/titles":
            query = self.path.split('?', 1)[1] if '?' in self.path else ''
            params = dict(qc.split('=') for qc in query.split('&') if qc)
            event_id = params.get('event_id', '')
            player_id = params.get('player_id', '')
            # プレイヤーオブジェクトを取得する必要があるが、ここでは簡易的に空リストを返す
            # 実際には、エンジンからプレイヤーオブジェクトを取得する
            titles = []  # プレースホルダー
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(titles, ensure_ascii=False).encode('utf-8'))
        elif self.path == "/api/event/all_rankings":
            all_rankings = get_all_event_rankings()
            self._set_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(all_rankings, ensure_ascii=False).encode('utf-8'))
        elif self.path in ("/", "/index.html"):
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
            # 静的ファイル（HTML, JS, PNG, JSON, CSS 等）の配信
            rel_path = self.path.lstrip("/").split("?")[0]
            file_path = os.path.join(os.path.dirname(__file__), rel_path)
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                content_types = {
                    ".html": "text/html; charset=utf-8",
                    ".js": "application/javascript; charset=utf-8",
                    ".css": "text/css; charset=utf-8",
                    ".json": "application/json; charset=utf-8",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".gif": "image/gif"
                }
                ctype = content_types.get(ext, "application/octet-stream")
                self._set_headers(ctype)
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()

    def do_POST(self):
        global _ENGINE_INSTANCE, _ENGINE_LOCK
        if self.path == "/api/action":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}

            action = data.get("action")
            result_msg = "OK"

            with _ENGINE_LOCK:
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
        light_color = []

        # --- Phase 2-A: 再帰的シャドウキャスティングによるライトマップ ---
        # プレイヤー（ランタン）＋松明を光源とし、壁で光を遮断する。
        light_intensity = None
        light_rgb = None
        client_light_sources = []
        if _FOV_AVAILABLE:
            try:
                blocked = [
                    [not engine.game_map.is_transparent(cam_x + vx, cam_y + vy)
                     if (0 <= cam_x + vx < engine.game_map.width
                         and 0 <= cam_y + vy < engine.game_map.height)
                     else True
                     for vx in range(view_w)]
                    for vy in range(view_h)
                ]
                sources = [{
                    "x": p.x - cam_x, "y": p.y - cam_y,
                    "radius": 8.0, "intensity": 1.0,
                    "color": (255, 240, 210),
                }]
                for (tx, ty) in getattr(engine.game_map, "torch_positions", []):
                    lx, ly = tx - cam_x, ty - cam_y
                    if 0 <= lx < view_w and 0 <= ly < view_h:
                        sources.append({
                            "x": lx, "y": ly,
                            "radius": 5.0, "intensity": 0.9,
                            "color": (255, 170, 80),
                        })
                client_light_sources = [
                    {"x": s["x"], "y": s["y"],
                     "radius": s["radius"], "intensity": s["intensity"],
                     "color": [int(s["color"][0]), int(s["color"][1]), int(s["color"][2])]}
                    for s in sources
                ]
                light_intensity, light_rgb = _compute_light_map(
                    blocked, sources, view_w, view_h, ambient=0.06)
            except Exception:
                light_intensity = None

        for vy in range(view_h):
            row = []
            raw_row = []
            light_row = []
            color_row = []
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
                        if light_intensity is not None:
                            intensity = max(0.12, round(float(light_intensity[vy][vx]), 2))
                            r, g, b = light_rgb[vy][vx]
                            color_row.append(f"{r},{g},{b}")
                        else:
                            # フォールバック: プレイヤー距離ベース
                            dist_sq = (mx - p.x) ** 2 + (my - p.y) ** 2
                            intensity = max(0.15, 1.0 - (dist_sq / 64.0))
                            color_row.append("255,240,210")
                        light_row.append(intensity)
                    elif is_exp:
                        row.append(raw_tile)
                        light_row.append(0.0)  # 探索済みだが視界外 (Fog of war)
                        color_row.append("40,42,55")
                    else:
                        row.append(" ")
                        light_row.append(-1.0)  # 未探索
                        color_row.append("0,0,0")
                else:
                    row.append(" ")
                    raw_row.append(" ")
                    light_row.append(-1.0)
                    color_row.append("0,0,0")
            visible_tiles.append(row)
            raw_tiles.append(raw_row)
            light_map.append(light_row)
            light_color.append(color_row)

        entities_data = []
        enemy_cones = []
        for e in engine.entities:
            if engine.game_map.visible[e.x][e.y] and e.hp > 0:
                vx = e.x - cam_x
                vy = e.y - cam_y
                if 0 <= vx < view_w and 0 <= vy < view_h:
                    # エンティティタイプからTileDef ID決定
                    if e.is_player:
                        tile_id = "PLAYER"
                    elif getattr(e, "is_pet", False):
                        tile_id = "PET"
                    else:
                        tile_id = "ENEMY_GOBLIN"
                    
                    # 向き計算 (移動ベクトルから推定)
                    facing = getattr(e, "facing", 0)
                    if facing == 0 and (hasattr(e, 'prev_x') and hasattr(e, 'prev_y')):
                        dx = e.x - e.prev_x
                        dy = e.y - e.prev_y
                        if dx != 0 or dy != 0:
                            if abs(dx) > abs(dy):
                                facing = 2 if dx > 0 else 1
                            else:
                                facing = 0 if dy > 0 else 3
                    
                    # 状態判定
                    state = "idle"
                    if getattr(e, "attacking", False):
                        state = "attack"
                    elif getattr(e, "attack_timer", 0) > 0:
                        state = "attack"
                    elif e.hp <= 0:
                        state = "dead"
                    elif getattr(e, "moving", False) or getattr(e, "vx", 0) != 0 or getattr(e, "vy", 0) != 0:
                        state = "walk"
                    else:
                        state = "idle"
                    
                    entities_data.append({
                        "name": e.name,
                        "char": e.char,
                        "tile_id": tile_id,
                        "x": vx,
                        "y": vy,
                        "world_x": e.x,
                        "world_y": e.y,
                        "hp": e.hp,
                        "max_hp": e.max_hp,
                        "is_player": e.is_player,
                        "is_pet": getattr(e, "is_pet", False),
                        "facing": facing,
                        "state": state,
                        "attack_timer": getattr(e, "attack_timer", 0),
                        "moving": getattr(e, "moving", False),
                        "faction": getattr(e, "faction", "neutral"),
                        "status_effects": [st.name for st in getattr(e, "status_effects", [])]
                    })
                    # Phase 2-A: 敵の視界コーン（プレイヤー方向を向く）
                    if not getattr(e, "is_player", False):
                        ang = math.atan2(p.y - e.y, p.x - e.x)
                        enemy_cones.append({
                            "x": vx, "y": vy,
                            "angle": ang, "half_angle": 0.6,
                            "range": 6, "color": "255,60,60",
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

        # 光源リスト (Canvas Dynamic Lighting用) — プレイヤー(ランタン)＋松明
        # ＋祭壇(魔法光)を含む。FOV利用不可時はプレイヤーのみ。
        light_sources = list(client_light_sources)
        if hasattr(engine, "altar_pos"):
            ax, ay = engine.altar_pos
            if engine.game_map.visible[ax][ay]:
                light_sources.append({
                    "x": ax - cam_x, "y": ay - cam_y, "radius": 4.0,
                    "color": [100, 200, 255], "intensity": 0.8
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
            "light_color": light_color,
            "light_sources": light_sources,
            "enemy_cones": enemy_cones,
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
            "fog_density": getattr(engine, "fog_density", 0.35 + (engine.dungeon_level % 5) * 0.05),
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
    global _ENGINE_INSTANCE, _ENGINE_LOCK
    _ENGINE_INSTANCE = engine
    _ENGINE_LOCK = threading.Lock()

    try:
        server = HTTPServer(("0.0.0.0", port), GameHTTPRequestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"[WebServer] Server started on port {port} with Thread-Safety (Lock) enabled.")
        return server
    except Exception as e:
        print(f"Web server failed to bind on port {port}: {e}")
        return None
