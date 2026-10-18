"""
Entity System - Handles entity AI and interactions extracted from Engine.
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from naRou.systems import FACTION_GUARD

from constants import (
    AI_ROLE_KITER,
    COLOR_PET_PINK,
    ENERGY_THRESHOLD,
    KITER_PREFERRED_RANGE,
    PET_PATH_LENGTH_CHECK,
    PET_RETREAT_HP_RATIO,
)
from core_framework import AStar, Point, bresenham_line
from pet_systems import PetGrowthSystem

if TYPE_CHECKING:
    from game import Engine

logger = logging.getLogger(__name__)


class EntitySystem:
    """Handles entity AI (pet, NPC) and interactions."""

    def __init__(self, engine: "Engine"):
        self.engine = engine

    def pet_ai(self) -> None:
        """Behavior tree and A* based pet AI."""
        engine = self.engine

        if engine.pet.hp <= 0 or engine.pet.energy < ENERGY_THRESHOLD:
            return

        if hasattr(engine, "ai_system"):
            engine.ai_system.process_ai(engine.pet, engine)
            return

        blocked = engine.get_blocked_positions()
        retreat = engine.pet.hp < engine.pet.max_hp * PET_RETREAT_HP_RATIO

        if not retreat:
            nearest = None
            min_dist = 99
            for e in engine.entity_manager.get_living_entities():
                if e not in (engine.player, engine.pet) and "グウェン" not in e.name and e.hp > 0:
                    d = Point(engine.pet.x, engine.pet.y).chebyshev_distance(Point(e.x, e.y))
                    if d < min_dist and engine.has_los(
                        Point(engine.pet.x, engine.pet.y), Point(e.x, e.y)
                    ):
                        min_dist = d
                        nearest = e

            if nearest and min_dist <= 6:
                if min_dist == 1:
                    weapon = (
                        engine.pet_inventory.equipment.get("main_hand")
                        if hasattr(engine, "pet_inventory")
                        else None
                    )
                    dmg, is_crit, _msg = engine.combat_system.calculate_melee_attack(
                        engine.pet, nearest, weapon=weapon
                    )
                    nearest.hp -= dmg
                    engine.combat_system.publish_damage_event(
                        engine.event_bus,
                        dmg,
                        nearest.x,
                        nearest.y,
                        is_crit,
                        nearest.hp <= 0,
                    )
                    engine.log(
                        f"【シエル】「えいっ！」-> {nearest.name}に{dmg}ダメージ！",
                        COLOR_PET_PINK,
                    )
                    if nearest.hp <= 0:
                        engine.combat_system.publish_kill_event(engine.event_bus, nearest.x, nearest.y)
                        engine.log(f"【シエル】が{nearest.name}を倒した！", (255, 200, 220))
                        for l in engine.pet.gain_exp(40):
                            engine.log(l, COLOR_PET_PINK)
                        # 進化条件達成の検知と進化イベント発火 (T30 案B)
                        PetGrowthSystem.check_and_apply_evolution(engine)
                        engine.entity_manager.remove_entity(nearest)
                else:
                    path = AStar.get_path(
                        Point(engine.pet.x, engine.pet.y),
                        Point(nearest.x, nearest.y),
                        lambda x, y: engine.is_tile_free(x, y, blocked),
                    )
                    if path:
                        engine.pet.x, engine.pet.y = path[0].x, path[0].y
                    engine.pet.energy -= ENERGY_THRESHOLD
                    return

        goal = Point(engine.player.x, engine.player.y)
        path = AStar.get_path(
            Point(engine.pet.x, engine.pet.y),
            goal,
            lambda x, y: engine.is_tile_free(x, y, blocked),
        )
        if path and len(path) > PET_PATH_LENGTH_CHECK:
            nxt = path[0]
            if (nxt.x, nxt.y) != (engine.player.x, engine.player.y):
                engine.pet.x, engine.pet.y = nxt.x, nxt.y
        engine.pet.energy -= ENERGY_THRESHOLD

    def npc_ai(self, npc) -> None:
        """Behavior tree and tactical archetype NPC AI."""
        engine = self.engine

        if npc in (engine.player, engine.pet) or "グウェン" in npc.name or npc.hp <= 0:
            return

        if hasattr(engine, "ai_system"):
            engine.ai_system.process_ai(npc, engine)
            return

        target = engine.player
        if getattr(npc, "faction", None) == FACTION_GUARD and engine.survival.karma > -30:
            npc.energy -= ENERGY_THRESHOLD
            return

        dist = Point(npc.x, npc.y).chebyshev_distance(Point(target.x, target.y))
        can_see = engine.has_los(Point(npc.x, npc.y), Point(target.x, target.y))

        if dist == 1:
            dmg, is_crit, msg = engine.combat_system.calculate_melee_attack(npc, target)
            target.hp -= dmg
            engine.combat_system.publish_damage_event(
                engine.event_bus, dmg, target.x, target.y, is_crit, target.hp <= 0
            )
            engine.log(msg, (255, 100, 100))
            if target.hp <= 0 and target == engine.pet:
                engine.log("【悲痛】シエル「お兄ちゃん…ごめんね…」", (255, 80, 150))
                if hasattr(engine.pet, "pet_ai"):
                    engine.pet.pet_ai.increase_bond(-50, "defeated")
                engine.combat_system.publish_kill_event(engine.event_bus, target.x, target.y)
                # エミートトリガ: 仲間倒れ → 悲しみ (T46 案A)
                bus = getattr(engine, "event_bus", None)
                if bus is not None:
                    bus.publish(
                        "ally_down",
                        {"entity": target, "name": getattr(target, "name", "仲間")},
                    )
        elif dist <= 8 and can_see:
            blocked = engine.get_blocked_positions()
            path = AStar.get_path(
                Point(npc.x, npc.y),
                Point(target.x, target.y),
                lambda x, y: engine.is_tile_free(x, y, blocked),
            )
            if path:
                nxt = path[0]
                if engine.is_tile_free(nxt.x, nxt.y, blocked):
                    npc.x, npc.y = nxt.x, nxt.y
        npc.energy -= ENERGY_THRESHOLD

    def talk_to_neighbor(self) -> None:
        """Talk to adjacent entity."""
        engine = self.engine

        neighbor = engine.get_entity_at(
            engine.player.x + engine.player.dx, engine.player.y + engine.player.dy
        )
        if not neighbor:
            engine.message_log.add("誰もいません。")
            return

        # Main quest progress
        if hasattr(engine, "main_quest_system"):
            logs = engine.main_quest_system.update_progress(
                engine.player, "visit", neighbor.name, 1, engine
            )
            for log in logs:
                engine.message_log.add(log)

        # T39 案C: 負傷した無害なNPCを見舞うと救済 (善意行動) としてカルマに反映
        self._relieve_wounded_neighbor(neighbor)

        for dx, dy in [
            (0, -1), (0, 1), (-1, 0), (1, 0),
            (-1, -1), (1, 1), (-1, 1), (1, -1),
        ]:
            t = engine.get_entity_at(engine.player.x + dx, engine.player.y + dy)
            if t and t != engine.player:
                engine.active_dialogue = engine.dialogue_manager.get_dialogue(t, engine.player, engine)

                if hasattr(engine, "relationship_manager"):
                    engine.relationship_manager.update_relationship(
                        engine.player, t.name, action="talk"
                    )
                    # T39 案C: 関係値変動後の評判ゲート再評価
                    self._evaluate_reputation_gates()
                return

        engine.log("周囲に話しかけられる相手がいない。")

    def _relieve_wounded_neighbor(self, neighbor) -> None:
        """負傷した無害なNPCへの話しかけを看病 (救済) としてカルマへ反映する (T39 案C)。

        同一エンティティに対しては karma_relief_done フラグで一度のみ適用する。
        """
        engine = self.engine
        try:
            hp = getattr(neighbor, "hp", None)
            max_hp = getattr(neighbor, "max_hp", None)
            if hp is None or max_hp is None or hp >= max_hp:
                return
            from naRou.systems import FACTION_MONSTER

            if getattr(neighbor, "faction", FACTION_MONSTER) == FACTION_MONSTER:
                return
            if getattr(neighbor, "karma_relief_done", False):
                return
            karma_mgr = getattr(engine, "karma_manager", None)
            if karma_mgr is None or getattr(engine, "player", None) is None:
                return
            neighbor.karma_relief_done = True
            karma_mgr.apply_action(engine.player, "relief_wounded", engine=engine)
            engine.log(f"【善行】負傷した{neighbor.name}を看病した。 (Karma +2)", (160, 220, 255))
            # T43 案A: 救済を対象 NPC の記憶・態度・噂へ反映
            self._record_npc_social_memory(neighbor, "relief_wounded")
        except Exception:
            logger.exception("看病 (救済) のカルマ反映に失敗")

    def _record_npc_social_memory(self, target, action: str) -> None:
        """プレイヤーの行動を対象 NPC の記憶・態度・噂へ反映する (T43 案A)。"""
        try:
            from npc_memory_system import notify_player_action

            notify_player_action(self.engine, target, action, player=self.engine.player)
        except Exception:
            logger.exception("NPC 記憶への行動反映に失敗")

    def _evaluate_reputation_gates(self) -> None:
        """関係値変動後に ReputationGate を再評価する (T39 案C)。"""
        engine = self.engine
        try:
            from reputation_gate_system import ensure_reputation_gate

            player = getattr(engine, "player", None)
            gate = ensure_reputation_gate(engine) if player is not None else None
            if gate is not None:
                gate.check_all_gates(player)
        except Exception:
            logger.exception("評判ゲートの再評価に失敗")

    def harvest_resource(self) -> None:
        """Harvest resource nodes."""
        engine = self.engine

        for node in engine.entity_manager.resource_nodes:
            d = abs(node.x - engine.player.x) + abs(node.y - engine.player.y)
            if d <= 1 and not node.depleted:
                itm, msg = node.harvest(engine.player)
                engine.log(msg, (180, 255, 180))
                engine.sound_manager.play_se("get_item")
                if itm:
                    _ok, add_msg = engine.inventory.add_item(itm)
                    engine.log(add_msg, (200, 255, 200))
                    engine.floating_texts.append(
                        engine.fx_manager.FloatingText(
                            f"+{itm.name}",
                            engine.player.x,
                            engine.player.y - 0.3,
                            (100, 255, 150),
                        )
                    )
                    engine._progress_generated_quests("collect", itm.name, 1)
                engine.player.energy -= ENERGY_THRESHOLD
                engine.advance_world()
                return

        engine.log("周囲に採取できるものがない。")
