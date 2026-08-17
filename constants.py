"""
Elona Roguelike Masterpiece - Core Constants & Enums
Step 1 of the Ultimate Plan
"""

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
    COMBAT    = "combat"     # 戦闘演出中（ターン処理待ち）
    DIALOGUE  = "dialogue"   # NPCとの会話中
    MENU      = "menu"       # インベントリやスキルツリーなどのメニュー展開中
    EVENT     = "event"      # 世界イベント・ストーリー選択のカットシーン中
    PAUSED    = "paused"     # 一時停止状態
