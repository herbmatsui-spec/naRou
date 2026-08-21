"""
Elona Masterpiece Edition - Advanced AI System (Behavior Trees & Tactical Archetypes)
Implements rich AI decision-making for monsters, pets, and neutral NPCs.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from constants import ENERGY_THRESHOLD
from core_framework import AStar, BaseSystem, Point

if TYPE_CHECKING:
    from entity import Entity
    from game import Engine


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
        actor.energy -= ENERGY_THRESHOLD
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
            actor.x, actor.y = best_move
            actor.energy -= ENERGY_THRESHOLD
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
                engine.log(
                    f"【死亡】{actor.name} に倒された……", (255, 30, 30), level="ERROR"
                )
            elif target == engine.pet:
                engine.log(f"{target.name} は力尽きて倒れた！", (255, 100, 100))
            else:
                engine._on_kill(target)
                # Publish kill event for FX
                CombatSystem.publish_kill_event(engine.event_bus, target.x, target.y)

        actor.energy -= ENERGY_THRESHOLD
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
            if ent and ent.hp > 0 and (
                actor.faction == "monster"
                and (ent.is_player or getattr(ent, "is_pet", False))
                or getattr(actor, "is_pet", False)
                and ent.faction == "monster"
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
        if 2 <= dist <= 5 and engine.has_los(
            Point(actor.x, actor.y), Point(target.x, target.y)
        ):
            if random.random() < 0.40:
                dmg = random.randint(8, 16)
                target.hp -= dmg
                engine.log(
                    f"⚡ {actor.name} は魔力の矢を放った！ ({target.name} に {dmg} ダメージ)",
                    (200, 100, 255),
                )
                if hasattr(engine, "floating_texts"):
                    from ui_fx_systems import FloatingText

                    engine.floating_texts.append(
                        FloatingText(
                            f"-{dmg}", target.x, target.y - 0.2, (200, 100, 255)
                        )
                    )
                actor.energy -= ENERGY_THRESHOLD
                return True
        return False


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
                actor.x, actor.y = next_pt.x, next_pt.y
                actor.energy -= ENERGY_THRESHOLD
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
            actor.energy -= ENERGY_THRESHOLD // 2
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
                actor.x, actor.y = next_pt.x, next_pt.y
                actor.energy -= ENERGY_THRESHOLD
                return True
        return False


class WanderAction(BehaviorNode):
    """周囲のランダム移動"""

    def execute(self, actor: Entity, engine: Engine) -> bool:
        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])
        nx, ny = actor.x + dx, actor.y + dy
        if engine.is_tile_free(nx, ny):
            actor.x, actor.y = nx, ny
        actor.energy -= ENERGY_THRESHOLD
        return True


# ==================== ADVANCED AI CONTROLLER ====================


# ==================== 提案4: 陣形・連携タクティクス用ヘルパ ====================

DIRS8 = [
    (0, 1), (0, -1), (1, 0), (-1, 0),
    (1, 1), (-1, -1), (1, -1), (-1, 1),
]


def _cheb(ax: int, ay: int, bx: int, by: int) -> int:
    return max(abs(ax - bx), abs(ay - by))


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
        crowded = any(
            _is_monster_at(engine, actor.x + dx, actor.y + dy, actor)
            for dx, dy in DIRS8
        )
        if not crowded:
            return False
        best = min(neighbors, key=lambda t: _ally_density(engine, t[0], t[1], actor))
        actor.x, actor.y = best
        actor.energy -= ENERGY_THRESHOLD
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
            CastSpellAction().execute(actor, engine)
            return True

        if dist < pref:
            neighbors = _free_neighbors(engine, actor)
            if not neighbors:
                return False
            nx, ny = max(
                neighbors, key=lambda t: _cheb(t[0], t[1], player.x, player.y)
            )
            actor.x, actor.y = nx, ny
            actor.energy -= ENERGY_THRESHOLD
            return True

        if dist > pref:
            neighbors = _free_neighbors(engine, actor)
            if not neighbors:
                return False
            cand = [
                t for t in neighbors
                if _cheb(t[0], t[1], player.x, player.y) >= pref - 1
            ]
            if not cand:
                cand = neighbors
            nx, ny = min(
                cand, key=lambda t: _cheb(t[0], t[1], player.x, player.y)
            )
            actor.x, actor.y = nx, ny
            actor.energy -= ENERGY_THRESHOLD
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
        actor.x, actor.y = nx, ny
        actor.energy -= ENERGY_THRESHOLD
        return True


class AdvancedAISystem(BaseSystem):
    """先進的AIシステム (ビヘイビアツリー管理・ディスパッチ)"""

    def __init__(self):
        super().__init__()
        # 各種AIツリーの構築
        self.trees: dict[str, BehaviorNode] = {
            "coward": SelectorNode(
                [
                    SequenceNode([HealSelfAction(0.5), FleeAction()]),
                    MeleeAttackAction(),
                    FleeAction(),
                    WanderAction(),
                ]
            ),
            "aggressive": SelectorNode(
                [SpreadAction(), MeleeAttackAction(), ChaseAction(), WanderAction()]
            ),
            "caster": SelectorNode(
                [
                    HealSelfAction(0.35),
                    CastSpellAction(),
                    MeleeAttackAction(),
                    ChaseAction(),
                    WanderAction(),
                ]
            ),
            "tactical": SelectorNode(
                [
                    HealSelfAction(0.30),
                    SpreadAction(),
                    MeleeAttackAction(),
                    CastSpellAction(),
                    ChaseAction(),
                    WanderAction(),
                ]
            ),
            "boss": SelectorNode(
                [CastSpellAction(), MeleeAttackAction(), ChaseAction(), WanderAction()]
            ),
            # 提案4: 陣形AIロール用ツリー
            "kiter": SelectorNode(
                [KiteAction(), CastSpellAction(), ChaseAction(), WanderAction()]
            ),
            "flanker": SelectorNode(
                [FlankAction(), MeleeAttackAction(), ChaseAction(), WanderAction()]
            ),
        }

    def _allies_in_sight(self, actor: Entity, engine: Engine) -> int:
        """視界内の味方モンスター数を数える (提案4: 連携判定)"""
        from core_framework import Point

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

        from constants import (
            AI_ROLE_BRUTE,
            AI_ROLE_FLANKER,
            AI_ROLE_KITER,
            PINCER_MIN_ALLIES,
        )

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
                tree = SelectorNode(
                    [MeleeAttackAction(), ChaseAction(), PetFollowAction()]
                )
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
