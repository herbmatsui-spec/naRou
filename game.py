"""
Elona Roguelike Ultimate Masterpiece - Full Integration game.py
Steps 1-72 all systems unified: Speed Tick, A* AI, LOS, UUID Items, Cursed Items,
Food Rot, AoE+FriendlyFire, Bleeding, Crafting, Wish Parser, CompressedSave, DebugConsole,
Status Screen, Tabbed Inventory, Colored Logs, Faction/Aggro
"""
from __future__ import annotations
import random
from typing import List, Optional, Tuple, Dict, Any, Set

import tcod
import tcod.event

from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, MAP_WIDTH, MAP_HEIGHT, ENERGY_THRESHOLD, TILE_WALL, TILE_FLOOR, TILE_STAIRS_DOWN, TILE_TRAP,
    COLOR_GOLD_YELLOW, COLOR_PET_PINK, Element, GameState,
    SPAWN_SNAIL_CHANCE, SPAWN_MONSTER_CHANCE, SPAWN_ITEM_CHANCE, SPAWN_RESOURCE_NODE_CHANCE,
    SNAIL_SPEED, SNAIL_COLOR,
    TITLE_CHECK_INTERVAL, JOB_EXP_PER_TURN, JOB_LEVEL_UP_THRESHOLD,
    SKILL_TREE_CHECK_INTERVAL, SKILL_POINTS_NOTIFICATION_THRESHOLD,
    GUILD_QUEST_RESET_INTERVAL, FACTION_INFLUENCE_INTERVAL,
    PET_WALKING_BOND_DISTANCE, PET_NEGLECTED_BOND_DISTANCE, PET_PATH_LENGTH_CHECK,
    AUTO_SAVE_INTERVAL
)
from core_framework import Point, bresenham_line, AStar, EventBus, MessageLog
from turn_manager import TimeSystem, TurnQueue
from entity import Entity, GodInfo
from game_state import GameStateData
from map_engine import GameMap
from system_coordinator import SystemCoordinator
from entity_manager import EntityManager
from item_system import (
    Item, Inventory, create_sample_item,
    CAT_FOOD, QUALITY_NORMAL,
)
from systems import (
    CombatSystem, SurvivalSystem, MonsterPreset, Quest,
    StatusEffect, FACTION_GUARD, ResistanceSet, AggroList,
)
from advanced_systems import (
    ResourceNode, WishParser, UniqueItemManager, SaveSystem, DebugConsole,
)
from sound_manager import SoundManager
from fx_manager import FXManager
from ui_fx_systems import (
    FloatingText, Particle, LookCursor, ContextMenu, ContextAction,
    TutorialManager, NotificationManager, ScreenShake
)
from web_server import start_web_server
from skill_tree_system import SkillTreeRegistry, SkillTreeManager
from job_system import JobRegistry, JobManager
from skill_fusion_system import FusionRegistry
from guild_system import GuildRegistry, GuildManager
from guild_quest_system import GuildQuestRegistry, GuildQuestManager
from faction_war_system import FactionWarRegistry, FactionWarManager
from guild_skill_system import GuildSkillRegistry, GuildSkillManager
from pet_contract_system import PetContractRegistry, PetContractManager
from config_manager import get_config_manager
from renderer import Renderer, get_renderer, set_renderer
from pet_evolution_system import PetEvolutionRegistry, PetEvolutionManager
from pet_fusion_system import PetFusionRegistry, PetFusionManager
from dialogue_system import DialogueManager
from systems_manager import SystemManager


class Engine:
    """計画書1〜72ステップ完全統合エンジン (商用疎結合アーキテクチャ)"""
    def __init__(self, renderer: Renderer | None = None):
        # --- レンダラ設定 (Step 3) ---
        if renderer is not None:
            self.renderer = renderer
            set_renderer(renderer)
        else:
            self.renderer = get_renderer()

        # --- 設定管理 (Step 4) ---
        self.config_mgr = get_config_manager()
        player_cfg = self.config_mgr.get_player_config()
        pet_cfg = self.config_mgr.get_pet_config()

        # --- 依存性注入 & SystemManager 初期化 (Phase 1: Step 1-7, 8) ---
        self.systems_coordinator = SystemCoordinator(self)
        self.setup_systems()

# --- ゲーム状態データの初期化 ---
        self.game_state_data = GameStateData(
            player=Entity(
                x=player_cfg.get("start_x", 20),
                y=player_cfg.get("start_y", 20),
                char=player_cfg.get("char", "@"),
                color=tuple(player_cfg.get("color", [255, 255, 255])),
                name=player_cfg.get("name", "名無しの冒険者"),
                is_player=True,
                speed=player_cfg.get("speed", 85),
                attributes=player_cfg.get("attributes", {}),
            ),
            pet=Entity(
                x=pet_cfg.get("start_x", 21),
                y=pet_cfg.get("start_y", 20),
                char=pet_cfg.get("char", "p"),
                color=tuple(pet_cfg.get("color", [255, 180, 210])),
                name=pet_cfg.get("name", "妹分『シエル』"),
                is_pet=True,
                speed=pet_cfg.get("speed", 90),
                attributes=pet_cfg.get("attributes", {}),
            ),
            inventory=Inventory(max_items=26, max_weight=60.0),
            pet_inventory=Inventory(max_items=12, max_weight=30.0),
            survival=SurvivalSystem(),
        )

        # --- エンティティマネージャーの初期化 ---
        self.entity_manager = EntityManager()
        # 初期エンティティを追加
        self.entity_manager.add_entity(self.game_state_data.player)
        self.entity_manager.add_entity(self.game_state_data.pet)
        # アイテムとリソースノードのリストは空で初期化（EntityManager内で管理）

        # --- マップ ---
        self.game_state_data.dungeon_level = 1
        self.game_state_data.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT, floor_level=self.game_state_data.dungeon_level)
        self.game_state_data.game_map.generate_dungeon()
        self.game_state_data.player.x, self.game_state_data.player.y = self.game_state_data.game_map.start_pos
        self.game_state_data.pet.x = self.game_state_data.player.x + 1
        self.game_state_data.pet.y = self.game_state_data.player.y

        rx, ry = self.game_state_data.game_map.rooms[0].center
        self.game_state_data.altar_pos = (rx + 2, ry)

        # プレイヤーとペットの初期化
        self._initialize_player_and_pet()

        # --- インベントリアイテムの設定 ---
        self._setup_initial_inventory()

        # エンティティマネージャーに初期エンティティを設定（すでに追加済み）
        # アイテムとリソースノードのリストは空で初期化済み
        self._spawn_dungeon()

        # --- クエスト・状態 ---
        self.game_state_data.quests = [
            Quest(title="ぷち掃討の栄誉", target_monster="ぷち",  target_count=3, reward_gold=350,  reward_platinum=2),
            Quest(title="オーク討伐令",   target_monster="オーク", target_count=2, reward_gold=750, reward_platinum=3),
        ]
        self.game_state_data.current_state = GameState.EXPLORING  # Step 6.1, 6.2
        self.game_state_data.game_state = "play"  # 旧互換用: "play","inventory","status","debug","wish","look","context","help"
        self.game_state_data.help_tab = 0         # 0..3 ヘルプ画面タブ
        self.game_state_data.inventory_target = "player"
        self.game_state_data.inventory_cursor = 0
        self.game_state_data.inventory_tab = 0   # 0=全 1=武器 2=防具 3=消費 4=その他
        self.game_state_data.active_dialogue: Optional[Tuple[str, str]] = None
        self.game_state_data.wish_input = ""
        self.game_state_data.debug_input = ""
        self.game_state_data.turns = 0
        # 考古学 解釈プロンプト状態 (改善②)
        self.game_state_data.arch_interpret_active = False
        self.game_state_data.arch_interpret_groups_cache: List[Dict[str, Any]] = []
        self.game_state_data.arch_interpret_truth_idx = 0
        self.game_state_data.arch_interpret_ending_idx = 0

