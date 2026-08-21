"""
Elona Roguelike Masterpiece - Core Constants & Enums
Step 1 of the Ultimate Plan
"""
from __future__ import annotations

from enum import Enum, auto

# バージョン管理 (Step 17)
VERSION = "1.0.0"
RELEASE_TYPE = "Commercial"
SAVE_FORMAT_VERSION = "2.0.0"

# 画面設定
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
MAP_WIDTH = 120
MAP_HEIGHT = 80
VIEW_WIDTH = 80
VIEW_HEIGHT = 38

# 行動エネルギー閾値 (Elona仕様)
ENERGY_THRESHOLD = 1000

# タイル文字 (libtcod標準互換)
TILE_WALL = "#"
TILE_FLOOR = "."
TILE_STAIRS_DOWN = ">"
TILE_STAIRS_UP = "<"
TILE_WATER = "~"
TILE_TRAP = "^"

# 敵の「次回行動（意図）」種別 (提案2: 意図可視化)
INTENT_ATTACK = "attack"
INTENT_CAST = "cast"
INTENT_FLEE = "flee"
INTENT_HEAL = "heal"
INTENT_MOVE = "move"
INTENT_GUARD = "guard"

# 意図アイコン (頭上描画用)
INTENT_GLYPH = {
    INTENT_ATTACK: "⚔",
    INTENT_CAST: "✷",
    INTENT_FLEE: "➛",
    INTENT_HEAL: "✚",
    INTENT_MOVE: "·",
    INTENT_GUARD: "🛡",
}

# 意図ラベル (JA)
INTENT_LABEL_JA = {
    INTENT_ATTACK: "突撃",
    INTENT_CAST: "詠唱",
    INTENT_FLEE: "逃走",
    INTENT_HEAL: "回復",
    INTENT_MOVE: "接近",
    INTENT_GUARD: "防御",
}

# 敵AIロール (提案4: 陣形・連携タクティクス)
AI_ROLE_BRUTE = "brute"      # 接近してぶつかる（既定）
AI_ROLE_KITER = "kiter"      # 間合いを維持して遠隔
AI_ROLE_FLANKER = "flanker"  # プレイヤーの裏を取る
AI_ROLE_SUPPORT = "support"  # 回復・バフ優先

# 陣形・連携用定数
KITER_PREFERRED_RANGE = 4     # kiter が維持する理想距離
FLEE_HP_RATIO = 0.30          # このHP比率未満で逃走を検討
FORMATION_SPREAD_GAP = 1      # 味方と重ならないための最低間隔
FLANK_SIDE_OFFSET = 1         # 挟撃時の側面オフセット
PINCER_MIN_ALLIES = 2         # 連携(挟撃)発動に必要な視界内味方数
HARD_KITER_RANGE_BONUS = 1    # 難易度hard時の kiter 間合いボーナス


# 属性Enum
class Element(Enum):
    PHYSICAL = auto()
    FIRE = auto()
    COLD = auto()
    LIGHTNING = auto()
    DARKNESS = auto()
    CHAOS = auto()
    MAGIC = auto()


# アイテムカテゴリ
class ItemCategory(Enum):
    WEAPON = "weapon"
    SHIELD = "shield"
    HELM = "helm"
    ARMOR = "armor"
    RING = "ring"
    POTION = "potion"
    SCROLL = "scroll"
    FOOD = "food"
    SPELLBOOK = "spellbook"
    TOOL = "tool"
    ROD = "rod"
    ORE = "ore"
    GOLD = "gold"


# アイテムカテゴリ定数（後方互換用）
CAT_WEAPON = "weapon"
CAT_SHIELD = "shield"
CAT_ARMOR = "armor"
CAT_FOOD = "food"
CAT_POTION = "potion"
CAT_ORE = "ore"
CAT_HELM = "helm"
CAT_RING = "ring"
CAT_SCROLL = "scroll"
CAT_SPELLBOOK = "spellbook"
CAT_TOOL = "tool"
CAT_ROD = "rod"
CAT_GOLD = "gold"

