from __future__ import annotations

from packages.core.kernel.kernel import Kernel
from packages.core.kernel.package import IPackage, PackageMetadata


# Module-level functions for pickling support
def _create_starter_items(kernel: Kernel) -> list:
    from item_system import (
        QUALITY_NORMAL,
        Item,
        create_sample_item,
    )

    starter_sword = create_sample_item("longsword")
    starter_sword.name = "使い古しの長剣"
    starter_sword.material = "iron"
    starter_sword.quality = QUALITY_NORMAL
    starter_sword.hit_bonus = 0
    starter_sword.dmg_bonus = 1

    shield = create_sample_item("shield")
    potion = create_sample_item("potion_heal")
    potion.count = 8
    bread = create_sample_item("bread")
    bread.count = 5
    spellbook = create_sample_item("book_fire")
    instrument = Item(
        "★ストラディバリウス",
        "tool",
        "🎻",
        (255, 215, 0),
        base_weight=1.5,
        base_value=800,
    )
    wish_rod = Item(
        "★願いの杖", "rod", "🪄", (100, 255, 255), base_weight=0.8, base_value=3000
    )
    return [starter_sword, shield, potion, bread, spellbook, instrument, wish_rod]


def _spawn_dungeon(kernel: Kernel, engine) -> None:
    import random

    from advanced_systems import ResourceNode
    from constants import (
        SNAIL_COLOR,
        SNAIL_SPEED,
        SPAWN_ITEM_CHANCE,
        SPAWN_MONSTER_CHANCE,
        SPAWN_RESOURCE_NODE_CHANCE,
        SPAWN_SNAIL_CHANCE,
    )
    from entity import Entity
    from item_system import create_sample_item

    game_map = engine.game_map
    entity_manager = kernel.get_system("entity_manager")
    data_manager = (
        kernel.get_system("data_manager") if kernel.has_system("data_manager") else None
    )

    for room in game_map.rooms[1:]:
        if random.random() < SPAWN_SNAIL_CHANCE:
            gx = random.randint(room.x1 + 1, room.x2 - 1)
            gy = random.randint(room.y1 + 1, room.y2 - 1)
            gwen = Entity(
                gx,
                gy,
                "🐌",
                SNAIL_COLOR,
                "かたつむり少女『グウェン』",
                speed=SNAIL_SPEED,
            )
            gwen.status_effects = []
            gwen.faction = "townsfolk"
            entity_manager.add_entity(gwen)

        if random.random() < SPAWN_MONSTER_CHANCE:
            mx, my = (
                random.randint(room.x1 + 1, room.x2 - 1),
                random.randint(room.y1 + 1, room.y2 - 1),
            )
            if data_manager:
                mob = data_manager.get_random_monster_for_floor(
                    engine.dungeon_level, mx, my
                )
            else:
                from systems import MonsterPreset

                mob = MonsterPreset.create(
                    random.choice(["slime", "slime", "goblin", "orc"]), mx, my
                )
            entity_manager.add_entity(mob)

        if random.random() < SPAWN_ITEM_CHANCE:
            ix, iy = (
                random.randint(room.x1 + 1, room.x2 - 1),
                random.randint(room.y1 + 1, room.y2 - 1),
            )
            if data_manager:
                itm = data_manager.get_random_item_for_floor(
                    engine.dungeon_level, ix, iy
                )
            else:
                itm = create_sample_item(
                    random.choice(
                        [
                            "potion_heal",
                            "bread",
                            "ration",
                            "shortsword",
                            "leather_armor",
                        ]
                    ),
                    ix,
                    iy,
                )
            entity_manager.add_item(itm)

        if random.random() < SPAWN_RESOURCE_NODE_CHANCE:
            rx, ry = (
                random.randint(room.x1 + 1, room.x2 - 1),
                random.randint(room.y1 + 1, room.y2 - 1),
            )
            ntype = random.choice(["herb", "mushroom", "ore_vein"])
            entity_manager.add_resource_node(ResourceNode(rx, ry, ntype))


