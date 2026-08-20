"""
Render Context Module - Holds all data needed for rendering
"""

from __future__ import annotations

from entity import Entity
from fx_manager import FXManager
from item_system import Item
from localization_manager import LocalizationManager
from map_engine import GameMap
from message_log import MessageLog
from notification_manager import NotificationManager
from survival_system import SurvivalSystem
from turn_manager import TimeSystem


class RenderContext:
    """All data needed for rendering, extracted from Engine"""

    def __init__(
        self,
        game_map: GameMap,
        player: Entity,
        pet: Entity,
        entities: list[Entity],
        items_on_ground: list[Item],
        resource_nodes: list[ResourceNode],
        survival: SurvivalSystem,
        floating_texts: list,
        particles: list,
        look_cursor: object | None,  # LookCursor type
        game_state: str,
        time_system: TimeSystem,
        dungeon_level: int,
        msg_log: MessageLog,
        fx_manager: FXManager,
        notification_manager: NotificationManager,
        achievement_notifications: list,
        current_weather: str,
        casting_spell: object | None,
        frame_count: int,
        inventory_target: str,
        inventory_tab: int,
        inventory_cursor: int,
        pet_inventory: list[Item],
        altar_pos: tuple[int, int],
        localization_manager: LocalizationManager = None,
    ):
        self.game_map = game_map
        self.player = player
        self.pet = pet
        self.entities = entities
        self.items_on_ground = items_on_ground
        self.resource_nodes = resource_nodes
        self.survival = survival
        self.floating_texts = floating_texts
        self.particles = particles
        self.look_cursor = look_cursor
        self.game_state = game_state
        self.time_system = time_system
        self.dungeon_level = dungeon_level
        self.msg_log = msg_log
        self.fx_manager = fx_manager
        self.notification_manager = notification_manager
        self.achievement_notifications = achievement_notifications
        self.current_weather = current_weather
        self.casting_spell = casting_spell
        self.frame_count = frame_count
        self.inventory_target = inventory_target
        self.inventory_tab = inventory_tab
        self.inventory_cursor = inventory_cursor
        self.pet_inventory = pet_inventory
        self.altar_pos = altar_pos
        self.localization_manager = localization_manager
