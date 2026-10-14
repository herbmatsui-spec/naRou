"""
Elona Masterpiece Edition - Advanced AI System (Behavior Trees & Tactical Archetypes)
Implements rich AI decision-making for monsters, pets, and neutral NPCs.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from constants import ENERGY_THRESHOLD, HIT_RATE_BASE, Element
from core_framework import AStar, BaseSystem, Point
from systems import (
    STATUS_BLEEDING,
    STATUS_PARALYSIS,
    STATUS_POISON,
    CombatSystem,
    StatusEffect,
)

if TYPE_CHECKING:
    from ecs.entity import Entity
    from game import Engine


# ==================== Facing Direction Helpers ====================

DIRS8 = [
    (0, -1),  # N
    (0, 1),   # S
    (1, 0),   # E
    (-1, 0),  # W
    (1, -1),  # NE
    (-1, 1),  # SW
    (1, 1),   # SE
    (-1, -1), # NW
]

DIR_TO_FACING = {
    (0, -1): "N",
    (0, 1): "S",
    (1, 0): "E",
    (-1, 0): "W",
    (1, -1): "N",
    (-1, 1): "S",
    (1, 1): "S",
    (-1, -1): "N",
}


def set_facing_toward(actor: Entity, target_x: int, target_y: int) -> None:
    """Update actor's facing direction toward target coordinates."""
    dx = target_x - actor.x
    dy = target_y - actor.y
    # Normalize to 8-direction
    if dx != 0:
        dx = 1 if dx > 0 else -1
    if dy != 0:
        dy = 1 if dy > 0 else -1
    facing = DIR_TO_FACING.get((dx, dy), "S")
    actor.facing = facing


def set_facing_from_move(actor: Entity, old_x: int, old_y: int) -> None:
    """Update actor's facing direction based on movement delta."""
    dx = actor.x - old_x
    dy = actor.y - old_y
    if dx != 0:
        dx = 1 if dx > 0 else -1
    if dy != 0:
        dy = 1 if dy > 0 else -1
    facing = DIR_TO_FACING.get((dx, dy), "S")
    actor.facing = facing


def _cheb(ax: int, ay: int, bx: int, by: int) -> int:
    return max(abs(ax - bx), abs(ay - by))


# ペット戦術コマンド
TACTIC_BALANCED = "balanced"  # バランス (通常追従・迎撃)
TACTIC_AGGRESSIVE = "aggressive"  # 積極迎撃 (視界内の敵を索敵・撃滅)
TACTIC_DEFENSIVE = "defensive"  # 専守防衛 (主人の隣接2マス以内を維持)
TACTIC_SUPPORT = "support"  # 支援優先 (回復・バフ・遠隔)
TACTIC_PASSIVE = "passive"  # 不戦避難 (攻撃せず主人の後ろをキープ)


class BehaviorNode:
    """ビヘイビアツリー基底ノード"""

    def execute(self, actor: Entity, engine: Engine) -> bool:
        raise NotImplementedError


class SelectorNode(BehaviorNode):
    """いずれかの子供ノードが成功したら成功を返す (OR)"""

    def __init__(self, children: list[BehaviorNode]):
        self.children = children

    def execute(self, actor: Entity, engine: Engine) -> bool:
        for child in self.children:
            if child.execute(actor, engine):
                return True
        return False


class SequenceNode(BehaviorNode):
    """全ての子供ノードが成功した場合のみ成功を返す (AND)"""

    def __init__(self, children: list[BehaviorNode]):
        self.children = children

    def execute(self, actor: Entity, engine: Engine) -> bool:
        for child in self.children:
            if not child.execute(actor, engine):
                return False
        return True


# ==================== モンスター固有能力 ====================
# `data/monsters.yaml` の `skills` が宣言する、モンスターごとの固有行動。
# 効果量 (formula / element) はスキーマ変換で落ちるため、実行仕様はここに持つ。

# 能力の種別
ABILITY_ATTACK = "attack"  # 命中判定つきの打撃 (近接/远程/属性)
ABILITY_HEAL = "heal"  # 自身の回復
ABILITY_STEAL_GOLD = "steal_gold"  # 開場から金を奪う
ABILITY_DRAIN_MP = "drain_mp"  # 相手の魔力を吸い上げる
ABILITY_SUMMON = "summon"  # 周囲に屍体を出す
ABILITY_ROAR = "roar"  # 己の防御を上げる戦吼
ABILITY_INTIMIDATE = "intimidate"  # 相手ひるがせ、動きを止める威嚇