class GameplayLoop:
    def __init__(self, kernel: Kernel, engine):
        self.kernel = kernel
        self.engine = engine

    def player_act(self, dx: int, dy: int) -> bool:

        from constants import ENERGY_THRESHOLD, TILE_TRAP
        from sound_manager import SoundManager
        from systems import CombatSystem
        from ui_fx_systems import FloatingText

        tx, ty = self.engine.player.x + dx, self.engine.player.y + dy
        target = self.engine.get_entity_at(tx, ty)

        if target and target not in (self.engine.player, self.engine.pet):
            if "グウェン" in target.name:
                self.engine.survival.karma -= 15
                self.engine.log(
                    "【悪行】グウェンを攻撃した！ (Karma -15)", (255, 80, 80)
                )
            weapon = self.engine.inventory.equipment.get("main_hand")
            dmg, is_crit, msg = CombatSystem.calculate_melee_attack(
                self.engine.player, target, weapon
            )
            target.hp -= dmg
            CombatSystem.publish_damage_event(
                self.engine.event_bus, dmg, target.x, target.y, is_crit, target.hp <= 0
            )
            self.engine.log(msg, (255, 130, 130) if is_crit else (240, 240, 240))
            SoundManager.play_se("hit")

            if is_crit and hasattr(self.engine, "screen_shake"):
                self.engine.screen_shake.trigger(intensity=1.5, duration=4)

            self.engine.floating_texts.append(
                FloatingText(
                    f"-{dmg}",
                    target.x,
                    target.y - 0.2,
                    (255, 100, 100) if not is_crit else (255, 230, 80),
                )
            )

            for l in self.engine.player.gain_skill_exp("long_sword", 18):
                self.engine.log(l, (150, 255, 150))
            if target.hp <= 0:
                CombatSystem.publish_kill_event(
                    self.engine.event_bus, target.x, target.y
                )
                self.engine._on_kill(target)
            self.engine.player.energy -= ENERGY_THRESHOLD
            return True

        elif self.engine.game_map.is_walkable(tx, ty) and not self.engine.get_entity_at(
            tx, ty
        ):
            self.engine.player.x, self.engine.player.y = tx, ty

            try:
                from event_bus import event_bus, EVENT_ON_MOVE
                event_bus.publish(EVENT_ON_MOVE, {"entity": self.engine.player, "x": tx, "y": ty})
            except ImportError:
                pass

            if (tx, ty) == self.engine.altar_pos:
                from constants import GodInfo

                self.engine.log(
                    f"神【{GodInfo.GODS[self.engine.player.god_id]['name']}】の祭壇。([p]祈る [o]捧げる)",
                    (255, 215, 0),
                )
            tile = self.engine.game_map.tiles[tx][ty]
            if tile == TILE_TRAP:
                self.engine.player.hp -= 6
                CombatSystem.publish_trap_event(
                    self.engine.event_bus, 6, self.engine.player.x, self.engine.player.y
                )
                if hasattr(self.engine, "screen_shake"):
                    self.engine.screen_shake.trigger(intensity=1.0, duration=3)
                self.engine.floating_texts.append(
                    FloatingText(
                        "-6",
                        self.engine.player.x,
                        self.engine.player.y - 0.2,
                        (255, 80, 80),
                    )
                )
                self.engine.log(
                    "トラップ発動！ 毒矢が急所を貫く！ (-6 HP)",
                    (255, 80, 80),
                    level="WARNING",
                )
            self.engine.player.energy -= ENERGY_THRESHOLD
            return True
        return False

    def advance_world(self) -> None:
        from constants import ENERGY_THRESHOLD
        from core_framework import Point
        from systems import CombatSystem

        max_cycles = 200
        cycle = 0
        while self.engine.player.energy < ENERGY_THRESHOLD and cycle < max_cycles:
            cycle += 1
            actor, _ = self.engine.turn_queue.step_next_actor(
                self.engine.entity_manager.get_living_entities()
            )
            if not actor or actor == self.engine.player:
                break
            if actor == self.engine.pet:
                self.engine._pet_ai()
            else:
                self.engine._npc_ai(actor)

        for entity in list(self.engine.entity_manager.get_living_entities()):
            if entity.hp > 0:
                logs, _is_bleeding = CombatSystem.process_status_effects(entity)
                if entity == self.engine.player:
                    pass
                if logs and (
                    entity == self.engine.player
                    or self.engine.has_los(
                        Point(self.engine.player.x, self.engine.player.y),
                        Point(entity.x, entity.y),
                    )
                ):
                    for l in logs:
                        self.engine.log(l, (200, 80, 80))

        # 提案2: 敵の意図予測を更新（描画・予測のみ。失敗しても進行を止めない）
        try:
            from enemy_intent import compute_intent

            for ent in list(self.engine.entity_manager.get_living_entities()):
                if getattr(ent, "faction", None) == "monster" and ent.hp > 0:
                    ent.next_intent = compute_intent(ent, self.engine)
                else:
                    ent.next_intent = None
        except Exception:  # noqa: BLE001
            pass

        for msg in self.engine.inventory.tick_food_rot(ticks=5):
            self.engine.log(msg, (180, 120, 60))
        for item in self.engine.entity_manager.items_on_ground:
            item.tick_rot(ticks=5)

        for l in self.engine.survival.pass_turn(self.engine.player):
            self.engine.log(l, (255, 180, 100))

        if hasattr(self.engine, "quest_scheduler"):
            from quest_scheduler import ScheduleContext

            context = ScheduleContext.from_engine(self.engine)
            available = self.engine.quest_scheduler.get_available_quests(
                context, self.engine.player
            )
            for schedule in available:
                pass  # Quest scheduling handled elsewhere

        # World A (Skill Eater) Turn Tick (Steps 49-56)
        if getattr(getattr(self.engine, "game_state_data", None), "current_world", "main") == "skill_eater":
            w_data = self.engine.game_state_data.world_a_data
            toxicity = w_data.get("toxicity", 0) + 1
            w_data["toxicity"] = min(100, toxicity)
            if w_data["toxicity"] >= 80:
                self.engine.player.hp = max(1, self.engine.player.hp - 2)
                if w_data["toxicity"] == 80 or w_data["toxicity"] % 10 == 0:
                    self.engine.log(
                        f"【毒性侵食警報】スキル拒絶反応により体力が蝕まれる！（毒性: {w_data['toxicity']}%）",
                        (255, 80, 80),
                    )

            dispatches = w_data.get("pet_dispatches", [])
            for disp in list(dispatches):
                disp["remaining_turns"] -= 1
                if disp["remaining_turns"] <= 0:
                    dispatches.remove(disp)
                    reward_gold = disp.get("reward_gold", 500)
                    self.engine.player.gold = getattr(self.engine.player, "gold", 0) + reward_gold
                    self.engine.log(
                        f"【ペット帰還】派遣任務『{disp['mission_name']}』が完了し、報酬 {reward_gold} アルドを獲得！",
                        (255, 215, 0),
                    )


class GameplayPackage(IPackage):
    @property
    def metadata(self) -> PackageMetadata:
        return PackageMetadata(
            name="gameplay",
            provides=[
                "combat_system",
                "survival_system",
                "inventory_system",
                "item_factory",
                "starter_items_factory",
                "dungeon_spawner",
                "gameplay_loop",
            ],
            requires=["event_bus", "entity_manager", "time_system", "turn_queue"],
            dependencies=["core"],
        )

    def setup(self, kernel: Kernel) -> None:
        from item_system import Inventory, Item
        from systems import CombatSystem, SurvivalSystem

        kernel.register_system("combat_system", CombatSystem())
        kernel.register_system("survival_system", SurvivalSystem())
        kernel.register_system("inventory_system", Inventory)
        kernel.register_system("item_factory", Item)
        kernel.register_system("starter_items_factory", _create_starter_items)
        kernel.register_system("dungeon_spawner", _spawn_dungeon)
        kernel.register_system("gameplay_loop", GameplayLoop)

    def teardown(self, kernel: Kernel) -> None:
        pass
