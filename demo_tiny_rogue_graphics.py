#!/usr/bin/env python3
"""
Demo script showcasing all Tiny Rogue Graphics Pack features.
Run with: python demo_tiny_rogue_graphics.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import random

import tcod
import tcod.event

from constants import (
    MAP_HEIGHT,
    MAP_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    VIEW_HEIGHT,
    VIEW_WIDTH,
)
from core_framework import EventBus
from entity import Attributes, Entity
from feature_flags import is_enabled, set_flag
from fx_manager import FXManager
from item_system import Item
from map_engine import GameMap
from render_context import RenderContext
from systems import MonsterPreset
from ui_fx_systems import DynamicLighting

# Enable Tiny Rogue graphics
set_flag("ENABLE_TINY_ROGUE_GFX", True)


class DemoEngine:
    """Minimal engine for demo purposes."""

    def __init__(self):
        self.event_bus = EventBus()
        self.fx_manager = FXManager(self.event_bus)
        self.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT)
        self.game_map.generate_dungeon(max_rooms=8)

        # Create player
        self.player = Entity(
            x=self.game_map.rooms[0].center[0],
            y=self.game_map.rooms[0].center[1],
            char="@",
            color=(255, 255, 255),
            name="Hero",
            attributes=Attributes(
                strength=12,
                endurance=12,
                dexterity=12,
                perception=12,
                learning=12,
                will=12,
                magic=12,
                charisma=12,
            ),
        )
        self.player.is_player = True
        self.player.max_hp = 50
        self.player.hp = 50
        self.player.max_mp = 30
        self.player.mp = 30
        self.player.level = 5
        self.player.piety = 100
        self.player.god_id = "jure"
        self.player.faction = "player"

        # Create pet
        self.pet = Entity(
            x=self.player.x + 1,
            y=self.player.y,
            char="d",
            color=(255, 200, 100),
            name="Ciel",
            attributes=Attributes(
                strength=10,
                endurance=10,
                dexterity=12,
                perception=10,
                learning=10,
                will=10,
                magic=8,
                charisma=14,
            ),
        )
        self.pet.is_pet = True
        self.pet.max_hp = 40
        self.pet.hp = 40
        self.pet.faction = "player"

        # Spawn some monsters
        self.entities = [self.player, self.pet]
        self.monsters = []
        monster_types = [
            "slime",
            "goblin",
            "orc",
            "kobold",
            "snail",
            "red_slime",
            "hound_fire",
            "rogue_thief",
            "novice_wizard",
            "minotaur",
            "lich",
            "dragon_red",
        ]
        for i, mtype in enumerate(monster_types):
            room = self.game_map.rooms[i % len(self.game_map.rooms)]
            mx, my = room.center
            mx += random.randint(-2, 2)
            my += random.randint(-2, 2)
            m = MonsterPreset.create(mtype, mx, my)
            self.entities.append(m)
            self.monsters.append(m)

        # Items on ground
        self.items_on_ground = []
        item_categories = ["potion", "scroll", "weapon", "armor", "gold", "food", "gem"]
        for i, cat in enumerate(item_categories):
            room = self.game_map.rooms[i % len(self.game_map.rooms)]
            ix, iy = room.center
            ix += random.randint(-1, 1)
            iy += random.randint(-1, 1)
            itm = Item(
                x=ix,
                y=iy,
                char="!",
                color=(255, 255, 255),
                name=cat.capitalize(),
                category=cat,
            )
            self.items_on_ground.append(itm)

        # Resource nodes
        self.resource_nodes = []

        # Time system
        from time_system import TimeSystem

        self.time_system = TimeSystem()
        self.dungeon_level = 1

        # Visual state
        self.floating_texts = []
        self.particles = []
        self.current_weather = "fog"
        self.casting_spell = None
        self.survival = type("Survival", (), {"hunger": 5000, "gold": 1234})()
        self.altar_pos = self.game_map.rooms[-1].center if self.game_map.rooms else None

    def get_render_context(self):
        ctx = RenderContext()
        ctx.player = self.player
        ctx.entities = self.entities
        ctx.game_map = self.game_map
        ctx.items_on_ground = self.items_on_ground
        ctx.resource_nodes = self.resource_nodes
        ctx.floating_texts = self.floating_texts
        ctx.particles = self.particles
        ctx.time_system = self.time_system
        ctx.dungeon_level = self.dungeon_level
        ctx.current_weather = self.current_weather
        ctx.casting_spell = self.casting_spell
        ctx.survival = self.survival
        ctx.altar_pos = self.altar_pos
        ctx.frame_count = self.frame_count
        ctx.pet = self.pet
        return ctx

    def update(self):
        self.fx_manager.update()
        self.frame_count += 1

        # Spawn weather particles occasionally
        if self.frame_count % 30 == 0:
            cam_x = max(0, min(MAP_WIDTH - VIEW_WIDTH, self.player.x - VIEW_WIDTH // 2))
            cam_y = max(
                0, min(MAP_HEIGHT - VIEW_HEIGHT, self.player.y - VIEW_HEIGHT // 2)
            )
            from ui_fx_systems import WeatherAtmosphereLayer

            WeatherAtmosphereLayer.spawn_weather_particles(
                self.fx_manager,
                self.current_weather,
                cam_x,
                cam_y,
                VIEW_WIDTH,
                VIEW_HEIGHT,
                self.frame_count,
            )

        # Spawn footstep particles when player moves
        # (In real game, this would be tied to actual movement)


def main():
    # Initialize SDL
    tileset = tcod.tileset.load_tilesheet(
        "assets/tiles/tileset_16x16.png", 16, 16, tcod.tileset.CHARMAP_CP437
    )

    engine = DemoEngine()
    engine.frame_count = 0

    with tcod.context.new(
        columns=SCREEN_WIDTH,
        rows=SCREEN_HEIGHT,
        tileset=tileset,
        title="Tiny Rogue Graphics Pack Demo - Press G to toggle, ESC to quit",
        vsync=True,
    ) as context:
        root_console = tcod.console.Console(SCREEN_WIDTH, SCREEN_HEIGHT, order="F")

        print("=== Tiny Rogue Graphics Pack Demo ===")
        print("Controls:")
        print("  Arrow keys / WASD - Move camera")
        print("  G - Toggle Tiny Rogue graphics")
        print("  1-9 - Spawn test effects")
        print("  W - Cycle weather")
        print("  ESC - Quit")
        print()

        while True:
            engine.update()

            # Render
            ctx = engine.get_render_context()
            ctx.frame_count = engine.frame_count

            # Camera
            cam_x = max(
                0, min(MAP_WIDTH - VIEW_WIDTH, engine.player.x - VIEW_WIDTH // 2)
            )
            cam_y = max(
                0, min(MAP_HEIGHT - VIEW_HEIGHT, engine.player.y - VIEW_HEIGHT // 2)
            )

            # Light sources
            light_sources = DynamicLighting.get_light_sources_for_engine(ctx)

            # Clear console
            root_console.clear()

            # Render map (simplified for demo)
            from map_renderer import MapRenderer

            MapRenderer.render(root_console, ctx, cam_x, cam_y, light_sources)

            # Render items
            from item_renderer import ItemRenderer

            ItemRenderer.render(root_console, ctx, cam_x, cam_y, light_sources)

            # Render entities
            from entity_renderer import EntityRenderer

            EntityRenderer.render(root_console, ctx, cam_x, cam_y, light_sources)

            # Render particles
            from particle_renderer import ParticleRenderer

            ParticleRenderer.render(root_console, ctx, cam_x, cam_y)

            # Render UI
            from uirenderer import UIRenderer

            UIRenderer.render(root_console, ctx, cam_x, cam_y)

            # Weather overlay
            from ui_fx_systems import WeatherAtmosphereLayer

            WeatherAtmosphereLayer.apply_atmosphere(
                root_console,
                cam_x,
                cam_y,
                VIEW_WIDTH,
                VIEW_HEIGHT,
                engine.current_weather,
                engine.frame_count,
                engine.player.speed if hasattr(engine.player, "speed") else 70,
                1.0,
            )

            # Demo info overlay
            ui_y = VIEW_HEIGHT
            root_console.draw_rect(0, ui_y, SCREEN_WIDTH, 4, 0, (10, 12, 16))
            root_console.print(
                2,
                ui_y + 1,
                f"Tiny Rogue GFX: {'ON' if is_enabled('ENABLE_TINY_ROGUE_GFX') else 'OFF'} (Press G to toggle)",
                fg=(100, 255, 100),
            )
            root_console.print(
                2,
                ui_y + 2,
                f"Weather: {engine.current_weather} (Press W to cycle) | Frame: {engine.frame_count}",
                fg=(170, 170, 170),
            )
            root_console.print(
                2,
                ui_y + 3,
                "Keys: 1=Magic 2=Fire 3=Ice 4=Lightning 5=Poison 6=Heal 7=Teleport 8=Explosion 9=Sparkle 0=Smoke",
                fg=(200, 200, 150),
            )

            context.present(root_console)

            # Handle input
            for event in tcod.event.get():
                if isinstance(event, tcod.event.KeyDown):
                    if event.sym == tcod.event.KeySym.ESCAPE:
                        return
                    elif event.sym == tcod.event.KeySym.G:
                        from feature_flags import set_flag

                        new_state = not is_enabled("ENABLE_TINY_ROGUE_GFX")
                        set_flag("ENABLE_TINY_ROGUE_GFX", new_state)
                        print(f"Tiny Rogue GFX: {'ON' if new_state else 'OFF'}")
                    elif event.sym == tcod.event.KeySym.W:
                        weathers = ["fog", "rain", "snow", "heatwave", "ash", "clear"]
                        idx = (
                            weathers.index(engine.current_weather)
                            if engine.current_weather in weathers
                            else 0
                        )
                        engine.current_weather = weathers[(idx + 1) % len(weathers)]
                        print(f"Weather: {engine.current_weather}")
                    elif event.sym == tcod.event.KeySym.KEY_1:
                        engine.fx_manager.spawn_magic_cast(
                            engine.player.x, engine.player.y
                        )
                    elif event.sym == tcod.event.KeySym.KEY_2:
                        engine.fx_manager.spawn_fire_effect(
                            engine.player.x, engine.player.y
                        )
                    elif event.sym == tcod.event.KeySym.KEY_3:
                        engine.fx_manager.spawn_ice_effect(
                            engine.player.x, engine.player.y
                        )
                    elif event.sym == tcod.event.KeySym.KEY_4:
                        engine.fx_manager.spawn_lightning_effect(
                            engine.player.x, engine.player.y
                        )
                    elif event.sym == tcod.event.KeySym.KEY_5:
                        engine.fx_manager.spawn_poison_effect(
                            engine.player.x, engine.player.y
                        )
                    elif event.sym == tcod.event.KeySym.KEY_6:
                        engine.fx_manager.spawn_heal_effect(
                            engine.player.x, engine.player.y
                        )
                    elif event.sym == tcod.event.KeySym.KEY_7:
                        engine.fx_manager.spawn_teleport_effect(
                            engine.player.x, engine.player.y
                        )
                    elif event.sym == tcod.event.KeySym.KEY_8:
                        engine.fx_manager.spawn_explosion_effect(
                            engine.player.x, engine.player.y
                        )
                    elif event.sym == tcod.event.KeySym.KEY_9:
                        engine.fx_manager.spawn_sparkle_effect(
                            engine.player.x, engine.player.y
                        )
                    elif event.sym == tcod.event.KeySym.KEY_0:
                        engine.fx_manager.spawn_smoke_effect(
                            engine.player.x, engine.player.y
                        )
                    elif event.sym in (tcod.event.KeySym.UP, tcod.event.KeySym.K_w):
                        engine.player.y -= 1
                        engine.fx_manager.spawn_footstep_particles(
                            engine.player.x, engine.player.y, "stone", (0, -1)
                        )
                    elif event.sym in (tcod.event.KeySym.DOWN, tcod.event.KeySym.K_s):
                        engine.player.y += 1
                        engine.fx_manager.spawn_footstep_particles(
                            engine.player.x, engine.player.y, "stone", (0, 1)
                        )
                    elif event.sym in (tcod.event.KeySym.LEFT, tcod.event.KeySym.K_a):
                        engine.player.x -= 1
                        engine.fx_manager.spawn_footstep_particles(
                            engine.player.x, engine.player.y, "stone", (-1, 0)
                        )
                    elif event.sym in (tcod.event.KeySym.RIGHT, tcod.event.KeySym.K_d):
                        engine.player.x += 1
                        engine.fx_manager.spawn_footstep_particles(
                            engine.player.x, engine.player.y, "stone", (1, 0)
                        )


if __name__ == "__main__":
    main()
