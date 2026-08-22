"""skill_eater_black_market.py
Aの世界（スキル喰い） Phase 5+: 闇市場ネットワークシステム
- 複数拠点・動的価格・密輸ルート・専売品・演出統合
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


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
    faction_rep_bonus: dict[str, float] = field(default_factory=dict)
    specialty_items: list[str] = field(default_factory=list)
    is_mobile: bool = False
    current_position: tuple[int, int] | None = None
    unlock_condition: str | None = None
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
    contraband_types: list[str]
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
    source_locations: list[str]
    route_restrictions: list[str]
    heat_risk: int
    description: str = ""
    stock: int = -1


@dataclass
class MarketPriceSnapshot:
    location_id: str
    item_id: str
    turn: int
    final_price: int
    demand_factor: float
    supply_factor: float
    heat_penalty: float
    faction_bonus: float
