"""
secret_area_system.py
SkillEaterSecretAccess - 隠しエリア・秘密通路・鍵システム
Steps 9-11: Data classes and Registry
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Any

import yaml

from constants import (
    ACCESS_FACTION_REP,
    ACCESS_QUEST_FLAG,
    ACCESS_SACRIFICE,
    ACCESS_SKILL_REQUIRED,
    ACCESS_TIME_WINDOW,
    EMOTE_EYE,
    EMOTE_KEY,
    KEY_TYPE_BIOMETRIC,
    KEY_TYPE_DECRYPTION,
    KEY_TYPE_KEYCARD,
    KEY_TYPE_PHYSICAL,
    REWARD_CONCEPT_CRYSTAL,
    REWARD_FORBIDDEN_SKILL,
    REWARD_HIDDEN_MERCHANT,
    REWARD_LORE,
    REWARD_SHORTCUT,
    TILE_FALSE_WALL,
    TILE_HIDDEN_DOOR,
    TILE_SECRET_FLOOR,
    TILE_VENT,
)
from skill_eater_system import CharacterState, SkillEaterRegistry


@dataclass
class SecretArea:
    """隠しエリア・秘密通路の定義"""
    id: str
    name: str
    layer_key: str              # "zone:biome:depth:dimension"
    secret_type: str            # hidden_door, false_wall, secret_floor, vent
    position: tuple[int, int]
    detection_difficulty: int
    access_conditions: list[dict]
    key_required: dict | None
    rewards: list[dict]
    audio: dict
    emotes: dict
    is_discovered: bool = False
    is_unlocked: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SecretArea:
        pos = data.get("position", [0, 0])
        return cls(
            id=data["id"],
            name=data["name"],
            layer_key=data["layer"],
            secret_type=data["secret_type"],
            position=(pos[0], pos[1]),
            detection_difficulty=data.get("detection_difficulty", 20),
            access_conditions=data.get("access_conditions", []),
            key_required=data.get("key_required"),
            rewards=data.get("rewards", []),
            audio=data.get("audio", {}),
            emotes=data.get("emotes", {}),
            is_discovered=False,
            is_unlocked=False,
        )

    def get_hint_text(self) -> str:
        """未解除時のヒントテキストを生成"""
        hints = []
        for cond in self.access_conditions:
            ctype = cond.get("type")
            if ctype == ACCESS_FACTION_REP:
                hints.append(f"必要派閥評判: {cond['faction']} {cond['min_rep']}以上")
            elif ctype == ACCESS_SKILL_REQUIRED:
                registry = SkillEaterRegistry.get_instance()
                skill = registry.get_skill(cond["skill_id"])
                sname = skill.name if skill else cond["skill_id"]
                hints.append(f"必要スキル: {sname}")
            elif ctype == ACCESS_QUEST_FLAG:
                hints.append(f"必要クエスト: {cond['quest_flag']}")
            elif ctype == ACCESS_TIME_WINDOW:
                hints.append(f"時間帯: {cond['hour_start']}:00-{cond['hour_end']}:00")
            elif ctype == ACCESS_SACRIFICE:
                if "hp_cost" in cond:
                    hints.append(f"犠牲: HP {cond['hp_cost']}")
                if "skill_cost" in cond:
                    hints.append(f"犠牲: スキル {cond['skill_cost']}")
                if "item_cost" in cond:
                    hints.append(f"犠牲: アイテム {cond['item_cost']}")
        if self.key_required:
            kt = self.key_required.get("type")
            if kt == KEY_TYPE_KEYCARD:
                hints.append(f"必要: キーカード Lv.{self.key_required.get('level', 1)}以上")
            elif kt == KEY_TYPE_BIOMETRIC:
                hints.append(f"必要: 生体認証({self.key_required.get('subtype', 'fingerprint')})")
            elif kt == KEY_TYPE_DECRYPTION:
                hints.append(f"必要: 暗号解除モジュール Lv.{self.key_required.get('level', 1)}以上")
            elif kt == KEY_TYPE_PHYSICAL:
                hints.append(f"必要: 物理鍵({self.key_required.get('key_id', 'unknown')})")
        return " / ".join(hints) if hints else "条件なし"


@dataclass
class KeyItem:
    """鍵アイテムの定義"""
    id: str
    name: str
    key_type: str               # keycard, biometric, decryption, physical
    level: int = 1
    subtype: str = ""
    consumable: bool = False
    description: str = ""
    market_value: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KeyItem:
        return cls(
            id=data["id"],
            name=data["name"],
            key_type=data["type"],
            level=data.get("level", 1),
            subtype=data.get("subtype", ""),
            consumable=data.get("consumable", False),
            description=data.get("description", ""),
            market_value=data.get("market_value", 0),
        )


@dataclass
class SecretConnection:
    """秘密エリア間の接続定義"""
    from_area: str
    to_area: str
    connection_type: str        # tunnel, vent, teleport
    one_way: bool = False


class SecretAreaRegistry:
    """隠しエリア・鍵アイテムのレジストリ（シングルトン）"""
    _instance: SecretAreaRegistry | None = None

    def __new__(cls) -> SecretAreaRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._secret_areas: dict[str, SecretArea] = {}
        self._key_items: dict[str, KeyItem] = {}
        self._areas_by_layer: dict[str, list[SecretArea]] = {}
        self._connections: list[SecretConnection] = []

    def load_from_yaml(self, secret_areas_path: str = "data/secret_areas.yaml",
                       key_items_path: str = "data/key_items.yaml") -> None:
        """YAMLファイルからデータを読み込み"""
        # Secret Areas
        if os.path.exists(secret_areas_path):
            with open(secret_areas_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for area_data in data.get("secret_areas", []):
                area = SecretArea.from_dict(area_data)
                self._secret_areas[area.id] = area
                if area.layer_key not in self._areas_by_layer:
                    self._areas_by_layer[area.layer_key] = []
                self._areas_by_layer[area.layer_key].append(area)

        # Key Items
        if os.path.exists(key_items_path):
            with open(key_items_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for key_data in data.get("key_items", []):
                key = KeyItem.from_dict(key_data)
                self._key_items[key.id] = key

    def get_secret_area(self, area_id: str) -> SecretArea | None:
        return self._secret_areas.get(area_id)

    def get_areas_in_layer(self, layer_key: str) -> list[SecretArea]:
        return self._areas_by_layer.get(layer_key, [])

    def get_all_areas(self) -> list[SecretArea]:
        return list(self._secret_areas.values())

    def get_key_item(self, key_id: str) -> KeyItem | None:
        return self._key_items.get(key_id)

    def get_all_key_items(self) -> list[KeyItem]:
        return list(self._key_items.values())

    def add_connection(self, connection: SecretConnection) -> None:
        self._connections.append(connection)

    def get_connections_from(self, area_id: str) -> list[SecretConnection]:
        return [c for c in self._connections if c.from_area == area_id]

    def get_connections_to(self, area_id: str) -> list[SecretConnection]:
        return [c for c in self._connections if c.to_area == area_id]


# グローバルインスタンス
SECRET_REGISTRY = SecretAreaRegistry()


def perception_check(player: CharacterState, base_difficulty: int,
                     skill_bonus: int = 0) -> tuple[bool, int]:
    """
    知覚判定を実行
    Returns: (success, margin) - 成功時は margin > 0
    """
    perception = getattr(player, 'perception', 10)
    analysis = getattr(player, 'analysis_level', 1)

    # 連続失敗ペナルティ (Step 21)
    failed_count = getattr(player, 'failed_search_count', 0)
    penalty = failed_count * 2  # 失敗ごとに難易度+2

    roll = random.randint(1, 100)
    target = base_difficulty + skill_bonus + penalty
    effective = perception * 2 + analysis * 3
    success = (roll + effective) >= target
    margin = (roll + effective) - target if success else 0
    return success, margin


def check_secret_detection(player: CharacterState, game_map, current_layer_key: str) -> list[SecretArea]:
    """
    プレイヤー周囲の未発見シークレットエリアを検知判定
    発見成功したエリアのリストを返す
    """
    registry = SECRET_REGISTRY
    areas = registry.get_areas_in_layer(current_layer_key)
    discovered = []

    px, py = player.x, player.y
    for area in areas:
        if area.is_discovered or area.is_unlocked:
            continue
        if area.id in player.discovered_secrets:
            area.is_discovered = True
            continue

        # 距離チェック（周囲3マス以内）
        ax, ay = area.position
        dist = max(abs(px - ax), abs(py - ay))
        if dist > 3:
            continue

        # スキルボーナス計算 (Step 20)
        skill_bonus = 0
        detection_skills = {
            "detection_mastery": 5,
            "trap_finder": 3,
            "secret_sense": 4,
            "perception_training": 2,
        }
        for skill_id, bonus_per_level in detection_skills.items():
            if player.has_skill(skill_id):
                slot = player.skills.get(skill_id)
                if slot:
                    skill_bonus += slot.level * bonus_per_level

        # 検知判定
        success, margin = perception_check(player, area.detection_difficulty, skill_bonus)

        if success:
            area.is_discovered = True
            player.discovered_secrets.add(area.id)
            player.failed_search_count = 0  # 成功でリセット
            discovered.append(area)
            # タイル変更処理
            _apply_secret_tile_change(game_map, area)
            # イベント発行・音響・エモート
            from event_bus import event_bus
            event_bus.publish("secret_detected", {
                "area_id": area.id,
                "position": area.position,
                "secret_type": area.secret_type,
                "margin": margin,
                "skill_bonus": skill_bonus,
            })
            # 音響・エモート再生
            _play_detection_audio_emote(area)
        else:
            # 失敗時のカウント
            player.failed_search_count += 1

    return discovered


def _apply_secret_tile_change(game_map, area: SecretArea) -> None:
    """検知成功時にタイルを変更"""
    x, y = area.position
    if not game_map.is_in_bounds(x, y):
        return

    # 隠しタイル情報を記録
    original_tile = game_map.tiles[x][y]
    if not hasattr(game_map, 'hidden_tiles'):
        game_map.hidden_tiles = {}
    game_map.hidden_tiles[(x, y)] = {
        "original_tile": original_tile,
        "secret_type": area.secret_type,
        "area_id": area.id,
    }

    # 秘密タイプに応じたタイルに変更
    if area.secret_type == "hidden_door":
        game_map.tiles[x][y] = TILE_HIDDEN_DOOR
    elif area.secret_type == "false_wall":
        game_map.tiles[x][y] = TILE_FALSE_WALL
    elif area.secret_type == "secret_floor":
        game_map.tiles[x][y] = TILE_SECRET_FLOOR
    elif area.secret_type == "vent":
        game_map.tiles[x][y] = TILE_VENT


def try_unlock_secret(player: CharacterState, area: SecretArea, game_map) -> tuple[bool, str]:
    """
    秘密エリアの解除を試行
    Returns: (success, message)
    """
    registry = SECRET_REGISTRY

    # 1. 発見済みチェック
    if not area.is_discovered and area.id not in player.discovered_secrets:
        return False, "まだ発見されていません。周囲を探索してください。"

    # 2. 既に解除済み
    if area.is_unlocked or area.id in player.unlocked_secrets:
        return False, "既に解放済みです。"

    # 3. アクセス条件チェック
    for cond in area.access_conditions:
        ok, msg = _check_access_condition(player, cond)
        if not ok:
            return False, msg

    # 4. 鍵要件チェック
    if area.key_required:
        ok, msg, key_id = _check_key_requirement(player, area.key_required)
        if not ok:
            return False, msg
        # 消費型キーなら消費
        if key_id and registry.get_key_item(key_id) and registry.get_key_item(key_id).consumable:
            player.remove_key(key_id, 1)

    # 5. 解除成功
    area.is_unlocked = True
    player.unlocked_secrets.add(area.id)

    # タイルを恒久的に通行可能に変更
    x, y = area.position
    if game_map.is_in_bounds(x, y):
        from constants import TILE_FLOOR
        game_map.tiles[x][y] = TILE_FLOOR
        # 隠しタイル情報削除
        if hasattr(game_map, 'hidden_tiles') and (x, y) in game_map.hidden_tiles:
            del game_map.hidden_tiles[(x, y)]

    # 報酬付与
    reward_msgs = _grant_rewards(player, area)

    # 音響・エモート再生 (Step 36)
    _play_unlock_audio_emote(area)

    # 秘密通路タイプなら突入音も再生
    if area.secret_type in ("secret_floor", "vent"):
        _play_enter_audio_emote(area)

    # イベント発行
    from event_bus import event_bus
    event_bus.publish("secret_unlocked", {
        "area_id": area.id,
        "position": area.position,
        "secret_type": area.secret_type,
        "rewards": area.rewards,
    })

    msg = f"【{area.name}】が解放されました！"
    if reward_msgs:
        msg += " " + " ".join(reward_msgs)
    return True, msg


def _check_access_condition(player: CharacterState, condition: dict) -> tuple[bool, str]:
    """アクセス条件の個別チェック"""
    ctype = condition.get("type")

    if ctype == ACCESS_FACTION_REP:
        faction = condition["faction"]
        min_rep = condition["min_rep"]
        current = player.faction_reputation.get(faction, 0)
        if current < min_rep:
            return False, f"派閥『{faction}』の評判が足りません（必要: {min_rep}, 現在: {current}）"
        return True, ""

    elif ctype == ACCESS_SKILL_REQUIRED:
        skill_id = condition["skill_id"]
        if not player.has_skill(skill_id):
            registry = SkillEaterRegistry.get_instance()
            skill = registry.get_skill(skill_id)
            sname = skill.name if skill else skill_id
            return False, f"スキル『{sname}』を習得していません。"
        return True, ""

    elif ctype == ACCESS_QUEST_FLAG:
        flag = condition["quest_flag"]
        if not player.story_variables.get(flag, False):
            return False, f"クエストフラグ『{flag}』が立っていません。"
        return True, ""

    elif ctype == ACCESS_TIME_WINDOW:
        # ゲーム内時間取得（既存システム連携）
        current_hour = getattr(player, 'current_hour', 12)  # 仮実装
        start = condition["hour_start"]
        end = condition["hour_end"]
        if start <= end:
            if not (start <= current_hour < end):
                return False, f"時間帯ではありません（{start}:00-{end}:00）"
        else:  # 日をまたぐ場合 (例: 22-4)
            if not (current_hour >= start or current_hour < end):
                return False, f"時間帯ではありません（{start}:00-{end}:00）"
        return True, ""

    elif ctype == ACCESS_SACRIFICE:
        # 犠牲確認・支払いは解除実行時に行う（ここではチェックのみ）
        return True, ""

    return True, ""


def _check_key_requirement(player: CharacterState, key_req: dict) -> tuple[bool, str, str]:
    """鍵要件チェック。成功時 (True, "", key_id)"""
    ktype = key_req.get("type")

    if ktype == KEY_TYPE_KEYCARD:
        required_level = key_req.get("level", 1)
        for key_id, count in player.owned_keys.items():
            key_def = SECRET_REGISTRY.get_key_item(key_id)
            if key_def and key_def.key_type == KEY_TYPE_KEYCARD and key_def.level >= required_level:
                return True, "", key_id
        return False, f"キーカード Lv.{required_level} 以上が必要です。", ""

    elif ktype == KEY_TYPE_BIOMETRIC:
        subtype = key_req.get("subtype", "fingerprint")
        key_id = f"biometric_{subtype}"
        if player.owned_keys.get(key_id, 0) > 0:
            return True, "", key_id
        return False, f"生体認証キー（{subtype}）が必要です。", ""

    elif ktype == KEY_TYPE_DECRYPTION:
        required_level = key_req.get("level", 1)
        for key_id, count in player.owned_keys.items():
            key_def = SECRET_REGISTRY.get_key_item(key_id)
            if key_def and key_def.key_type == KEY_TYPE_DECRYPTION and key_def.level >= required_level:
                return True, "", key_id
        return False, f"暗号解除モジュール Lv.{required_level} 以上が必要です。", ""

    elif ktype == KEY_TYPE_PHYSICAL:
        key_id = key_req.get("key_id", "")
        if player.owned_keys.get(key_id, 0) > 0:
            return True, "", key_id
        key_def = SECRET_REGISTRY.get_key_item(key_id)
        kname = key_def.name if key_def else key_id
        return False, f"物理鍵『{kname}』が必要です。", ""

    return False, "不明な鍵タイプです。", ""


def _grant_rewards(player: CharacterState, area: SecretArea) -> list[str]:
    """報酬を付与し、メッセージリストを返す"""
    messages = []
    for reward in area.rewards:
        rtype = reward.get("type")
        if rtype == REWARD_FORBIDDEN_SKILL:
            skill_id = reward.get("skill_id")
            if player.add_skill(skill_id):
                registry = SkillEaterRegistry.get_instance()
                skill = registry.get_skill(skill_id)
                sname = skill.name if skill else skill_id
                messages.append(f"禁忌スキル『{sname}』を習得！")
            else:
                messages.append("スキル習得失敗（メモリ容量不足）")

        elif rtype == REWARD_CONCEPT_CRYSTAL:
            crystal_id = reward.get("crystal_id")
            # アイテムとして追加（item_system連携は別途）
            messages.append(f"コンセプト結晶『{crystal_id}』を入手！")

        elif rtype == REWARD_LORE:
            text = reward.get("text", "")
            if not hasattr(player, 'discovered_lore'):
                player.discovered_lore = []
            player.discovered_lore.append({"id": area.id, "text": text})
            messages.append("ロアを発見！")

        elif rtype == REWARD_SHORTCUT:
            # WorldMapManager連携は別途（Step 44）
            messages.append("ショートカットを開通！")

        elif rtype == REWARD_HIDDEN_MERCHANT:
            # EconomySystem連携は別途（Step 43）
            messages.append("隠し商人が出現！")

    return messages


def _play_detection_audio_emote(area: SecretArea) -> None:
    """検知成功時の音響・エモート再生 (Step 23)"""
    try:
        from skill_eater_presentation_system import SkillEaterPresentationSystem
        presentation = SkillEaterPresentationSystem.get_instance()

        # 音響再生
        detect_sfx = area.audio.get("detect", "perception_success")
        if detect_sfx:
            presentation.play_sound(detect_sfx)

        # エモート表示
        detect_emote = area.emotes.get("detect", EMOTE_EYE)
        if detect_emote:
            presentation.show_emote(detect_emote, area.position[0], area.position[1])
    except Exception:
        pass  # 音響システム未初期化時は無視


def _play_unlock_audio_emote(area: SecretArea) -> None:
    """解除成功時の音響・エモート再生 (Step 36)"""
    try:
        from skill_eater_presentation_system import SkillEaterPresentationSystem
        presentation = SkillEaterPresentationSystem.get_instance()

        # 音響再生
        unlock_sfx = area.audio.get("unlock", "secret_wall_slide")
        if unlock_sfx:
            presentation.play_sound(unlock_sfx)

        # エモート表示
        unlock_emote = area.emotes.get("unlock", EMOTE_KEY)
        if unlock_emote:
            presentation.show_emote(unlock_emote, area.position[0], area.position[1])
    except Exception:
        pass


def _play_enter_audio_emote(area: SecretArea) -> None:
    """秘密通路突入時の音響再生"""
    try:
        from skill_eater_presentation_system import SkillEaterPresentationSystem
        presentation = SkillEaterPresentationSystem.get_instance()

        enter_sfx = area.audio.get("enter", "ancient_mechanism")
        if enter_sfx:
            presentation.play_sound(enter_sfx)
    except Exception:
        pass


def use_secret_passage(player: CharacterState, area: SecretArea, game_map, engine=None) -> tuple[bool, str]:
    """
    秘密通路を使用して移動 (Steps 37, 38)
    Returns: (success, message)
    """
    if not area.is_unlocked and area.id not in player.unlocked_secrets:
        return False, "この通路はまだ解放されていません。"

    x, y = player.x, player.y
    ax, ay = area.position

    # プレイヤーが通路の入り口にいるかチェック
    if max(abs(x - ax), abs(y - ay)) > 1:
        return False, "通路の入り口にいません。"

    if area.secret_type == "secret_floor":
        # 床下通路: 下層へワープ
        return _use_secret_floor(player, area, game_map, engine)
    elif area.secret_type == "vent":
        # 換気ダクト: クロール移動
        return _use_vent(player, area, game_map, engine)

    return False, "このタイプの通路は使用できません。"


def _use_secret_floor(player: CharacterState, area: SecretArea, game_map, engine=None) -> tuple[bool, str]:
    """床下通路（下層接続）を使用"""
    # 接続先レイヤーを決定

    # 接続情報からターゲットを取得
    connections = SECRET_REGISTRY.get_connections_from(area.id)
    floor_connections = [c for c in connections if c.connection_type in ("tunnel", "floor")]

    if not floor_connections:
        # デフォルト: 現在の層の下層へ
        target_layer_key = _get_next_layer_key(area.layer_key, -1)
    else:
        target_area = SECRET_REGISTRY.get_secret_area(floor_connections[0].to_area)
        if target_area:
            target_layer_key = target_area.layer_key
        else:
            target_layer_key = _get_next_layer_key(area.layer_key, -1)

    if engine and hasattr(engine, 'world_map_manager'):
        # WorldMapManagerで層移動
        target_layer = engine.world_map_manager.get_or_create_layer(
            *target_layer_key.split(":")
        )
        if target_layer:
            entrance = target_layer.get_entrance_position()
            # プレイヤー位置更新
            old_pos = (player.x, player.y)
            player.x, player.y = entrance

            # イベント発行
            from event_bus import event_bus
            event_bus.publish("secret_passage_used", {
                "from_pos": old_pos,
                "to_pos": entrance,
                "passage_type": "secret_floor",
                "area_id": area.id,
                "from_layer": area.layer_key,
                "to_layer": target_layer_key,
            })

            # 音響再生
            _play_enter_audio_emote(area)

            return True, f"床下通路を這い抜け、{target_layer.name}へ到達した。"

    return False, "接続先の層が見つかりません。"


def _use_vent(player: CharacterState, area: SecretArea, game_map, engine=None) -> tuple[bool, str]:
    """換気ダクト（クロール移動）を使用"""
    # 接続先を探索
    connections = SECRET_REGISTRY.get_connections_from(area.id)
    vent_connections = [c for c in connections if c.connection_type == "vent"]

    if not vent_connections:
        return False, "このダクトは行き止まりだ。"

    target_area = SECRET_REGISTRY.get_secret_area(vent_connections[0].to_area)
    if not target_area or not target_area.is_unlocked:
        return False, "向こう側が塞がれている。"

    # スタミナ消費
    stamina_cost = 10
    if hasattr(player, 'stamina') and player.stamina < stamina_cost:
        return False, "スタミナが足りない。"
    if hasattr(player, 'stamina'):
        player.stamina -= stamina_cost

    # 移動実行
    old_pos = (player.x, player.y)
    player.x, player.y = target_area.position

    # イベント発行
    from event_bus import event_bus
    event_bus.publish("secret_passage_used", {
        "from_pos": old_pos,
        "to_pos": target_area.position,
        "passage_type": "vent",
        "area_id": area.id,
    })

    # 音響再生
    _play_enter_audio_emote(area)

    return True, f"換気ダクトを這い進み、『{target_area.name}』へ到達した。"


def _get_next_layer_key(current_layer_key: str, depth_delta: int) -> str:
    """隣接層のキーを取得"""
    parts = current_layer_key.split(":")
    if len(parts) == 4:
        zone, biome, depth_str, dimension = parts
        try:
            depth = int(depth_str)
            new_depth = depth + depth_delta
            if new_depth < 0:
                new_depth = 0
            return f"{zone}:{biome}:{new_depth}:{dimension}"
        except ValueError:
            pass
    return current_layer_key


def add_secret_connection(from_area_id: str, to_area_id: str,
                          connection_type: str = "tunnel", one_way: bool = False) -> None:
    """秘密エリア間の接続を追加 (Step 41)"""
    conn = SecretConnection(
        from_area=from_area_id,
        to_area=to_area_id,
        connection_type=connection_type,
        one_way=one_way,
    )
    SECRET_REGISTRY.add_connection(conn)


def get_secret_connections_from(area_id: str) -> list[SecretConnection]:
    """指定エリアからの接続を取得"""
    return SECRET_REGISTRY.get_connections_from(area_id)


def get_secret_connections_to(area_id: str) -> list[SecretConnection]:
    """指定エリアへの接続を取得"""
    return SECRET_REGISTRY.get_connections_to(area_id)


def spawn_hidden_merchant(engine, area: SecretArea) -> bool:
    """隠し商人を出現させる (Step 43)"""
    for reward in area.rewards:
        if reward.get("type") == REWARD_HIDDEN_MERCHANT:
            merchant_id = reward.get("merchant_id", "shadow_broker_01")
            try:
                from skill_eater_economy_system import SkillEaterEconomySystem
                economy = SkillEaterEconomySystem()
                # 商人エンティティを生成
                from ecs.entity import Entity
                merchant = Entity(
                    area.position[0], area.position[1],
                    "🤝", (255, 215, 0), f"隠し商人 {merchant_id}"
                )
                merchant.is_merchant = True
                merchant.merchant_id = merchant_id
                merchant.faction = "broker"

                if hasattr(engine, 'entity_manager'):
                    engine.entity_manager.add_entity(merchant)

                engine.log(f"【出現】隠し商人『{merchant_id}』が現れた！", (255, 215, 0))
                return True
            except Exception:
                pass
    return False


def register_shortcut(engine, area: SecretArea) -> bool:
    """ショートカットを登録 (Step 44)"""
    for reward in area.rewards:
        if reward.get("type") == REWARD_SHORTCUT:
            target_layer = reward.get("target_layer")
            target_pos = reward.get("target_pos")
            if target_layer and target_pos:
                try:
                    if hasattr(engine, 'world_map_manager'):
                        engine.world_map_manager.register_shortcut(
                            area.layer_key, area.position, target_layer, tuple(target_pos)
                        )
                    engine.log(f"【開通】{area.layer_key} ↔ {target_layer} 間のショートカットが開通！", (100, 255, 150))
                    return True
                except Exception:
                    pass
    return False


def grant_rewards_full(engine, player: CharacterState, area: SecretArea, game_map) -> list[str]:
    """全報酬処理 (Steps 43, 44, 45, 46, 47)"""
    messages = _grant_rewards(player, area)

    # 隠し商人
    if spawn_hidden_merchant(engine, area):
        messages.append("隠し商人が出現！")

    # ショートカット
    if register_shortcut(engine, area):
        messages.append("ショートカットを開通！")

    return messages


# Save/Load support (Step 67)
def save_secret_registry_state() -> dict:
    """SecretAreaRegistryの状態を保存用dictで返す"""
    registry = SECRET_REGISTRY
    return {
        "secret_areas": {
            area_id: {
                "is_discovered": area.is_discovered,
                "is_unlocked": area.is_unlocked,
            }
            for area_id, area in registry._secret_areas.items()
        },
        "connections": [
            {
                "from_area": c.from_area,
                "to_area": c.to_area,
                "connection_type": c.connection_type,
                "one_way": c.one_way,
            }
            for c in registry._connections
        ],
    }


def load_secret_registry_state(state: dict) -> None:
    """SecretAreaRegistryの状態を復元"""
    registry = SECRET_REGISTRY
    registry.load_from_yaml()  # まず基本データを読み込み

    # 状態を復元
    for area_id, data in state.get("secret_areas", {}).items():
        area = registry._secret_areas.get(area_id)
        if area:
            area.is_discovered = data.get("is_discovered", False)
            area.is_unlocked = data.get("is_unlocked", False)

    # 接続を復元
    registry._connections.clear()
    for conn_data in state.get("connections", []):
        conn = SecretConnection(
            from_area=conn_data["from_area"],
            to_area=conn_data["to_area"],
            connection_type=conn_data["connection_type"],
            one_way=conn_data.get("one_way", False),
        )
        registry.add_connection(conn)


# Difficulty scaling (Step 68)
def get_difficulty_secret_modifier(difficulty: str) -> int:
    """難易度による秘密検知修正値を取得 (Step 68)"""
    modifiers = {
        "easy": -5,
        "normal": 0,
        "hard": 5,
        "lunatic": 10,
    }
    return modifiers.get(difficulty.lower(), 0)


def perception_check_with_difficulty(player: CharacterState, base_difficulty: int,
                                     skill_bonus: int = 0, difficulty: str = "normal") -> tuple[bool, int]:
    """難易度補正付き知覚判定 (Step 68)"""
    modifier = get_difficulty_secret_modifier(difficulty)
    return perception_check(player, base_difficulty + modifier, skill_bonus)


# Reincarnation carryover (Step 69)
def get_reincarnation_secret_carryover(player: CharacterState) -> set[str]:
    """転生時の秘密発見知識引き継ぎ (Step 69)"""
    # 記憶の欠片アイテムを持っている場合は全引き継ぎ
    if player.has_key("memory_fragment") or player.has_key("key_memory_fragment"):
        return player.discovered_secrets.copy()

    # 通常は発見済みの20%をランダムに引き継ぎ
    import random
    discovered = list(player.discovered_secrets)
    carryover_count = max(1, len(discovered) // 5)
    return set(random.sample(discovered, min(carryover_count, len(discovered)))) if discovered else set()


def apply_reincarnation_secret_carryover(player: CharacterState, carried_secrets: set[str]) -> None:
    """転生秘密知識を適用"""
    player.discovered_secrets.update(carried_secrets)
    for secret_id in carried_secrets:
        area = SECRET_REGISTRY.get_secret_area(secret_id)
        if area:
            area.is_discovered = True


# Achievements/Titles integration (Step 70)
def check_secret_achievements(player: CharacterState) -> list[str]:
    """秘密関連実績をチェック (Step 70)"""
    granted = []

    # 最初の発見
    if len(player.discovered_secrets) >= 1 and "first_discovery" not in player.get_archived_skill_ids():
        granted.append("first_discovery")

    # 10個発見
    if len(player.discovered_secrets) >= 10 and "secret_hunter" not in player.get_archived_skill_ids():
        granted.append("secret_hunter")

    # 全隠し扉解放
    all_areas = SECRET_REGISTRY.get_all_areas()
    hidden_doors = [a for a in all_areas if a.secret_type == "hidden_door"]
    unlocked_doors = [a for a in hidden_doors if a.is_unlocked]
    if len(unlocked_doors) == len(hidden_doors) and hidden_doors and "master_unlocker" not in player.get_archived_skill_ids():
        granted.append("master_unlocker")

    # キーコレクター
    total_keys = sum(player.owned_keys.values())
    if total_keys >= 5 and "key_collector" not in player.get_archived_skill_ids():
        granted.append("key_collector")

    # 全キーカード収集
    keycards = [k for k in player.owned_keys.keys() if "keycard" in k]
    if len(keycards) >= 5 and "keycard_master" not in player.get_archived_skill_ids():
        granted.append("keycard_master")

    return granted


def get_secret_titles(player: CharacterState) -> list[str]:
    """秘密関連称号を取得 (Step 70)"""
    titles = []

    if len(player.discovered_secrets) >= 1:
        titles.append("秘密の探求者")
    if len(player.discovered_secrets) >= 5:
        titles.append("隠し通路の案内人")
    if len(player.discovered_secrets) >= 10:
        titles.append("ダンジョンの主")
    if sum(player.owned_keys.values()) >= 5:
        titles.append("鍵主")
    if len([k for k in player.owned_keys.keys() if "keycard" in k]) >= 3:
        titles.append("セキュリティスペシャリスト")

    return titles
