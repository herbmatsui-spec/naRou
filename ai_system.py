"""
Elona Masterpiece Edition - Advanced AI System (Behavior Trees & Tactical Archetypes)
Implements rich AI decision-making for monsters, pets, and neutral NPCs.
"""

from __future__ import annotations
import random
from typing import Optional, List, Dict, TYPE_CHECKING
from core_framework import Point, AStar, BaseSystem
from constants import ENERGY_THRESHOLD

if TYPE_CHECKING:
    from game import Engine
    from entity import Entity


# ペット戦術コマンド
TACTIC_BALANCED    = "balanced"     # バランス (通常追従・迎撃)
TACTIC_AGGRESSIVE  = "aggressive"   # 積極迎撃 (視界内の敵を索敵・撃滅)
TACTIC_DEFENSIVE   = "defensive"    # 専守防衛 (主人の隣接2マス以内を維持)
TACTIC_SUPPORT     = "support"      # 支援優先 (回復・バフ・遠隔)
TACTIC_PASSIVE     = "passive"      # 不戦避難 (攻撃せず主人の後ろをキープ)


class BehaviorNode:
    """ビヘイビアツリー基底ノード"""
    def execute(self, actor: "Entity", engine: "Engine") -> bool:
        raise NotImplementedError


class SelectorNode(BehaviorNode):
    """いずれかの子供ノードが成功したら成功を返す (OR)"""
    def __init__(self, children: List[BehaviorNode]):
        self.children = children

    def execute(self, actor: "Entity", engine: "Engine") -> bool:
        for child in self.children:
            if child.execute(actor, engine):
                return True
        return False


class SequenceNode(BehaviorNode):
    """全ての子供ノードが成功した場合のみ成功を返す (AND)"""
    def __init__(self, children: List[BehaviorNode]):
        self.children = children

    def execute(self, actor: "Entity", engine: "Engine") -> bool:
        for child in self.children:
            if not child.execute(actor, engine):
                return False
        return True


# ==================== ACTIONS ====================

class HealSelfAction(BehaviorNode):
    """HP低下時の自己治癒アクション"""
    def __init__(self, threshold_ratio: float = 0.35):
        self.threshold = threshold_ratio

    def execute(self, actor: "Entity", engine: "Engine") -> bool:
        if actor.hp > actor.max_hp * self.threshold:
            return False
        # 治癒ポーション所持または治癒魔法
        heal_val = int(actor.max_hp * 0.4)
        actor.hp = min(actor.max_hp, actor.hp + heal_val)
        actor.energy -= ENERGY_THRESHOLD
        engine.log(f"{actor.name} は傷口を手当てし、体力を回復した！ (+{heal_val} HP)", (100, 255, 150))
        return True


class FleeAction(BehaviorNode):
    """脅威からの逃走アクション"""
    def execute(self, actor: "Entity", engine: "Engine") -> bool:
        player = engine.player
        dist = Point(actor.x, actor.y).chebyshev_distance(Point(player.x, player.y))
        if dist > 8:
            return False  # すでに十分離れている

        best_move = None
        max_dist = dist

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
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
    def execute(self, actor: "Entity", engine: "Engine") -> bool:
        target = self._find_adjacent_enemy(actor, engine)
        if not target:
            return False

        from systems import CombatSystem
        from sound_manager import SoundManager
        from ui_fx_systems import FloatingText

        dmg, is_crit, msg = CombatSystem.calculate_melee_attack(actor, target, None)
        target.hp -= dmg
        engine.log(msg, (255, 120, 120) if target == engine.player else (220, 220, 220))
        SoundManager.play_se("hit")

        # 浮動ダメージ表示
        if hasattr(engine, "floating_texts"):
            engine.floating_texts.append(FloatingText(f"-{dmg}", target.x, target.y - 0.2, (255, 80, 80)))

        if target.hp <= 0:
            if target == engine.player:
                engine.log(f"【死亡】{actor.name} に倒された……", (255, 30, 30), level="ERROR")
            elif target == engine.pet:
                engine.log(f"{target.name} は力尽きて倒れた！", (255, 100, 100))
            else:
                engine._on_kill(target)

        actor.energy -= ENERGY_THRESHOLD
        return True

    def _find_adjacent_enemy(self, actor: "Entity", engine: "Engine") -> Optional["Entity"]:
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
            ent = engine.get_entity_at(actor.x + dx, actor.y + dy)
            if ent and ent.hp > 0:
                if actor.faction == "monster" and (ent.is_player or getattr(ent, "is_pet", False)):
                    return ent
                elif getattr(actor, "is_pet", False) and ent.faction == "monster":
                    return ent
        return None