# 己の癒し: heal_self の formula `int * 1.4 + 15`
HEAL_MAGIC_RATIO = 1.4
HEAL_FLAT_BONUS = 15
# 金の窃盗: steal_gold の formula `*0.35`
STEAL_GOLD_RATIO = 0.35
# 魔力吸引: drain_mp の formula (敵 mp -40 / 己 mp +25)
DRAIN_MP_TAKEN = 40
DRAIN_MP_GAINED = 25
# 戦吼: roar の formula (defense +3)
ROAR_DEFENSE_BONUS = 3
# 一時強化の持続ターン
BUFF_DURATION = 6
# 威嚇の持続。CombatSystem.process_status_effects は1tick あたり 10 減らす
INTIMIDATE_TICKS = 10
# 召喚は周囲に屍体が揃うまで繰り返さない (データ側の count: 2 相当)
SUMMON_MINION_CAP = 2
SUMMON_MINION_REACH = 2
SUMMON_MINION_MAX_HP = 18
SUMMON_MINION_NAME = "亡骸"
# 状態異常の持続 (data/worlds/skill_eater/skills.yaml の duration: 3)
STATUS_DURATION = 3
# 投射系の能力は最低でもこの距離から放つ。隣接時は間合いを取る/殴る方に任せる。
# `CastSpellAction` の射程下限と同じ規矩。
ABILITY_MIN_RANGED_REACH = 2
# 魔力吸引は索敵範囲 (= ChaseAction の視界) まで届く。近い相手は追いかけ
# られるので射程内の魔力吸引は成立しにくい。遠方の相手だけが使える。
DRAIN_MP_REACH = 8


@dataclass(frozen=True)
class AbilitySpec:
    """モンスター固有能力の実行仕様

    reach は「対象が必要になる距離」。0 なら対象は不要 (自身技・召喚) 。
    reach > 1 の投射系は ABILITY_MIN_RANGED_REACH 以上、reach 以下でだけ成立する。
    power は近接攻撃の基準ダメージに乗せる倍率。属性耐性の軽減は
    `CombatSystem.calc_element_damage` に委ねるので、power を先に掛ける。
    """

    kind: str
    reach: int
    element: Element = Element.PHYSICAL
    power: float = 1.0
    status: tuple[str, int] | None = None  # (状態異常名, 付与確率 %)


ABILITY_REGISTRY: dict[str, AbilitySpec] = {
    # --- 物理打撃 ---
    "throw_stone": AbilitySpec(ABILITY_ATTACK, reach=5, power=1.0),
    "power_bash": AbilitySpec(ABILITY_ATTACK, reach=1, power=1.3),
    "backstab": AbilitySpec(ABILITY_ATTACK, reach=1, power=1.5),
    "heavy_cleave": AbilitySpec(
        ABILITY_ATTACK, reach=1, power=1.6, status=(STATUS_BLEEDING, 40)
    ),
    "tail_swipe": AbilitySpec(ABILITY_ATTACK, reach=1, power=1.3),
    # --- 远程/属性 ---
    "cast_dart": AbilitySpec(
        ABILITY_ATTACK, reach=5, element=Element.MAGIC, power=1.2, status=(STATUS_POISON, 35)
    ),
    "fire_breath": AbilitySpec(ABILITY_ATTACK, reach=4, element=Element.FIRE, power=1.5),
    "cast_fireball": AbilitySpec(ABILITY_ATTACK, reach=6, element=Element.FIRE, power=1.8),
    "inferno_breath": AbilitySpec(ABILITY_ATTACK, reach=6, element=Element.FIRE, power=2.2),
    # --- 自身/対象操作 ---
    "heal_self": AbilitySpec(ABILITY_HEAL, reach=0),
    "steal_gold": AbilitySpec(ABILITY_STEAL_GOLD, reach=5),
    "drain_mp": AbilitySpec(ABILITY_DRAIN_MP, reach=DRAIN_MP_REACH),
    "summon_undead": AbilitySpec(ABILITY_SUMMON, reach=0),
    "roar": AbilitySpec(ABILITY_ROAR, reach=0),
    "intimidate": AbilitySpec(ABILITY_INTIMIDATE, reach=0),
}

# 属性別のメッセージ色 (プレイヤーが何が来たか即座に分かるように)
_ELEMENT_COLORS: dict[Element, tuple[int, int, int]] = {
    Element.FIRE: (255, 140, 60),
    Element.MAGIC: (200, 100, 255),
    Element.POISON: (140, 220, 90),
    Element.PHYSICAL: (220, 220, 220),
}


# ==================== ACTIONS ====================


class HealSelfAction(BehaviorNode):
    """HP低下時の自己治癒アクション"""

    def __init__(self, threshold_ratio: float = 0.35):
        self.threshold = threshold_ratio

    def execute(self, actor: Entity, engine: Engine) -> bool:
        if actor.hp > actor.max_hp * self.threshold:
            return False
        # 治癒ポーション所持または治癒魔法
        heal_val = int(actor.max_hp * 0.4)
        actor.hp = min(actor.max_hp, actor.hp + heal_val)
        if not actor.spend_ap(1):
            return False
        engine.log(
            f"{actor.name} は傷口を手当てし、体力を回復した！ (+{heal_val} HP)",
            (100, 255, 150),
        )
        return True


