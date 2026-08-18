"""
Render Context Module - Holds all data needed for rendering
"""
from __future__ import annotations
from typing import List, Optional, Tuple
from entity import Entity, GodInfo
from item_system import Item, CAT_WEAPON, CAT_SHIELD, CAT_ARMOR, CAT_POTION, CAT_FOOD
from systems import STATUS_BLEEDING
from map_engine import GameMap
from survival_system import SurvivalSystem
from fx_manager import FXManager
from ui_fx_systems import MiniMapRenderer, DynamicLighting, GaugeBar, WeatherAtmosphereLayer, ScreenFilterManager, CinematicLogVisualizer
from turn_manager import TimeSystem
from message_log import MessageLog
from notification_manager import NotificationManager
from localization_manager import LocalizationManager
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, MAP_WIDTH, MAP_HEIGHT, VIEW_WIDTH, VIEW_HEIGHT, TILE_STAIRS_DOWN, COLOR_WALL_DARK, COLOR_WALL_LIT, COLOR_FLOOR_DARK, COLOR_FLOOR_LIT, COLOR_ALTAR, COLOR_HP_GREEN, COLOR_MP_BLUE, COLOR_GOLD_YELLOW, COLOR_PET_PINK
from game_state import GameState


class RenderContext:
    """All data needed for rendering, extracted from Engine"""
    
    def __init__(self, 
                 game_map: GameMap,
                 player: Entity,
                 pet: Entity,
                 entities: List[Entity],
                 items_on_ground: List[Item],
                 resource_nodes: List['ResourceNode'],
                 survival: SurvivalSystem,
                 floating_texts: List,
                 particles: List,
                 look_cursor: Optional[object],  # LookCursor type
                 game_state: str,
                 time_system: TimeSystem,
                 dungeon_level: int,
                 msg_log: MessageLog,
                 fx_manager: FXManager,
                 notification_manager: NotificationManager,
                 achievement_notifications: List,
                 current_weather: str,
                 casting_spell: Optional[object],
                 frame_count: int,
                 inventory_target: str,
                 inventory_tab: int,
                 inventory_cursor: int,
                 pet_inventory: List[Item],
                 altar_pos: Tuple[int, int],
                 localization_manager: LocalizationManager = None):
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