# --- Visual FX & UI システム (Phase 1-9, FXManager委譲) ---
        self.look_cursor = LookCursor(self.game_state_data.player.x, self.game_state_data.player.y)
        self.context_menu = ContextMenu()
        self.tutorial_manager = TutorialManager()
        self.notification_manager = NotificationManager()
        self.web_server = start_web_server(self, port=8080)
        print("DEBUG: Web server started")
        print("DEBUG: Web server started")

    def _initialize_player_and_pet(self) -> None:
        """プレイヤーとペットの初期化処理"""
        # --- プレイヤー (設定駆動) ---
        self.game_state_data.player.god_id = "jure"
        self.game_state_data.player.piety = 80
        self.game_state_data.player.hp = self.game_state_data.player.max_hp
        self.game_state_data.player.mp = self.game_state_data.player.max_mp
        self.game_state_data.player.status_effects: List[StatusEffect] = []
        self.game_state_data.player.resistances = ResistanceSet()
        self.game_state_data.player.resistances.fire = 10
        self.game_state_data.player.faction = "player"
        self.game_state_data.player.aggro = AggroList()
        self.meta_progression_manager.recalculate_and_apply_bonuses(self.game_state_data.player)

        # --- ペット (設定駆動) ---
        self.game_state_data.pet.status_effects = []
        self.game_state_data.pet.resistances = ResistanceSet()
        self.game_state_data.pet.faction = "player"

    def _setup_initial_inventory(self) -> None:
        """初期インベントリアイテムの設定"""
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
        instrument = Item("★ストラディバリウス", "tool", "🎻", (255, 215, 0), base_weight=1.5, base_value=800)
        wish_rod = Item("★願いの杖", "rod", "🪄", (100, 255, 255), base_weight=0.8, base_value=3000)

        for itm in [starter_sword, shield, potion, bread, spellbook, instrument, wish_rod]:
            self.game_state_data.inventory.add_item(itm)
        self.game_state_data.inventory.equip(starter_sword, "main_hand")
        self.game_state_data.inventory.equip(shield, "off_hand")
        print("DEBUG: Web server started")

        # --- 初期ログ ---
        self.log("『naRou: Masterpiece Edition』の世界へようこそ！", (255, 255, 120), level="SUCCESS")
        self.log("妹分シエル「お兄ちゃん、今日も一緒に頑張ろうね！」", COLOR_PET_PINK, level="INFO")
        self.log("【初心者ガイド】[?]または[h]キーでいつでもヘルプを確認できます！", (120, 255, 200), level="INFO")
        self.log("【操作】矢印:移動 [Space]:行動 [l]:調査 [i]:カバン [c]:能力 [j]:職業 [Shift+S]:ツリー [Shift+G]:ギルド", (180, 220, 255), level="INFO")
        self.log("⚡ Web版接続待機中: http://localhost:8080 にアクセスしてブラウザでもプレイ可能！", (100, 255, 200), level="INFO")

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
    
    @property
    def pet(self) -> Entity:
        """ペットエンティティ"""
        return self.game_state_data.pet
    
    @property
    def inventory(self) -> Inventory:
        """プレイヤーのインベントリ"""
        return self.game_state_data.inventory
    
    @property
    def pet_inventory(self) -> Inventory:
        """ペットのインベントリ"""
        return self.game_state_data.pet_inventory
    
    @property
    def survival(self) -> SurvivalSystem:
        """サバイバルシステム"""
        return self.game_state_data.survival
    
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
    def altar_pos(self) -> Tuple[int, int]:
        """祭壇の位置"""
        return self.game_state_data.altar_pos
    
    @altar_pos.setter
    def altar_pos(self, value: Tuple[int, int]) -> None:
        """祭壇の位置を設定"""
        self.game_state_data.altar_pos = value
    
    @property
    def entities(self) -> List[Entity]:
        """ゲーム内のエンティティリスト"""
        return self.entity_manager.get_entities()
    
    @entities.setter
    def entities(self, value: List[Entity]) -> None:
        """エンティティリストを設定"""
        # 既存のエンティティをすべて削除
        self.entity_manager.entities.clear()
        # 新しいエンティティを追加
        for entity in value:
            self.entity_manager.add_entity(entity)
    
    @property
    def items_on_ground(self) -> List[Item]:
        """地面上のアイテムリスト"""
        return self.entity_manager.items_on_ground
    
    @items_on_ground.setter
    def items_on_ground(self, value: List[Item]) -> None:
        """地面上のアイテムリストを設定"""
        # 既存のアイテムをすべて削除
        self.entity_manager.items_on_ground.clear()
        # 新しいアイテムを追加
        for item in value:
            self.entity_manager.add_item(item)
    
    @property
    def resource_nodes(self) -> List[ResourceNode]:
        """資源ノードリスト"""
        return self.entity_manager.resource_nodes
    
    @resource_nodes.setter
    def resource_nodes(self, value: List[ResourceNode]) -> None:
        """資源ノードリストを設定"""
        # 既存の資源ノードをすべて削除
        self.entity_manager.resource_nodes.clear()
        # 新しい資源ノードを追加
        for node in value:
            self.entity_manager.add_resource_node(node)
    
    @property
    def quests(self) -> List[Quest]:
        """クエストリスト"""
        return self.game_state_data.quests
    
    @quests.setter
    def quests(self, value: List[Quest]) -> None:
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
    def active_dialogue(self) -> Optional[Tuple[str, str]]:
        """アクティブなダイアログ"""
        return self.game_state_data.active_dialogue
    
    @active_dialogue.setter
    def active_dialogue(self, value: Optional[Tuple[str, str]]) -> None:
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
    def arch_interpret_groups_cache(self) -> List[Dict[str, Any]]:
        """考古学解釈グループキャッシュ"""
        return self.game_state_data.arch_interpret_groups_cache
    
    @arch_interpret_groups_cache.setter
    def arch_interpret_groups_cache(self, value: List[Dict[str, Any]]) -> None:
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

    def setup_systems(self) -> None:
        """各種マネージャーとサブシステムの生成・初期化 (Step 8)"""
        from main_quest_system import MainQuestSystem
        from world_state_system import WorldStateManager
        from journal_ui import JournalUI
        from achievement_system import AchievementRegistry, AchievementManager
        from reincarnation_system import ReincarnationRegistry, ReincarnationManager
        from inheritance_system import InheritanceRegistry, InheritanceManager
        from karma_system import KarmaRegistry, KarmaManager
        from reincarnation_dungeon_system import ReincarnationDungeonRegistry, ReincarnationDungeonManager
        from legacy_skill_system import LegacySkillRegistry, LegacySkillManager
        from reincarnation_challenge_system import ReincarnationChallengeRegistry, ReincarnationChallengeManager
        from skill_fusion_system import SkillFusionRegistry, SkillFusionManager
        from skill_evolution_system import SkillEvolutionRegistry, SkillEvolutionManager
        from skill_awakening_system import SkillAwakeningRegistry, SkillAwakeningManager
        from skill_transfer_system import SkillTransferRegistry, SkillTransferManager
        from skill_resonance_system import SkillResonanceRegistry, SkillResonanceManager
        from skill_inheritance_system import SkillInheritanceRegistry, SkillInheritanceManager
        from skill_specialization_system import SkillSpecializationRegistry, SkillSpecializationManager
        from storyteller_system import StorytellerRegistry, StorytellerManager
        from choice_system import ChoiceRegistry, ChoiceManager
        from world_state_system import WorldStateRegistry, WorldStateManager
        from procedural_dungeon_generator import DungeonThemeRegistry, ProceduralDungeonGenerator
        from relationship_system import RelationshipRegistry, RelationshipManager
        from world_event_system import WorldEventRegistry, WorldEventManager
        from meta_progression_system import MetaProgressionRegistry, MetaProgressionManager
        from procedural_quest_generator import (
            QuestGenerationRegistry, ProceduralQuestGenerator, ProceduralQuestManager
        )
        from archaeology_system import ArchaeologyRegistry, ArchaeologyManager

        self.event_bus = EventBus()
        self.fx_manager = FXManager(event_bus=self.event_bus)
        self.msg_log = MessageLog(max_history=200)
        self.time_system = TimeSystem(event_bus=self.event_bus)
        self.turn_queue = TurnQueue(self.time_system)
        self.unique_mgr = UniqueItemManager()
        self.debug = DebugConsole()
        self.main_quest_system = MainQuestSystem()
        self.journal_ui = JournalUI()

        # Skill & Job
        self.skill_tree_registry = SkillTreeRegistry()
        self.skill_tree_registry.load()
        self.skill_tree_manager = self.systems_coordinator.register_system("skill_tree_manager", SkillTreeManager(self.skill_tree_registry))

        self.job_registry = JobRegistry()
        self.job_registry.load()
        self.job_manager = self.systems_coordinator.register_system("job_manager", JobManager(self.job_registry))

        self.fusion_registry = FusionRegistry()
        self.fusion_registry.load()

        # Guild & Faction
        self.guild_registry = GuildRegistry()
        self.guild_registry.load()
        self.guild_manager = self.systems_coordinator.register_system("guild_manager", GuildManager(self.guild_registry))

        self.guild_quest_registry = GuildQuestRegistry()
        self.guild_quest_registry.load()
        self.guild_quest_manager = self.systems_coordinator.register_system("guild_quest_manager", GuildQuestManager(self.guild_quest_registry))

        self.faction_war_registry = FactionWarRegistry()
        self.faction_war_registry.load()
        self.faction_war_manager = self.systems_coordinator.register_system("faction_war_manager", FactionWarManager(self.faction_war_registry))

        self.guild_skill_registry = GuildSkillRegistry()
        self.guild_skill_registry.load()
        self.guild_skill_manager = self.systems_coordinator.register_system("guild_skill_manager", GuildSkillManager(self.guild_skill_registry))

        # Pets
        self.pet_contract_registry = PetContractRegistry()
        self.pet_contract_registry.load()
        self.pet_contract_manager = self.systems_coordinator.register_system("pet_contract_manager", PetContractManager(self.pet_contract_registry))

        self.pet_evolution_registry = PetEvolutionRegistry()
        self.pet_evolution_registry.load()
        self.pet_evolution_manager = self.systems_coordinator.register_system("pet_evolution_manager", PetEvolutionManager(self.pet_evolution_registry))

        self.pet_fusion_registry = PetFusionRegistry()
        self.pet_fusion_registry.load()
        self.pet_fusion_manager = self.systems_coordinator.register_system("pet_fusion_manager", PetFusionManager(self.pet_fusion_registry))

        # Achievements
        self.achievement_registry = AchievementRegistry()
        self.achievement_registry.load()
        self.achievement_manager = self.systems_coordinator.register_system("achievement_manager", AchievementManager(self.achievement_registry))

        # Reincarnation
        self.reincarnation_registry = ReincarnationRegistry()
        self.reincarnation_registry.load()
        self.reincarnation_manager = self.systems_coordinator.register_system("reincarnation_manager", ReincarnationManager(self.reincarnation_registry))

        self.inheritance_registry = InheritanceRegistry()
        self.inheritance_registry.load()
        self.inheritance_manager = self.systems_coordinator.register_system("inheritance_manager", InheritanceManager(self.inheritance_registry))

        self.karma_registry = KarmaRegistry()
        self.karma_registry.load()
        self.karma_manager = self.systems_coordinator.register_system("karma_manager", KarmaManager(self.karma_registry))

        self.reincarnation_dungeon_registry = ReincarnationDungeonRegistry()
        self.reincarnation_dungeon_registry.load()
        self.reincarnation_dungeon_manager = self.systems_coordinator.register_system("reincarnation_dungeon_manager", ReincarnationDungeonManager(self.reincarnation_dungeon_registry))

        self.legacy_skill_registry = LegacySkillRegistry()
        self.legacy_skill_registry.load()
        self.legacy_skill_manager = self.systems_coordinator.register_system("legacy_skill_manager", LegacySkillManager(self.legacy_skill_registry))

        self.challenge_registry = ReincarnationChallengeRegistry()
        self.challenge_registry.load()
        self.challenge_manager = self.systems_coordinator.register_system("challenge_manager", ReincarnationChallengeManager(self.challenge_registry))

        # Skill Fusion & Evolution
        self.skill_fusion_registry = SkillFusionRegistry()
        self.skill_fusion_registry.load()
        self.skill_fusion_manager = self.systems_coordinator.register_system("skill_fusion_manager", SkillFusionManager(self.skill_fusion_registry))

        self.skill_evolution_registry = SkillEvolutionRegistry()
        self.skill_evolution_registry.load()
        self.skill_evolution_manager = self.systems_coordinator.register_system("skill_evolution_manager", SkillEvolutionManager(self.skill_evolution_registry))

        self.skill_awakening_registry = SkillAwakeningRegistry()
        self.skill_awakening_registry.load()
        self.skill_awakening_manager = self.systems_coordinator.register_system("skill_awakening_manager", SkillAwakeningManager(self.skill_awakening_registry))

        self.skill_transfer_registry = SkillTransferRegistry()
        self.skill_transfer_registry.load()
        self.skill_transfer_manager = self.systems_coordinator.register_system("skill_transfer_manager", SkillTransferManager(self.skill_transfer_registry))

        self.skill_resonance_registry = SkillResonanceRegistry()
        self.skill_resonance_registry.load()
        self.skill_resonance_manager = self.systems_coordinator.register_system("skill_resonance_manager", SkillResonanceManager(self.skill_resonance_registry))

        self.skill_inheritance_registry = SkillInheritanceRegistry()
        self.skill_inheritance_registry.load()
        self.skill_inheritance_manager = self.systems_coordinator.register_system("skill_inheritance_manager", SkillInheritanceManager(self.skill_inheritance_registry))

        self.skill_specialization_registry = SkillSpecializationRegistry()
        self.skill_specialization_registry.load()
        self.skill_specialization_manager = self.systems_coordinator.register_system("skill_specialization_manager", SkillSpecializationManager(self.skill_specialization_registry))

        # Storyteller & World
        self.storyteller_registry = StorytellerRegistry()
        self.storyteller_registry.load()
        self.storyteller_manager = self.systems_coordinator.register_system("storyteller_manager", StorytellerManager(self.storyteller_registry))

        self.choice_registry = ChoiceRegistry()
        self.choice_registry.load()
        self.choice_manager = self.systems_coordinator.register_system("choice_manager", ChoiceManager(self.choice_registry))

        self.world_state_registry = WorldStateRegistry()
        self.world_state_registry.load()
        self.world_state_manager = self.systems_coordinator.register_system("world_state_manager", WorldStateManager(self.world_state_registry))

        self.dungeon_theme_registry = DungeonThemeRegistry()
        self.dungeon_theme_registry.load()
        self.procedural_dungeon_generator = self.systems_coordinator.register_system("procedural_dungeon_generator", ProceduralDungeonGenerator(self.dungeon_theme_registry))

        self.relationship_registry = RelationshipRegistry()
        self.relationship_registry.load()
        self.relationship_manager = self.systems_coordinator.register_system("relationship_manager", RelationshipManager(self.relationship_registry))

        self.world_event_registry = WorldEventRegistry()
        self.world_event_registry.load()
        self.world_event_manager = self.systems_coordinator.register_system("world_event_manager", WorldEventManager(self.world_event_registry))

        # Procedural Quest Generation (Steps 15-36)
        self.quest_generation_registry = QuestGenerationRegistry()
        self.quest_generation_registry.load()
        self.procedural_quest_generator = ProceduralQuestGenerator(self.quest_generation_registry)
        self.procedural_quest_manager = self.systems_coordinator.register_system(
            "procedural_quest_manager", ProceduralQuestManager(self.procedural_quest_generator))

        # 考古学・発掘・解読メタゲーム (Steps 25, 15)
        self.archaeology_registry = ArchaeologyRegistry()
        self.archaeology_registry.load()
        self.archaeology_manager = self.systems_coordinator.register_system(
            "archaeology_manager", ArchaeologyManager(self.archaeology_registry))

        # Meta Progression
        self.meta_progression_registry = MetaProgressionRegistry()
        self.meta_progression_registry.load()
        self.meta_progression_manager = self.systems_coordinator.register_system("meta_progression_manager", MetaProgressionManager(self.meta_progression_registry))

        # Data & AI Systems
        from data_manager import DataManager
        from ai_system import AdvancedAISystem
        self.data_manager = self.systems_coordinator.register_system("data_manager", DataManager())
        self.ai_system = self.systems_coordinator.register_system("ai_system", AdvancedAISystem())

        # 一括初期化 (Step 14)
        self.systems_coordinator.initialize_all(self)


    @property
    def floating_texts(self) -> List[FloatingText]:
        return self.fx_manager.floating_texts

    @floating_texts.setter
    def floating_texts(self, val: List[FloatingText]) -> None:
        self.fx_manager.floating_texts = val

    @property
    def particles(self) -> List[Particle]:
        return self.fx_manager.particles

    @particles.setter
    def particles(self, val: List[Particle]) -> None:
        self.fx_manager.particles = val

    @property
    def screen_shake(self) -> ScreenShake:
        return self.fx_manager.screen_shake

    @screen_shake.setter
    def screen_shake(self, val: ScreenShake) -> None:
        self.fx_manager.screen_shake = val


    def change_state(self, new_state: GameState) -> None:
        """状態遷移（ステートマシン）の厳格化とフック処理 (Step 6.2)"""
        if self.current_state == new_state:
            return

        old_state = self.current_state
        # on_exit hook
        if old_state == GameState.DIALOGUE:
            self.active_dialogue = None
        elif old_state == GameState.MENU:
            self.inventory_cursor = 0

        self.current_state = new_state

        # 旧 game_state 文字列への双方向同期
        state_mapping = {
            GameState.EXPLORING: "play",
            GameState.COMBAT: "play",
            GameState.DIALOGUE: "talk",
            GameState.MENU: "inventory",
            GameState.EVENT: "story_choice",
            GameState.PAUSED: "pause"
        }
        self.game_state = state_mapping.get(new_state, "play")

        # on_enter hook
        if new_state == GameState.MENU:
            if hasattr(self, 'look_cursor'):
                self.look_cursor.active = False

    def open_journal(self) -> None:
        """冒険日誌を開く"""
        self.journal_ui.toggle()
        if self.journal_ui.visible:
            self.game_state = "journal"
        else:
            self.game_state = "play"

    def open_context_menu(self) -> None:
        """Spaceキーによる文脈アクション候補の動的生成 (Phase 4)"""
        self.game_state = "context"
        actions: List[ContextAction] = []
        px, py = self.player.x, self.player.y

        # 1. 足元のアイテム
        ground_items = self.entity_manager.get_items_at(px, py)
        for itm in ground_items:
            actions.append(ContextAction(f"拾う: {itm.display_name}", "pickup", "pickup_item", itm))
            if itm.category == CAT_FOOD:
                actions.append(ContextAction(f"食べる: {itm.display_name}", "eat", "eat_ground", itm))

        # 2. 隣接するNPC
        for dx, dy in [(0,-1),(0,1),(-1,0),(1,0)]:
            nx, ny = px + dx, py + dy
            ent = self.get_entity_at(nx, ny)
            if ent and ent not in (self.player, self.pet):
                actions.append(ContextAction(f"話す / 調べる: {ent.name}", "talk", "talk_target", ent))
            elif ent == self.pet:
                actions.append(ContextAction("シエルの荷物を見る", "pet_inv", "open_pet_inv", ent))

        # 3. 祭壇
        if (px, py) == self.altar_pos:
            actions.append(ContextAction("神に祈る", "pray", "pray", None))
            actions.append(ContextAction("祭壇に供物を捧げる", "offer", "offer_altar", None))

        # 4. 採取ポイント
        for node in self.entity_manager.resource_nodes:
            if abs(node.x - px) + abs(node.y - py) <= 1 and not node.depleted:
                actions.append(ContextAction(f"採取する ({node.node_type})", "harvest", "harvest_resource", node))
                break

        # 5. 壁掘り
        can_mine = any(self.game_map.is_in_bounds(px+dx, py+dy) and self.game_map.tiles[px+dx][py+dy] == TILE_WALL for dx, dy in [(0,-1),(0,1),(-1,0),(1,0)])
        if can_mine:
            actions.append(ContextAction("隣の壁を掘る", "mine", "mine_wall", None))

        if actions:
            self.context_menu.set_actions(actions)
            self.game_state = "context"
        else:
            self.log("周囲にアクション可能な対象がない。")

    def log(self, text: str, color: Tuple[int, int, int] = (230, 230, 230), level: str = "INFO") -> None:
        self.msg_log.add(text, color, level=level)

    def check_tutorial_triggers(self, trigger_condition: str) -> Optional[Any]:
        """チュートリアルの発動条件を検知し、未完了なら通知・ポップアップ設定 (Step 1.2)"""
        if not hasattr(self, "tutorial_manager") or not self.player:
            return None
        guide = self.tutorial_manager.check_triggers(trigger_condition, self.player.completed_tutorials)
        if guide:
            self.player.completed_tutorials.add(guide.id)
            self.player.pending_tutorial_popup = guide.to_dict()
            # ログにも案内表示
            self.log(f"📖【ガイド】{guide.title}: {guide.message}", (100, 255, 200), level="SUCCESS")
            # 画面上部ポップアップ通知キューにも登録
            if hasattr(self, "notification_manager"):
                self.notification_manager.notify(
                    title=f"📖 ガイド: {guide.title}",
                    message=guide.message,
                    category="tutorial",
                    color=(100, 255, 200),
                    duration=40
                )
            return guide
        return None

    def _spawn_dungeon(self) -> None:
        for room in self.game_map.rooms[1:]:
            if random.random() < SPAWN_SNAIL_CHANCE:
                gx = random.randint(room.x1 + 1, room.x2 - 1)
                gy = random.randint(room.y1 + 1, room.y2 - 1)
                gwen = Entity(gx, gy, "🐌", SNAIL_COLOR, "かたつむり少女『グウェン』", speed=SNAIL_SPEED)
                gwen.status_effects = []
                gwen.faction = "townsfolk"
                self.entity_manager.add_entity(gwen)

            if random.random() < SPAWN_MONSTER_CHANCE:
                mx, my = random.randint(room.x1+1, room.x2-1), random.randint(room.y1+1, room.y2-1)
                if hasattr(self, "data_manager"):
                    mob = self.data_manager.get_random_monster_for_floor(self.dungeon_level, mx, my)
                else:
                    mob = MonsterPreset.create(random.choice(["slime","slime","goblin","orc"]), mx, my)
                self.entity_manager.add_entity(mob)

            if random.random() < SPAWN_ITEM_CHANCE:
                ix, iy = random.randint(room.x1+1, room.x2-1), random.randint(room.y1+1, room.y2-1)
                if hasattr(self, "data_manager"):
                    itm = self.data_manager.get_random_item_for_floor(self.dungeon_level, ix, iy)
                else:
                    itm = create_sample_item(random.choice(["potion_heal","bread","ration","shortsword","leather_armor"]), ix, iy)
                self.entity_manager.add_item(itm)

            # 採取ポイント (ステップ46)
            if random.random() < SPAWN_RESOURCE_NODE_CHANCE:
                rx, ry = random.randint(room.x1+1, room.x2-1), random.randint(room.y1+1, room.y2-1)
                ntype = random.choice(["herb","mushroom","ore_vein"])
                self.entity_manager.add_resource_node(ResourceNode(rx, ry, ntype))

    def has_los(self, p1: Point, p2: Point) -> bool:
        """射線判定 (ステップ21)"""
        line = bresenham_line(p1, p2)
        for pt in line[1:-1]:
            if not self.game_map.is_transparent(pt.x, pt.y):
                return False
        return True

    def get_blocked_positions(self) -> Set[Tuple[int, int]]:
        """全生存エンティティの座標セット (O(1)衝突判定用)"""
        return self.entity_manager.get_blocked_positions()

    def is_tile_free(self, x: int, y: int, blocked: Optional[Set[Tuple[int, int]]] = None) -> bool:
        if not self.game_map.is_walkable(x, y):
            return False
        if blocked is not None:
            return (x, y) not in blocked
        return not self.entity_manager.is_position_blocked(x, y)

    def get_entity_at(self, x: int, y: int) -> Optional[Entity]:
        """指定された位置にあるエンティティを取得する"""
        return self.entity_manager.get_entity_at(x, y)

    def player_act(self, dx: int, dy: int) -> bool:
        tx, ty = self.player.x + dx, self.player.y + dy
        target = self.get_entity_at(tx, ty)

        if target and target not in (self.player, self.pet):
            if "グウェン" in target.name:
                self.survival.karma -= 15
                self.log("【悪行】グウェンを攻撃した！ (Karma -15)", (255, 80, 80))
            weapon = self.inventory.equipment.get("main_hand")
            dmg, is_crit, msg = CombatSystem.calculate_melee_attack(self.player, target, weapon)
            self.log(msg, (255, 130, 130) if is_crit else (240, 240, 240))
            SoundManager.play_se("hit")

            # 画面シェイク & ポップアップ (Step 2.3)
            if is_crit:
                if hasattr(self, "screen_shake"):
                    self.screen_shake.trigger(intensity=1.5, duration=4)

            # ポップアップダメージ (Phase 6)
            self.floating_texts.append(FloatingText(f"-{dmg}", target.x, target.y - 0.2, (255, 100, 100) if not is_crit else (255, 230, 80)))

            for l in self.player.gain_skill_exp("long_sword", 18):
                self.log(l, (150, 255, 150))
            target.hp -= dmg
            if target.hp <= 0:
                self._on_kill(target)
            self.player.energy -= ENERGY_THRESHOLD
            return True

        elif self.game_map.is_walkable(tx, ty) and not self.get_entity_at(tx, ty):
            self.player.x, self.player.y = tx, ty
            if (tx, ty) == self.altar_pos:
                self.log(f"神【{GodInfo.GODS[self.player.god_id]['name']}】の祭壇。([p]祈る [o]捧げる)", (255, 215, 0))
            tile = self.game_map.tiles[tx][ty]
            if tile == TILE_TRAP:
                self.player.hp -= 6
                if hasattr(self, "screen_shake"):
                    self.screen_shake.trigger(intensity=1.0, duration=3)
                self.floating_texts.append(FloatingText("-6", self.player.x, self.player.y - 0.2, (255, 80, 80)))
                self.log("トラップ発動！ 毒矢が急所を貫く！ (-6 HP)", (255, 80, 80), level="WARNING")
            self.player.energy -= ENERGY_THRESHOLD
            return True
        return False

    def _on_kill(self, entity: Entity) -> None:
        # メインクエストの進行を更新
        if hasattr(self, "main_quest_system"):
            logs = self.main_quest_system.update_progress(
                self.player, "kill", entity.name, 1, self
            )
            for log in logs:
                self.message_log.add(log, level="SUCCESS")
        # プロシージャル・クエスト（依頼ボード/ダンジョン/NPC）の討伐進捗を通知
        self._progress_generated_quests("kill", entity.name, 1)
        self.log(f"★{entity.name}を撃破！", (255, 215, 0), level="SUCCESS")
        SoundManager.play_se("kill")
        if hasattr(self, "screen_shake"):
            self.screen_shake.trigger(intensity=1.2, duration=3)
        # 爆発パーティクル (Phase 7)
        for _ in range(3):
            self.particles.append(Particle("💥", entity.x, entity.y, (255, 180, 50), life=3, vx=random.uniform(-0.4, 0.4), vy=random.uniform(-0.4, 0.4)))

        corpse = Item(f"{entity.name}の肉", CAT_FOOD, "🍖", (220, 80, 80), entity.x, entity.y, base_weight=2.0, base_value=40, nutrition=2800)
        self.entity_manager.add_item(corpse)

        # 転生経験値ペナルティ適用 (Steps 57, 58)
        # TODO: Reincarnation XP penalty
        base_exp = 35 * self.dungeon_level
        reinc_cnt = getattr(self.player, "reincarnation_count", 0)
        if reinc_cnt > 0:
            penalty = max(0.50, 1.0 - reinc_cnt * 0.05)
            base_exp = max(1, int(base_exp * penalty))

        for l in self.player.gain_exp(base_exp):
            self.log(l, (255, 255, 100))
        for q in self.quests:
            if q.target_monster in entity.name and not q.completed:
                q.current_count += 1
                if q.current_count >= q.target_count:
                    q.completed = True
            self.survival.gold += q.reward_gold
            self.survival.platinum += q.reward_platinum
            SoundManager.play_se("level_up")
            self.log(f"★依頼達成！ {q.reward_gold}G + {q.reward_platinum}P 獲得！", COLOR_GOLD_YELLOW)
            self.entity_manager.remove_entity(entity)

        # === 称号システム: キルカウント記録 ===
        if self.player and hasattr(self.player, 'kill_counts'):
            # モンスター名正規化（小文字・スペース→アンダースコア）
            key = entity.name.lower().replace(' ', '_')
            self.player.kill_counts[key] = self.player.kill_counts.get(key, 0) + 1

            # モンスターキルタイプ更新 (Step 46)
            m_type = getattr(entity, "char", "monster")
            if "goblin" in key or "ゴブリン" in entity.name:
                m_type = "goblin"
            elif "slime" in key or "ぷち" in entity.name:
                m_type = "slime"
            self.player.monster_killed_types[m_type] = self.player.monster_killed_types.get(m_type, 0) + 1
            
            # 称号チェック（即時）
            from title_system import MANAGER
            granted = MANAGER.check_all_titles(self.player)
            for tid in granted:
                pass

            # 実績チェック (Steps 26, 27)
            # TODO: Achievement check
            if hasattr(self, 'achievement_manager'):
                self.achievement_manager.check_all_achievements(self.player, self)

        # === スキルポイント付与 (Step 26 オプションフック) ===
        if random.random() < 0.20:
            sp_bonus = random.randint(1, 2)
            self.player.skill_points += sp_bonus
            self.player.total_skill_points_earned += sp_bonus
            self.log(f"★討伐の閃き！ {sp_bonus} スキルポイントを獲得！", (150, 255, 200))

        # === ペット共闘時の絆度増加 (Step 33) ===
        if self.pet and self.pet.hp > 0 and hasattr(self.pet, 'pet_ai'):
            p_dist = Point(self.pet.x, self.pet.y).chebyshev_distance(Point(entity.x, entity.y))
            if p_dist <= 3:
                self.pet.pet_ai.increase_bond(5, "combat_together")

        # === ギルドクエスト進捗更新 (Step 40) ===
        if self.player and getattr(self.player, 'guild_id', None):
            mon_name = entity.name.lower()
            if "ゴブリン" in mon_name or "goblin" in mon_name:
                done = self.guild_quest_manager.update_quest_progress(self.player, "slay_goblins", amount=20)
                self.log("【ギルドクエスト】ゴブリン討伐進捗を記録！", (100, 255, 200))
                if done:
                    ok, qmsg, _ = self.guild_quest_manager.complete_quest(self.player, "slay_goblins")
                    if ok: self.log(qmsg, (255, 215, 0))
            elif "ぷち" in mon_name or "slime" in mon_name:
                done = self.guild_quest_manager.update_quest_progress(self.player, "slay_slimes", amount=34)
                self.log("【ギルドクエスト】ぷち駆除進捗を記録！", (100, 255, 200))
                if done:
                    ok, qmsg, _ = self.guild_quest_manager.complete_quest(self.player, "slay_slimes")
                    if ok: self.log(qmsg, (255, 215, 0))

        # === 派閥評判更新 (Step 63 オプション) ===
        if hasattr(self.player, 'faction_reputation'):
            self.player.faction_reputation["kingdom_garde"] = self.player.faction_reputation.get("kingdom_garde", 0) + 1

        # === 動的記憶の欠片のドロップ判定 (強敵討伐 / 稀な確率) ===
        if random.random() < 0.08 and hasattr(self, "meta_progression_manager"):
            from meta_progression_system import MemoryFragmentGenerator
            frag = MemoryFragmentGenerator.generate(
                self.player,
                trigger_type="boss_kill",
                context={"enemy_name": entity.name, "dungeon_level": self.dungeon_level}
            )
            self.meta_progression_manager.add_memory_fragment(self.player, frag, self)



    def _progress_generated_quests(self, event_type: str, target_id: str, amount: int = 1) -> None:
        """プロシージャル生成クエストの進捗をゲームイベントから通知 (Steps 34, 36)"""
        mgr = getattr(self, "procedural_quest_manager", None)
        if mgr is None or self.player is None:
            return
        msgs = mgr.update_progress(self.player, event_type, target_id, amount, self)
        for m in msgs:
            self.log(m, (255, 215, 0), level="SUCCESS")

    def advance_world(self) -> None:
        """速度Tick制による全NPCターン処理 (ステップ10-15)"""
        max_cycles = 200
        cycle = 0
        while self.player.energy < ENERGY_THRESHOLD and cycle < max_cycles:
            cycle += 1
            actor, _ = self.turn_queue.step_next_actor(self.entity_manager.get_living_entities())
            if not actor or actor == self.player:
                break
            if actor == self.pet:
                self._pet_ai()
            else:
                self._npc_ai(actor)

        # 状態異常処理 (全エンティティ: ステップ16, 45)
        player_bleeding = False
        for entity in list(self.entity_manager.get_living_entities()):
            if entity.hp > 0:
                logs, is_bleeding = CombatSystem.process_status_effects(entity)
                if entity == self.player:
                    player_bleeding = is_bleeding
                if logs and (entity == self.player or self.has_los(Point(self.player.x, self.player.y), Point(entity.x, entity.y))):
                    for l in logs:
                        self.log(l, (200, 80, 80))

        # 食料腐敗 (インベントリ + 地面アイテム: ステップ35)
        for msg in self.inventory.tick_food_rot(ticks=5):
            self.log(msg, (180, 120, 60))
        for item in self.entity_manager.items_on_ground:
            item.tick_rot(ticks=5)

        # サバイバル
        for l in self.survival.pass_turn(self.player):
            self.log(l, (255, 180, 100))

        # 自然回復(出血中は停止: ステップ45)
        self.turns += 1
        if self.turns % 4 == 0 and self.survival.hunger > 1000 and not player_bleeding:
            self.player.hp = min(self.player.max_hp, self.player.hp + 1)
            self.player.mp = min(self.player.max_mp, self.player.mp + 1)
            if self.pet.hp > 0:
                self.pet.hp = min(self.pet.max_hp, self.pet.hp + 1)

        # 世界のニュース・噂の動的生成 (Step 8.1)
        if self.turns % 30 == 0:
            if hasattr(self, 'world_state_manager'):
                self.world_state_manager.generate_world_news(self)

        # 動的サウンドスケープ: 危機状態のBGM判定 (Step 7.3)
        if hasattr(self, 'player') and self.player:
            SoundManager.bgm_manager.check_crisis_trigger(self.player.hp, self.player.max_hp)

        # オートセーブ: 50ターンごと (ステップ71)
        if self.turns % AUTO_SAVE_INTERVAL == 0:
            msg = SaveSystem.save(self)
            self.log(f"[Auto] {msg}", (80, 200, 80))

        # === 称号システム: 定期チェック（10ターンごと） ===
        if self.player and hasattr(self.player, 'total_turns'):
            self.player.total_turns += 1
            
            # 10ターンごとにチェック（パフォーマンス考慮）
            if self.player.total_turns % TITLE_CHECK_INTERVAL == 0:
                from title_system import MANAGER
                granted = MANAGER.check_all_titles(self.player)
                # 通知は自動で player.title_notifications に入る

        # === ジョブ経験値加算 & レベルアップ (Step 51) ===
        if self.player:
            self.player.job_exp += JOB_EXP_PER_TURN
            if self.player.job_exp >= JOB_LEVEL_UP_THRESHOLD:
                self.player.job_exp -= 100
                self.player.job_level += 1
                self.log(f"★職業【{self.player.job}】の熟練度が上がり、Job Lv.{self.player.job_level} に到達！", (255, 220, 100))

        # === スキルツリー定期チェック (Step 27) ===
        if self.turns % SKILL_TREE_CHECK_INTERVAL == 0 and self.player.skill_points >= SKILL_POINTS_NOTIFICATION_THRESHOLD:
            avail = self.skill_tree_manager.get_available_skills(self.player)
            if avail:
                # 習得可能スキルがある旨を通知
                pass

        # === ギルドクエスト日次リセット (Step 41) ===
        # 1000ターンを1日としてリセット判定
        if self.turns % GUILD_QUEST_RESET_INTERVAL == 0 and self.player and hasattr(self.player, 'guild_quest_progress'):
            self.log("【ギルド】日次ギルド依頼が更新・リセットされました。", (180, 220, 255))

        # === 派閥影響力定期変動 (Step 62) ===
        if self.turns % FACTION_INFLUENCE_INTERVAL == 0:
            for fid in self.faction_war_registry.all().keys():
                chg = self.faction_war_manager.calculate_influence_change(fid, self)
                self.faction_war_manager.apply_influence_effects(fid, chg)

        # === ペット絆度 & 進化チェック (Steps 30, 34, 44, 45) ===
        if self.pet and hasattr(self.pet, 'pet_ai'):
            # 歩行・近傍絆度 (Step 30) vs 放置絆度減少 (Step 34)
            p_dist = Point(self.pet.x, self.pet.y).chebyshev_distance(Point(self.player.x, self.player.y))
            if p_dist <= PET_WALKING_BOND_DISTANCE and self.pet.hp > 0:
                self.pet.pet_ai.increase_bond(1, "walking")
            elif p_dist >= PET_NEGLECTED_BOND_DISTANCE:
                self.pet.pet_ai.increase_bond(-2, "neglected")

        # 浮遊テキスト & パーティクル & 通知 & 画面シェイクの更新 (Phase 6, 7, UX強化)
        self.floating_texts = [ft for ft in self.floating_texts if ft.update()]
        self.particles = [pt for pt in self.particles if pt.update()]
        if hasattr(self, "notification_manager"):
            self.notification_manager.update()
        if hasattr(self, "screen_shake"):
            self.screen_shake.update()

        self.game_map.compute_fov(self.player.x, self.player.y, radius=8)

    def _pet_ai(self) -> None:
        """ビヘイビアツリー及びA*による高度なペットAI"""
        if self.pet.hp <= 0 or self.pet.energy < ENERGY_THRESHOLD:
            return
        if hasattr(self, "ai_system"):
            self.ai_system.process_ai(self.pet, self)
            return

        blocked = self.get_blocked_positions()
        retreat = self.pet.hp < self.pet.max_hp * 0.3

        if not retreat:
            nearest = None
            min_dist = 99
            for e in self.entity_manager.get_living_entities():
                if e not in (self.player, self.pet) and "グウェン" not in e.name and e.hp > 0:
                    d = Point(self.pet.x, self.pet.y).chebyshev_distance(Point(e.x, e.y))
                    if d < min_dist and self.has_los(Point(self.pet.x, self.pet.y), Point(e.x, e.y)):
                        min_dist = d
                        nearest = e

            if nearest and min_dist <= 6:
                if min_dist == 1:
                    weapon = self.pet_inventory.equipment.get("main_hand") if hasattr(self, "pet_inventory") else None
                    dmg, _, msg = CombatSystem.calculate_melee_attack(self.pet, nearest, weapon=weapon)
                    self.log(f"【シエル】「えいっ！」-> {nearest.name}に{dmg}ダメージ！", COLOR_PET_PINK)
                    nearest.hp -= dmg
                    if nearest.hp <= 0:
                        self.log(f"【シエル】が{nearest.name}を倒した！", (255, 200, 220))
                        for l in self.pet.gain_exp(40): self.log(l, COLOR_PET_PINK)
                        self.entity_manager.remove_entity(nearest)
                else:
                    path = AStar.get_path(Point(self.pet.x, self.pet.y), Point(nearest.x, nearest.y), lambda x, y: self.is_tile_free(x, y, blocked))
                    if path:
                        self.pet.x, self.pet.y = path[0].x, path[0].y
                    self.pet.energy -= ENERGY_THRESHOLD
                    return

        goal = Point(self.player.x, self.player.y)
        path = AStar.get_path(Point(self.pet.x, self.pet.y), goal, lambda x, y: self.is_tile_free(x, y, blocked))
        if path and len(path) > PET_PATH_LENGTH_CHECK:
            nxt = path[0]
            if (nxt.x, nxt.y) != (self.player.x, self.player.y):
                self.pet.x, self.pet.y = nxt.x, nxt.y
        self.pet.energy -= ENERGY_THRESHOLD

    def _npc_ai(self, npc: Entity) -> None:
        """ビヘイビアツリー及び戦術アーキタイプによるNPC AI"""
        if npc in (self.player, self.pet) or "グウェン" in npc.name or npc.hp <= 0:
            return

        if hasattr(self, "ai_system"):
            self.ai_system.process_ai(npc, self)
            return

        # ガードはカルマが低いプレイヤーを追跡 (ステップ43)
        target = self.player
        if getattr(npc, "faction", None) == FACTION_GUARD and self.survival.karma > -30:
            npc.energy -= ENERGY_THRESHOLD
            return

        dist = Point(npc.x, npc.y).chebyshev_distance(Point(target.x, target.y))
        can_see = self.has_los(Point(npc.x, npc.y), Point(target.x, target.y))

        if dist == 1:
            dmg, _, msg = CombatSystem.calculate_melee_attack(npc, target)
            self.log(msg, (255, 100, 100))
            target.hp -= dmg
            if target.hp <= 0:
                if target == self.player:
                    self.log("★あなたは力尽きた… 【GAME OVER】", (255, 50, 50))
                elif target == self.pet:
                    self.log("【悲痛】シエル「お兄ちゃん…ごめんね…」", (255, 80, 150))
                    if hasattr(self.pet, 'pet_ai'):
                        self.pet.pet_ai.increase_bond(-50, "defeated")
        elif dist <= 8 and can_see:
            blocked = self.get_blocked_positions()
            path = AStar.get_path(Point(npc.x, npc.y), Point(target.x, target.y), lambda x, y: self.is_tile_free(x, y, blocked))
            if path:
                nxt = path[0]
                if self.is_tile_free(nxt.x, nxt.y, blocked):
                    npc.x, npc.y = nxt.x, nxt.y
        npc.energy -= ENERGY_THRESHOLD

    def talk_to_neighbor(self) -> None:
        # 近隣のエンティティを取得
        neighbor = self.get_entity_at(self.player.x + self.player.dx, self.player.y + self.player.dy)
        if not neighbor:
            self.message_log.add("誰もいません。")
            return

        # メインクエストの進行を更新 (visitイベント)
        if hasattr(self, "main_quest_system"):
            logs = self.main_quest_system.update_progress(
                self.player, "visit", neighbor.name, 1, self
            )
            for log in logs:
                self.message_log.add(log)
        for dx, dy in [(0,-1),(0,1),(-1,0),(1,0),(-1,-1),(1,1),(-1,1),(1,-1)]:
            t = self.get_entity_at(self.player.x+dx, self.player.y+dy)
            if t and t != self.player:
                # DialogueManagerによる対話テキスト生成 (リファクタリング適用)
                self.active_dialogue = DialogueManager.get_dialogue(t, self.player, self)

                # キャラクター関係性更新 (Step 72)
                if hasattr(self, "relationship_manager"):
                    self.relationship_manager.update_relationship(self.player, t.name, action="talk")

                return
        self.log("周囲に話しかけられる相手がいない。")

    def harvest_resource(self) -> None:
        """採取ポイントの検索と採取 (ステップ46)"""
        for node in self.entity_manager.resource_nodes:
            d = abs(node.x - self.player.x) + abs(node.y - self.player.y)
            if d <= 1 and not node.depleted:
                itm, msg = node.harvest(self.player)
                self.log(msg, (180, 255, 180))
                SoundManager.play_se("get_item")
                if itm:
                    ok, add_msg = self.inventory.add_item(itm)
                    self.log(add_msg, (200, 255, 200))
                    self.floating_texts.append(FloatingText(f"+{itm.name}", self.player.x, self.player.y - 0.3, (100, 255, 150)))
                    # プロシージャル・クエスト: 採取進捗を通知
                    self._progress_generated_quests("collect", itm.name, 1)
                self.player.energy -= ENERGY_THRESHOLD
                self.advance_world()
                return
        self.log("周囲に採取できるものがない。")

    def cast_fireball(self) -> None:
        """ファイアボール詠唱 - 詠唱失敗率・フレンドリーファイア (ステップ39, 40, 41)"""
        success, backlash = CombatSystem.calc_spell_success(self.player, "fireball")
        if not success:
            self.player.hp -= backlash
            SoundManager.play_se("hit")
            self.floating_texts.append(FloatingText(f"-{backlash}", self.player.x, self.player.y - 0.2, (255, 80, 80)))
            self.log(f"魔法の詠唱に失敗！ 魔力が暴走し {backlash} ダメージを受けた！", (255, 80, 80))
            self.player.energy -= ENERGY_THRESHOLD
            self.advance_world()
            return

        mp_cost = 10
        if self.player.mp < mp_cost:
            self.log("MPが足りない！", (255, 100, 100))
            return

        SoundManager.play_se("cast")
        self.player.mp -= mp_cost
        tx, ty = self.player.x + 3, self.player.y
        # 軌跡パーティクル (Phase 7)
        for i in range(1, 4):
            self.particles.append(Particle("🔥", self.player.x + i, self.player.y, (255, 120, 30), life=2))

        coords = CombatSystem.aoe_radius(tx, ty, radius=1)
        karma_ref = {"value": self.survival.karma}
        logs = CombatSystem.apply_aoe(self.player, coords, (18, 35), Element.FIRE, self.entity_manager.get_living_entities(), karma_ref)
        self.survival.karma = karma_ref["value"]
        for l in logs:
            self.log(l, (255, 140, 60))
        # 死亡チェック
        for e in list(self.entity_manager.get_living_entities()):
            if e not in (self.player, self.pet) and e.hp <= 0:
                self._on_kill(e)
        self.player.energy -= ENERGY_THRESHOLD
        self.advance_world()

    def mine_wall(self) -> None:
        for dx, dy in [(0,-1),(0,1),(-1,0),(1,0)]:
            nx, ny = self.player.x+dx, self.player.y+dy
            if self.game_map.is_in_bounds(nx, ny) and self.game_map.tiles[nx][ny] == TILE_WALL:
                self.game_map.tiles[nx][ny] = TILE_FLOOR
                self.player.gain_skill_exp("mining", 25)
                roll = random.random()
                if roll < 0.25:
                    ore = Item("鉄鉱石", "ore", "🪨", (160,160,160), nx, ny, base_weight=1.5, base_value=50)
                    self.entity_manager.add_item(ore)
                    self.log("壁を掘り崩した！ 鉄鉱石を発見！", (200, 200, 255))
                elif roll < 0.40:
                    g = random.randint(50, 200)
                    self.survival.gold += g
                    self.log(f"壁から金貨が飛び散った！ (+{g}G)", COLOR_GOLD_YELLOW)
                else:
                    self.log("壁を掘り崩した。", (180, 180, 180))
                self.player.energy -= ENERGY_THRESHOLD
                self.advance_world()
                return
        self.log("近くに掘れる壁がない。")

    def excavate(self) -> None:
        """考古学メタゲーム: 現在の深度で遺跡を発掘する (Steps 25, 26)"""
        mgr = getattr(self, "archaeology_manager", None)
        if mgr is None:
            self.log("考古学システムが利用できない。")
            return
        depth = getattr(self, "dungeon_level", 1)
        site_id = mgr.registry.pick_site_for_excavation(depth)
        if not site_id:
            self.log(f"地下{depth}階には発掘できる遺跡がない。", (180, 180, 180))
            return
        if site_id not in self.player.archaeology.excavated_sites:
            self.player.archaeology.excavated_sites.append(site_id)
        frag_id, key_id = mgr.resolve_excavation(site_id)
        if frag_id:
            mgr.collect_fragment(self.player, frag_id, self)
        if key_id:
            mgr.acquire_key(self.player, key_id, self)
        # 入手直後に解読を試みる（鍵があれば解読される）
        if frag_id:
            mgr.decode_fragment(self.player, frag_id, self)
        self.player.energy -= ENERGY_THRESHOLD
        self.advance_world()

    # ---- 改善②: 解釈選択プロンプト（ジャーナル内インタラクティブ） ----
    def _arch_interpret_groups(self) -> List[Dict[str, Any]]:
        """到達真理ごとに候補エンディングをグループ化"""
        mgr = getattr(self, "archaeology_manager", None)
        if mgr is None:
            return []
        groups: Dict[str, Dict[str, Any]] = {}
        for tid, eid in mgr.suggest_endings(self.player):
            g = groups.setdefault(tid, {"tid": tid, "name": "", "endings": []})
            g["endings"].append(eid)
        # 名称付与
        for tid, g in groups.items():
            t = mgr.registry.get_truth(tid)
            g["name"] = t.get("name", tid) if t else tid
        return list(groups.values())

    def open_interpret_prompt(self) -> None:
        """ジャーナル内で解釈プロンプトを開始（[e]）"""
        groups = self._arch_interpret_groups()
        if not groups:
            self.log("まだ真理に到達していないので、解釈を記録できない。", (200, 160, 120))
            return
        self.arch_interpret_active = True
        self.arch_interpret_groups_cache = groups
        self.arch_interpret_truth_idx = 0
        self.arch_interpret_ending_idx = 0
        self.log("💭 解釈プロンプト: ↑↓で真理、←→でエンディング、Enterで決定、Escで取消。", (220, 200, 255))

    def interpret_move_truth(self, delta: int) -> None:
        if not getattr(self, "arch_interpret_active", False):
            return
        n = len(self.arch_interpret_groups_cache)
        self.arch_interpret_truth_idx = (self.arch_interpret_truth_idx + delta) % max(n, 1)
        self.arch_interpret_ending_idx = 0

    def interpret_move(self, delta: int) -> None:
        if not getattr(self, "arch_interpret_active", False):
            return
        g = self.arch_interpret_groups_cache[self.arch_interpret_truth_idx]
        n = len(g["endings"])
        self.arch_interpret_ending_idx = (self.arch_interpret_ending_idx + delta) % max(n, 1)

    def confirm_interpret(self) -> None:
        if not getattr(self, "arch_interpret_active", False):
            return
        g = self.arch_interpret_groups_cache[self.arch_interpret_truth_idx]
        eid = g["endings"][self.arch_interpret_ending_idx]
        mgr = self.archaeology_manager
        mgr.interpret_truth(self.player, g["tid"], eid, engine=self)
        self.arch_interpret_active = False

    def cancel_interpret(self) -> None:
        self.arch_interpret_active = False

    def play_music(self) -> None:
        """演奏 - 視界内のNPCのみおひねり (ステップ52)"""
        perf_lv = self.player.skills.get("performance")
        lv = perf_lv.level if perf_lv else 1
        lv += self.player.attributes.charisma // 3
        self.player.gain_skill_exp("performance", 35)
        total_tips = 0
        for e in self.entity_manager.get_living_entities():
            if e not in (self.player, self.pet) and e.hp > 0:
                success_rate = min(95, max(10, lv * 8 + self.player.attributes.charisma))
                if random.randint(1, 100) <= success_rate:
                    tip = random.randint(5, 10 + lv * 3)
                    total_tips += tip
                    self.log(f"{e.name}が拍手を送った！ (+{tip}G)", (255, 220, 100))
                else:
                    self.log(f"{e.name}は不満げに石を投げた！(演奏失敗 -1 HP)", (200, 100, 100))
                    self.player.hp -= 1
        if total_tips > 0:
            self.survival.gold += total_tips
            self.log(f"★演奏の報酬合計: {total_tips}G！", COLOR_GOLD_YELLOW)
        self.player.energy -= ENERGY_THRESHOLD
        self.advance_world()

    def pray(self) -> None:
        success, msg = self.player.pray_to_god()
        self.log(msg, (255, 215, 0) if success else (200, 200, 200))
        if success:
            self.player.energy -= ENERGY_THRESHOLD
            self.advance_world()

    def offer_altar(self) -> None:
        if (self.player.x, self.player.y) != self.altar_pos:
            self.log("祭壇の上に立っていない。")
            return
        for itm in list(self.inventory.items):
            if any(kw in itm.name for kw in ["肉", "鉱石", "パン", "ハーブ"]):
                self.inventory.remove_item(itm, count=1)
                self.player.piety += 30
                self.log(f"{itm.name} を捧げた！ 信仰度: {self.player.piety}", (255, 215, 0))
                self.player.energy -= ENERGY_THRESHOLD
                self.advance_world()
                return
        self.log("捧げる供物がない（肉・鉱石・パン・ハーブなど）。")

    def use_wish_rod(self) -> None:
        for itm in self.inventory.items:
            if "願いの杖" in itm.name:
                self.game_state = "wish"
                self.wish_input = ""
                self.log("★願いの杖を振った！ 何を望む？（テキストを入力してEnter）", (100, 255, 255))
                return
        self.log("願いの杖を持っていない。")

    def use_pet_evolution_stone(self) -> None:
        """特別アイテムによるペット進化トリガー (Step 46)"""
        if not self.pet or self.pet.hp <= 0:
            self.log("進化させられるペットがいません。")
            return
        p_type = getattr(self.pet, 'pet_type', 'puppy')
        evos = self.pet_evolution_manager.get_available_evolutions(p_type, self.pet.pet_ai, self.pet)
        if evos:
            target_evo = evos[0]
            ok = self.pet_evolution_manager.apply_evolution(self.pet.pet_ai, target_evo, self.pet)
            if ok:
                self.log(f"★進化の秘石が輝き、【{self.pet.name}】へと劇的進化した！", (255, 215, 0))
                SoundManager.play_se("level_up")
        else:
            self.log("ペットの絆度またはレベルが進化条件に達していません。")

    def use_alchemy_lab(self) -> None:
        """アルケミーラボでのペット融合施設利用トリガー (Steps 67, 68)"""
        # プレイヤーのペットと従えているペット群
        pets = [self.pet] + getattr(self.player, 'pets', [])
        if len(pets) < 2:
            self.log("融合には2体以上のペットが必要です。")
            return

        res_id = self.pet_fusion_manager.can_fuse(pets[:2], self.player)
        if not res_id:
            self.log("融合条件（種族・絆度・レベル等）を満たしていません。")
            return

        p1_name, p2_name = pets[0].name, pets[1].name
        fused = self.pet_fusion_manager.execute_fusion(pets[:2], self.player, res_id)
        if fused:
            self.pet = fused
            from ui_fx_systems import play_pet_fusion_fx
            play_pet_fusion_fx(self, p1_name, p2_name, fused.name)

    def confirm_wish(self) -> None:
        result = WishParser.parse(self.wish_input, self.player, self.inventory, self.survival)
        self.log(f"★願い「{self.wish_input}」: {result}", (100, 255, 255))
        self.game_state = "play"
        self.wish_input = ""

    def descend_stairs(self) -> None:
        if self.game_map.tiles[self.player.x][self.player.y] == TILE_STAIRS_DOWN:
            # 転生ダンジョン入場制限チェック (Step 52)
            if hasattr(self, "reincarnation_dungeon_manager") and self.dungeon_level >= 10:
                # 階層が深い場合などの制限チェックフック
                pass

            self.dungeon_level += 1
            self.log(f"★ダンジョン地下{self.dungeon_level}階へ降り立った！", (255, 200, 100))
            # プロシージャル・クエスト: 探索(深度到達)進捗を通知
            self._progress_generated_quests("explore", "depth", 1)
            self.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT, floor_level=self.dungeon_level)
            self.game_map.generate_dungeon()
            self.player.x, self.player.y = self.game_map.start_pos
            self.pet.x = self.player.x + 1
            self.pet.y = self.player.y
            # エンティティマネージャーをリセットしてプレイヤーとペットのみを設定
            self.entity_manager.clear()
            self.entity_manager.add_entity(self.player)
            self.entity_manager.add_entity(self.pet)
            self.entity_manager.items_on_ground.clear()
            self.entity_manager.resource_nodes.clear()
            self._spawn_dungeon()
            # 祭壇
            rx, ry = self.game_map.rooms[0].center
            self.altar_pos = (rx + 2, ry)
            self.game_map.compute_fov(self.player.x, self.player.y, radius=8)

            # ダンジョン訪問フロア記録 (Step 34)
            if hasattr(self.player, 'dungeon_floors_visited'):
                self.player.dungeon_floors_visited.add((1, self.dungeon_level))
            if hasattr(self.player, 'max_dungeon_depth'):
                self.player.max_dungeon_depth = max(self.player.max_dungeon_depth, self.dungeon_level)

            # メタ進行用の通算階層カウント
            if hasattr(self.player, 'meta_progression'):
                self.player.meta_progression["cumulative_depth_stat"] = self.player.meta_progression.get("cumulative_depth_stat", 0) + 1

            if hasattr(self, 'achievement_manager'):
                self.achievement_manager.check_all_achievements(self.player, self)
            if hasattr(self, 'meta_progression_manager'):
                self.meta_progression_manager.check_meta_goals(self.player, self)


            # 階層到達チュートリアル (Step 1.2)
            if self.dungeon_level >= 10:
                self.check_tutorial_triggers("reach_depth_10")

            # オートセーブ
            msg = SaveSystem.save(self)
            self.log(f"[Auto] {msg}", (80, 200, 80))
        else:
            self.log("ここには下り階段はない。")

    def check_reincarnation_option(self) -> bool:
        """転生オプション表示・判定 (Steps 29, 30)"""
        # TODO: Reincarnation option
        if hasattr(self, "reincarnation_manager"):
            can_reinc = self.reincarnation_manager.can_reincarnate(self.player)
            if can_reinc:
                self.check_tutorial_triggers("reincarnate_ready")
            return can_reinc
        return False

    def reincarnate(self) -> None:
        """転生処理 (Steps 27, 28, 60, 61, 71)"""
        if not self.player:
            return
        if hasattr(self, "reincarnation_manager"):
            self.reincarnation_manager.reincarnate(self.player, self)
        else:
            self.player.reincarnation_count += 1
            self.player.total_level_earned += self.player.level
            self.player.level = 1
            self.player.exp = 0
            self.player.exp_next = 100
            self.log(f"★転生を実行した！ (転生回数: {self.player.reincarnation_count}, 累計レベル: {self.player.total_level_earned})", (255, 215, 0))
        self.check_tutorial_triggers("reincarnate_ready")


    def help_friend(self) -> None:
        """フレンド救援処理 (Step 57)"""
        if not self.player:
            return
        self.player.friend_helps += 1
        self.player.social_points += 10
        self.log(f"★フレンドを救援した！ (救援回数: {self.player.friend_helps})", (100, 255, 200))
        if hasattr(self, 'achievement_manager'):
            self.achievement_manager.check_all_achievements(self.player, self)

    # -------------------------------------------------------------
    # ゲームループ分離: 更新と描画 (Step 5)
    # -------------------------------------------------------------
    def update(self, delta_time: float = 1.0) -> None:
        """ゲームロジック更新 (描画を行わない)"""
        # ターン処理
        if hasattr(self, 'turn_queue') and self.turn_queue:
            self.turn_queue.process(self, delta_time)

        # システム更新
        if hasattr(self, 'systems_coordinator'):
            self.systems_coordinator.update_all(self, delta_time)

        # FX更新
        if hasattr(self, 'fx_manager'):
            self.fx_manager.update(delta_time)

        # チュートリアル更新
        if hasattr(self, 'tutorial_manager'):
            self.tutorial_manager.update(delta_time)

        # 通知更新
        if hasattr(self, 'notification_manager'):
            self.notification_manager.update(delta_time)

        # アニメーションタイル更新
        if hasattr(self, 'game_map'):
            self.game_map.update_animations(delta_time)

        self.turns += 1

    def render(self, console: Any) -> None:
        """描画処理 (ゲームロジックを含まない)"""
        from render_system import RenderSystem
        from renderer import TcodRenderer
        from render_context import RenderContext
        # Step 7: Renderer インターフェースをコンソール実装で活用
        self.renderer = TcodRenderer(console)
        # Create render context
        render_context = RenderContext(
            game_map=self.game_state_data.game_map,
            player=self.game_state_data.player,
            pet=self.game_state_data.pet,
            entities=self.entity_manager.get_entities(),
            items_on_ground=self.entity_manager.items_on_ground,
            resource_nodes=self.entity_manager.resource_nodes,
            survival=self.game_state_data.survival,
            floating_texts=self.fx_manager.floating_texts,
            particles=self.fx_manager.particles,
            look_cursor=self.look_cursor,
            game_state=self.game_state_data.game_state,
            time_system=self.time_system,
            dungeon_level=self.game_state_data.dungeon_level,
            msg_log=self.msg_log,
            fx_manager=self.fx_manager,
            notification_manager=self.notification_manager,
            achievement_notifications=getattr(self.game_state_data.player, 'achievement_notifications', []),
            current_weather=getattr(self, "current_weather", "fog"),
            casting_spell=getattr(self, "casting_spell", None),
            frame_count=getattr(self, "frame_count", 0),
            inventory_target=self.inventory_target,
            inventory_tab=self.inventory_tab,
            inventory_cursor=self.inventory_cursor,
            pet_inventory=self.game_state_data.pet_inventory,
            altar_pos=self.game_state_data.altar_pos
        )
        RenderSystem.render_all(console, render_context)