class FleeAction(BehaviorNode):
    """脅威からの逃走アクション"""

    def execute(self, actor: Entity, engine: Engine) -> bool:
        player = engine.player
        dist = Point(actor.x, actor.y).chebyshev_distance(Point(player.x, player.y))
        if dist > 8:
            return False  # すでに十分離れている

        best_move = None
        max_dist = dist

        for dx, dy in [
            (0, 1),
            (0, -1),
            (1, 0),
            (-1, 0),
            (1, 1),
            (-1, -1),
            (1, -1),
            (-1, 1),
        ]:
            nx, ny = actor.x + dx, actor.y + dy
            if engine.is_tile_free(nx, ny):
                d = Point(nx, ny).chebyshev_distance(Point(player.x, player.y))
                if d > max_dist:
                    max_dist = d
                    best_move = (nx, ny)

        if best_move:
            old_x, old_y = actor.x, actor.y
            actor.x, actor.y = best_move
            set_facing_from_move(actor, old_x, old_y)
            if not actor.spend_ap(1):
                return False
            return True
        return False


class MeleeAttackAction(BehaviorNode):
    """隣接敵への近接攻撃アクション"""

    def execute(self, actor: Entity, engine: Engine) -> bool:
        target = self._find_adjacent_enemy(actor, engine)
        if not target:
            return False

        from sound_manager import SoundManager
        from systems import CombatSystem
        from ui_fx_systems import FloatingText

        # Face the target before attacking
        set_facing_toward(actor, target.x, target.y)

        dmg, is_crit, msg = CombatSystem.calculate_melee_attack(actor, target, None)
        target.hp -= dmg

        # Publish damage event for FX (blood splatter, etc.)
        CombatSystem.publish_damage_event(
            engine.event_bus, dmg, target.x, target.y, is_crit, target.hp <= 0
        )

        engine.log(msg, (255, 120, 120) if target == engine.player else (220, 220, 220))
        SoundManager.play_se("hit")

        # 浮動ダメージ表示
        if hasattr(engine, "floating_texts"):
            engine.floating_texts.append(
                FloatingText(f"-{dmg}", target.x, target.y - 0.2, (255, 80, 80))
            )

        if target.hp <= 0:
            if target == engine.player:
                engine._on_player_death()
            elif target == engine.pet:
                engine.log(f"{target.name} は力尽きて倒れた！", (255, 100, 100))
            else:
                engine._on_kill(target)
                # Publish kill event for FX
                CombatSystem.publish_kill_event(engine.event_bus, target.x, target.y)

        if not actor.spend_ap(1):
            return False
        return True

    def _find_adjacent_enemy(self, actor: Entity, engine: Engine) -> Entity | None:
        for dx, dy in [
            (0, 1),
            (0, -1),
            (1, 0),
            (-1, 0),
            (1, 1),
            (-1, -1),
            (1, -1),
            (-1, 1),
        ]:
            ent = engine.get_entity_at(actor.x + dx, actor.y + dy)
            if (
                ent
                and ent.hp > 0
                and (
                    actor.faction == "monster"
                    and (ent.is_player or getattr(ent, "is_pet", False))
                    or getattr(actor, "is_pet", False)
                    and ent.faction == "monster"
                )
            ):
                return ent
        return None


class CastSpellAction(BehaviorNode):
    """遠隔呪文・スキル使用アクション"""

    def execute(self, actor: Entity, engine: Engine) -> bool:
        # キャスター系がターゲット視認時に魔矢/火炎球等を使用
        target = engine.player if actor.faction == "monster" else None
        if not target or target.hp <= 0:
            return False

        dist = Point(actor.x, actor.y).chebyshev_distance(Point(target.x, target.y))
        if 2 <= dist <= 5 and engine.has_los(Point(actor.x, actor.y), Point(target.x, target.y)):
            if random.random() < 0.40:
                # Face the target before casting
                set_facing_toward(actor, target.x, target.y)

                # Step 50.1: 敵の呪文ダメージも DifficultyManager を通す (プレイヤーと同一補正)
                from core.difficulty import DifficultyManager

                dmg = random.randint(8, 16)
                if target.is_player:
                    dmg = int(DifficultyManager().player_damage_taken(dmg))
                target.hp -= dmg
                engine.log(
                    f"⚡ {actor.name} は魔力の矢を放った！ ({target.name} に {dmg} ダメージ)",
                    (200, 100, 255),
                )
                if hasattr(engine, "floating_texts"):
                    from ui_fx_systems import FloatingText

                    engine.floating_texts.append(
                        FloatingText(f"-{dmg}", target.x, target.y - 0.2, (200, 100, 255))
                    )
                if target == engine.player and target.hp <= 0:
                    engine._on_player_death()
                if not actor.spend_ap(1):
                    return False
                return True
        return False


