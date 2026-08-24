from __future__ import annotations

"""Constants for naRou - Centralized magic numbers and configuration values."""

from enum import Enum

# Combat
HIT_RATE_BASE = 75
HIT_RATE_DEX_MULTIPLIER = 2
CRIT_RATE_BASE = 5
CRIT_RATE_DEX_MULTIPLIER = 1
CRIT_DAMAGE_MULTIPLIER = 1.5
BLEED_CHANCE = 0.05
BLEED_DAMAGE_PER_TURN = 0.1
POISON_DAMAGE_PER_TURN = 0.08
BURN_DAMAGE_PER_TURN = 0.12

# Stats
MAX_LEVEL = 200
EXP_BASE = 100
EXP_GROWTH_FACTOR = 1.5
STAT_POINT_PER_LEVEL = 5
STARTING_STAT_VALUE = 10
MAX_STAT_VALUE = 999

# Health/Mana
HP_PER_VITALITY = 5
MP_PER_WILL = 3
HP_REGEN_RATE = 0.02
MP_REGEN_RATE = 0.015
NATURAL_HEAL_THRESHOLD = 0.5
NATURAL_REGEN_HUNGER_THRESHOLD = 1000
NATURAL_REGEN_INTERVAL = 10

# Inventory
MAX_INVENTORY_WEIGHT = 1000
DEFAULT_INVENTORY_SLOTS = 50
STACK_SIZE_LIMIT = 999

# Equipment
EQUIP_SLOTS = (
    "main_hand",
    "off_hand",
    "head",
    "body",
    "legs",
    "feet",
    "hands",
    "neck",
    "ring_left",
    "ring_right",
    "back",
    "waist",
    "ammo",
)

# Skills
SKILL_EXP_BASE = 10
SKILL_EXP_GROWTH = 1.3
MAX_SKILL_LEVEL = 50
SKILL_POINT_PER_LEVEL = 1

# Faction
FACTION_NEUTRAL = 0
FACTION_ALLIED_MIN = 50
FACTION_HOSTILE_MAX = -50
FACTION_CHANGE_PER_ACTION = 5

# Aggro
AGGRO_DECAY_PER_TURN = 0.1
AGGRO_THREAT_MULTIPLIER = 1.5
AGGRO_HEAL_MULTIPLIER = 0.5

# World
MAP_WIDTH = 80
MAP_HEIGHT = 50
VIEW_WIDTH = 80
VIEW_HEIGHT = 50
SCREEN_WIDTH = 100
SCREEN_HEIGHT = 60
TILE_SIZE = 16

# Tiles
TILE_FLOOR = 0
TILE_WALL = 1
TILE_STAIRS_DOWN = 2
TILE_STAIRS_UP = 3
TILE_DOOR_CLOSED = 4
TILE_DOOR_OPEN = 5
TILE_HIDDEN_DOOR = 6
TILE_SECRET_FLOOR = 7
TILE_FALSE_WALL = 8
TILE_VENT = 9
TILE_TRAP = 10


# Energy
ENERGY_THRESHOLD = 100
PLAYER_ENERGY_PER_TURN = 100
MONSTER_ENERGY_PER_TURN = 100

# Pet
PET_PATH_LENGTH_CHECK = 20
PET_RETREAT_HP_RATIO = 0.3
PET_LOYALTY_MAX = 100
PET_LOYALTY_DECAY = 0.1
FACTION_INFLUENCE_INTERVAL = 100
COMBAT_BOND_GAIN = 2
BOND_NEGLECTED_LOSS = 1
BOND_WALKING_GAIN = 1
PET_NEGLECTED_BOND_DISTANCE = 10
PET_WALKING_BOND_DISTANCE = 3
REINCARNATION_XP_PENALTY_BASE = 0.5
REINCARNATION_XP_PENALTY_STEP = 0.05
SKILL_DROP_CHANCE = 0.3
SKILL_DROP_MAX = 3
SKILL_DROP_MIN = 1

# Pet Personalities (Step 49)
PERSONALITY_BRAVE = "brave"
PERSONALITY_COWARDLY = "cowardly"
PERSONALITY_CALM = "calm"
PERSONALITY_GLUTTONOUS = "gluttonous"
PERSONALITY_AGGRESSIVE = "aggressive"

