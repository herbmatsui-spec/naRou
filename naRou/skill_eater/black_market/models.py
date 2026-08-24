from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

BLACK_MARKET_EVENTS = {
    "ui_open": ("emote_graph_up.png", "hologram_ui_open.ogg"),
    "buy_success": ("emote_cash.png", "credits_transfer.ogg"),
    "sell_success": ("emote_cash.png", "handleCoins.ogg"),
    "route_establish": ("emote_exclamations.png", "encrypted_comms.ogg"),
    "route_profit": ("emote_stars.png", "credits_transfer.ogg"),
    "route_detected": ("emote_alert.png", "metalLatch.ogg"),
    "route_abandon": ("emote_cross.png", "doorClose_1.ogg"),
    "price_surge": ("emote_graph_up.png", "hologram_ui_open.ogg"),
    "contraband_get": ("emote_heart.png", "encrypted_comms.ogg"),
    "heat_warning": ("emote_alert.png", "metalClick.ogg"),
    "caravan_encounter": ("emote_idea.png", "bookOpen.ogg"),
    "location_unlock": ("emote_stars.png", "doorOpen_2.ogg"),
    "location_upgrade": ("emote_stars.png", "chop.ogg"),
}


class DistrictType(str, Enum):
    SLUM = "slum"
    CYBER = "cyber"
    MIDAS_BACK = "midas_back"
    MOBILE = "mobile"


class ContrabandType(str, Enum):
    ILLEGAL_SKILL = "illegal_skill"
    CONCEPT_CRYSTAL = "concept_crystal"
    FORBIDDEN_DATA_CHIP = "forbidden_data_chip"


class Rarity(str, Enum):
    COMMON = "common"
    RARE = "rare"
    UNIQUE = "unique"
    LEGENDARY = "legendary"


@dataclass
class BlackMarketLocation:
    id: str
    name: str
    district: DistrictType
    base_demand_factor: float = 0.0
    base_supply_factor: float = 0.0
    heat_penalty: float = 0.0
    faction_rep_bonus: Dict[str, float] = field(default_factory=dict)
    specialty_items: List[str] = field(default_factory=list)
    is_mobile: bool = False
    current_position: Optional[Tuple[int, int]] = None
    unlock_condition: Optional[str] = None
    is_unlocked: bool = False
    level: int = 1
    max_level: int = 5
    total_trade_volume: int = 0
    upgrade_threshold: int = 10000


@dataclass
class SmuggleRoute:
    id: str
    origin_id: str
    destination_id: str
    risk_level: int
    base_profit_per_turn: int
    heat_generation_per_turn: int
    contraband_types: List[str]
    is_active: bool = True
    turns_remaining: int = 0
    established_turn: int = 0
    total_profit: int = 0
    detection_accumulator: float = 0.0
    investment: int = 0


@dataclass
class ContrabandItem:
    id: str
    name: str
    type: ContrabandType
    base_price: int
    rarity: Rarity
    source_locations: List[str]
    route_restrictions: List[str]
    heat_risk: int
    description: str = ""
    stock: int = -1


