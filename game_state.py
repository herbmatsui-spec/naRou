"""
Elona Roguelike - Game State Management
Step 7: GameState クラス抽出 (Part 1)
ゲーム状態データをEngineクラスから分離して管理する
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from constants import GameState as GameStateEnum

# Export GameState for backward compatibility
GameState = GameStateEnum
from crafting_system import ResourceNode
from ecs.entity import Entity
from item_system import Inventory, Item
from systems import Quest, SurvivalSystem


@dataclass
class GameStateData:
    """ゲーム状態データクラス（Engineから分離）"""

    # プレイヤーとペット（どちらもEntityだが、is_petフラグで区別）
    player: Entity
    pet: Entity

    # インベントリ
    inventory: Inventory
    pet_inventory: Inventory

    # サバイバルシステム
    survival: SurvivalSystem

    # ダンジョン状態
    dungeon_level: int = 1
    game_map: Any | None = None  # GameMap型だが循環インポートを避けるためAnyに
    altar_pos: tuple[int, int] = (0, 0)

    # 動的エンティティとアイテム
    entities: list[Entity] = field(default_factory=list)
    items_on_ground: list[Item] = field(default_factory=list)
    resource_nodes: list[ResourceNode] = field(default_factory=list)

    # クエスト
    quests: list[Quest] = field(default_factory=list)

    # ゲーム状態
    current_state: GameStateEnum = GameStateEnum.EXPLORING
    game_state: str = "play"  # 旧互換用
    current_world: str = "main"  # "main", "skill_eater", etc.
    world_a_data: dict[str, Any] = field(default_factory=dict)

    # UI状態
    help_tab: int = 0
    inventory_target: str = "player"
    inventory_cursor: int = 0
    inventory_tab: int = 0  # 0=全 1=武器 2=防具 3=消費 4=その他
    active_dialogue: tuple[str, str] | None = None

    # 入力状態
    wish_input: str = ""
    debug_input: str = ""

    # カウンター
    turns: int = 0

    # 考古学解釈プロンプト状態
    arch_interpret_active: bool = False
    arch_interpret_groups_cache: list[dict[str, Any]] = field(default_factory=list)
    arch_interpret_truth_idx: int = 0
    arch_interpret_ending_idx: int = 0

    def __post_init__(self):
        """初期化後の処理"""
        # プレイヤーとペットの基本設定
        self.player.faction = "player"
        self.pet.faction = "player"

        # 初期インベントリ設定（空の場合）
        if not self.inventory.items and not self.pet_inventory.items:
            # これはEngine.__init__で設定されるべきだが、
            # デフォルト値として空のインベントリを用意
            pass