PERSONALITY_LABELS = {
    PERSONALITY_BRAVE: "勇敢",
    PERSONALITY_COWARDLY: "臆病",
    PERSONALITY_CALM: "冷静",
    PERSONALITY_GLUTTONOUS: "食いしん坊",
    PERSONALITY_AGGRESSIVE: "好戦的",
}

# Food Tags (Step 51-52)
FOOD_TAG_MEAT = "meat"
FOOD_TAG_VEGETABLE = "vegetable"
FOOD_TAG_SWEET = "sweet"
FOOD_TAG_FISH = "fish"
FOOD_TAG_HERB = "herb"


# Food/Hunger
HUNGER_MAX = 10000
HUNGER_PER_TURN = 1
STARVING_THRESHOLD = 1000
FULL_THRESHOLD = 8000
FOOD_ROT_TIME = 86400  # 24 hours in seconds

# Crafting
CRAFT_SUCCESS_BASE = 70
CRAFT_SUCCESS_SKILL_BONUS = 2
CRAFT_CRIT_CHANCE = 0.05

# Materials / Crafting Resources
MATERIAL_WOOD = "wood"
MATERIAL_IRON = "iron"
MATERIAL_STEEL = "steel"
MATERIAL_MYTHRIL = "mythril"
MATERIAL_RUBINUS = "rubinus"
MATERIAL_DIAMOND = "diamond"
MATERIAL_LEATHER = "leather"
MATERIAL_CLOTH = "cloth"
MATERIAL_HERB = "herb"

MATERIAL_NAMES = {
    MATERIAL_WOOD: "木材",
    MATERIAL_IRON: "鉄インゴット",
    MATERIAL_STEEL: "鋼鉄インゴット",
    MATERIAL_MYTHRIL: "ミスリル鉱石",
    MATERIAL_RUBINUS: "ルビナス原石",
    MATERIAL_DIAMOND: "ダイヤモンド",
    MATERIAL_LEATHER: "革",
    MATERIAL_CLOTH: "布",
    MATERIAL_HERB: "薬草",
}

# Wish
WISH_COST_BASE = 1000
WISH_COST_MULTIPLIER = 1.5

# Reincarnation
REINCARNATION_BONUS_STATS = 5
REINCARNATION_BONUS_SKILL_POINTS = 10
MAX_REINCARNATIONS = 10

# Difficulty
DIFFICULTY_EASY = "easy"
DIFFICULTY_NORMAL = "normal"
DIFFICULTY_HARD = "hard"
DIFFICULTY_NIGHTMARE = "nightmare"

DIFFICULTY_MODIFIERS = {
    DIFFICULTY_EASY: {
        "enemy_hp_mult": 0.7,
        "enemy_damage_mult": 0.7,
        "exp_mult": 1.2,
        "drop_rate_mult": 1.2,
    },
    DIFFICULTY_NORMAL: {
        "enemy_hp_mult": 1.0,
        "enemy_damage_mult": 1.0,
        "exp_mult": 1.0,
        "drop_rate_mult": 1.0,
    },
    DIFFICULTY_HARD: {
        "enemy_hp_mult": 1.3,
        "enemy_damage_mult": 1.3,
        "exp_mult": 1.1,
        "drop_rate_mult": 0.9,
    },
    DIFFICULTY_NIGHTMARE: {
        "enemy_hp_mult": 2.0,
        "enemy_damage_mult": 2.0,
        "exp_mult": 1.5,
        "drop_rate_mult": 0.7,
    },
}

# Colors
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (128, 128, 128)
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_YELLOW = (255, 255, 0)
COLOR_CYAN = (0, 255, 255)
COLOR_MAGENTA = (255, 0, 255)
COLOR_ORANGE = (255, 165, 0)
COLOR_PINK = (255, 192, 203)
COLOR_GOLD_YELLOW = (255, 215, 0)
COLOR_PET_PINK = (255, 105, 180)
COLOR_HP_GREEN = (0, 255, 100)
COLOR_MP_BLUE = (100, 150, 255)
COLOR_ALTAR = (255, 215, 0)
SNAIL_COLOR = (150, 200, 150)
SNAIL_SPEED = 50
SPAWN_ITEM_CHANCE = 0.5
SPAWN_MONSTER_CHANCE = 0.6
SPAWN_RESOURCE_NODE_CHANCE = 0.3
SPAWN_SNAIL_CHANCE = 0.2

