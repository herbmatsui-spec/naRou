"""
World State Manager Module
Encapsulates entity initialization, map generation, and world state setup from game.py Engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from constants import MAP_HEIGHT, MAP_WIDTH, GameState
from ecs.entity import Entity
from game_state import GameStateData
from item_system import Inventory
from map_engine import GameMap
from systems import Quest, SurvivalSystem

if TYPE_CHECKING:
    from game import Engine


class GameStateInitializer:
    """Manages the creation and initialization of game world state, player, pet, and dungeon maps."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def initialize_world_state(self) -> GameStateData:
        """Create and populate initial GameStateData, player, pet, and starting map."""
        player_cfg = self.engine.config_mgr.get_player_config()
        pet_cfg = self.engine.config_mgr.get_pet_config()

        player = Entity(
            x=player_cfg.get("start_x", 20),
            y=player_cfg.get("start_y", 20),
            char=player_cfg.get("char", "@"),
            color=tuple(player_cfg.get("color", [255, 255, 255])),
            name=player_cfg.get("name", "名無しの冒険者"),
            is_player=True,
            speed=player_cfg.get("speed", 85),
            attributes=player_cfg.get("attributes", {}),
        )

        pet = Entity(
            x=pet_cfg.get("start_x", 21),
            y=pet_cfg.get("start_y", 20),
            char=pet_cfg.get("char", "p"),
            color=tuple(pet_cfg.get("color", [255, 180, 210])),
            name=pet_cfg.get("name", "妹分『シエル』"),
            is_pet=True,
            speed=pet_cfg.get("speed", 90),
            attributes=pet_cfg.get("attributes", {}),
        )

        state_data = GameStateData(
            player=player,
            pet=pet,
            inventory=Inventory(max_items=26, max_weight=60.0),
            pet_inventory=Inventory(max_items=12, max_weight=30.0),
            survival=SurvivalSystem(),
        )

        # マップ初期化
        state_data.dungeon_level = 1
        state_data.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT, floor_level=state_data.dungeon_level)
        state_data.game_map.generate_dungeon()
        state_data.player.x, state_data.player.y = state_data.game_map.start_pos
        state_data.pet.x = state_data.player.x + 1
        state_data.pet.y = state_data.player.y

        if state_data.game_map.rooms:
            rx, ry = state_data.game_map.rooms[0].center
            state_data.altar_pos = (rx + 2, ry)
        else:
            state_data.altar_pos = (state_data.player.x + 2, state_data.player.y)

        # クエスト
        state_data.quests = [
            Quest(
                title="ぷち掃討の栄誉",
                target_monster="ぷち",
                target_count=3,
                reward_gold=350,
                reward_platinum=2,
            ),
            Quest(
                title="オーク討伐令",
                target_monster="オーク",
                target_count=2,
                reward_gold=750,
                reward_platinum=3,
            ),
        ]
        state_data.current_state = GameState.EXPLORING
        state_data.game_state = "play"
        state_data.current_world = player_cfg.get("world", "main")
        state_data.world_a_data = {}
        state_data.help_tab = 0
        state_data.inventory_target = "player"
        state_data.inventory_cursor = 0
        state_data.inventory_tab = 0
        state_data.active_dialogue = None
        state_data.wish_input = ""
        state_data.debug_input = ""
        state_data.turns = 0
        state_data.arch_interpret_active = False
        state_data.arch_interpret_groups_cache = []
        state_data.arch_interpret_truth_idx = 0
        state_data.arch_interpret_ending_idx = 0

        return state_data