def get_tabbed_items(engine: Engine) -> List[Item]:
    """RenderSystem への委譲 (後方互換性)"""
    from render_system import RenderSystem
    from render_context import RenderContext
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
        achievement_notifications=getattr(engine.game_state_data.player, 'achievement_notifications', []),
        current_weather=getattr(engine, "current_weather", "fog"),
        casting_spell=getattr(engine, "casting_spell", None),
        frame_count=getattr(engine, "frame_count", 0),
        inventory_target=engine.inventory_target,
        inventory_tab=engine.inventory_tab,
        inventory_cursor=engine.inventory_cursor,
        pet_inventory=engine.game_state_data.pet_inventory,
        altar_pos=engine.game_state_data.altar_pos
    )
    return RenderSystem.get_tabbed_items(render_context)


def render_all(console: tcod.console.Console, engine: Engine) -> None:
    """RenderSystem への委譲 (後方互換性)"""
    from render_system import RenderSystem
    from render_context import RenderContext
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
        achievement_notifications=getattr(engine.game_state_data.player, 'achievement_notifications', []),
        current_weather=getattr(engine, "current_weather", "fog"),
        casting_spell=getattr(engine, "casting_spell", None),
        frame_count=getattr(engine, "frame_count", 0),
        inventory_target=engine.inventory_target,
        inventory_tab=engine.inventory_tab,
        inventory_cursor=engine.inventory_cursor,
        pet_inventory=engine.game_state_data.pet_inventory,
        altar_pos=engine.game_state_data.altar_pos
    )
    RenderSystem.render_all(console, render_context)


def main() -> None:
    from input_handler import InputHandler

    engine = Engine()
    print("DEBUG: Engine created successfully")

    try:
        with tcod.context.new(
            columns=SCREEN_WIDTH,
            rows=SCREEN_HEIGHT,
            title="naRou: Masterpiece Edition - Steps 1~72 Complete",
            vsync=True,
        ) as context:
            root_console = tcod.console.Console(SCREEN_WIDTH, SCREEN_HEIGHT, order="F")

            while True:
                engine.update()
                engine.render(root_console)
                context.present(root_console)
                # Step 6.5: 入力を ActionRegistry 経由で処理
                for event in tcod.event.get(timeout=0):
                    InputHandler.handle_event(event, engine)
    except Exception as e:
        # If we can't initialize the SDL context (e.g., in headless environment),
        # we can still run the web server for testing
        print(f"Warning: Could not initialize SDL context: {e}")
        print("Web server is still running. Access it at http://localhost:8080")
        # Keep the process running to maintain the web server
        import time
        while True:
            time.sleep(1)

if __name__ == "__main__":
    main()