# Secret Area & Access Requirements
ACCESS_FACTION_REP = "faction_rep"
ACCESS_QUEST_FLAG = "quest_flag"
ACCESS_SACRIFICE = "sacrifice"
ACCESS_SKILL_REQUIRED = "skill_required"
ACCESS_TIME_WINDOW = "time_window"

EMOTE_EYE = "👁️"
EMOTE_KEY = "🔑"

KEY_TYPE_BIOMETRIC = "biometric"
KEY_TYPE_DECRYPTION = "decryption"
KEY_TYPE_KEYCARD = "keycard"
KEY_TYPE_PHYSICAL = "physical"

REWARD_CONCEPT_CRYSTAL = "concept_crystal"
REWARD_FORBIDDEN_SKILL = "forbidden_skill"
REWARD_HIDDEN_MERCHANT = "hidden_merchant"
REWARD_LORE = "lore"
REWARD_SHORTCUT = "shortcut"
COLOR_FLOOR_DARK = (50, 50, 60)
COLOR_FLOOR_LIT = (200, 180, 150)
COLOR_WALL_DARK = (0, 0, 100)
COLOR_WALL_LIT = (130, 110, 50)


# Elements
class Element(Enum):
    NONE = "none"
    FIRE = "fire"
    ICE = "ice"
    COLD = "ice"
    LIGHTNING = "lightning"
    POISON = "poison"
    HOLY = "holy"
    DARK = "dark"
    DARKNESS = "dark"
    CHAOS = "chaos"
    MAGIC = "magic"
    PHYSICAL = "physical"


ELEMENT_LABELS = {
    "fire": "火炎",
    "ice": "氷結",
    "lightning": "電撃",
    "poison": "毒",
    "holy": "聖なる力",
    "dark": "暗黒",
    "chaos": "混沌",
    "magic": "魔法",
    "physical": "物理",
}

ELEMENT_WEAKNESS_MAP = {
    "fire": "ice",       # 火炎は氷結に強い (氷結属性持ちは火炎が弱点)
    "ice": "lightning",  # 氷結は電撃に強い
    "lightning": "poison",
    "poison": "holy",
    "holy": "dark",
    "dark": "holy",
}

# Status Effects (Steps 50, 54)
STATUS_POISON = "poison"
STATUS_BURN = "burn"
STATUS_FREEZE = "freeze"
STATUS_PARALYZE = "paralyze"
STATUS_CONFUSION = "confusion"
STATUS_BLIND = "blind"
STATUS_SLEEP = "sleep"

ALL_STATUS_EFFECTS = (
    STATUS_POISON,
    STATUS_BURN,
    STATUS_FREEZE,
    STATUS_PARALYZE,
    STATUS_CONFUSION,
    STATUS_BLIND,
    STATUS_SLEEP,
)

STATUS_LABELS = {
    STATUS_POISON: "毒",
    STATUS_BURN: "炎上",
    STATUS_FREEZE: "凍結",
    STATUS_PARALYZE: "麻痺",
    STATUS_CONFUSION: "混乱",
    STATUS_BLIND: "盲目",
    STATUS_SLEEP: "睡眠",
}

STATUS_ICONS = {
    STATUS_POISON: "🧪",
    STATUS_BURN: "🔥",
    STATUS_FREEZE: "❄️",
    STATUS_PARALYZE: "⚡",
    STATUS_CONFUSION: "💫",
    STATUS_BLIND: "👁️‍🗨️",
    STATUS_SLEEP: "💤",
}


# Game States
class GameState(Enum):
    TITLE = "title"
    PLAYING = "playing"
    EXPLORING = "exploring"
    PAUSED = "paused"
    INVENTORY = "inventory"
    CHARACTER = "character"
    SKILL_TREE = "skill_tree"
    QUEST_LOG = "quest_log"
    SETTINGS = "settings"
    GAME_OVER = "game_over"
    VICTORY = "victory"
    MENU = "menu"
    DIALOGUE = "dialogue"
    COMBAT = "combat"
    LOADING = "loading"
    EVENT = "event"