class CastSpellAction(BehaviorNode):
    """遠隔呪文・スキル使用アクション"""
    def execute(self, actor: "Entity", engine: "Engine") -> bool:
        # キャスター系がターゲット視認時に魔矢/火炎球等を使用
        target = engine.player if actor.faction == "monster" else None
        if not target or target.hp <= 0:
            return False

        dist = Point(actor.x, actor.y).chebyshev_distance(Point(target.x, target.y))
        if 2 <= dist <= 5 and engine.has_los(Point(actor.x, actor.y), Point(target.x, target.y)):
            if random.random() < 0.40:
                dmg = random.randint(8, 16)
                target.hp -= dmg
                engine.log(f"⚡ {actor.name} は魔力の矢を放った！ ({target.name} に {dmg} ダメージ)", (200, 100, 255))
                if hasattr(engine, "floating_texts"):
                    from ui_fx_systems import FloatingText
                    engine.floating_texts.append(FloatingText(f"-{dmg}", target.x, target.y - 0.2, (200, 100, 255)))
                actor.energy -= ENERGY_THRESHOLD
                return True
        return False


class ChaseAction(BehaviorNode):
    """A*による目標追従アクション"""
    def execute(self, actor: "Entity", engine: "Engine") -> bool:
        target = self._find_target(actor, engine)
        if not target:
            return False

        path = AStar.find_path(
            Point(actor.x, actor.y),
            Point(target.x, target.y),
            engine.game_map,
            engine.get_blocked_positions()
        )

        if path and len(path) > 1:
            next_pt = path[1]
            if engine.is_tile_free(next_pt.x, next_pt.y):
                actor.x, actor.y = next_pt.x, next_pt.y
                actor.energy -= ENERGY_THRESHOLD
                return True
        return False

    def _find_target(self, actor: "Entity", engine: "Engine") -> Optional["Entity"]:
        if actor.faction == "monster":
            # 視界内のプレイヤーまたはペット
            dist_p = Point(actor.x, actor.y).chebyshev_distance(Point(engine.player.x, engine.player.y))
            if dist_p <= 8 and engine.has_los(Point(actor.x, actor.y), Point(engine.player.x, engine.player.y)):
                return engine.player
        elif getattr(actor, "is_pet", False):
            # 視界内の最寄りのモンスター
            closest_mob = None
            min_d = 999
            for e in engine.entities:
                if e.faction == "monster" and e.hp > 0:
                    d = Point(actor.x, actor.y).chebyshev_distance(Point(e.x, e.y))
                    if d < min_d and d <= 8 and engine.has_los(Point(actor.x, actor.y), Point(e.x, e.y)):
                        min_d = d
                        closest_mob = e
            return closest_mob
        return None


class PetFollowAction(BehaviorNode):
    """ペットの主人追従・陣形維持アクション"""
    def execute(self, actor: "Entity", engine: "Engine") -> bool:
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
            engine.get_blocked_positions()
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
    def execute(self, actor: "Entity", engine: "Engine") -> bool:
        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)])
        nx, ny = actor.x + dx, actor.y + dy
        if engine.is_tile_free(nx, ny):
            actor.x, actor.y = nx, ny
        actor.energy -= ENERGY_THRESHOLD
        return True


# ==================== ADVANCED AI CONTROLLER ====================

class AdvancedAISystem(BaseSystem):
    """先進的AIシステム (ビヘイビアツリー管理・ディスパッチ)"""
    def __init__(self):
        super().__init__()
        # 各種AIツリーの構築
        self.trees: Dict[str, BehaviorNode] = {
            "coward": SelectorNode([
                SequenceNode([HealSelfAction(0.5), FleeAction()]),
                MeleeAttackAction(),
                FleeAction(),
                WanderAction()
            ]),
            "aggressive": SelectorNode([
                MeleeAttackAction(),
                ChaseAction(),
                WanderAction()
            ]),
            "caster": SelectorNode([
                HealSelfAction(0.35),
                CastSpellAction(),
                MeleeAttackAction(),
                ChaseAction(),
                WanderAction()
            ]),
            "tactical": SelectorNode([
                HealSelfAction(0.30),
                MeleeAttackAction(),
                CastSpellAction(),
                ChaseAction(),
                WanderAction()
            ]),
            "boss": SelectorNode([
                CastSpellAction(),
                MeleeAttackAction(),
                ChaseAction(),
                WanderAction()
            ])
        }

    def process_ai(self, actor: "Entity", engine: "Engine") -> None:
        """エンティティのAIタイプに応じた行動実行"""
        if getattr(actor, "is_pet", False):
            self.process_pet_ai(actor, engine)
            return

        ai_type = getattr(actor, "ai_type", "aggressive")
        tree = self.trees.get(ai_type, self.trees["aggressive"])
        tree.execute(actor, engine)

    def process_pet_ai(self, pet: "Entity", engine: "Engine") -> None:
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
        else: # TACTIC_BALANCED
            tree = SelectorNode([
                HealSelfAction(0.30),
                MeleeAttackAction(),
                ChaseAction(),
                PetFollowAction(),
                WanderAction()
            ])

        tree.execute(pet, engine)