# カラーパレット (RGB)
COLOR_WALL_DARK = (35, 35, 45)
COLOR_WALL_LIT = (145, 120, 90)
COLOR_FLOOR_DARK = (18, 18, 25)
COLOR_FLOOR_LIT = (195, 175, 145)
COLOR_ALTAR = (255, 215, 0)
COLOR_TRAP = (220, 80, 80)
COLOR_WATER = (60, 120, 220)

COLOR_HP_GREEN = (100, 255, 100)
COLOR_MP_BLUE = (100, 200, 255)
COLOR_GOLD_YELLOW = (255, 215, 0)
COLOR_PET_PINK = (255, 180, 210)

# アイテム品質定数
QUALITY_BAD = "粗悪"
QUALITY_NORMAL = "通常"
QUALITY_GOOD = "良質"
QUALITY_MIRACLE = "奇跡"
QUALITY_GOD = "神器"


# ゲーム状態Enum (Step 6.1)
class GameState(Enum):
    EXPLORING = "exploring"  # 通常の探索・移動状態
    COMBAT = "combat"  # 戦闘演出中（ターン処理待ち）
    DIALOGUE = "dialogue"  # NPCとの会話中
    MENU = "menu"  # インベントリやスキルツリーなどのメニュー展開中
    EVENT = "event"  # 世界イベント・ストーリー選択のカットシーン中
    PAUSED = "paused"  # 一時停止状態


# 状態遷移: GameState値 -> 旧 game_state 文字列 (Step 6.2)
GAME_STATE_TO_LEGACY: dict[str, str] = {
    GameState.EXPLORING.value: "play",
    GameState.COMBAT.value: "play",
    GameState.DIALOGUE.value: "talk",
    GameState.MENU.value: "inventory",
    GameState.EVENT.value: "story_choice",
    GameState.PAUSED.value: "pause",
}


# ゲームバランス定数
SPAWN_SNAIL_CHANCE = 0.35
SPAWN_MONSTER_CHANCE = 0.85
SPAWN_ITEM_CHANCE = 0.7
SPAWN_RESOURCE_NODE_CHANCE = 0.3
SNAIL_SPEED = 60
SNAIL_COLOR = (255, 180, 220)
TITLE_CHECK_INTERVAL = 10
JOB_EXP_PER_TURN = 10
JOB_LEVEL_UP_THRESHOLD = 100
SKILL_TREE_CHECK_INTERVAL = 10
SKILL_POINTS_NOTIFICATION_THRESHOLD = 10
GUILD_QUEST_RESET_INTERVAL = 1000
FACTION_INFLUENCE_INTERVAL = 100
PET_WALKING_BOND_DISTANCE = 2
PET_NEGLECTED_BOND_DISTANCE = 8
PET_PATH_LENGTH_CHECK = 1
AUTO_SAVE_INTERVAL = 50

# --- 追加のマジックナンバー集約 (リファクタリング計画 Step 31-34) ---
REINCARNATION_XP_PENALTY_BASE = 0.50
REINCARNATION_XP_PENALTY_STEP = 0.05
SKILL_DROP_CHANCE = 0.20
SKILL_DROP_MIN = 1
SKILL_DROP_MAX = 2
BOSS_FRAGMENT_DROP_CHANCE = 0.08
NATURAL_REGEN_INTERVAL = 4
NATURAL_REGEN_HUNGER_THRESHOLD = 1000
WORLD_NEWS_INTERVAL = 30
PET_RETREAT_HP_RATIO = 0.3
DEFAULT_GOD_ID = "eyth"
STARTING_GOD_ID = "jure"
BOND_WALKING_GAIN = 1
BOND_NEGLECTED_LOSS = 2
COMBAT_BOND_GAIN = 5
