"""
Entity System - Handles entity AI and interactions extracted from Engine.
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from constants import (
    COLOR_PET_PINK,
    ENERGY_THRESHOLD,
    PET_RETREAT_HP_RATIO,
    PET_PATH_LENGTH_CHECK,
    AI_ROLE_KITER,
    KITER_PREFERRED_RANGE,
)
from naRou.systems import FACTION_GUARD
from core_framework import AStar, Point, bresenham_line

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
                return

        engine.log("周囲に話しかけられる相手がいない。")

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