def declared_ability_ids(actor) -> tuple[str, ...]:
    """`data/monsters.yaml` の abilities 宣言を、並び順どおりに返す。

    `Entity.abilities` は配列で、各要素は MonsterAbility オブジェクト。
    """
    abilities = getattr(actor, "abilities", None)
    if abilities is None:
        return ()
    return tuple(getattr(a, "id", str(a)) for a in abilities)


def ability_display_name(engine: Engine, skill_id: str) -> str:
    """宣言能力の本番表示名。ログは本番データに揃える。"""
    kernel = getattr(engine, "kernel", None)
    if kernel is None or not kernel.has_system("data_manager"):
        return skill_id
    definition = kernel.get_system("data_manager").monster_abilities.get(skill_id)
    return definition.name if definition is not None else skill_id


def _ability_target(actor: Entity, engine: Engine):
    """能力の相手になる実体 (生きたプレイヤー。無ければ None)"""
    target = engine.player
    if target is None or target.hp <= 0:
        return None
    if not _has_los(engine, actor, target):
        return None
    return target


def _minions_in_reach(actor: Entity, engine: Engine) -> int:
    """召喚先の周囲に既に並んでいる味方数。"""
    count = 0
    for e in getattr(engine, "entities", []):
        if e is actor or getattr(e, "is_player", False) or getattr(e, "is_pet", False):
            continue
        if _cheb(actor.x, actor.y, e.x, e.y) <= SUMMON_MINION_REACH:
            count += 1
    return count


def usable_ability(actor: Entity, engine: Engine) -> tuple[str, AbilitySpec] | None:
    """このターンに出せる宣言能力の (id, 仕様) を返す。乱数は一切引かない。

    `enemy_intent` も同じ関数で意図を予測するため、副作用を持たない。
    宣言順に最初の成立だけを返す (=data/monsters.yaml の並びが優先順)。
    """
    player = engine.player
    if player is None or player.hp <= 0:
        return None
    dist = _cheb(actor.x, actor.y, player.x, player.y)

    for skill_id in declared_ability_ids(actor):
        spec = ABILITY_REGISTRY.get(skill_id)
        if spec is None:
            continue
        if spec.kind == ABILITY_HEAL:
            if actor.hp < actor.max_hp:
                return skill_id, spec
            continue
        if spec.kind == ABILITY_ROAR:
            return skill_id, spec
        if spec.kind == ABILITY_SUMMON:
            if _minions_in_reach(actor, engine) < SUMMON_MINION_CAP:
                return skill_id, spec
            continue
        if spec.kind == ABILITY_INTIMIDATE:
            if _ability_target(actor, engine) is not None:
                return skill_id, spec
            continue
        # 対象が必要な攻撃・窃盗・吸引: 射程内で視認できること
        if spec.reach > 1 and dist < ABILITY_MIN_RANGED_REACH:
            continue
        if dist > spec.reach:
            continue
        target = _ability_target(actor, engine)
        if target is None:
            continue
        if spec.kind == ABILITY_STEAL_GOLD and target.gold <= 0:
            continue
        if spec.kind == ABILITY_DRAIN_MP and target.mp <= 0:
            continue
        return skill_id, spec
    return None


