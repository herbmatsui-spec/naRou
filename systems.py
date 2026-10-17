"""
Elona Roguelike - フェーズ5: 高度な戦闘・属性・フレンドリーファイア・出血システム
Steps 37-45: 属性耐性, 詠唱失敗率, AoEパターン, Faction/Aggro, 出血と自然回復の相殺

Note: CombatSystem is now a thin wrapper delegating to engine.systems.combat_system.CombatSystem.
The actual implementation has been consolidated there.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from constants import Element
from naRou import combat

if TYPE_CHECKING:
    from core_framework import Point
    from ecs.entity import Entity
    from item_system import Item

# 状態異常
STATUS_POISON = "毒"
STATUS_PARALYSIS = "麻痺"
STATUS_CONFUSION = "混乱"
STATUS_BLIND = "盲目"
STATUS_BLEEDING = "出血"  # ステップ45
STATUS_HASTE = "加速"
STATUS_SLOW = "鈍足"
STATUS_RETURN = "帰還待機"  # ステップ63 遅延ワープ

# ファクション (ステップ42)
FACTION_PLAYER = "player"
FACTION_MONSTER = "monster"
FACTION_TOWNSFOLK = "townsfolk"
FACTION_GUARD = "guard"


# ============================================================
# 呪文データ読み込み・統一実行 (Phase 2 Step 40-41)
# ============================================================

def load_spell_data() -> dict:
    """data/spells.yaml から呪文定義を読み込む"""
    try:
        from pathlib import Path

        import yaml
        spell_path = Path("data/spells.yaml")
        if spell_path.exists():
            with open(spell_path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    except Exception:
        pass
    return {}


_SPELL_DATA_CACHE: dict | None = None


def get_spell_data() -> dict:
    """呪文データをキャッシュ付きで取得"""
    global _SPELL_DATA_CACHE
    if _SPELL_DATA_CACHE is None:
        _SPELL_DATA_CACHE = load_spell_data()
    return _SPELL_DATA_CACHE


def get_spell_ids() -> list[str]:
    """定義済み呪文ID一覧を取得"""
    return list(get_spell_data().keys())


# -------------------------------------------------------------
# 統一呪文詠唱関数 (Phase 2 Step 40-41)
# -------------------------------------------------------------

def cast(spell_id: str, caster: Entity, target: Entity | None = None, engine=None) -> tuple[bool, str]:
    """
    統一呪文詠唱関数。

    Args:
        spell_id: 呪文ID (data/spells.yaml のキー)
        caster: 詠唱者
        target: 対象エンティティ (self-targetの場合は caster)
        engine: Engineインスタンス (teleport等で必要)

    Returns:
        (成功可否, ログメッセージ)
    """
    spell_data = get_spell_data().get(spell_id)
    if not spell_data:
        return False, f"未知の呪文: {spell_id}"

    mp_cost = spell_data.get("mp_cost", 0)
    if caster.mp < mp_cost:
        return False, "MPが足りない！"

    # MP消費
    caster.mp -= mp_cost

    target = target or caster
    element = spell_data.get("element", "magic")
    range_val = spell_data.get("range", 0)
    target_type = spell_data.get("target_type", "single")
    dice_num = spell_data.get("dice_num", 1)
    dice_side = spell_data.get("dice_side", 6)
    dmg_bonus = spell_data.get("dmg_bonus", 0)
    duration = spell_data.get("duration", 0)
    radius = spell_data.get("radius", 0)
    spell_name = spell_data.get("name", spell_id)

    # 距離チェック (self-target以外)
    if target != caster and engine and hasattr(engine, 'has_los'):
        from core_framework import Point
        if not engine.has_los(Point(caster.x, caster.y), Point(target.x, target.y)):
            return False, "視線が通っていない！"

    # 成功率計算 (プレイヤー呪文は高確率)
    skill_lv = caster.skills.get("magic_cast", None)
    skill_val = skill_lv.level if skill_lv else 1
    magic_attr = caster.attributes.magic if hasattr(caster, "attributes") else 10
    success_rate = min(95, max(5, skill_val * 8 + magic_attr * 3))

    if random.randint(1, 100) > success_rate:
        # 詠唱失敗: MP反動ダメージ
        backlash = random.randint(3, 10 + magic_attr)
        caster.hp -= backlash
        return False, f"詠唱失敗！魔力暴走で{backlash}ダメージ！"

    # 案4: element別のFX接続 (MP消費後・効果実行前)
    fx_manager = getattr(engine, "fx_manager", None) if engine is not None else None
    if fx_manager is not None:
        _spawn_spell_fx(fx_manager, spell_id, spell_data, caster, target)

    # 呪文効果実行
    return _execute_spell_effect(spell_id, spell_data, caster, target, engine)


# element → FXManager spawn系APIの対応表 (案4)
_SPELL_FX_SPAWNERS = {
    "fire": "spawn_fire_effect",
    "cold": "spawn_ice_effect",
    "lightning": "spawn_lightning_effect",
    "heal": "spawn_heal_effect",
    "utility": "spawn_teleport_effect",
}

# WebクライアントのemitSpell (ParticleSystem) に渡すエフェクト種別
_SPELL_FX_ELEMENT_MAP = {
    "fire": "fire",
    "cold": "ice",
    "lightning": "lightning",
    "heal": "heal",
    "utility": "teleport",
}


def _spawn_spell_fx(fx_manager, spell_id: str, spell_data: dict, caster: Entity, target: Entity) -> None:
    """詠唱成功時のelement別エフェクト生成 (既存spawn系API利用、Web連携含む)。

    Note:
        engine.fx_manager はテスト等でduck-typingされるため、
        属性欠け時は個別にスキップする。
    """
    element = spell_data.get("element", "magic")

    # 詠唱者位置の共通エフェクト
    spawn_magic_cast = getattr(fx_manager, "spawn_magic_cast", None)
    if callable(spawn_magic_cast):
        spawn_magic_cast(caster.x, caster.y)

    # element別の着弾エフェクト
    spawner = getattr(fx_manager, _SPELL_FX_SPAWNERS.get(element, ""), None)
    if callable(spawner):
        spawner(target.x, target.y)

    # Webクライアント向けの詠唱イベント記録 (spell IDベーストリガー用)
    record_spell_cast = getattr(fx_manager, "record_spell_cast", None)
    if callable(record_spell_cast):
        fx_element = _SPELL_FX_ELEMENT_MAP.get(element, "magic")
        record_spell_cast(spell_id, fx_element, target.x, target.y)


def _execute_spell_effect(spell_id: str, spell_data: dict, caster: Entity, target: Entity, engine=None) -> tuple[bool, str]:
    """呪文固有の効果を実行"""
    spell_name = spell_data.get("name", spell_id)
    element = spell_data.get("element", "magic")
    target_type = spell_data.get("target_type", "single")
    dice_num = spell_data.get("dice_num", 1)
    dice_side = spell_data.get("dice_side", 6)
    dmg_bonus = spell_data.get("dmg_bonus", 0)
    duration = spell_data.get("duration", 0)
    radius = spell_data.get("radius", 0)

    # ビーム系: 直線貫通
    if target_type == "beam":
        return _execute_beam_spell(spell_id, spell_data, caster, target)

    # エリア系: 半径内AoE
    if target_type == "area":
        return _execute_area_spell(spell_id, spell_data, caster, target, engine)

    # セルフターゲット (回復/バフ/テレポート等)
    if target_type == "self":
        return _execute_self_spell(spell_id, spell_data, caster, engine)

    # 単体対象 (攻撃呪文等)
    return _execute_single_spell(spell_id, spell_data, caster, target)


def _execute_single_spell(spell_id: str, spell_data: dict, caster: Entity, target: Entity) -> tuple[bool, str]:
    """単体対象呪文の実行"""
    spell_name = spell_data.get("name", spell_id)
    element = spell_data.get("element", "magic")
    dice_num = spell_data.get("dice_num", 1)
    dice_side = spell_data.get("dice_side", 6)
    dmg_bonus = spell_data.get("dmg_bonus", 0)

    if element == "heal":
        # 回復呪文
        heal = sum(random.randint(1, spell_data.get("dice_side", 8)) for _ in range(spell_data.get("dice_num", 2))) + spell_data.get("dmg_bonus", 0)
        target.hp = min(target.max_hp, target.hp + heal)
        return True, f"{caster.name}は{spell_data.get('name', spell_id)}を唱え、{target.name}の傷が癒えた！ (HP +{heal})"

    # 攻撃呪文
    dmg = sum(random.randint(1, spell_data.get("dice_side", 6)) for _ in range(spell_data.get("dice_num", 1))) + spell_data.get("dmg_bonus", 0)
    dmg += int(caster.attributes.magic / 2) if hasattr(caster, "attributes") else 0

    from constants import Element
    from engine.systems.combat_system import CombatSystem

    # 属性ダメージ適用
    element_enum = getattr(Element, element.upper(), Element.MAGIC)
    res_val = getattr(target, "resistances", None)
    if res_val and hasattr(res_val, "get"):
        res = res_val.get(element_enum)
    else:
        res = 0

    final_dmg = CombatSystem.calc_element_damage(dmg, element_enum, res)
    final_dmg = max(1, final_dmg)

    target.hp -= final_dmg
    if target.hp <= 0:
        target.hp = 0

    return True, f"{caster.name}は{spell_data.get('name', spell_id)}を唱え{target.name}に{final_dmg}ダメージ！"


def _execute_beam_spell(spell_id: str, spell_data: dict, caster: Entity, target: Entity) -> tuple[bool, str]:
    """ビーム系呪文: 直線貫通"""
    import random

    from constants import MAP_HEIGHT, MAP_WIDTH, Element
    from core_framework import Point
    from engine.systems.combat_system import CombatSystem

    spell_name = spell_data.get("name", spell_id)
    element = spell_data.get("element", "magic")
    dice_num = spell_data.get("dice_num", 1)
    dice_side = spell_data.get("dice_side", 6)
    dmg_bonus = spell_data.get("dmg_bonus", 0)

    # 方向ベクトル計算
    dx = target.x - caster.x
    dy = target.y - caster.y
    dist = max(abs(dx), abs(dy))
    if dist == 0:
        return False, "対象が同じ位置にいる"

    dx = dx // dist
    dy = dy // dist

    # 射程距離
    max_range = spell_data.get("range", 10)

    # ビーム軌道上の全タイルにダメージ
    hit_count = 0
    total_dmg = 0

    for d in range(1, max_range + 1):
        tx = caster.x + dx * d
        ty = caster.y + dy * d

        if tx < 0 or tx >= MAP_WIDTH or ty < 0 or ty >= MAP_HEIGHT:
            break

        # この位置に敵がいるかチェック
        ent = None
        # 簡易実装: 対象がこの位置にいる場合のみダメージ
        if tx == target.x and ty == target.y:
            ent = target

        if ent:
            dmg = sum(random.randint(1, spell_data.get("dice_side", 6)) for _ in range(spell_data.get("dice_num", 1))) + spell_data.get("dmg_bonus", 0)
            dmg += int(caster.attributes.magic / 2) if hasattr(caster, "attributes") else 0

            element_enum = getattr(Element, spell_data.get("element", "magic").upper(), Element.MAGIC)
            final_dmg = CombatSystem.calc_element_damage(dmg, element_enum, 0)
            final_dmg = max(1, final_dmg)

            ent.hp -= final_dmg
            if ent.hp <= 0:
                ent.hp = 0
            hit_count += 1
            total_dmg += final_dmg

    # 対象に必ずヒットさせる (安全側)
    if total_dmg == 0:
        dmg = sum(random.randint(1, spell_data.get("dice_side", 6)) for _ in range(spell_data.get("dice_num", 1))) + spell_data.get("dmg_bonus", 0)
        dmg += int(caster.attributes.magic / 2) if hasattr(caster, "attributes") else 0

        element_enum = getattr(Element, spell_data.get("element", "magic").upper(), Element.MAGIC)
        final_dmg = CombatSystem.calc_element_damage(dmg, element_enum, 0)
        final_dmg = max(1, final_dmg)

        target.hp -= final_dmg
        if target.hp <= 0:
            target.hp = 0
        total_dmg = final_dmg
        hit_count = 1

    return True, f"{caster.name}の{spell_data.get('name', spell_id)}が{target.name}を貫いた！ ({total_dmg}ダメージ, {hit_count}ヒット)"


def _execute_area_spell(spell_id: str, spell_data: dict, caster: Entity, target: Entity, engine) -> tuple[bool, str]:
    """エリア呪文: 半径内AoE"""
    from constants import Element
    from core_framework import Point
    from engine.systems.combat_system import CombatSystem

    spell_name = spell_data.get("name", spell_id)
    radius = spell_data.get("radius", 1)
    dice_num = spell_data.get("dice_num", 1)
    dice_side = spell_data.get("dice_side", 6)
    dmg_bonus = spell_data.get("dmg_bonus", 0)
    element = spell_data.get("element", "magic")

    if not engine:
        return False, "Engineが必要"

    # 対象座標中心にAoE
    from constants import MAP_HEIGHT, MAP_WIDTH
    cx, cy = target.x, target.y

    hit_entities = []
    for entity in list(engine.entity_manager.get_living_entities()):
        if entity == caster:
            continue
        dist = max(abs(entity.x - cx), abs(entity.y - cy))
        if dist <= radius:
            hit_entities.append(entity)

    logs = []
    for entity in hit_entities:
        dmg = sum(random.randint(1, spell_data.get("dice_side", 6)) for _ in range(spell_data.get("dice_num", 1))) + spell_data.get("dmg_bonus", 0)
        dmg += int(caster.attributes.magic / 2) if hasattr(caster, "attributes") else 0

        element_enum = getattr(Element, spell_data.get("element", "magic").upper(), Element.MAGIC)
        res = getattr(entity, "resistances", None)
        res_val = res.get(element_enum) if res and hasattr(res, "get") else 0
        final_dmg = CombatSystem.calc_element_damage(dmg, element_enum, res_val)
        final_dmg = max(1, final_dmg)

        entity.hp -= final_dmg
        if entity.hp <= 0:
            entity.hp = 0
        logs.append(f"  -> {entity.name}に{final_dmg}ダメージ！")

    return True, f"{caster.name}の{spell_data.get('name', spell_id)}が爆発！" + ("".join(logs) if logs else " しかし誰も巻き込まれなかった")


def _execute_self_spell(spell_id: str, spell_data: dict, caster: Entity, engine=None) -> tuple[bool, str]:
    """セルフターゲット呪文 (回復/バフ/テレポート)"""
    import random
    spell_name = spell_data.get("name", spell_id)
    element = spell_data.get("element", "magic")

    if element == "heal":
        # 回復呪文
        dice_num = spell_data.get("dice_num", 2)
        dice_side = spell_data.get("dice_side", 8)
        dmg_bonus = spell_data.get("dmg_bonus", 0)
        heal = sum(random.randint(1, dice_side) for _ in range(dice_num)) + dmg_bonus
        caster.hp = min(caster.max_hp, caster.hp + heal)
        return True, f"{caster.name}の傷が癒えた！ (HP +{heal})"

    if spell_id == "teleport":
        # テレポート: 安全な場所へ移動 (現在地は除く)
        if not engine or not hasattr(engine, 'is_tile_free'):
            return False, "テレポートに失敗した"

        import random

        from constants import MAP_HEIGHT, MAP_WIDTH

        # 安全なタイルを探す (最大100回試行、現在地は除く)
        for _ in range(100):
            tx = random.randint(0, MAP_WIDTH - 1)
            ty = random.randint(0, MAP_HEIGHT - 1)

            # 現在地と同じならスキップ
            if tx == caster.x and ty == caster.y:
                continue

            if engine.is_tile_free(tx, ty):
                # 周囲に敵がいないかチェック
                safe = True
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        ent = engine.get_entity_at(tx + dx, ty + dy)
                        if ent and getattr(ent, 'faction', '') in ('monster', 'enemy', 'hostile'):
                            safe = False
                            break
                    if not safe:
                        break
                if safe:
                    caster.x, caster.y = tx, ty
                    return True, f"{caster.name}はテレポートで安全な場所へ移動した！"
        return False, "安全な場所が見つからない"

    if spell_id == "haste":
        # ヘイスト: 速度上昇バフ
        duration = spell_data.get("duration", 30)
        if not hasattr(caster, "status_effects"):
            caster.status_effects = []
        # 同ファイル内の StatusEffect クラスを使用
        caster.status_effects = [e for e in caster.status_effects if e.name != "Haste"]
        caster.status_effects.append(StatusEffect("Haste", duration * 10, power=2))
        caster.speed = int(caster.speed * 1.5)
        return True, f"{caster.name}の動きが加速した！ ({duration}ターン)"

    return False, f"未実装のセルフ呪文: {spell_id}"


# -------------------------------------------------------------
# 既存の CombatSystem ラッパー (後方互換)
# ============================================================

@dataclass
class StatusEffect:
    """状態異常 - Tick連動(ステップ16)"""

    name: str
    remaining_ticks: int  # 残り持続Tick
    power: int = 1  # 効果の強さ
    source: str | None = None


class ResistanceSet:
    """属性耐性セット (ステップ37)"""

    def __init__(self):
        self.fire = 0  # -100〜100, 0=通常, 100=無効, -50=弱点(1.5倍)
        self.cold = 0
        self.lightning = 0
        self.darkness = 0
        self.chaos = 0
        self.magic = 0

    def get(self, element: Element) -> int:
        mapping = {
            Element.FIRE: self.fire,
            Element.COLD: self.cold,
            Element.LIGHTNING: self.lightning,
            Element.DARKNESS: self.darkness,
            Element.CHAOS: self.chaos,
            Element.MAGIC: self.magic,
        }
        return mapping.get(element, 0)


class AggroList:
    """ヘイトリスト (ステップ42)"""

    def __init__(self):
        self._table: dict[str, int] = {}  # entity name -> hate_value

    def add_hate(self, target_name: str, amount: int) -> None:
        self._table[target_name] = self._table.get(target_name, 0) + amount

    def top_target(self) -> str | None:
        if not self._table:
            return None
        return max(self._table, key=lambda k: self._table[k])


# ==================== DELEGATED COMBAT SYSTEM (thin wrapper for backward compat) ====================
class CombatSystem:
    """Legacy CombatSystem - delegates to engine.systems.combat_system.CombatSystem.

    This is a backward-compatibility wrapper. New code should use
    engine.systems.combat_system.CombatSystem directly.
    """

    # Phase 2 Step 35: AP制アクションコスト
    AP_COST = {
        "attack": 1,      # 近接攻撃・射程攻撃
        "move": 1,        # 1マス移動
        "wait": 0,        # 待機（パス）— 世界を1tick進めるのみ
        "spell": 1,       # 呪文詠唱
        "item": 1,        # アイテム使用
        "skill": 1,       # スキル発動
    }

    @staticmethod
    def _get_new_combat():
        """Get the new CombatSystem class."""
        from engine.systems.combat_system import CombatSystem as NewCombatSystem
        return NewCombatSystem

    # Delegate all static methods to new implementation
    @staticmethod
    def aoe_radius(cx: int, cy: int, radius: int = 1):
        return CombatSystem._get_new_combat().aoe_radius(cx, cy, radius)

    @staticmethod
    def aoe_beam(sx: int, sy: int, direction: tuple[int, int], length: int = 5):
        return CombatSystem._get_new_combat().aoe_beam(sx, sy, direction, length)

    @staticmethod
    def aoe_nova(cx: int, cy: int):
        return CombatSystem._get_new_combat().aoe_nova(cx, cy)

    @staticmethod
    def publish_damage_event(event_bus, damage: int, x: int, y: int, is_crit: bool = False, is_kill: bool = False):
        return CombatSystem._get_new_combat().publish_damage_event(event_bus, damage, x, y, is_crit, is_kill)

    @staticmethod
    def publish_kill_event(event_bus, x: int, y: int):
        return CombatSystem._get_new_combat().publish_kill_event(event_bus, x, y)

    @staticmethod
    def publish_trap_event(event_bus, damage: int, x: int, y: int):
        return CombatSystem._get_new_combat().publish_trap_event(event_bus, damage, x, y)

    @staticmethod
    def calc_element_damage(base_dmg: int, element: Element, resistance: int):
        return CombatSystem._get_new_combat().calc_element_damage(base_dmg, element, resistance)

    @staticmethod
    def calc_spell_success(caster: Entity, spell_id: str):
        return CombatSystem._get_new_combat().calc_spell_success(caster, spell_id)

    @staticmethod
    def calculate_melee_attack(attacker: Entity, defender: Entity, weapon=None, element: Element = Element.PHYSICAL):
        return CombatSystem._get_new_combat().calculate_melee_attack(attacker, defender, weapon, element)

    @staticmethod
    def apply_aoe(caster: Entity, coords: list[tuple[int, int]], base_dmg_range: tuple[int, int], element: Element, entities: list[Entity], karma_ref: Any = None):
        return CombatSystem._get_new_combat().apply_aoe(caster, coords, base_dmg_range, element, entities, karma_ref)

    @staticmethod
    def process_status_effects(entity: Entity):
        return CombatSystem._get_new_combat().process_status_effects(entity)

    @staticmethod
    def cast_spell(caster: Entity, spell_name: str, target: Entity):
        return CombatSystem._get_new_combat().cast_spell(caster, spell_name, target)

    @staticmethod
    def is_exclusive_skill(skill_id: str):
        return CombatSystem._get_new_combat().is_exclusive_skill(skill_id)

    @staticmethod
    def get_exclusive_skill_data(skill_id: str):
        return CombatSystem._get_new_combat().get_exclusive_skill_data(skill_id)

    @staticmethod
    def execute_exclusive_skill(caster: Entity, skill_id: str, target: Entity):
        return CombatSystem._get_new_combat().execute_exclusive_skill(caster, skill_id, target)

    # TODO: Reincarnation scaling


# ==================== AP制 行動解決 (Phase 2 Step 35) ====================

def resolve_action(actor: Entity, action_type: str, engine=None, **kwargs) -> tuple[bool, str]:
    """
    AP制による行動解決の統一エントリポイント。

    Args:
        actor: 行動主体
        action_type: "attack" | "move" | "wait" | "spell" | "item" | "skill"
        engine: Engineインスタンス（世界進行用）
        **kwargs: 各アクション固有の引数

    Returns:
        (成功可否, ログメッセージ)
    """
    cost = CombatSystem.AP_COST.get(action_type, 1)

    # APチェック
    if not actor.can_act(cost):
        return False, f"AP不足 ({actor.ap}/{cost})"

    # AP消費
    actor.spend_ap(cost)

    # アクション別実行
    if action_type == "attack":
        return _resolve_attack(actor, engine, **kwargs)
    elif action_type == "move":
        return _resolve_move(actor, engine, **kwargs)
    elif action_type == "wait":
        return _resolve_wait(actor, engine, **kwargs)
    elif action_type == "spell":
        return _resolve_spell(actor, engine, **kwargs)
    elif action_type == "item":
        return _resolve_item(actor, engine, **kwargs)
    elif action_type == "skill":
        return _resolve_skill(actor, engine, **kwargs)

    return False, f"不明なアクション: {action_type}"


def _resolve_attack(actor: Entity, engine, target: Entity = None, **kwargs) -> tuple[bool, str]:
    """近接攻撃解決"""
    if target is None:
        return False, "攻撃対象が指定されていない"

    # 既存の calculate_melee_attack を使用
    from engine.systems.combat_system import CombatSystem as NewCombatSystem
    dmg, is_crit, msg = NewCombatSystem.calculate_melee_attack(actor, target)
    if dmg > 0:
        target.hp -= dmg
        if target.hp <= 0:
            target.hp = 0
    return True, msg


def _resolve_move(actor: Entity, engine, dx: int = 0, dy: int = 0, **kwargs) -> tuple[bool, str]:
    """移動解決"""
    if engine is None:
        return False, "エンジンが必要"

    nx, ny = actor.x + dx, actor.y + dy
    if engine.is_tile_free(nx, ny):
        actor.x, actor.y = nx, ny
        return True, f"{actor.name}は({dx},{dy})へ移動した"
    return False, "その方向には進めない"


def _resolve_wait(actor: Entity, engine, **kwargs) -> tuple[bool, str]:
    """待機解決 — 世界を1tick進める唯一の経路"""
    if engine is None:
        return False, "エンジンが必要"

    # advance_world() を呼んで世界を進行
    engine.advance_world()
    return True, f"{actor.name}は待機した"


def _resolve_spell(actor: Entity, engine, spell_id: str = None, target: Entity = None, **kwargs) -> tuple[bool, str]:
    """呪文詠唱解決"""
    if spell_id is None:
        return False, "呪文IDが指定されていない"

    from engine.systems.combat_system import CombatSystem as NewCombatSystem
    success, backlash = NewCombatSystem.calc_spell_success(actor, spell_id)
    if not success:
        actor.hp -= backlash
        return False, f"詠唱失敗！魔力暴走で{backlash}ダメージ"

    # 簡易実装: fireballのみ対応
    if spell_id == "fireball":
        if target is None:
            return False, "対象が必要"
        actor.mp -= 10
        dmg = random.randint(1, 6) + int(actor.attributes.magic / 2) + 10
        target.hp -= dmg
        return True, f"{actor.name}のファイアボール！{target.name}に{dmg}ダメージ！"

    return False, f"未実装呪文: {spell_id}"


def _resolve_item(actor: Entity, engine, item_id: str = None, **kwargs) -> tuple[bool, str]:
    """アイテム使用解決"""
    return False, "未実装: アイテム使用"


def _resolve_skill(actor: Entity, engine, skill_id: str = None, **kwargs) -> tuple[bool, str]:
    """スキル発動解決"""
    return False, "未実装: スキル発動"


# -------------------------------------------------------------
# aimed_tile ユーティリティ (Phase 2 Step 37) — B側実装
# -------------------------------------------------------------
def aimed_tile(origin: Entity, direction: tuple[int, int], distance: int, engine=None):
    """
    照準タイル計算: originからdirection方向へdistanceマス進んだ座標を返す。
    壁・視線判定込みで「最初に撃てる敵」を返す実装 (Step 37)。

    Args:
        origin: 射出元エンティティ
        direction: 8方向ベクトル (dx, dy) - 正規化済み前提
        distance: 最大射程距離
        engine: Engineインスタンス (視線・タイル判定用)

    Returns:
        Point: 命中した敵の座標、または射程末端の座標。壁で遮断ならNone。
    """
    from constants import MAP_HEIGHT, MAP_WIDTH
    from core_framework import Point

    dx, dy = direction

    # 方向が正規化されていない場合は正規化
    if dx != 0 and dy != 0:
        # 斜め方向は既に正規化されている想定
        pass

    for d in range(1, distance + 1):
        tx, ty = origin.x + dx * d, origin.y + dy * d

        # マップ範囲外チェック
        if tx < 0 or tx >= MAP_WIDTH or ty < 0 or ty >= MAP_HEIGHT:
            return None

        # 壁判定
        if engine and hasattr(engine, 'is_tile_free'):
            if not engine.is_tile_free(tx, ty):
                return None  # 壁で遮断

        # エンティティ判定
        if engine and hasattr(engine, 'get_entity_at'):
            ent = engine.get_entity_at(tx, ty)
            if ent and ent != origin and getattr(ent, 'hp', 0) > 0:
                # 敵対的なエンティティのみを対象とする
                if getattr(ent, 'faction', '') in ('monster', 'enemy', 'hostile'):
                    return Point(tx, ty)

    # 射程内に敵がいない場合は射程末端を返す
    end_x = origin.x + dx * distance
    end_y = origin.y + dy * distance

    # マップ範囲内なら末端を返す
    if 0 <= end_x < MAP_WIDTH and 0 <= end_y < MAP_HEIGHT:
        return Point(end_x, end_y)

    return None


def find_nearest_visible_target(origin: Entity, max_range: int, engine) -> "tuple[Entity, Point] | None":
    """
    8方向から視線が通る最寄りの敵を探索する。

    Returns:
        (target_entity, target_point) または None
    """
    directions = [
        (0, -1), (1, -1), (1, 0), (1, 1),
        (0, 1), (-1, 1), (-1, 0), (-1, -1)
    ]

    nearest_target = None
    nearest_point = None
    nearest_dist = max_range + 1

    for dx, dy in directions:
        result = aimed_tile(origin, (dx, dy), max_range, engine)
        if result:
            dist = max(abs(result.x - origin.x), abs(result.y - origin.y))
            if dist < nearest_dist:
                # その位置に敵がいるか確認
                ent = engine.get_entity_at(result.x, result.y)
                if ent and ent != origin and getattr(ent, 'hp', 0) > 0:
                    if getattr(ent, 'faction', '') in ('monster', 'enemy', 'hostile'):
                        nearest_target = ent
                        nearest_point = result
                        nearest_dist = dist

    if nearest_target:
        return (nearest_target, nearest_point)
    return None




class SurvivalSystem:
    """生存システム (ステップ33)"""

    def __init__(self):
        self.hunger = 8000  # Start with full hunger (8000)
        self.thirst = 0
        self.fatigue = 0
        self.karma = 0
        self.gold = 0
        self.platinum = 0
        self.fame = 0
        self.turns = 0

    def pass_turn(self, entity: Entity, engine=None) -> list[str]:
        """Process one turn of survival mechanics.

        Called each turn by advance_world. Handles:
        - Hunger decay (1 per turn)
        - Natural HP/MP regen (+1 every 10 turns if hunger > threshold and not bleeding)
        - Starvation damage (2 HP/turn when hunger <= 0)
        """
        logs = []
        self.turns += 1

        # Hunger decay
        self.hunger = max(0, self.hunger - 1)

        # Natural regen: +1 HP/MP every 10 turns (if conditions met)
        if engine and self.turns % 10 == 0:
            from constants import NATURAL_REGEN_HUNGER_THRESHOLD, NATURAL_REGEN_INTERVAL

            # Check bleeding status
            player_bleeding = any(
                getattr(e, "effect_type", getattr(e, "type", getattr(e, "name", ""))) == "bleeding"
                for e in entity.status_effects
            )

            if (
                self.hunger > NATURAL_REGEN_HUNGER_THRESHOLD
                and not player_bleeding
            ):
                if entity.hp < entity.max_hp:
                    entity.hp = min(entity.max_hp, entity.hp + 1)
                    logs.append(f"自然回復: HP +1 ({entity.hp}/{entity.max_hp})")
                if hasattr(entity, 'mp') and entity.mp < entity.max_mp:
                    entity.mp = min(entity.max_mp, entity.mp + 1)

        # Starvation damage when hunger reaches 0
        if self.hunger <= 0:
            entity.hp -= 2
            if entity.hp > 0:
                logs.append(f"飢餓ダメージ: HP -2 ({entity.hp}/{entity.max_hp})")
            elif entity.hp <= 0:
                logs.append("飢餓により力尽きた……")

        return logs

    def tick(self, entity: Entity) -> list[str]:
        """Alias for pass_turn for backward compatibility."""
        return self.pass_turn(entity)

    def eat(self, entity: Entity, food_value: int) -> str:
        """Consume food to restore hunger."""
        if isinstance(food_value, int):
            nutrition = food_value
        else:
            nutrition = getattr(food_value, 'nutrition', 0)

        self.hunger = min(10000, self.hunger + nutrition)
        return f"食べた: {getattr(food_value, 'name', '食料')} (空腹度 +{nutrition})"

    def drink(self, entity: Entity, water_value: int) -> str:
        """Consume water to restore thirst."""
        if isinstance(water_value, int):
            nutrition = water_value
        else:
            nutrition = getattr(water_value, 'nutrition', 0)

        self.thirst = max(0, self.thirst - nutrition)
        return f"飲んだ: {getattr(water_value, 'name', '水')} (渇き -{nutrition})"


@dataclass
class Quest:
    """クエストクラス (ステップ34)"""

    title: str
    target_monster: str
    target_count: int
    current_count: int = 0
    reward_gold: int = 200
    reward_platinum: int = 2
    completed: bool = False


# ==================== MonsterPreset (restored from original) ====================

class MonsterPreset:
    # Map monster names to Tiny Rogue tile IDs
    # FF6風スプライト (案2/案3) を優先し、未生成種はTiny Rogueへフォールバックする。
    # 正規ソースは naRou/monster_preset.py の MONSTER_TILE_MAP (同一内容を同期)。
    MONSTER_TILE_MAP = {
        "slime": "TR_MONSTER_01",
        "red_slime": "TR_MONSTER_01",
        "snail": "TR_MONSTER_02",
        "goblin": "FF6_GOBLIN",
        "kobold": "FF6_GOBLIN",
        "orc": "TR_MONSTER_03",
        "wolf": "FF6_WOLF",
        "hound_fire": "FF6_WOLF",
        "skeleton": "FF6_SKELETON",
        "bat": "FF6_BAT",
        "giant_bat": "FF6_BAT",
        "rogue_thief": "TR_MONSTER_VAR_02",
        "novice_wizard": "TR_MONSTER_VAR_03",
        "minotaur": "TR_MONSTER_VAR_01",
        "lich": "TR_MONSTER_VAR_02",
        "dragon_red": "TR_MONSTER_VAR_03",
        # 案3: 大型ボス (64x64)
        "void_boss": "FF6_BOSS",
    }

    # Map pet types to Tiny Rogue tile IDs so pets render with real art
    # instead of the generic placeholder. Falls back to "PET" when unknown.
    PET_TILE_MAP = {
        "puppy": "TR_MONSTER_VAR_01",
        "hound": "TR_MONSTER_VAR_01",
        "hound_fire": "TR_MONSTER_VAR_01",
        "guard_dog": "TR_MONSTER_VAR_01",
        "magic_hound": "TR_MONSTER_VAR_01",
        "wolf": "TR_MONSTER_VAR_01",
        "panther": "TR_MONSTER_VAR_02",
        "cat": "TR_MONSTER_VAR_02",
        "tiger": "TR_MONSTER_VAR_02",
        "slime": "TR_MONSTER_01",
        "dragon": "TR_MONSTER_VAR_03",
        "dragon_red": "TR_MONSTER_VAR_03",
    }

    @staticmethod
    def create(name: str, x: int, y: int) -> Entity:
        from config_manager import DataCache
        from ecs.entity import Attributes, Entity

        m_data = DataCache.get_data("data/monsters.yaml")
        if m_data and name in m_data:
            entry = m_data[name]
            attr_dict = entry.get("attributes", {})
            attr = Attributes(
                strength=attr_dict.get("strength", 10),
                endurance=attr_dict.get("endurance", 10),
                dexterity=attr_dict.get("dexterity", 10),
                perception=attr_dict.get("perception", 10),
                learning=attr_dict.get("learning", 10),
                will=attr_dict.get("will", 10),
                magic=attr_dict.get("magic", 10),
                charisma=attr_dict.get("charisma", 10),
            )
            e = Entity(
                x=x,
                y=y,
                char=entry.get("char", "👾"),
                color=tuple(entry.get("color", [255, 255, 255])),
                name=entry.get("name", name),
                speed=entry.get("speed", 70),
                attributes=attr,
            )
            e.max_hp = entry.get("max_hp", 20)
            e.hp = e.max_hp
            e.faction = FACTION_MONSTER
            e.aggro = AggroList()
            e.resistances = ResistanceSet()
            e.status_effects = []
            # Store monster type for tile rendering
            e.monster_type = name
            return e

        # フォールバック
        presets = {
            "slime": (
                "ぷち",
                "🍮",
                (100, 255, 100),
                50,
                Attributes(strength=5, endurance=6, dexterity=6),
            ),
            "goblin": (
                "ゴブリン",
                "👺",
                (200, 100, 50),
                70,
                Attributes(strength=8, endurance=8, dexterity=8),
            ),
            "orc": (
                "オーク",
                "👹",
                (150, 150, 50),
                65,
                Attributes(strength=14, endurance=12, dexterity=6),
            ),
        }
        if name not in presets:
            return Entity(x, y, "👾", (255, 255, 255), "モンスター")
        n, c, col, spd, attr = presets[name]
        e = Entity(x, y, c, col, n, speed=spd, attributes=attr)
        hp_map = {"slime": 14, "goblin": 24, "orc": 42}
        e.max_hp = hp_map.get(name, 20)
        e.hp = e.max_hp
        e.faction = FACTION_MONSTER
        e.aggro = AggroList()
        e.resistances = ResistanceSet()
        e.status_effects = []
        e.monster_type = name
        return e


# --- LocalizationManager integration (i18n, Step 3.x) ---
from localization_manager import localize  # noqa: E402,F401

logger = logging.getLogger(__name__)
