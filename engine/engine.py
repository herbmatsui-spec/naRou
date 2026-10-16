"""
Elona Roguelike Ultimate Masterpiece - Full Integration game.py
Steps 1-72 all systems unified: Speed Tick, A* AI, LOS, UUID Items, Cursed Items,
Food Rot, AoE+FriendlyFire, Bleeding, Crafting, Wish Parser, CompressedSave, DebugConsole,
Status Screen, Tabbed Inventory, Colored Logs, Faction/Aggro
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import pydantic  # noqa: F401  (availability probe for stubs fallback)
except ImportError:
    _stubs = Path(__file__).resolve().parent / "stubs"
    if str(_stubs) not in sys.path:
        sys.path.insert(0, str(_stubs))

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.core.kernel.kernel import Kernel

import tcod
import tcod.event
from naRou.systems import (
    FACTION_GUARD,
    AggroList,
    Quest,
    ResistanceSet,
    StatusEffect,
    SurvivalSystem,
)

from advanced_systems import ResourceNode, SaveSystem, WishParser
from config_manager import get_config_manager
from constants import (
    COLOR_GOLD_YELLOW,
    COLOR_PET_PINK,
    ENERGY_THRESHOLD,
    MAP_HEIGHT,
    MAP_WIDTH,
    PET_PATH_LENGTH_CHECK,
    PET_RETREAT_HP_RATIO,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STARTING_GOD_ID,
    TILE_FLOOR,
    TILE_STAIRS_DOWN,
    TILE_WALL,
    VIEW_HEIGHT,
    VIEW_WIDTH,
    Element,
    GameState,
)
from core.progression_manager import ProgressionFlagComponent
from core_framework import AStar, Point, bresenham_line
from dialogue_system import DialogueManager
from ecs.entity import Entity
from item_system import Inventory, Item
from localization_manager import LocalizationManager
from logging_config import configure_logging
from map_engine import GameMap
from renderer import Renderer, get_renderer, set_renderer
from run_history import RunHistoryStore
from run_summary import (
    CAUSE_COMBAT,
    CAUSE_HUNGER,
    CAUSE_SELF,
    CAUSE_UNKNOWN,
    GAME_OVER_TITLE,
    RunSummary,
)
from skill_tree_system import SkillTreeManager
from sound_manager import SoundManager
from system_coordinator import SystemCoordinator
from ui_fx_systems import FloatingText, Particle, ScreenShake

from .game_state import GameStateMachine

configure_logging()


def _declared_skill_ids(entity: Entity) -> list[str]:
    """Entity が宣言しているスキル id を、並び順どおりに返す。

    `Entity.skills` は未設定の個体に対してプレイヤーの既定 17 種を生成し、触れた時点で
    `_skills` にまで書き込む property なので、判定には生値を使う。
    data_manager.create_monster は id 文字列のリスト、プレイヤーは Skill 辞書を保持する。
    """
    declared = getattr(entity, "_skills", None)
    if declared is None:
        return []
    if isinstance(declared, dict):
        return [str(key) for key in declared]
    return [str(s) for s in declared]


def _character_state_from_entity(entity: Entity, analysis_level: int = 1):
    """Entity が保持する実データから、喰らい判定用の `CharacterState` を構成する。"""
    from skill_eater_system import CharacterState

    attributes = entity.attributes
    return CharacterState(
        id=str(getattr(entity, "id", entity.name)),
        name=entity.name,
        hp=entity.hp,
        max_hp=entity.max_hp,
        mp=entity.mp,
        max_mp=entity.max_mp,
        atk=attributes.strength,
        defense=attributes.endurance,
        intelligence=attributes.perception,
        speed=entity.speed,
        analysis_level=analysis_level,
        # 奪取率は target.status_effects も読む（Paralyzed / Sleep で +0.20）。
        # Entity には宣言フィールドがないため動的属性として付き、実データだけを写す。
        status_effects=list(getattr(entity, "status_effects", None) or []),
    )


class Engine:
    """計画書1〜72ステップ完全統合エンジン (商用疎結合アーキテクチャ)"""

    skill_tree_manager: SkillTreeManager

    # --- テキスト(ASCII)モード描画用タイル表示定義 (Step 12-16) ---
    _TILE_DISPLAY = {
        "TILE_WALL": ("#", (140, 140, 140)),
        "TILE_FLOOR": (".", (90, 90, 90)),
        "TILE_STAIRS_DOWN": (">", (255, 215, 0)),
        "TILE_STAIRS_UP": ("<", (255, 215, 0)),
        "TILE_WATER": ("~", (40, 120, 220)),
        "TILE_TRAP": ("^", (220, 80, 80)),
    }

    def __init__(self, renderer: Renderer | None = None, kernel: "Kernel | None" = None, headless: bool = False):
        self.headless = headless
        # --- Kernel 初期化 & CorePackage ロード ---
        from exceptions import SystemInitError

        # Dependency injection: allow tests to supply a pre-built kernel.
        if kernel is not None:
            self.kernel = kernel
        else:
            from packages.character.package import CharacterPackage
            from packages.core.kernel.kernel import Kernel
            from packages.core.package import CorePackage
            from packages.gameplay.package import GameplayPackage
            from packages.meta.package import MetaPackage
            from packages.narrative.package import NarrativePackage
            from packages.platform.package import PlatformPackage
            from packages.social.package import SocialPackage
            from packages.world.package import WorldPackage
            from packages.world_a.package import WorldAPackage

        if kernel is None:
            try:
                self.kernel = Kernel()
                self.kernel.load_package(CorePackage())
                self.kernel.load_package(GameplayPackage())
                self.kernel.load_package(CharacterPackage())
                self.kernel.load_package(SocialPackage())
                self.kernel.load_package(MetaPackage())
                self.kernel.load_package(WorldPackage())
                self.kernel.load_package(NarrativePackage())
                self.kernel.load_package(PlatformPackage())
                self.kernel.load_package(WorldAPackage())
            except Exception as e:
                logger.exception("Failed to load core packages during engine initialization: %s", e)
                raise SystemInitError(f"Package initialization failed: {e}") from e
        else:
            self.kernel = kernel

        # --- レンダラ設定 (Step 3) ---
        if renderer is not None:
            self.renderer = renderer
            set_renderer(renderer)
        else:
            self.renderer = get_renderer()

        # --- 設定管理 (Step 4) ---
        self.config_mgr = get_config_manager()
        self.config_mgr.get_player_config()
        self.config_mgr.get_pet_config()

        # --- LocalizationManager (Phase 3: Step 41) ---
        self.localization_manager = LocalizationManager()

        # --- 依存性注入 & SystemManager 初期化 (Phase 1: Step 1-7, 8) ---
        self.systems_coordinator = SystemCoordinator(self)
        self.setup_systems()

        # --- 分離済みシステムハンドラ (P0 refactor: engine.py 分割) ---
        from engine.systems.combat_system import CombatSystem
        from engine.systems.entity_system import EntitySystem
        from engine.systems.game_loop import GameLoopHandler
        from engine.systems.pet_system import PetSystemHandler
        from engine.systems.render_system import RenderSystemHandler
        from engine.systems.skill_eater_system import SkillEaterSystemHandler
        from engine.systems.ui_system import UISystemHandler
        from engine.systems.world_system import WorldSystem

        self.combat_handler = CombatSystem(self)
        self.world_handler = WorldSystem(self)
        self.entity_handler = EntitySystem(self)
        self.skill_eater_handler = SkillEaterSystemHandler(self)
        self.pet_handler = PetSystemHandler(self)
        self.game_loop_handler = GameLoopHandler(self)
        self.render_handler = RenderSystemHandler(self)
        self.ui_handler = UISystemHandler(self)

        # --- GameStateInitializer によるゲーム状態データの初期化 (Phase 4) ---
        from core.world_state_manager import GameStateInitializer

        self.game_state_initializer = GameStateInitializer(self)
        # Stub registry for faction war to satisfy references in tests/benchmarks
        self.faction_war_registry = {}
        self.game_state_data = self.game_state_initializer.initialize_world_state()

        # Step 27: Unify survival and survival_system to be the same object
        self.kernel.register_system("survival_system", self.game_state_data.survival)

        # --- run 終了状態 (死亡判定と run summary) ---
        # 文字列を素で持ち回さず、許可された遷移だけを通る状態機械にする (Step 10)
        self.game_state_machine = GameStateMachine("playing")
        self.run_summary: RunSummary | None = None
        # 死因とその観測時点の HP の対。HP を添えるのは観測点の間で起きた
        # ダメージ (トラップなど) に死因の観測が無かったことを示すため。
        self._harm_cause: str = CAUSE_UNKNOWN
        self._harm_cause_hp: int | None = None

        # --- エンティティマネージャーに初期エンティティを追加 ---
        self.entity_manager.add_entity(self.game_state_data.player)
        self.entity_manager.add_entity(self.game_state_data.pet)

        # プレイヤーとペットの初期化 (CharacterPackage 経由)
        self.player_pet_initializer(self.kernel, self)

        # --- インベントリアイテムの設定 ---
        self._setup_initial_inventory()

        # ダンジョンスポーン
        self._spawn_dungeon()

        # --- Visual FX & UI システム & Web サービス初期化 (Phase 5) ---
        from core.system_initializer import SystemInitializer

        (
            self.look_cursor,
            self.context_menu,
            self.tutorial_manager,
            self.notification_manager,
            self.web_server,
        ) = SystemInitializer.initialize_ui_and_services(self)

    def __getstate__(self) -> dict:
        """Return state for pickling, excluding unpicklable attributes."""
        state = self.__dict__.copy()
        # Remove unpicklable attributes
        unpicklable = [
            "renderer",  # tcod renderer
            "kernel",  # Kernel with modules
            "systems_coordinator",  # SystemCoordinator
            "combat_handler",  # CombatSystem
            "world_handler",  # WorldSystem
            "entity_handler",  # EntitySystem
            "skill_eater_handler",  # SkillEaterSystemHandler
            "pet_handler",  # PetSystemHandler
            "game_loop_handler",  # GameLoopHandler
            "render_handler",  # RenderSystemHandler
            "ui_handler",  # UISystemHandler
            "game_state_initializer",  # GameStateInitializer
            "web_server",  # HTTPServer
            "localization_manager",  # LocalizationManager
            "config_mgr",  # ConfigManager
            "entity_manager",  # EntityManager
            "player_pet_initializer",  # function
            "_shutdown_hook",  # function
        ]
        for key in unpicklable:
            state.pop(key, None)
        return state

    def __setstate__(self, state: dict) -> None:
        """Restore state after unpickling."""
        self.__dict__.update(state)
        # Don't set unpicklable properties (they have setters that require kernel)
        # These will be None since they were removed in __getstate__

    def _initialize_player_and_pet(self) -> None:
        """プレイヤーとペットの初期化処理"""
        from exceptions import DataParseError

        if not self.game_state_data.player or not self.game_state_data.pet:
            raise DataParseError(
                "Player or Pet entity is missing from game_state_data during initialization"
            )

        # --- プレイヤー (設定駆動) ---
        self.game_state_data.player.god_id = STARTING_GOD_ID
        self.game_state_data.player.piety = 80
        self.game_state_data.player.hp = self.game_state_data.player.max_hp
        self.game_state_data.player.mp = self.game_state_data.player.max_mp
        self.game_state_data.player.status_effects: list[StatusEffect] = []
        self.game_state_data.player.resistances = ResistanceSet()
        self.game_state_data.player.resistances.fire = 10
        self.game_state_data.player.faction = "player"
        self.game_state_data.player.aggro = AggroList()
        self.meta_progression_manager.recalculate_and_apply_bonuses(self.game_state_data.player)

        # --- ペット (設定駆動) ---
        self.game_state_data.pet.status_effects = []
        self.game_state_data.pet.resistances = ResistanceSet()
        self.game_state_data.pet.faction = "player"
        # ペット性格・好物の付与 (改善案6 機能3)
        from pet_personality_system import PetPersonalitySystem

        PetPersonalitySystem.initialize_pet_personality(self.game_state_data.pet)

    def _setup_initial_inventory(self) -> None:
        """初期インベントリアイテムの設定 (GameplayPackage 経由)"""
        from exceptions import ResourceLoadError

        starter_items = self.starter_items_factory(self.kernel)
        if not starter_items:
            raise ResourceLoadError("Failed to generate starter items from factory")
        for itm in starter_items:
            self.game_state_data.inventory.add_item(itm)
        if len(starter_items) >= 2:
            self.game_state_data.inventory.equip(starter_items[0], "main_hand")
            self.game_state_data.inventory.equip(starter_items[1], "off_hand")

        # --- 初期ログ ---
        self.log(
            "『naRogue: Masterpiece Edition』の世界へようこそ！",
            (255, 255, 120),
            level="SUCCESS",
        )
        self.log(
            "妹分シエル「お兄ちゃん、今日も一緒に頑張ろうね！」",
            COLOR_PET_PINK,
            level="INFO",
        )
        self.log(
            "【初心者ガイド】[?]または[h]キーでいつでもヘルプを確認できます！",
            (120, 255, 200),
            level="INFO",
        )
        self.log(
            "【操作】矢印:移動 [Space]:行動 [l]:調査 [i]:カバン [c]:能力 [j]:職業 [Shift+S]:ツリー [Shift+G]:ギルド",
            (180, 220, 255),
            level="INFO",
        )
        self.log(
            "⚡ Web版接続待機中: http://localhost:8080 にアクセスしてブラウザでもプレイ可能！",
            (100, 255, 200),
            level="INFO",
        )
        self._present_run_history()

        self.game_map.compute_fov(self.player.x, self.player.y, radius=8)
        self.check_tutorial_triggers("game_start")

        # Step 6.4: 既定の入力アクションを ActionRegistry に登録
        from input_handler import InputHandler

        InputHandler.register_default_actions()

    # --- プロパティデレゲーション: GameStateData の属性へのアクセス ---
    # これにより、既存のコードは変更せずにゲーム状態データにアクセスできる

    @property
    def player(self) -> Entity:
        """プレイヤーエンティティ"""
        return self.game_state_data.player

    @player.setter
    def player(self, value: Entity) -> None:
        self.game_state_data.player = value

    @property
    def pet(self) -> Entity:
        """ペットエンティティ"""
        return self.game_state_data.pet

    @pet.setter
    def pet(self, value: Entity) -> None:
        self.game_state_data.pet = value

    @property
    def inventory(self) -> Inventory:
        """プレイヤーのインベントリ"""
        return self.game_state_data.inventory

    @inventory.setter
    def inventory(self, value: Inventory) -> None:
        self.game_state_data.inventory = value

    @property
    def pet_inventory(self) -> Inventory:
        """ペットのインベントリ"""
        return self.game_state_data.pet_inventory

    @pet_inventory.setter
    def pet_inventory(self, value: Inventory) -> None:
        self.game_state_data.pet_inventory = value

    @property
    def survival(self) -> SurvivalSystem:
        """サバイバルシステム (Step 27: kernel 登録と同一オブジェクトを返す)

        kernel に "survival_system" として登録されたオブジェクトが正本。
        main_quest_system の報酬書き込み (kernel 経由) と engine.survival の読み出しが
        同一オブジェクトに向くことで、6100金の不活性を防ぐ。
        旧セーブ/未初期化 Engine では game_state_data.survival にフォールバック。
        """
        kernel_survival = self.kernel.get_system("survival_system")
        if kernel_survival is not None:
            return kernel_survival
        return self.game_state_data.survival

    @survival.setter
    def survival(self, value: SurvivalSystem) -> None:
        self.game_state_data.survival = value

    @property
    def systems_mgr(self) -> Any:
        """互換用システムコーディネーター"""
        return self.systems_coordinator

    @property
    def dungeon_level(self) -> int:
        """現在のダンジョンレベル"""
        return self.game_state_data.dungeon_level

    @dungeon_level.setter
    def dungeon_level(self, value: int) -> None:
        """ダンジョンレベルを設定"""
        self.game_state_data.dungeon_level = value

    @property
    def game_map(self) -> Any:
        """現在のゲームマップ"""
        return self.game_state_data.game_map

    @game_map.setter
    def game_map(self, value: Any) -> None:
        """ゲームマップを設定"""
        self.game_state_data.game_map = value

    @property
    def altar_pos(self) -> tuple[int, int]:
        """祭壇の位置"""
        return self.game_state_data.altar_pos

    @altar_pos.setter
    def altar_pos(self, value: tuple[int, int]) -> None:
        """祭壇の位置を設定"""
        self.game_state_data.altar_pos = value

    @property
    def entities(self) -> list[Entity]:
        """ゲーム内のエンティティリスト"""
        return self.entity_manager.get_entities()

    @entities.setter
    def entities(self, value: list[Entity]) -> None:
        """エンティティリストを設定"""
        # 既存のエンティティをすべて削除
        self.entity_manager.entities.clear()
        # 新しいエンティティを追加
        for entity in value:
            self.entity_manager.add_entity(entity)

    @property
    def items_on_ground(self) -> list[Item]:
        """地面上のアイテムリスト"""
        return self.entity_manager.items_on_ground

    @items_on_ground.setter
    def items_on_ground(self, value: list[Item]) -> None:
        """地面上のアイテムリストを設定"""
        # 既存のアイテムをすべて削除
        self.entity_manager.items_on_ground.clear()
        # 新しいアイテムを追加
        for item in value:
            self.entity_manager.add_item(item)

    @property
    def resource_nodes(self) -> list[ResourceNode]:
        """資源ノードリスト"""
        return self.entity_manager.resource_nodes

    @resource_nodes.setter
    def resource_nodes(self, value: list[ResourceNode]) -> None:
        """資源ノードリストを設定"""
        # 既存の資源ノードをすべて削除
        self.entity_manager.resource_nodes.clear()
        # 新しい資源ノードを追加
        for node in value:
            self.entity_manager.add_resource_node(node)

    @property
    def quests(self) -> list[Quest]:
        """クエストリスト"""
        return self.game_state_data.quests

    @quests.setter
    def quests(self, value: list[Quest]) -> None:
        """クエストリストを設定"""
        self.game_state_data.quests = value

    @property
    def current_state(self) -> GameState:
        """現在のゲーム状態"""
        return self.game_state_data.current_state

    @current_state.setter
    def current_state(self, value: GameState) -> None:
        """ゲーム状態を設定"""
        self.game_state_data.current_state = value

    @property
    def game_state(self) -> str:
        """旧互換用ゲーム状態文字列"""
        return self.game_state_data.game_state

    @property
    def territory_state(self) -> Any:
        """テリトリーシステムの状態"""
        from skill_eater_territory_system import TerritoryState

        return TerritoryState.get_instance()

    @territory_state.setter
    def territory_state(self, value: Any) -> None:
        """テリトリーシステムの状態を設定（デシリアライズ用）"""
        from skill_eater_territory_system import TerritoryState

        TerritoryState._instance = value

    @game_state.setter
    def game_state(self, value: str) -> None:
        """旧互換用ゲーム状態文字列を設定"""
        self.game_state_data.game_state = value

    @property
    def help_tab(self) -> int:
        """ヘルプ画面タブ"""
        return self.game_state_data.help_tab

    @help_tab.setter
    def help_tab(self, value: int) -> None:
        """ヘルプ画面タブを設定"""
        self.game_state_data.help_tab = value

    @property
    def inventory_target(self) -> str:
        """インベントリターゲット"""
        return self.game_state_data.inventory_target

    @inventory_target.setter
    def inventory_target(self, value: str) -> None:
        """インベントリターゲットを設定"""
        self.game_state_data.inventory_target = value

    @property
    def inventory_cursor(self) -> int:
        """インベントリカーソル位置"""
        return self.game_state_data.inventory_cursor

    @inventory_cursor.setter
    def inventory_cursor(self, value: int) -> None:
        """インベントリカーソル位置を設定"""
        self.game_state_data.inventory_cursor = value

    @property
    def inventory_tab(self) -> int:
        """インベントリタブ"""
        return self.game_state_data.inventory_tab

    @inventory_tab.setter
    def inventory_tab(self, value: int) -> None:
        """インベントリタブを設定"""
        self.game_state_data.inventory_tab = value

    @property
    def active_dialogue(self) -> tuple[str, str] | None:
        """アクティブなダイアログ"""
        return self.game_state_data.active_dialogue

    @active_dialogue.setter
    def active_dialogue(self, value: tuple[str, str] | None) -> None:
        """アクティブなダイアログを設定"""
        self.game_state_data.active_dialogue = value

    @property
    def wish_input(self) -> str:
        """願いの入力テキスト"""
        return self.game_state_data.wish_input

    @wish_input.setter
    def wish_input(self, value: str) -> None:
        """願いの入力テキストを設定"""
        self.game_state_data.wish_input = value

    @property
    def debug_input(self) -> str:
        """デバッグ入力テキスト"""
        return self.game_state_data.debug_input

    @debug_input.setter
    def debug_input(self, value: str) -> None:
        """デバッグ入力テキストを設定"""
        self.game_state_data.debug_input = value

    @property
    def turns(self) -> int:
        """ターンカウンター"""
        return self.game_state_data.turns

    @turns.setter
    def turns(self, value: int) -> None:
        """ターンカウンターを設定"""
        self.game_state_data.turns = value

    @property
    def arch_interpret_active(self) -> bool:
        """考古学解釈プロンプトのアクティブ状態"""
        return self.game_state_data.arch_interpret_active

    @arch_interpret_active.setter
    def arch_interpret_active(self, value: bool) -> None:
        """考古学解釈プロンプトのアクティブ状態を設定"""
        self.game_state_data.arch_interpret_active = value

    @property
    def arch_interpret_groups_cache(self) -> list[dict[str, Any]]:
        """考古学解釈グループキャッシュ"""
        return self.game_state_data.arch_interpret_groups_cache

    @arch_interpret_groups_cache.setter
    def arch_interpret_groups_cache(self, value: list[dict[str, Any]]) -> None:
        """考古学解釈グループキャッシュを設定"""
        self.game_state_data.arch_interpret_groups_cache = value

    @property
    def arch_interpret_truth_idx(self) -> int:
        """考古学解釈真理インデックス"""
        return self.game_state_data.arch_interpret_truth_idx

    @arch_interpret_truth_idx.setter
    def arch_interpret_truth_idx(self, value: int) -> None:
        """考古学解釈真理インデックスを設定"""
        self.game_state_data.arch_interpret_truth_idx = value

    @property
    def arch_interpret_ending_idx(self) -> int:
        """考古学解釈エンディングインデックス"""
        return self.game_state_data.arch_interpret_ending_idx

    @arch_interpret_ending_idx.setter
    def arch_interpret_ending_idx(self, value: int) -> None:
        """考古学解釈エンディングインデックスを設定"""
        self.game_state_data.arch_interpret_ending_idx = value

    @property
    def last_scan_result(self):
        """直近の解析結果（捕食成功率表示用）"""
        return getattr(self, "_last_scan_result", None)

    @last_scan_result.setter
    def last_scan_result(self, value):
        self._last_scan_result = value

    # --- Kernel システムアクセス用プロパティ (Feature Package Architecture) ---
    @property
    def event_bus(self):
        return self.kernel.get_system("event_bus")

    @property
    def time_system(self):
        return self.kernel.get_system("time_system")

    @property
    def turn_queue(self):
        return self.kernel.get_system("turn_queue")

    @property
    def entity_manager(self):
        return self.kernel.get_system("entity_manager")

    @property
    def renderer(self):
        return self.kernel.get_system("renderer")

    @renderer.setter
    def renderer(self, value):
        self.kernel._systems["renderer"] = value
        set_renderer(value)

    @property
    def message_log(self):
        return self.kernel.get_system("message_log")

    @property
    def msg_log(self):
        return self.kernel.get_system("message_log")

    @property
    def debug_console(self):
        return self.kernel.get_system("debug_console")

    # Gameplay package systems
    @property
    def combat_system(self):
        return self.kernel.get_system("combat_system")

    @property
    def survival_system(self):
        return self.kernel.get_system("survival_system")

    @property
    def starter_items_factory(self):
        return self.kernel.get_system("starter_items_factory")

    @property
    def dungeon_spawner(self):
        return self.kernel.get_system("dungeon_spawner")

    @property
    def gameplay_loop(self):
        return self.kernel.get_system("gameplay_loop")

    # Character package systems
    @property
    def skill_tree_manager(self):
        return self.kernel.get_system("skill_tree_manager")

    @property
    def job_manager(self):
        return self.kernel.get_system("job_manager")

    @property
    def skill_fusion_manager(self):
        return self.kernel.get_system("skill_fusion_manager")

    @property
    def skill_evolution_manager(self):
        return self.kernel.get_system("skill_evolution_manager")

    @property
    def skill_awakening_manager(self):
        return self.kernel.get_system("skill_awakening_manager")

    @property
    def skill_transfer_manager(self):
        return self.kernel.get_system("skill_transfer_manager")

    @property
    def skill_resonance_manager(self):
        return self.kernel.get_system("skill_resonance_manager")

    @property
    def skill_inheritance_manager(self):
        return self.kernel.get_system("skill_inheritance_manager")

    @property
    def skill_specialization_manager(self):
        return self.kernel.get_system("skill_specialization_manager")

    @property
    def player_pet_initializer(self):
        return self.kernel.get_system("player_pet_initializer")

    # Social package systems
    @property
    def guild_manager(self):
        return self.kernel.get_system("guild_manager")

    @property
    def guild_quest_manager(self):
        return self.kernel.get_system("guild_quest_manager")

    @property
    def faction_war_manager(self):
        return self.kernel.get_system("faction_war_manager")

    @property
    def guild_skill_manager(self):
        return self.kernel.get_system("guild_skill_manager")

    @property
    def pet_contract_manager(self):
        return self.kernel.get_system("pet_contract_manager")

    @property
    def pet_evolution_manager(self):
        return self.kernel.get_system("pet_evolution_manager")

    @property
    def pet_fusion_manager(self):
        return self.kernel.get_system("pet_fusion_manager")

    @property
    def relationship_manager(self):
        return self.kernel.get_system("relationship_manager")

    @property
    def procedural_quest_manager(self):
        return self.kernel.get_system("procedural_quest_manager")

    @property
    def quest_generation_registry(self):
        from procedural_quest_generator import REGISTRY

        return REGISTRY

    @property
    def procedural_quest_generator(self):
        from procedural_quest_generator import GENERATOR

        return GENERATOR

    @property
    def quest_scheduler(self):
        return self.kernel.get_system("quest_scheduler")

    # Meta package systems
    @property
    def achievement_manager(self):
        return self.kernel.get_system("achievement_manager")

    @property
    def reincarnation_manager(self):
        return self.kernel.get_system("reincarnation_manager")

    @property
    def inheritance_manager(self):
        return self.kernel.get_system("inheritance_manager")

    @property
    def karma_manager(self):
        return self.kernel.get_system("karma_manager")

    @property
    def reincarnation_dungeon_manager(self):
        return self.kernel.get_system("reincarnation_dungeon_manager")

    @property
    def legacy_skill_manager(self):
        return self.kernel.get_system("legacy_skill_manager")

    @property
    def challenge_manager(self):
        return self.kernel.get_system("challenge_manager")

    @property
    def meta_progression_manager(self):
        return self.kernel.get_system("meta_progression_manager")

    @property
    def title_manager(self):
        return self.kernel.get_system("title_manager")

    # World package systems
    @property
    def procedural_dungeon_generator(self):
        return self.kernel.get_system("procedural_dungeon_generator")

    @property
    def world_event_manager(self):
        return self.kernel.get_system("world_event_manager")

    @property
    def archaeology_manager(self):
        return self.kernel.get_system("archaeology_manager")

    @property
    def world_state_manager(self):
        return self.kernel.get_system("world_state_manager")

    @property
    def dungeon_theme_registry(self):
        return self.kernel.get_system("dungeon_theme_registry")

    # Narrative package systems
    @property
    def storyteller_manager(self):
        return self.kernel.get_system("storyteller_manager")

    @property
    def choice_manager(self):
        return self.kernel.get_system("choice_manager")

    @property
    def dialogue_manager(self):
        return self.kernel.get_system("dialogue_manager")

    @property
    def main_quest_system(self):
        return self.kernel.get_system("main_quest_system")

    @property
    def journal_ui(self):
        return self.kernel.get_system("journal_ui")

    # Platform package systems
    @property
    def web_server_factory(self):
        return self.kernel.get_system("web_server_factory")

    # World A (Skill Eater) package systems
    @property
    def skill_eater_combat_system(self):
        player = self.game_state_data.player
        flags = player.get_component(ProgressionFlagComponent)
        if not flags.skill_eater:
            return None
        return (
            self.kernel.get_system("skill_eater_combat_system")
            if self.kernel.has_system("skill_eater_combat_system")
            else None
        )

    @property
    def skill_eater_registry(self):
        return (
            self.kernel.get_system("skill_eater_registry")
            if self.kernel.has_system("skill_eater_registry")
            else None
        )

    @property
    def skill_eater_synthesis_system(self):
        return (
            self.kernel.get_system("skill_eater_synthesis_system")
            if self.kernel.has_system("skill_eater_synthesis_system")
            else None
        )

    @property
    def skill_eater_toxicity_manager(self):
        return (
            self.kernel.get_system("skill_eater_toxicity_manager")
            if self.kernel.has_system("skill_eater_toxicity_manager")
            else None
        )

    @property
    def slum_base_expansion_manager(self):
        return (
            self.kernel.get_system("slum_base_expansion_manager")
            if self.kernel.has_system("slum_base_expansion_manager")
            else None
        )

    @property
    def skill_eater_pet_dispatch_manager(self):
        return (
            self.kernel.get_system("skill_eater_pet_dispatch_manager")
            if self.kernel.has_system("skill_eater_pet_dispatch_manager")
            else None
        )

    @property
    def skill_eater_underground_arena(self):
        return (
            self.kernel.get_system("skill_eater_underground_arena")
            if self.kernel.has_system("skill_eater_underground_arena")
            else None
        )

    @property
    def skill_eater_bounty_system(self):
        return (
            self.kernel.get_system("skill_eater_bounty_system")
            if self.kernel.has_system("skill_eater_bounty_system")
            else None
        )

    @property
    def skill_eater_ascension_board(self):
        return (
            self.kernel.get_system("skill_eater_ascension_board")
            if self.kernel.has_system("skill_eater_ascension_board")
            else None
        )

    @property
    def skill_eater_concept_crystal(self):
        return (
            self.kernel.get_system("skill_eater_concept_crystal")
            if self.kernel.has_system("skill_eater_concept_crystal")
            else None
        )

    @property
    def skill_eater_temporal_vault(self):
        return (
            self.kernel.get_system("skill_eater_temporal_vault")
            if self.kernel.has_system("skill_eater_temporal_vault")
            else None
        )

    @property
    def skill_eater_epilogue_manager(self):
        return (
            self.kernel.get_system("skill_eater_epilogue_manager")
            if self.kernel.has_system("skill_eater_epilogue_manager")
            else None
        )

    @property
    def skill_eater_meta_intervention(self):
        return (
            self.kernel.get_system("skill_eater_meta_intervention")
            if self.kernel.has_system("skill_eater_meta_intervention")
            else None
        )

    @property
    def skill_eater_intervention_engine(self):
        return (
            self.kernel.get_system("skill_eater_intervention_engine")
            if self.kernel.has_system("skill_eater_intervention_engine")
            else None
        )

    @property
    def skill_eater_exploration_system(self):
        return (
            self.kernel.get_system("skill_eater_exploration_system")
            if self.kernel.has_system("skill_eater_exploration_system")
            else None
        )

    # --- スキルイーターシステム (SkillEaterSystemHandler へ委譲) ---
    def execute_scan(self) -> bool:
        """周囲の対象をスキャン・解析する (Step 14, 20, 38, 39)"""
        return self.skill_eater_handler.execute_scan()

    def execute_devour(self) -> bool:
        """隣接する敵からスキルを強奪する《喰らい》 (Steps 25-36)"""
        return self.skill_eater_handler.execute_devour()

    def _register_devoured_skill(self, skill_id: str, sk_def) -> None:
        """奪ったスキルを唱えられるスキル (`player.skills`) へ登録する。"""
        self.skill_eater_handler._register_devoured_skill(skill_id, sk_def)

    def execute_synthesis(self, skill_a: str | None = None, skill_b: str | None = None) -> bool:
        """スキル合成を実行する (Steps 43-47)"""
        return self.skill_eater_handler.execute_synthesis(skill_a, skill_b)

    def execute_pet_dispatch(
        self, mission_name: str, duration_turns: int = 10, reward_gold: int = 500
    ) -> bool:
        """ペットをスラム街の探索・調達任務に派遣する (Step 54-56)"""
        return self.skill_eater_handler.execute_pet_dispatch(mission_name, duration_turns, reward_gold)

    def execute_base_upgrade(self, facility_id: str, cost_aldo: int = 1000) -> bool:
        """スラム街の拠点を拡張・改修する (Step 54)"""
        return self.skill_eater_handler.execute_base_upgrade(facility_id, cost_aldo)

    def execute_solve_puzzle(self, puzzle_type: str, used_skill_tag: str) -> bool:
        """環境パズルを所持スキルで解除する (Step 57-59)"""
        return self.skill_eater_handler.execute_solve_puzzle(puzzle_type, used_skill_tag)

    def switch_world(self, world_id: str) -> bool:
        """ワールド間遷移（Aの世界 / 本編ワールドの切り替え） (Step 61-62)"""
        return self.skill_eater_handler.switch_world(world_id)

    def execute_epilogue_world_transition(self) -> bool:
        """Aの世界エピローグ＆次元ゲート開放 (Step 69-70)"""
        return self.skill_eater_handler.execute_epilogue_world_transition()

    @property
    def input_handler(self):
        return self.kernel.get_system("input_handler")

    def setup_systems(self) -> None:
        """各種マネージャーとサブシステムの生成・初期化 (setup_coordinator に委譲)"""
        from core.systems.setup_coordinator import setup_systems

        setup_systems(self)

    @property
    def floating_texts(self) -> list[FloatingText]:
        return self.fx_manager.floating_texts

    @floating_texts.setter
    def floating_texts(self, val: list[FloatingText]) -> None:
        self.fx_manager.floating_texts = val

    @property
    def particles(self) -> list[Particle]:
        return self.fx_manager.particles

    @particles.setter
    def particles(self, val: list[Particle]) -> None:
        self.fx_manager.particles = val

    @property
    def screen_shake(self) -> ScreenShake:
        return self.fx_manager.screen_shake

    @screen_shake.setter
    def screen_shake(self, val: ScreenShake) -> None:
        self.fx_manager.screen_shake = val

    def change_state(self, new_state: GameState) -> None:
        """状態遷移（ステートマシン）の厳格化とフック処理 (StateMachine に委譲)"""
        from core.state_machine import StateMachine

        StateMachine().apply(self, new_state)

    def open_journal(self) -> None:
        """冒険日誌を開く"""
        self.journal_ui.toggle()
        if self.journal_ui.visible:
            self.game_state = "journal"
        else:
            self.game_state = "play"

    def open_context_menu(self) -> None:
        """Spaceキーによる文脈アクション候補の動的生成 (ContextMenuBuilder に委譲)"""
        from managers.context_menu_builder import ContextMenuBuilder

        actions = ContextMenuBuilder().build_actions(self)
        if actions:
            self.context_menu.set_actions(actions)
            self.game_state = "context"
        else:
            self.log("周囲にアクション可能な対象がない。")

    def log(
        self,
        text: str,
        color: tuple[int, int, int] = (230, 230, 230),
        level: str = "INFO",
    ) -> None:
        self.msg_log.add(text, color, level=level)

    def check_tutorial_triggers(self, trigger_condition: str) -> Any | None:
        """チュートリアルの発動条件を検知し、未完了なら通知・ポップアップ設定 (Step 1.2)"""
        if not hasattr(self, "tutorial_manager") or not self.player:
            return None
        guide = self.tutorial_manager.check_triggers(
            trigger_condition, self.player.completed_tutorials
        )
        if guide:
            self.player.completed_tutorials.add(guide.id)
            self.player.pending_tutorial_popup = guide.to_dict()
            # ログにも案内表示
            self.log(
                f"📖【ガイド】{guide.title}: {guide.message}",
                (100, 255, 200),
                level="SUCCESS",
            )
            # 画面上部ポップアップ通知キューにも登録
            if hasattr(self, "notification_manager"):
                self.notification_manager.notify(
                    title=f"📖 ガイド: {guide.title}",
                    message=guide.message,
                    category="tutorial",
                    color=(100, 255, 200),
                    duration=40,
                )
            return guide
        return None

    def _spawn_dungeon(self) -> None:
        """ダンジョン内のエンティティ生成 (GameplayPackage 経由)"""
        try:
            self.dungeon_spawner(self.kernel, self)
        except Exception as e:
            logger.exception("Failed to spawn dungeon entities: %s", e)
            from exceptions import ResourceLoadError

            raise ResourceLoadError(f"Dungeon spawn failure: {e}") from e

    def has_los(self, p1: Point, p2: Point) -> bool:
        """射線判定 (ステップ21)"""
        line = bresenham_line(p1, p2)
        for pt in line[1:-1]:
            if not self.game_map.is_transparent(pt.x, pt.y):
                return False
        return True

    def get_blocked_positions(self) -> set[tuple[int, int]]:
        """全生存エンティティの座標セット (O(1)衝突判定用)"""
        return self.entity_manager.get_blocked_positions()

    def is_tile_free(self, x: int, y: int, blocked: set[tuple[int, int]] | None = None) -> bool:
        if not self.game_map.is_walkable(x, y):
            return False
        if blocked is not None:
            return (x, y) not in blocked
        return not self.entity_manager.is_position_blocked(x, y)

    def get_entity_at(self, x: int, y: int) -> Entity | None:
        """指定された位置にあるエンティティを取得する"""
        return self.entity_manager.get_entity_at(x, y)

    def player_act(self, dx: int, dy: int) -> bool:
        """プレイヤー行動 (GameplayPackage 経由)

        GAME_OVER 後は行動を受け付けない。死亡画面を閉じたまま遺体が歩き回る
        状態を作らないための門 ([S2.1] が求める world と turn の停止とは別物)。
        """
        if self.game_state_machine.current != "playing":
            return False
        return self.gameplay_loop(self.kernel, self).player_act(dx, dy)

    # -------------------------------------------------------------
    # P0 リファクタ: 分離済みシステムハンドラへの委譲
    # 実装は engine/systems/{combat,world,entity,skill_eater,pet,game_loop,ui,render}_system.py
    # -------------------------------------------------------------

    def _on_player_death(self) -> None:
        """プレイヤー死亡時の統一ハンドラ (GameLoopHandler へ委譲)"""
        self.game_loop_handler._on_player_death()

    def _on_kill(self, entity: Entity) -> None:
        """撃破処理 (CombatSystem へ委譲)"""
        self.combat_handler.handle_kill(entity)

    def _progress_generated_quests(self, event_type: str, target_id: str, amount: int = 1) -> None:
        """プロシージャル生成クエストの進捗をゲームイベントから通知 (Steps 34, 36)"""
        mgr = getattr(self, "procedural_quest_manager", None)
        if mgr is None or self.player is None:
            return
        msgs = mgr.update_progress(self.player, event_type, target_id, amount, self)
        for m in msgs:
            self.log(m, (255, 215, 0), level="SUCCESS")

    def _end_run_if_player_dead(self) -> bool:
        """死亡判定と run 終了 (GameLoopHandler へ委譲)"""
        return self.game_loop_handler._end_run_if_player_dead()

    def _record_harm_cause(self, cause: str) -> None:
        """死因記録 (GameLoopHandler へ委譲)"""
        self.game_loop_handler._record_harm_cause(cause)

    def _observed_harm_cause(self) -> str:
        """死因観測 (GameLoopHandler へ委譲)"""
        return self.game_loop_handler._observed_harm_cause()

    def _build_run_summary(self) -> RunSummary:
        """run summary 組み立て (GameLoopHandler へ委譲)"""
        return self.game_loop_handler._build_run_summary()

    def _present_run_summary(self, summary: RunSummary) -> None:
        """run summary 提示 (GameLoopHandler へ委譲)"""
        self.game_loop_handler._present_run_summary(summary)

    def _record_run_history(self, summary: RunSummary) -> None:
        """run 履歴記録 (GameLoopHandler へ委譲)"""
        self.game_loop_handler._record_run_history(summary)

    def _present_run_history(self) -> None:
        """前回 run 記録提示 (GameLoopHandler へ委譲)"""
        self.game_loop_handler._present_run_history()

    def check_win_condition(self) -> bool:
        """勝利条件判定 (WorldSystem へ委譲)"""
        return self.world_handler.check_win_condition()

    def advance_world(self) -> None:
        """速度Tick制による全NPCターン処理 (GameLoopHandler へ委譲)"""
        self.game_loop_handler.advance_world()

    def pass_turn(self) -> list[str]:
        """待機アクション: 生存システムのターン処理のみ実行し、世界を1tick進める"""
        logs = []
        if hasattr(self, "survival") and self.survival:
            logs.extend(self.survival.pass_turn(self.player, self))
        # 世界進行 (NPCのターン処理など)
        self.advance_world()
        return logs

    def _pet_ai(self) -> None:
        """ペットAI (EntitySystem へ委譲)"""
        self.entity_handler.pet_ai()

    def _npc_ai(self, npc: Entity) -> None:
        """NPC AI (EntitySystem へ委譲)"""
        self.entity_handler.npc_ai(npc)

    def talk_to_neighbor(self) -> None:
        """近隣住民との会話 (EntitySystem へ委譲)"""
        self.entity_handler.talk_to_neighbor()

    def harvest_resource(self) -> None:
        """採取 (EntitySystem へ委譲)"""
        self.entity_handler.harvest_resource()

    def cast_fireball(self) -> None:
        """ファイアボール詠唱 (CombatSystem へ委譲)"""
        self.combat_handler.cast_fireball()

    def mine_wall(self) -> None:
        """壁掘り (UISystemHandler へ委譲)"""
        self.ui_handler.mine_wall()

    def excavate(self) -> None:
        """考古学発掘 (UISystemHandler へ委譲)"""
        self.ui_handler.excavate()

    def _arch_interpret_groups(self) -> list[dict[str, Any]]:
        """解釈候補グループ化 (UISystemHandler へ委譲)"""
        return self.ui_handler._arch_interpret_groups()

    def open_interpret_prompt(self) -> None:
        """解釈プロンプト開始 (UISystemHandler へ委譲)"""
        self.ui_handler.open_interpret_prompt()

    def interpret_move_truth(self, delta: int) -> None:
        """解釈真理移動 (UISystemHandler へ委譲)"""
        self.ui_handler.interpret_move_truth(delta)

    def interpret_move(self, delta: int) -> None:
        """解釈エンディング移動 (UISystemHandler へ委譲)"""
        self.ui_handler.interpret_move(delta)

    def confirm_interpret(self) -> None:
        """解釈決定 (UISystemHandler へ委譲)"""
        self.ui_handler.confirm_interpret()

    def cancel_interpret(self) -> None:
        """解釈取消 (UISystemHandler へ委譲)"""
        self.ui_handler.cancel_interpret()

    def play_music(self) -> None:
        """演奏 (PetSystemHandler へ委譲)"""
        self.pet_handler.play_music()

    def pray(self) -> None:
        """祈り (PetSystemHandler へ委譲)"""
        self.pet_handler.pray()

    def offer_altar(self) -> None:
        """祭壇への供物 (PetSystemHandler へ委譲)"""
        self.pet_handler.offer_altar()

    def use_wish_rod(self) -> None:
        """願いの杖 (PetSystemHandler へ委譲)"""
        self.pet_handler.use_wish_rod()

    def use_pet_evolution_stone(self) -> None:
        """ペット進化石 (PetSystemHandler へ委譲)"""
        self.pet_handler.use_pet_evolution_stone()

    def use_alchemy_lab(self) -> None:
        """アルケミーラボ (PetSystemHandler へ委譲)"""
        self.pet_handler.use_alchemy_lab()

    def confirm_wish(self) -> None:
        """願い確定 (PetSystemHandler へ委譲)"""
        self.pet_handler.confirm_wish()

    def descend_stairs(self) -> None:
        """階段降下 (WorldSystem へ委譲)"""
        self.world_handler.descend_stairs()

    def check_reincarnation_option(self) -> bool:
        """転生オプション判定 (UISystemHandler へ委譲)"""
        return self.ui_handler.check_reincarnation_option()

    def reincarnate(self) -> None:
        """転生処理 (UISystemHandler へ委譲)"""
        self.ui_handler.reincarnate()

    def help_friend(self) -> None:
        """フレンド救援 (UISystemHandler へ委譲)"""
        self.ui_handler.help_friend()

    def update(self, delta_time: float = 1.0) -> None:
        """ゲームロジック更新 (GameLoopHandler へ委譲)"""
        self.game_loop_handler.update(delta_time)

    def render(self, console: Any) -> None:
        """描画処理 (RenderSystemHandler へ委譲)"""
        self.render_handler.render(console)
    def render_to_text(self, tr: Any) -> None:
        """Step 12-16: TextRenderer へマップ/エンティティ/HUD/ログを描画。"""

        tr.clear()

        player = self.player
        if player is None or self.game_map is None:
            tr.draw_text(0, 0, "Loading...", (255, 255, 255))
            tr.present()
            return

        # Step 13: カメラ付きマップ描画
        cam_x = max(0, min(player.x - VIEW_WIDTH // 2, MAP_WIDTH - VIEW_WIDTH))
        cam_y = max(0, min(player.y - VIEW_HEIGHT // 2, MAP_HEIGHT - VIEW_HEIGHT))
        for sy in range(tr.height):
            wy = cam_y + sy
            for sx in range(tr.width):
                wx = cam_x + sx
                if 0 <= wx < MAP_WIDTH and 0 <= wy < MAP_HEIGHT:
                    tile = self.game_map.tiles[wx][wy]
                    disp = self._TILE_DISPLAY.get(tile)
                    if disp is None:
                        disp = (".", (90, 90, 90))
                    tr.draw_tile(sx, sy, disp[0], disp[1])

        # Step 14: エンティティ描画
        for ent in self.entities:
            sx = ent.x - cam_x
            sy = ent.y - cam_y
            if 0 <= sx < tr.width and 0 <= sy < tr.height:
                if ent is player:
                    ch = "@"
                    col = (255, 255, 255)
                elif getattr(ent, "faction", None) == "player":
                    ch = getattr(ent, "char", "p") or "p"
                    col = getattr(ent, "color", (255, 180, 210)) or (255, 180, 210)
                else:
                    ch = getattr(ent, "char", None) or (ent.name[:1] if ent.name else "m")
                    col = getattr(ent, "color", (220, 80, 80)) or (220, 80, 80)
                tr.draw_tile(sx, sy, str(ch)[0], col)

        # Step 15: HUD (HP/MP)
        hp = getattr(player, "hp", 0)
        max_hp = getattr(player, "max_hp", 0)
        mp = getattr(player, "mp", 0)
        max_mp = getattr(player, "max_mp", 0)
        dlvl = getattr(self, "dungeon_level", 0)
        hud = f"HP:{hp}/{max_hp} MP:{mp}/{max_mp} Lv:{getattr(player, 'level', 1)} D:{dlvl}"
        tr.draw_text(0, 0, hud, (255, 255, 255))

        # Step 16: メッセージログ (最下行)
        log = self.message_log
        if log is not None:
            recent = log.get_recent(3)
            base_y = tr.height - len(recent)
            for i, msg in enumerate(recent):
                tr.draw_text(
                    0,
                    base_y + i,
                    msg.text[: tr.width],
                    getattr(msg, "color", (230, 230, 230)),
                )

        tr.present()

    def run_text_mode(self, width: int = 80, height: int = 50) -> None:
        """Step 18: テキスト入力でゲームを進行する最小ループ。"""
        from core.text_renderer import TextRenderer, get_text_action
        from input_actions import MovementAction, WaitAction

        tr = TextRenderer(width, height)
        show_guide = True  # Step 40: 操作ガイド表示トグル
        self.log(
            "テキストモード開始: w/a/s/d で移動, . で待機, ? でガイド, q で終了", (100, 255, 100)
        )
        while True:
            self.render_to_text(tr)
            if show_guide:
                tr.draw_text(
                    0, height - 1, "w/a/s/d:移動  .:待機  ?:ガイド  q:終了", (150, 200, 255)
                )
                tr.present()
            action = get_text_action()
            if "quit" in action:
                self.log("テキストモード終了。", (200, 200, 200))
                break
            elif action.get("unknown") == "?":
                show_guide = not show_guide
                self.log(f"操作ガイド: {'ON' if show_guide else 'OFF'}", (200, 200, 200))
            elif "move" in action:
                dx, dy = action["move"]
                MovementAction(dx, dy).execute(self, None)
            elif "wait" in action:
                WaitAction().execute(self, None)
            else:
                self.log(f"未知のコマンド: {action.get('unknown', '')}", (255, 200, 80))


def get_tabbed_items(engine: Engine) -> list[Item]:
    """RenderSystem への委譲 (後方互換性)"""
    from render_context import RenderContext
    from render_system import RenderSystem

    # Create render context
    render_context = RenderContext(
        game_map=engine.game_state_data.game_map,
        player=engine.game_state_data.player,
        pet=engine.game_state_data.pet,
        entities=engine.entity_manager.get_entities(),
        items_on_ground=engine.entity_manager.items_on_ground,
        resource_nodes=engine.entity_manager.resource_nodes,
        survival=engine.game_state_data.survival,
        floating_texts=engine.fx_manager.floating_texts,
        particles=engine.fx_manager.particles,
        look_cursor=engine.look_cursor,
        game_state=engine.game_state_data.game_state,
        time_system=engine.time_system,
        dungeon_level=engine.game_state_data.dungeon_level,
        msg_log=engine.msg_log,
        fx_manager=engine.fx_manager,
        notification_manager=engine.notification_manager,
        achievement_notifications=getattr(
            engine.game_state_data.player, "achievement_notifications", []
        ),
        current_weather=getattr(engine, "current_weather", "fog"),
        casting_spell=getattr(engine, "casting_spell", None),
        frame_count=getattr(engine, "frame_count", 0),
        inventory_target=engine.inventory_target,
        inventory_tab=engine.inventory_tab,
        inventory_cursor=engine.inventory_cursor,
        pet_inventory=engine.game_state_data.pet_inventory,
        altar_pos=engine.game_state_data.altar_pos,
        localization_manager=engine.localization_manager,
        world_a_data=engine.game_state_data.world_a_data,
        toxicity_manager=engine.skill_eater_toxicity_manager,
        skill_eater_combat_system=engine.skill_eater_combat_system,
        color_vision_mode=engine.config_mgr.get("accessibility.color_vision") or "none",
        last_scan_result=getattr(engine, "last_scan_result", None),
    )
    return RenderSystem.get_tabbed_items(render_context)


def render_all(console: tcod.console.Console, engine: Engine) -> None:
    """RenderSystem への委譲 (後方互換性)"""
    if engine.game_state_data.game_state == "skill_tree":
        from ui_fx_systems import format_skill_tree_display

        skill_tree_text = format_skill_tree_display(engine.skill_tree_registry)
        y = 1
        for line in skill_tree_text.splitlines():
            console.print(x=1, y=y, string=line, fg=(255, 255, 255))
            y += 1
        return
    from render_context import RenderContext
    from render_system import RenderSystem

    # Create render context
    render_context = RenderContext(
        game_map=engine.game_state_data.game_map,
        player=engine.game_state_data.player,
        pet=engine.game_state_data.pet,
        entities=engine.entity_manager.get_entities(),
        items_on_ground=engine.entity_manager.items_on_ground,
        resource_nodes=engine.entity_manager.resource_nodes,
        survival=engine.game_state_data.survival,
        floating_texts=engine.fx_manager.floating_texts,
        particles=engine.fx_manager.particles,
        look_cursor=engine.look_cursor,
        game_state=engine.game_state_data.game_state,
        time_system=engine.time_system,
        dungeon_level=engine.game_state_data.dungeon_level,
        msg_log=engine.msg_log,
        fx_manager=engine.fx_manager,
        notification_manager=engine.notification_manager,
        achievement_notifications=getattr(
            engine.game_state_data.player, "achievement_notifications", []
        ),
        current_weather=getattr(engine, "current_weather", "fog"),
        casting_spell=getattr(engine, "casting_spell", None),
        frame_count=getattr(engine, "frame_count", 0),
        inventory_target=engine.inventory_target,
        inventory_tab=engine.inventory_tab,
        inventory_cursor=engine.inventory_cursor,
        pet_inventory=engine.game_state_data.pet_inventory,
        altar_pos=engine.game_state_data.altar_pos,
        localization_manager=engine.localization_manager,
        world_a_data=engine.game_state_data.world_a_data,
        toxicity_manager=engine.skill_eater_toxicity_manager,
        skill_eater_combat_system=engine.skill_eater_combat_system,
        color_vision_mode=engine.config_mgr.get("accessibility.color_vision") or "none",
        last_scan_result=getattr(engine, "last_scan_result", None),
    )
    RenderSystem.render_all(console, render_context)


def main() -> None:
    from input_handler import InputHandler

    engine = Engine()
    logger.debug("Engine created successfully")

    # Load tileset to avoid libtcod font fallback warning
    from pathlib import Path

    tileset_path = Path("assets/tiles/tileset_32x32.png")
    if tileset_path.exists():
        tileset = tcod.tileset.load_tilesheet(
            tileset_path.as_posix(), 32, 8, tcod.tileset.CHARMAP_TCOD
        )
    else:
        tileset = tcod.tileset.procedural_block_elements()

    try:
        with tcod.context.new(
            columns=SCREEN_WIDTH,
            rows=SCREEN_HEIGHT,
            tileset=tileset,
            title="naRogue: Masterpiece Edition - Steps 1~72 Complete",
            vsync=True,
        ) as context:
            root_console = tcod.console.Console(SCREEN_WIDTH, SCREEN_HEIGHT, order="F")

            while True:
                engine.update()
                engine.render(root_console)
                context.present(root_console)
                # Step 6.5: 入力を ActionRegistry 経由で処理
                for event in tcod.event.get(timeout=0):
                    if isinstance(event, tcod.event.KeyDown):
                        if event.sym == tcod.event.KeySym.S:
                            # GAME_OVER は解除しない (画面だけ消えると world が
                            # 動かないまま操作を続けられる中途半端な状態になる)
                            if engine.current_state is not GameState.GAME_OVER:
                                engine.game_state = "skill_tree"
                            continue
                        elif event.sym == tcod.event.KeySym.J:
                            if engine.current_state is not GameState.GAME_OVER:
                                engine.game_state = "job"
                            continue
                        elif event.sym == tcod.event.KeySym.G:
                            # Toggle Tiny Rogue graphics
                            from feature_flags import is_enabled, set_flag

                            new_state = not is_enabled("ENABLE_TINY_ROGUE_GFX")
                            set_flag("ENABLE_TINY_ROGUE_GFX", new_state)
                            engine.log(
                                f"Tiny Rogue graphics: {'ON' if new_state else 'OFF'}",
                                (100, 255, 100) if new_state else (255, 100, 100),
                            )
                            continue
                        elif event.sym == tcod.event.KeySym.ESCAPE:
                            if engine.game_state in ("skill_tree", "job"):
                                engine.game_state = "play"
                            else:
                                # keep existing ESC handling for other states
                                pass
                            continue
                    InputHandler.handle_event(event, engine)
    except Exception as e:
        logger.exception("ロード失敗")
        # SDL コンテキストを作れない場合（ヘッドレス/ GPU なし等）のフォールバック
        from feature_flags import get_text_mode_enabled

        if get_text_mode_enabled():
            logger.warning("SDL context unavailable (%s); falling back to text mode.", e)
            engine.run_text_mode(SCREEN_WIDTH, SCREEN_HEIGHT)
            return
        # Web サーバーのみでテストしたい場合はそのまま待機
        logger.warning("Could not initialize SDL context: %s", e)
        logger.info("Web server is still running. Access it at http://localhost:8080")
        import time

        while True:
            time.sleep(1)


if __name__ == "__main__":
    main()