@dataclass
class MarketPriceSnapshot:

    # Added market trend and utility functions
    # These were previously defined in skill_eater_black_market.py but now belong in the data model layer.
    
    @dataclass
    class MarketTrends:
        """Step 25: 闇市場の相場トレンド管理クラス"""
        high_demand_tags: list[str] = field(default_factory=lambda: ["Fire", "Combat"])
        low_demand_tags: list[str] = field(default_factory=lambda: ["Defense", "Utility"])
        turn_counter: int = 0

        def shift_trends(self) -> dict[str, list[str]]:
            """Step 27: 相場の定期変動ジョブ"""
            all_tags = ["Fire", "Ice", "Wind", "Water", "Combat", "Defense", "Utility", "Dark", "Holy", "Speed"]
            random.shuffle(all_tags)
            self.high_demand_tags = all_tags[:2]
            self.low_demand_tags = all_tags[2:4]
            self.turn_counter += 1
            return {"high_demand": self.high_demand_tags, "low_demand": self.low_demand_tags}

    def calculate_skill_market_value(skill_def: Any, trends: MarketTrends | None = None) -> int:
        """Step 26: スキル売却価格（クレジット）算出"""
        if not skill_def:
            return 100
        base = getattr(skill_def, "memory_cost_mb", 20) * 50
        tier_mult = {
            "Common": 1.0,
            "Rare": 2.5,
            "Unique": 6.0,
            "Concept": 20.0,
            "Eater": 50.0,
        }
        tier_str = skill_def.tier.value if hasattr(skill_def.tier, "value") else str(skill_def.tier)
        price = int(base * tier_mult.get(tier_str, 1.0))
        if trends:
            for t in getattr(skill_def, "tags", []):
                if t in trends.high_demand_tags:
                    price = int(price * 1.5)
                elif t in trends.low_demand_tags:
                    price = int(price * 0.6)
        return max(50, price)

    def sell_skill_to_black_market(character: CharacterState, skill_id: str, trends: MarketTrends | None = None) -> tuple[bool, int, str]:
        """Step 29, 30: スキルを闇市場で換金・売却するトランザクション"""
        if not character.has_skill(skill_id):
            return False, 0, "売却対象のスキルを所持していません。"
        registry = SkillEaterRegistry.get_instance()
        skill_def = registry.get_skill(skill_id)
        if not skill_def:
            return False, 0, "スキルのメタデータが存在しません。"
        val = calculate_skill_market_value(skill_def, trends)
        character.remove_skill(skill_id)
        character.calculate_memory_usage()
        return True, val, f"《{skill_def.name}》を闇市場で売却し、{val} クレジットを獲得しました。（空きメモリ増加）"

    class CyberDoctorSurgery:
        """Step 31〜35: 闇医者による脳インプラント拡張手術"""
        @staticmethod
        def calculate_expansion_cost(current_capacity_mb: int, expansion_mb: int = 20) -> int:
            base_cost = 500
            step_count = max(0, (current_capacity_mb - 100) // 20)
            return int(base_cost * (1.6 ** step_count))
        @staticmethod
        def perform_memory_expansion(character: CharacterState, credits_available: int, expansion_mb: int = 20, max_limit_mb: int = 300) -> tuple[bool, int, str]:
            if character.base_memory_capacity_mb >= max_limit_mb:
                return False, 0, f"脳インプラント拡張が上限（{max_limit_mb}MB）に達しています。"
            cost = CyberDoctorSurgery.calculate_expansion_cost(character.base_memory_capacity_mb, expansion_mb)
            if credits_available < cost:
                return False, 0, f"クレジット不足です。（必要: {cost} Cr / 所持: {credits_available} Cr）"
            old_cap = character.base_memory_capacity_mb
            character.base_memory_capacity_mb += expansion_mb
            character.calculate_memory_usage()
            return True, cost, f"【手術成功】脳容量 {old_cap}MB → {character.base_memory_capacity_mb}MB に拡張（費用: {cost} Cr）"

    def get_contraband_drop_table(enemy_tier: str) -> list[dict]:
        drops = []
        if enemy_tier in ["boss", "unique"]:
            drops.append({"item_id": "crystal_01", "chance": 0.05, "min_quantity": 1, "max_quantity": 1})
            drops.append({"item_id": "chip_02", "chance": 0.03, "min_quantity": 1, "max_quantity": 1})
        if enemy_tier in ["elite", "boss", "unique"]:
            drops.append({"item_id": "ill_skill_01", "chance": 0.1, "min_quantity": 1, "max_quantity": 1})
            drops.append({"item_id": "chip_01", "chance": 0.08, "min_quantity": 1, "max_quantity": 1})
        if enemy_tier == "unique":
            drops.append({"item_id": "crystal_02", "chance": 0.02, "min_quantity": 1, "max_quantity": 1})
            drops.append({"item_id": "ill_skill_03", "chance": 0.01, "min_quantity": 1, "max_quantity": 1})
        return drops

    def process_contraband_drop(enemy_tier: str) -> list[str]:
        drops = get_contraband_drop_table(enemy_tier)
        obtained = []
        for drop in drops:
            if random.random() < drop["chance"]:
                qty = random.randint(drop["min_quantity"], drop["max_quantity"])
                obtained.extend([drop["item_id"]] * qty)
        return obtained
    location_id: str
    item_id: str
    turn: int
    final_price: int
    demand_factor: float
    supply_factor: float
    heat_penalty: float
    faction_bonus: float