class AbilityAction(BehaviorNode):
    """宣言された固有能力を実行する (=data/monsters.yaml の skills を持つ個体だけ働く)

    空振りしても 1 ターンは消費し、技名入りで必ずログに残す。
    黙って 1 ターン溶けるより、プレイヤーは何を撃たれたか知るほうがよい。
    """

    def execute(self, actor: Entity, engine: Engine) -> bool:
        chosen = usable_ability(actor, engine)
        if chosen is None:
            return False
        skill_id, spec = chosen
        name = ability_display_name(engine, skill_id)
        handler = {
            ABILITY_ATTACK: self._attack,
            ABILITY_HEAL: self._heal,
            ABILITY_STEAL_GOLD: self._steal,
            ABILITY_DRAIN_MP: self._drain,
            ABILITY_SUMMON: self._summon,
            ABILITY_ROAR: self._roar,
            ABILITY_INTIMIDATE: self._intimidate,
        }[spec.kind]
        handler(actor, engine, skill_id, spec, name)
        # AP制 (Phase 2) + 旧エネルギー制の二重消費 (移行期間: legacy_bump 相当)。
        # energy はターンスケジューラ (entity_system) が参照するため、AP と並行して減らす。
        if not actor.spend_ap(1):
            return False
        actor.energy -= ENERGY_THRESHOLD
        return True

    # --- 種別ごとの実処理 ---

    def _attack(
        self, actor: Entity, engine: Engine, skill_id: str, spec: AbilitySpec, name: str
    ) -> None:
        target = _ability_target(actor, engine)
        if target is None:
            return
        hit_rate = _ability_hit_rate(actor, target)
        if random.random() * 100 >= hit_rate:
            engine.log(
                f"{actor.name} は【{name}】を放ったが {target.name} に外された！",
                _ELEMENT_COLORS[spec.element],
            )
            return

        base = random.randint(1, 4) + int(actor.attributes.strength / 3)
        resistance = 0
        res_set = getattr(target, "resistances", None)
        if res_set is not None:
            resistance = res_set.get(spec.element)
        dmg = CombatSystem.calc_element_damage(int(base * spec.power), spec.element, resistance)
        dmg = max(1, dmg - random.randint(0, max(1, int(target.attributes.endurance / 4))))
        target.hp -= dmg

        engine.log(
            f"{actor.name} は【{name}】を放った！ ({target.name} に {dmg} ダメージ)",
            _ELEMENT_COLORS[spec.element],
        )
        if spec.status is not None and random.random() * 100 < spec.status[1]:
            _apply_status(target, spec.status[0], STATUS_DURATION)
        if target.hp <= 0:
            self._on_target_death(actor, engine, target)

    def _heal(
        self, actor: Entity, engine: Engine, skill_id: str, spec: AbilitySpec, name: str
    ) -> None:
        # heal_self の formula `int * 1.4 + 15`。int は engine/engine.py の橋渡し
        # (intelligence=attributes.perception) と同じ読み方をする。
        healed = int(actor.attributes.perception * HEAL_MAGIC_RATIO) + HEAL_FLAT_BONUS
        before = actor.hp
        actor.hp = min(actor.max_hp, actor.hp + healed)
        engine.log(
            f"{actor.name} は【{name}】で自身を癒した！ (+{actor.hp - before} HP)",
            (100, 255, 150),
        )

    def _steal(
        self, actor: Entity, engine: Engine, skill_id: str, spec: AbilitySpec, name: str
    ) -> None:
        target = _ability_target(actor, engine)
        if target is None:
            return
        stolen = int(target.gold * STEAL_GOLD_RATIO)
        target.gold -= stolen
        actor.gold += stolen
        engine.log(
            f"{actor.name} は【{name}】で {target.name} から金 {stolen} を詐取した！",
            (255, 215, 0),
        )

    def _drain(
        self, actor: Entity, engine: Engine, skill_id: str, spec: AbilitySpec, name: str
    ) -> None:
        target = _ability_target(actor, engine)
        if target is None:
            return
        taken = min(DRAIN_MP_TAKEN, target.mp)
        target.mp -= taken
        actor.mp += DRAIN_MP_GAINED
        engine.log(
            f"{actor.name} は【{name}】で {target.name} の魔力を {taken} 吸い上げた！",
            (200, 100, 255),
        )

    def _summon(
        self, actor: Entity, engine: Engine, skill_id: str, spec: AbilitySpec, name: str
    ) -> None:
        from constants import AI_ROLE_BRUTE
        from ecs.entity import Entity

        free = _free_neighbors(engine, actor)
        if not free:
            engine.log(f"{actor.name} は【{name}】を唱えたが 出す場所がない！", (160, 80, 255))
            return
        nx, ny = min(free, key=lambda t: _cheb(t[0], t[1], actor.x, actor.y))
        minion = Entity(
            x=nx,
            y=ny,
            char="💀",
            color=(160, 80, 255),
            name=SUMMON_MINION_NAME,
            is_player=False,
            is_pet=False,
        )
        minion.faction = "monster"
        minion.ai_type = "aggressive"
        minion.ai_role = AI_ROLE_BRUTE
        minion.max_hp = SUMMON_MINION_MAX_HP
        minion.hp = SUMMON_MINION_MAX_HP
        minion.status_effects = []
        engine.entity_manager.add_entity(minion)
        engine.log(
            f"{actor.name} は【{name}】を唱え、{SUMMON_MINION_NAME}を {nx},{ny} に召喚した！",
            (160, 80, 255),
        )

    def _roar(
        self, actor: Entity, engine: Engine, skill_id: str, spec: AbilitySpec, name: str
    ) -> None:
        actor.endurance += ROAR_DEFENSE_BONUS
        engine.log(
            f"{actor.name} は【{name}】を叫んだ！ (防御 +{ROAR_DEFENSE_BONUS})",
            (255, 165, 0),
        )

    def _intimidate(
        self, actor: Entity, engine: Engine, skill_id: str, spec: AbilitySpec, name: str
    ) -> None:
        target = _ability_target(actor, engine)
        if target is None:
            return
        _apply_status(target, STATUS_PARALYSIS, INTIMIDATE_TICKS)
        engine.log(
            f"{actor.name} は【{name}】で {target.name} をひるがせ、動きを封じた！",
            (200, 100, 255),
        )

    @staticmethod
    def _on_target_death(actor: Entity, engine: Engine, target: Entity) -> None:
        if target == engine.player:
            engine._on_player_death()
        elif target == engine.pet:
            engine.log(f"{target.name} は力尽きて倒れた！", (255, 100, 100))
        else:
            engine._on_kill(target)