GAME_STATE_TO_LEGACY = {
    GameState.TITLE: "title",
    GameState.PLAYING: "play",
    GameState.EXPLORING: "play",
    GameState.PAUSED: "paused",
    GameState.INVENTORY: "inventory",
    GameState.CHARACTER: "character",
    GameState.SKILL_TREE: "skill_tree",
    GameState.QUEST_LOG: "quest_log",
    GameState.SETTINGS: "settings",
    GameState.GAME_OVER: "game_over",
    GameState.VICTORY: "victory",
    GameState.MENU: "menu",
    GameState.DIALOGUE: "talk",
    GameState.COMBAT: "combat",
    GameState.LOADING: "loading",
    GameState.EVENT: "event",
}


# Starting values
STARTING_GOD_ID = "lulwy"
DEFAULT_GOD_ID = "lulwy"
STARTING_LEVEL = 1
STARTING_GOLD = 100

# AI Roles & Ranges
AI_ROLE_KITER = "kiter"
AI_ROLE_BRUTE = "brute"
AI_ROLE_FLANKER = "flanker"
AI_ROLE_SUPPORT = "support"
AI_ROLE_MELEE = "melee"
AI_ROLE_TANK = "tank"
AI_ROLE_CASTER = "caster"
PINCER_MIN_ALLIES = 2
KITER_PREFERRED_RANGE = 3
HARD_KITER_RANGE_BONUS = 2

# Item Quality & Categories
QUALITY_BAD = "bad"
QUALITY_NORMAL = "normal"
QUALITY_GOOD = "good"
QUALITY_MIRACLE = "miracle"
QUALITY_GOD = "god"

ALL_QUALITIES = (QUALITY_BAD, QUALITY_NORMAL, QUALITY_GOOD, QUALITY_MIRACLE, QUALITY_GOD)

QUALITY_LABELS = {
    QUALITY_BAD: "粗悪",
    QUALITY_NORMAL: "通常",
    QUALITY_GOOD: "良質",
    QUALITY_MIRACLE: "奇跡",
    QUALITY_GOD: "神器",
}

QUALITY_COLORS = {
    QUALITY_BAD: (130, 130, 130),       # 灰色
    QUALITY_NORMAL: (255, 255, 255),    # 白
    QUALITY_GOOD: (100, 200, 255),      # 青
    QUALITY_MIRACLE: (200, 100, 255),   # 紫
    QUALITY_GOD: (255, 215, 0),         # 金
}

QUALITY_VALUE_MULTIPLIERS = {
    QUALITY_BAD: 0.5,
    QUALITY_NORMAL: 1.0,
    QUALITY_GOOD: 1.5,
    QUALITY_MIRACLE: 3.0,
    QUALITY_GOD: 6.0,
}
CAT_WEAPON = "weapon"
CAT_SHIELD = "shield"
CAT_HELM = "helm"
CAT_ARMOR = "armor"
CAT_RING = "ring"
CAT_POTION = "potion"
CAT_SCROLL = "scroll"
CAT_FOOD = "food"
CAT_SPELLBOOK = "spellbook"
CAT_TOOL = "tool"
CAT_ROD = "rod"
CAT_ORE = "ore"
CAT_GOLD = "gold"


# Entity Intent
INTENT_ATTACK = "attack"
INTENT_MOVE = "move"
INTENT_CAST = "cast"
INTENT_HEAL = "heal"
INTENT_FLEE = "flee"
INTENT_GUARD = "guard"
INTENT_GLYPH = "glyph"

INTENT_LABEL_JA = {
    INTENT_ATTACK: "攻撃",
    INTENT_MOVE: "移動",
    INTENT_CAST: "詠唱",
    INTENT_HEAL: "回復",
    INTENT_FLEE: "逃走",
    INTENT_GUARD: "防御",
    INTENT_GLYPH: "魔法陣",
}

FLEE_HP_RATIO = 0.25


# Save
SAVE_VERSION = 2
SAVE_SLOT_COUNT = 10
AUTO_SAVE_INTERVAL = 300  # seconds

# World News & Progression Intervals
WORLD_NEWS_INTERVAL = 50
TITLE_CHECK_INTERVAL = 10
JOB_EXP_PER_TURN = 1
JOB_LEVEL_UP_THRESHOLD = 100
SKILL_POINTS_NOTIFICATION_THRESHOLD = 1
SKILL_TREE_CHECK_INTERVAL = 20
GUILD_QUEST_RESET_INTERVAL = 1000

# Network
DEFAULT_PORT = 8080
WS_PORT = 8765

# UI
LOG_MESSAGE_MAX = 100
HELP_TEXT_LINES = 20