def _ability_hit_rate(actor: Entity, target: Entity) -> int:
    """防御側の器用さを重みにした命中判定 (近接攻撃と同じ式)"""
    return max(
        10,
        min(95, HIT_RATE_BASE + actor.attributes.dexterity - target.attributes.dexterity),
    )


def _apply_status(target: Entity, status: str, duration: int) -> None:
    if any(s.name == status for s in target.status_effects):
        return
    target.status_effects.append(StatusEffect(status, duration))


class ChaseAction(BehaviorNode):
    """A*による目標追従アクション"""

    def execute(self, actor: Entity, engine: Engine) -> bool:
        target = self._find_target(actor, engine)
        if not target:
            return False

        path = AStar.find_path(
            Point(actor.x, actor.y),
            Point(target.x, target.y),
            engine.game_map,
            engine.get_blocked_positions(),
        )

        if path and len(path) > 1:
            next_pt = path[1]
            if engine.is_tile_free(next_pt.x, next_pt.y):
                old_x, old_y = actor.x, actor.y
                actor.x, actor.y = next_pt.x, next_pt.y
                set_facing_from_move(actor, old_x, old_y)
                if not actor.spend_ap(1):
                    return False
                return True
        return False

    def _find_target(self, actor: Entity, engine: Engine) -> Entity | None:
        if actor.faction == "monster":
            # 視界内のプレイヤーまたはペット
            dist_p = Point(actor.x, actor.y).chebyshev_distance(
                Point(engine.player.x, engine.player.y)
            )
            if dist_p <= 8 and engine.has_los(
                Point(actor.x, actor.y), Point(engine.player.x, engine.player.y)
            ):
                return engine.player
        elif getattr(actor, "is_pet", False):
            # 視界内の最寄りのモンスター
            closest_mob = None
            min_d = 999
            for e in engine.entities:
                if getattr(e, "faction", "monster") == "monster" and getattr(e, "hp", 1) > 0:
                    d = Point(actor.x, actor.y).chebyshev_distance(Point(e.x, e.y))
                    if (
                        d < min_d
                        and d <= 8
                        and engine.has_los(Point(actor.x, actor.y), Point(e.x, e.y))
                    ):
                        min_d = d
                        closest_mob = e
            return closest_mob
        return None


class PetFollowAction(BehaviorNode):
    """ペットの主人追従・陣形維持アクション"""

    def execute(self, actor: Entity, engine: Engine) -> bool:
        p = engine.player
        dist = Point(actor.x, actor.y).chebyshev_distance(Point(p.x, p.y))
        if dist <= 1:
            # すでに隣接
            if not actor.spend_ap(1):
                return False
            return True

        path = AStar.find_path(
            Point(actor.x, actor.y),
            Point(p.x, p.y),
            engine.game_map,
            engine.get_blocked_positions(),
        )
        if path and len(path) > 1:
            next_pt = path[1]
            if engine.is_tile_free(next_pt.x, next_pt.y):
                old_x, old_y = actor.x, actor.y
                actor.x, actor.y = next_pt.x, next_pt.y
                set_facing_from_move(actor, old_x, old_y)
                if not actor.spend_ap(1):
                    return False
                return True
        return False


class WanderAction(BehaviorNode):
    """周囲のランダム移動"""

    def execute(self, actor: Entity, engine: Engine) -> bool:
        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])
        nx, ny = actor.x + dx, actor.y + dy
        if engine.is_tile_free(nx, ny):
            old_x, old_y = actor.x, actor.y
            actor.x, actor.y = nx, ny
            if dx != 0 or dy != 0:
                set_facing_from_move(actor, old_x, old_y)
        if not actor.spend_ap(1):
            return False
        return True


# ==================== ADVANCED AI CONTROLLER ====================


# ==================== 提案4: 陣形・連携タクティクス用ヘルパ ====================


def _entity_at_tile(engine, x: int, y: int):
    fn = getattr(engine, "get_entity_at", None)
    if fn is None:
        return None
    return fn(x, y)


def _has_los(engine, a, b) -> bool:
    fn = getattr(engine, "has_los", None)
    if fn is None:
        return True
    from core_framework import Point

    return bool(fn(Point(a.x, a.y), Point(b.x, b.y)))


def _is_ranged_role(actor) -> bool:
    from constants import AI_ROLE_KITER, AI_ROLE_SUPPORT

    if actor.ai_role in (AI_ROLE_KITER, AI_ROLE_SUPPORT):
        return True
    return getattr(actor, "ai_type", None) == "caster"


def _is_free(engine, x: int, y: int, actor) -> bool:
    free_fn = getattr(engine, "is_tile_free", None)
    if free_fn is None or not free_fn(x, y):
        return False
    occ = _entity_at_tile(engine, x, y)
    return occ is None or occ is actor


def _free_neighbors(engine, actor) -> list:
    out = []
    for dx, dy in DIRS8:
        nx, ny = actor.x + dx, actor.y + dy
        if _is_free(engine, nx, ny, actor):
            out.append((nx, ny))
    return out


def _is_monster_at(engine, x: int, y: int, actor) -> bool:
    e = _entity_at_tile(engine, x, y)
    return e is not None and e is not actor and getattr(e, "faction", None) == "monster"


def _ally_density(engine, x: int, y: int, actor) -> int:
    return sum(1 for dx, dy in DIRS8 if _is_monster_at(engine, x + dx, y + dy, actor))


# 深度スケーリング (提案4: ステップ55) — 既定は無効
DEPTH_SCALING_ENABLED = False


def kiter_range(actor, depth: int = 0) -> int:
    base = getattr(actor, "preferred_range", 1)
    if not DEPTH_SCALING_ENABLED:
        return base
    return min(8, base + depth // 5)


class SpreadAction(BehaviorNode):
    """味方(他モンスター)と重ならないよう間隔を空ける (提案4: 固まり防止)"""

    def execute(self, actor: Entity, engine: Engine) -> bool:
        neighbors = _free_neighbors(engine, actor)
        if not neighbors:
            return False
        crowded = any(_is_monster_at(engine, actor.x + dx, actor.y + dy, actor) for dx, dy in DIRS8)
        if not crowded:
            return False
        old_x, old_y = actor.x, actor.y
        best = min(neighbors, key=lambda t: _ally_density(engine, t[0], t[1], actor))
        actor.x, actor.y = best
        set_facing_from_move(actor, old_x, old_y)
        if not actor.spend_ap(1):
            return False
        return True


class KiteAction(BehaviorNode):
    """間合いを維持して遠隔する (提案4: kiter)"""

    def execute(self, actor: Entity, engine: Engine) -> bool:
        player = engine.player
        if player is None or player.hp <= 0:
            return False
        from constants import HARD_KITER_RANGE_BONUS

        pref = kiter_range(actor, getattr(engine, "dungeon_level", 0))
        if getattr(engine, "difficulty", "normal") == "hard":
            pref += HARD_KITER_RANGE_BONUS
        dist = _cheb(actor.x, actor.y, player.x, player.y)

        # 射程内なら撃ってその場維持
        if _is_ranged_role(actor) and 2 <= dist <= 5 and _has_los(engine, actor, player):
            # Face the target when casting
            set_facing_toward(actor, player.x, player.y)
            CastSpellAction().execute(actor, engine)
            return True

        if dist < pref:
            neighbors = _free_neighbors(engine, actor)
            if not neighbors:
                return False
            nx, ny = max(neighbors, key=lambda t: _cheb(t[0], t[1], player.x, player.y))
            old_x, old_y = actor.x, actor.y
            actor.x, actor.y = nx, ny
            set_facing_from_move(actor, old_x, old_y)
            if not actor.spend_ap(1):
                return False
            return True

        if dist > pref:
            neighbors = _free_neighbors(engine, actor)
            if not neighbors:
                return False
            cand = [t for t in neighbors if _cheb(t[0], t[1], player.x, player.y) >= pref - 1]
            if not cand:
                cand = neighbors
            nx, ny = min(cand, key=lambda t: _cheb(t[0], t[1], player.x, player.y))
            old_x, old_y = actor.x, actor.y
            actor.x, actor.y = nx, ny
            set_facing_from_move(actor, old_x, old_y)
            if not actor.spend_ap(1):
                return False
            return True

        return False


class FlankAction(BehaviorNode):
    """プレイヤーの裏側を取る (提案4: flanker / pincer)"""

    def execute(self, actor: Entity, engine: Engine) -> bool:
        player = engine.player
        if player is None or player.hp <= 0:
            return False
        dist = _cheb(actor.x, actor.y, player.x, player.y)
        if dist <= 1:
            return MeleeAttackAction().execute(actor, engine)

        # actor を player を鏡として反射した点（プレイヤーの裏側）を目指す
        rx = 2 * player.x - actor.x
        ry = 2 * player.y - actor.y
        neighbors = _free_neighbors(engine, actor)
        if not neighbors:
            return False
        nx, ny = min(neighbors, key=lambda t: _cheb(t[0], t[1], rx, ry))
        old_x, old_y = actor.x, actor.y
        actor.x, actor.y = nx, ny
        set_facing_from_move(actor, old_x, old_y)
        if not actor.spend_ap(1):
            return False
        return True


class AdvancedAISystem(BaseSystem):
    """先進的AIシステム (ビヘイビアツリー管理・ディスパッチ)"""

    def __init__(self):
        super().__init__()
        # 各種AIツリーの構築
        self.trees: dict[str, BehaviorNode] = {
            "coward": SelectorNode(
                [
                    AbilityAction(),
                    SequenceNode([HealSelfAction(0.5), FleeAction()]),
                    MeleeAttackAction(),
                    FleeAction(),
                    WanderAction(),
                ]
            ),
            "aggressive": SelectorNode(
                [
                    AbilityAction(),
                    SpreadAction(),
                    MeleeAttackAction(),
                    ChaseAction(),
                    WanderAction(),
                ]
            ),
            "caster": SelectorNode(
                [
                    AbilityAction(),
                    HealSelfAction(0.35),
                    CastSpellAction(),
                    MeleeAttackAction(),
                    ChaseAction(),
                    WanderAction(),
                ]
            ),
            "tactical": SelectorNode(
                [
                    AbilityAction(),
                    HealSelfAction(0.30),
                    SpreadAction(),
                    MeleeAttackAction(),
                    CastSpellAction(),
                    ChaseAction(),
                    WanderAction(),
                ]
            ),
            "boss": SelectorNode(
                [
                    AbilityAction(),
                    CastSpellAction(),
                    MeleeAttackAction(),
                    ChaseAction(),
                    WanderAction(),
                ]
            ),
            # 提案4: 陣形AIロール用ツリー
            "kiter": SelectorNode(
                [AbilityAction(), KiteAction(), CastSpellAction(), ChaseAction(), WanderAction()]
            ),
            "flanker": SelectorNode(
                [
                    AbilityAction(),
                    FlankAction(),
                    MeleeAttackAction(),
                    ChaseAction(),
                    WanderAction(),
                ]
            ),
        }

    def _allies_in_sight(self, actor: Entity, engine: Engine) -> int:
        """視界内の味方モンスター数を数える (提案4: 連携判定)"""

        count = 0
        for e in getattr(engine, "entities", []):
            if e is actor or getattr(e, "faction", None) != "monster":
                continue
            d = _cheb(actor.x, actor.y, e.x, e.y)
            if d <= 8 and _has_los(engine, actor, e):
                count += 1
        return count

    def process_ai(self, actor: Entity, engine: Engine) -> None:
        """エンティティのAIタイプ/ロールに応じた行動実行"""
        if getattr(actor, "is_pet", False):
            self.process_pet_ai(actor, engine)
            return

        from constants import AI_ROLE_BRUTE, AI_ROLE_FLANKER, AI_ROLE_KITER, PINCER_MIN_ALLIES

        ai_type = getattr(actor, "ai_type", "aggressive")
        role = getattr(actor, "ai_role", AI_ROLE_BRUTE)

        # 提案4: 連携(挟撃) — 視界内に十分な味方がいれば brute を一時flank化
        if (
            getattr(actor, "faction", None) == "monster"
            and role == AI_ROLE_BRUTE
            and self._allies_in_sight(actor, engine) >= PINCER_MIN_ALLIES
        ):
            role = AI_ROLE_FLANKER

        if role == AI_ROLE_KITER:
            tree = self.trees.get("kiter", self.trees["aggressive"])
        elif role == AI_ROLE_FLANKER:
            tree = self.trees.get("flanker", self.trees["aggressive"])
        else:
            tree = self.trees.get(ai_type, self.trees["aggressive"])
        tree.execute(actor, engine)

    def process_pet_ai(self, pet: Entity, engine: Engine) -> None:
        """ペットの戦術指示に応じた行動実行"""
        tactic = getattr(pet, "tactic", TACTIC_BALANCED)

        if tactic == TACTIC_PASSIVE:
            tree = SelectorNode([PetFollowAction(), WanderAction()])
        elif tactic == TACTIC_DEFENSIVE:
            p = engine.player
            dist = Point(pet.x, pet.y).chebyshev_distance(Point(p.x, p.y))
            if dist > 2:
                tree = SelectorNode([PetFollowAction(), MeleeAttackAction()])
            else:
                tree = SelectorNode([MeleeAttackAction(), ChaseAction(), PetFollowAction()])
        elif tactic == TACTIC_AGGRESSIVE:
            tree = SelectorNode([MeleeAttackAction(), ChaseAction(), PetFollowAction()])
        else:  # TACTIC_BALANCED
            tree = SelectorNode(
                [
                    HealSelfAction(0.30),
                    MeleeAttackAction(),
                    ChaseAction(),
                    PetFollowAction(),
                    WanderAction(),
                ]
            )

        tree.execute(pet, engine)
