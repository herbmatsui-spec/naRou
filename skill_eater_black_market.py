"""
skill_eater_black_market.py
Aの世界（スキル喰い） Phase 5+: 闇市場ネットワークシステム
- 複数拠点・動的価格・密輸ルート・専売品・演出統合
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_economy_system import FactionState, SkillEaterEconomySystem
from skill_eater_presentation_system import SkillEaterPresentationSystem
from skill_eater_system import CharacterState, SkillEaterRegistry


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


class BlackMarketNetwork:
    _instance: BlackMarketNetwork | None = None

    def __new__(cls) -> BlackMarketNetwork:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        economy: SkillEaterEconomySystem | None = None,
        audio: SkillEaterAudioSystem | None = None,
        presentation: SkillEaterPresentationSystem | None = None,
    ):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self.economy = economy or SkillEaterEconomySystem.get_instance()
        self.audio = audio or SkillEaterAudioSystem.get_instance()
        self.presentation = presentation or SkillEaterPresentationSystem.get_instance()

        self.locations: dict[str, BlackMarketLocation] = {}
        self.routes: dict[str, SmuggleRoute] = {}
        self.contraband_items: dict[str, ContrabandItem] = {}
        self.price_history: list[MarketPriceSnapshot] = []
        self.trade_log: list[dict] = []
        self.current_turn: int = 0

        self._initialize_locations()
        self._initialize_routes()
        self._initialize_contraband()

    @classmethod
    def get_instance(cls) -> BlackMarketNetwork:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def _initialize_locations(self) -> None:
        self.locations = {
            "underground_bazaar": BlackMarketLocation(
                id="underground_bazaar",
                name="UndergroundBazaar",
                district=DistrictType.SLUM,
                base_demand_factor=0.15,
                base_supply_factor=-0.05,
                heat_penalty=0.02,
                faction_rep_bonus={"broker": 0.002, "resistance": 0.001},
                specialty_items=["ill_skill_01", "ill_skill_02"],
                unlock_condition=None,
                is_unlocked=True,
                level=1,
                upgrade_threshold=10000,
            ),
            "neon_data_haven": BlackMarketLocation(
                id="neon_data_haven",
                name="NeonDataHaven",
                district=DistrictType.CYBER,
                base_demand_factor=0.10,
                base_supply_factor=0.0,
                heat_penalty=0.03,
                faction_rep_bonus={"broker": 0.0015, "resistance": 0.002},
                specialty_items=["chip_01", "chip_02"],
                unlock_condition="resistance_rep_30",
                is_unlocked=False,
                level=1,
                upgrade_threshold=15000,
            ),
            "midas_black_vault": BlackMarketLocation(
                id="midas_black_vault",
                name="MidasBlackVault",
                district=DistrictType.MIDAS_BACK,
                base_demand_factor=0.20,
                base_supply_factor=-0.10,
                heat_penalty=0.05,
                faction_rep_bonus={"broker": 0.003, "midas": -0.003},
                specialty_items=["crystal_01", "crystal_02", "ill_skill_03", "ill_skill_05"],
                unlock_condition="midas_hostile_and_aldo_50000",
                is_unlocked=False,
                level=1,
                upgrade_threshold=25000,
            ),
            "mobile_caravan": BlackMarketLocation(
                id="mobile_caravan",
                name="MobileCaravan",
                district=DistrictType.MOBILE,
                base_demand_factor=0.05,
                base_supply_factor=0.05,
                heat_penalty=0.01,
                faction_rep_bonus={"broker": 0.001},
                specialty_items=["chip_03", "ill_skill_04", "crystal_03", "chip_04"],
                unlock_condition="quest_caravan_contact",
                is_unlocked=False,
                is_mobile=True,
                current_position=(0, 0),
                level=1,
                upgrade_threshold=20000,
            ),
        }

    def _initialize_routes(self) -> None:
        self.routes = {
            "bazaar_to_haven": SmuggleRoute(
                id="bazaar_to_haven",
                origin_id="underground_bazaar",
                destination_id="neon_data_haven",
                risk_level=3,
                base_profit_per_turn=500,
                heat_generation_per_turn=5,
                contraband_types=["illegal_skill", "forbidden_data_chip"],
                investment=5000,
            ),
            "haven_to_vault": SmuggleRoute(
                id="haven_to_vault",
                origin_id="neon_data_haven",
                destination_id="midas_black_vault",
                risk_level=5,
                base_profit_per_turn=1200,
                heat_generation_per_turn=10,
                contraband_types=["forbidden_data_chip", "concept_crystal"],
                investment=10000,
            ),
            "vault_to_bazaar": SmuggleRoute(
                id="vault_to_bazaar",
                origin_id="midas_black_vault",
                destination_id="underground_bazaar",
                risk_level=7,
                base_profit_per_turn=2000,
                heat_generation_per_turn=15,
                contraband_types=["concept_crystal", "illegal_skill"],
                investment=20000,
            ),
            "caravan_cycle": SmuggleRoute(
                id="caravan_cycle",
                origin_id="mobile_caravan",
                destination_id="mobile_caravan",
                risk_level=4,
                base_profit_per_turn=800,
                heat_generation_per_turn=8,
                contraband_types=["illegal_skill", "concept_crystal", "forbidden_data_chip"],
                investment=8000,
            ),
            "bazaar_to_vault_direct": SmuggleRoute(
                id="bazaar_to_vault_direct",
                origin_id="underground_bazaar",
                destination_id="midas_black_vault",
                risk_level=8,
                base_profit_per_turn=3000,
                heat_generation_per_turn=20,
                contraband_types=["concept_crystal"],
                investment=30000,
            ),
            "emergency_evac": SmuggleRoute(
                id="emergency_evac",
                origin_id="any",
                destination_id="safehouse",
                risk_level=10,
                base_profit_per_turn=0,
                heat_generation_per_turn=-30,
                contraband_types=["illegal_skill", "concept_crystal", "forbidden_data_chip"],
                turns_remaining=3,
                investment=0,
                is_active=False,
            ),
        }

    def _initialize_contraband(self) -> None:
        self.contraband_items = {
            "ill_skill_01": ContrabandItem(
                id="ill_skill_01",
                name="《影縫い》",
                type=ContrabandType.ILLEGAL_SKILL,
                base_price=15000,
                rarity=Rarity.RARE,
                source_locations=["underground_bazaar"],
                route_restrictions=["bazaar_to_haven"],
                heat_risk=5,
                description="敵の影を縫い付け、移動を封じる禁忌の暗殺術",
            ),
            "ill_skill_02": ContrabandItem(
                id="ill_skill_02",
                name="《記憶泥棒》",
                type=ContrabandType.ILLEGAL_SKILL,
                base_price=22000,
                rarity=Rarity.RARE,
                source_locations=["underground_bazaar"],
                route_restrictions=["bazaar_to_vault_direct"],
                heat_risk=8,
                description="対象の記憶を抜き取り、スキルとして複製する禁術",
            ),
            "ill_skill_03": ContrabandItem(
                id="ill_skill_03",
                name="《魂喰らい》",
                type=ContrabandType.ILLEGAL_SKILL,
                base_price=50000,
                rarity=Rarity.UNIQUE,
                source_locations=["midas_black_vault"],
                route_restrictions=["vault_to_bazaar"],
                heat_risk=15,
                description="倒した敵の魂を喰らい、永続的にステータスを吸収する",
            ),
            "ill_skill_04": ContrabandItem(
                id="ill_skill_04",
                name="《死者の囁き》",
                type=ContrabandType.ILLEGAL_SKILL,
                base_price=35000,
                rarity=Rarity.UNIQUE,
                source_locations=["mobile_caravan"],
                route_restrictions=["caravan_cycle"],
                heat_risk=12,
                description="死者の残留思念を読み取り、隠された情報を得る",
            ),
            "ill_skill_05": ContrabandItem(
                id="ill_skill_05",
                name="《因果律切断》",
                type=ContrabandType.ILLEGAL_SKILL,
                base_price=150000,
                rarity=Rarity.LEGENDARY,
                source_locations=["midas_black_vault"],
                route_restrictions=["vault_to_bazaar"],
                heat_risk=25,
                description="因果関係を断ち切り、受けたダメージを無かったことにする究極の防御",
            ),
            "crystal_01": ContrabandItem(
                id="crystal_01",
                name="《暴食の概念結晶》",
                type=ContrabandType.CONCEPT_CRYSTAL,
                base_price=80000,
                rarity=Rarity.UNIQUE,
                source_locations=["midas_black_vault"],
                route_restrictions=["haven_to_vault"],
                heat_risk=20,
                description="「喰らう」という概念そのものを結晶化した禁忌の宝石",
            ),
            "crystal_02": ContrabandItem(
                id="crystal_02",
                name="《虚無の概念結晶》",
                type=ContrabandType.CONCEPT_CRYSTAL,
                base_price=120000,
                rarity=Rarity.LEGENDARY,
                source_locations=["midas_black_vault"],
                route_restrictions=["vault_to_bazaar"],
                heat_risk=25,
                description="存在を虚無へ還す概念。装備者の記憶を徐々に削る代償で絶大な力を与える",
            ),
            "crystal_03": ContrabandItem(
                id="crystal_03",
                name="《終焉の概念結晶》",
                type=ContrabandType.CONCEPT_CRYSTAL,
                base_price=200000,
                rarity=Rarity.LEGENDARY,
                source_locations=["mobile_caravan"],
                route_restrictions=["emergency_evac"],
                heat_risk=30,
                description="世界の終わりを象る結晶。一度きりの「リセット」を可能にする",
            ),
            "chip_01": ContrabandItem(
                id="chip_01",
                name="《MIDAS人体実験記録》",
                type=ContrabandType.FORBIDDEN_DATA_CHIP,
                base_price=30000,
                rarity=Rarity.RARE,
                source_locations=["neon_data_haven"],
                route_restrictions=["bazaar_to_haven"],
                heat_risk=10,
                description="ミダスが隠蔽した人体実験の全記録。暴露すれば世論を動かせる",
            ),
            "chip_02": ContrabandItem(
                id="chip_02",
                name="《スキル銀行暗号鍵》",
                type=ContrabandType.FORBIDDEN_DATA_CHIP,
                base_price=45000,
                rarity=Rarity.UNIQUE,
                source_locations=["neon_data_haven"],
                route_restrictions=["haven_to_vault"],
                heat_risk=15,
                description="世界スキル銀行のマスターキー断片。全口座へのアクセス権を持つ",
            ),
            "chip_03": ContrabandItem(
                id="chip_03",
                name="《覚醒プロトコル原本》",
                type=ContrabandType.FORBIDDEN_DATA_CHIP,
                base_price=100000,
                rarity=Rarity.LEGENDARY,
                source_locations=["mobile_caravan"],
                route_restrictions=["caravan_cycle"],
                heat_risk=20,
                description="スキル覚醒の真の手順を記録したオリジナルプロトコル",
            ),
            "chip_04": ContrabandItem(
                id="chip_04",
                name="《世界の裏設定ログ》",
                type=ContrabandType.FORBIDDEN_DATA_CHIP,
                base_price=75000,
                rarity=Rarity.UNIQUE,
                source_locations=["mobile_caravan"],
                route_restrictions=["caravan_cycle"],
                heat_risk=18,
                description="世界の真実（バックグラウンドロア）が記された管理者用ログ",
            ),
        }

    def calculate_dynamic_price(
        self,
        location: BlackMarketLocation,
        item: ContrabandItem,
        player_faction_reps: dict[str, int],
    ) -> tuple[int, dict]:
        demand_factor = location.base_demand_factor
        supply_factor = location.base_supply_factor
        heat_penalty = min(0.5, self.economy.heat_level * 0.005)

        faction_bonus = 0.0
        for faction_id, rep in player_faction_reps.items():
            if faction_id in location.faction_rep_bonus:
                bonus_rate = location.faction_rep_bonus[faction_id]
                if bonus_rate > 0:
                    faction_bonus += min(0.2 if faction_id == "broker" else 0.1, rep * bonus_rate)
                else:
                    faction_bonus += max(-0.3, rep * bonus_rate)

        multiplier = 1.0 + demand_factor - supply_factor + heat_penalty + faction_bonus
        multiplier = max(0.5, min(2.0, multiplier))

        final_price = int(item.base_price * multiplier)

        breakdown = {
            "base_price": item.base_price,
            "demand_factor": demand_factor,
            "supply_factor": supply_factor,
            "heat_penalty": heat_penalty,
            "faction_bonus": faction_bonus,
            "multiplier": multiplier,
            "final_price": final_price,
        }

        return final_price, breakdown

    def update_demand_supply(self, location_id: str, is_buy: bool, quantity: int = 1) -> None:
        location = self.locations.get(location_id)
        if not location:
            return

        change = 0.05 * quantity
        if is_buy:
            location.base_demand_factor = min(0.5, location.base_demand_factor + change)
            location.base_supply_factor = max(-0.5, location.base_supply_factor - change * 0.4)
        else:
            location.base_supply_factor = min(0.5, location.base_supply_factor + change)
            location.base_demand_factor = max(-0.5, location.base_demand_factor - change * 0.4)

    def natural_recovery_demand_supply(self) -> None:
        for location in self.locations.values():
            if location.base_demand_factor > 0:
                location.base_demand_factor = max(0.0, location.base_demand_factor - 0.01)
            elif location.base_demand_factor < 0:
                location.base_demand_factor = min(0.0, location.base_demand_factor + 0.01)

            if location.base_supply_factor > 0:
                location.base_supply_factor = max(0.0, location.base_supply_factor - 0.01)
            elif location.base_supply_factor < 0:
                location.base_supply_factor = min(0.0, location.base_supply_factor + 0.01)

    def calculate_faction_bonus(self, location_id: str, player_faction_reps: dict[str, int]) -> float:
        location = self.locations.get(location_id)
        if not location:
            return 0.0

        bonus = 0.0
        for faction_id, rep in player_faction_reps.items():
            if faction_id in location.faction_rep_bonus:
                rate = location.faction_rep_bonus[faction_id]
                if rate > 0:
                    cap = 0.2 if faction_id == "broker" else 0.1
                    bonus += min(cap, rep * rate)
                else:
                    bonus += max(-0.3, rep * rate)
        return bonus

    def calculate_heat_penalty(self) -> float:
        return min(0.5, self.economy.heat_level * 0.005)

    def check_location_unlock(self, location_id: str, player: CharacterState) -> bool:
        location = self.locations.get(location_id)
        if not location or location.is_unlocked:
            return location.is_unlocked if location else False

        condition = location.unlock_condition
        if condition == "resistance_rep_30":
            rep = self.economy.factions.get("resistance", FactionState("resistance", "", 0)).reputation
            if rep >= 30:
                location.is_unlocked = True
                return True
        elif condition == "midas_hostile_and_aldo_50000":
            midas = self.economy.factions.get("midas", FactionState("midas", "", 0, True))
            if midas.is_hostile and self.economy.aldo_currency >= 50000:
                location.is_unlocked = True
                return True
        elif condition == "quest_caravan_contact":
            if hasattr(player, "quest_flags") and player.quest_flags.get("caravan_contact", False):
                location.is_unlocked = True
                return True
        return False

    def update_mobile_caravan_position(self) -> None:
        caravan = self.locations.get("mobile_caravan")
        if not caravan or not caravan.is_mobile:
            return

        if self.current_turn % 5 == 0 and self.current_turn > 0:
            districts = [
                (DistrictType.SLUM, (0, 0)),
                (DistrictType.CYBER, (10, 5)),
                (DistrictType.MIDAS_BACK, (20, 10)),
                (DistrictType.MOBILE, (5, 15)),
            ]
            import random
            new_district, new_pos = random.choice(districts)
            caravan.district = new_district
            caravan.current_position = new_pos

            self._rotate_caravan_specialty()

    def _rotate_caravan_specialty(self) -> None:
        caravan = self.locations.get("mobile_caravan")
        if not caravan:
            return

        all_items = list(self.contraband_items.keys())
        import random
        random.shuffle(all_items)
        caravan.specialty_items = all_items[:4]

    def get_location_status(self, location_id: str) -> dict:
        location = self.locations.get(location_id)
        if not location:
            return {"error": "Location not found"}

        player_faction_reps = {fid: fs.reputation for fid, fs in self.economy.factions.items()}
        available_items = {}
        for item_id in location.specialty_items:
            item = self.contraband_items.get(item_id)
            if item:
                price, breakdown = self.calculate_dynamic_price(location, item, player_faction_reps)
                available_items[item_id] = {
                    "name": item.name,
                    "type": item.type.value,
                    "rarity": item.rarity.value,
                    "price": price,
                    "breakdown": breakdown,
                    "heat_risk": item.heat_risk,
                    "description": item.description,
                }

        return {
            "id": location.id,
            "name": location.name,
            "district": location.district.value,
            "is_unlocked": location.is_unlocked,
            "is_mobile": location.is_mobile,
            "current_position": location.current_position,
            "level": location.level,
            "max_level": location.max_level,
            "total_trade_volume": location.total_trade_volume,
            "upgrade_threshold": location.upgrade_threshold,
            "heat_penalty": location.heat_penalty,
            "base_demand": location.base_demand_factor,
            "base_supply": location.base_supply_factor,
            "available_items": available_items,
            "unlock_condition": location.unlock_condition,
        }

    def travel_to_location(self, player: CharacterState, from_location_id: str, to_location_id: str) -> tuple[bool, str, int]:
        from_loc = self.locations.get(from_location_id)
        to_loc = self.locations.get(to_location_id)
        if not from_loc or not to_loc:
            return False, "無効な拠点です", 0

        if not to_loc.is_unlocked:
            return False, f"{to_loc.name} はまだ解放されていません", 0

        if self.economy.heat_level >= 80:
            return False, "警戒度が高すぎて移動できません（安全な場所で待機してください）", 0

        travel_cost = 500
        if from_loc.district != to_loc.district:
            travel_cost += 1000

        if self.economy.aldo_currency < travel_cost:
            return False, f"移動費用が不足しています（必要: {travel_cost} アルド）", 0

        self.economy.aldo_currency -= travel_cost

        encounter_roll = random.random()
        encounter_msg = ""
        if encounter_roll < 0.15:
            encounter_msg = " 途中、ミダスのパトロールと遭遇したが、うまくやり過ごした。"
            self.economy.heat_level = min(100, self.economy.heat_level + 5)
        elif encounter_roll < 0.25:
            encounter_msg = " 道中で行商人から有益な噂を聞いた。"
            self.presentation.add_event(
                emote_file="emote_idea.png",
                audio_file="bookOpen.ogg",
                message="移動中に情報を入手！",
            )

        return True, f"{from_loc.name} から {to_loc.name} へ移動しました（費用: {travel_cost} アルド）{encounter_msg}", travel_cost

    def generate_location_event(self, location_id: str) -> dict | None:
        location = self.locations.get(location_id)
        if not location or not location.is_unlocked:
            return None

        import random
        roll = random.random()
        event = None

        if location_id == "underground_bazaar":
            if roll < 0.2:
                event = {
                    "type": "rumor",
                    "message": "露天商の噂話: 「最近、サイバー地区のデータチップが高騰してるらしいぜ」",
                    "effect": "price_hint",
                    "target": "neon_data_haven",
                }
        elif location_id == "neon_data_haven":
            if roll < 0.2:
                event = {
                    "type": "hacker_meet",
                    "message": "ハッカー集会: 「禁忌データ、今なら1割引きで譲るよ」",
                    "effect": "discount",
                    "target": "forbidden_data_chip",
                    "discount": 0.1,
                }
        elif location_id == "midas_black_vault":
            if roll < 0.2:
                event = {
                    "type": "seminar",
                    "message": "裏金融セミナー: 「概念結晶の真の価値を知る者だけが生き残る」",
                    "effect": "rare_drop_info",
                    "target": "concept_crystal",
                }
        elif location_id == "mobile_caravan":
            if roll < 0.3:
                event = {
                    "type": "special_sale",
                    "message": "行商人の特別セール: 「全品10%オフ、今だけだぜ！」",
                    "effect": "global_discount",
                    "discount": 0.1,
                }

        if event:
            self.presentation.add_event(
                emote_file="emote_exclamation.png",
                audio_file="bookOpen.ogg",
                message=event["message"],
            )
        return event

    def upgrade_location(self, location_id: str) -> tuple[bool, str]:
        location = self.locations.get(location_id)
        if not location:
            return False, "存在しない拠点です"

        if location.level >= location.max_level:
            return False, "既に最大レベルに達しています"

        if location.total_trade_volume < location.upgrade_threshold:
            return False, f"取引実績が不足しています（必要: {location.upgrade_threshold}, 現在: {location.total_trade_volume}）"

        location.level += 1
        location.upgrade_threshold = int(location.upgrade_threshold * 1.5)
        location.heat_penalty = max(0.0, location.heat_penalty - 0.005)

        if location.level == 2:
            location.specialty_items.append(self._get_new_specialty_item(location_id))

        self.presentation.add_event(
            emote_file="emote_stars.png",
            audio_file="chop.ogg",
            message=f"【拠点強化】{location.name} が Lv.{location.level} に昇格！",
        )
        self.audio.play_sound("metalPot1.ogg")

        return True, f"{location.name} が Lv.{location.level} に昇格！熱ペナルティ軽減、新専売品追加"

    def _get_new_specialty_item(self, location_id: str) -> str:
        new_items = {
            "underground_bazaar": "ill_skill_02",
            "neon_data_haven": "chip_02",
            "midas_black_vault": "crystal_02",
            "mobile_caravan": "crystal_03",
        }
        return new_items.get(location_id, "")

    def format_location_for_ui(self, location_id: str) -> dict:
        status = self.get_location_status(location_id)
        if "error" in status:
            return status

        location = self.locations[location_id]
        district_names = {
            "slum": "スラム街",
            "cyber": "サイバー地区",
            "midas_back": "ミダスタワー裏",
            "mobile": "移動型",
        }

        price_trend = "安定"
        if location.base_demand_factor > 0.1:
            price_trend = "高騰傾向"
        elif location.base_supply_factor > 0.1:
            price_trend = "下落傾向"

        return {
            "name": location.name,
            "district_name": district_names.get(location.district.value, location.district.value),
            "icon": self._get_location_icon(location_id),
            "price_trend": price_trend,
            "heat_level": self.economy.heat_level,
            "location_heat_penalty": f"{location.heat_penalty * 100:.1f}%",
            "stock_count": len(status["available_items"]),
            "unlock_progress": self._get_unlock_progress(location_id),
            "level": location.level,
            "max_level": location.max_level,
        }

    def _get_location_icon(self, location_id: str) -> str:
        icons = {
            "underground_bazaar": "🏪",
            "neon_data_haven": "💾",
            "midas_black_vault": "🏦",
            "mobile_caravan": "🚚",
        }
        return icons.get(location_id, "❓")

    def _get_unlock_progress(self, location_id: str) -> str:
        location = self.locations.get(location_id)
        if not location or location.is_unlocked:
            return "解放済み"

        condition = location.unlock_condition
        if condition == "resistance_rep_30":
            rep = self.economy.factions.get("resistance", FactionState("resistance", "", 0)).reputation
            return f"レジスタンス評判: {rep}/30"
        elif condition == "midas_hostile_and_aldo_50000":
            midas = self.economy.factions.get("midas", FactionState("midas", "", 0, True))
            aldo = self.economy.aldo_currency
            hostile_str = "敵対中" if midas.is_hostile else "非敵対"
            return f"ミダス: {hostile_str}, アルド: {aldo}/50000"
        elif condition == "quest_caravan_contact":
            return "クエスト未完了"
        return "条件不明"

    def to_dict(self) -> dict:
        return {
            "locations": {
                loc_id: {
                    "id": loc.id,
                    "name": loc.name,
                    "district": loc.district.value,
                    "base_demand_factor": loc.base_demand_factor,
                    "base_supply_factor": loc.base_supply_factor,
                    "heat_penalty": loc.heat_penalty,
                    "faction_rep_bonus": loc.faction_rep_bonus,
                    "specialty_items": loc.specialty_items,
                    "is_mobile": loc.is_mobile,
                    "current_position": loc.current_position,
                    "unlock_condition": loc.unlock_condition,
                    "is_unlocked": loc.is_unlocked,
                    "level": loc.level,
                    "max_level": loc.max_level,
                    "total_trade_volume": loc.total_trade_volume,
                    "upgrade_threshold": loc.upgrade_threshold,
                }
                for loc_id, loc in self.locations.items()
            },
            "routes": {
                route_id: {
                    "id": route.id,
                    "origin_id": route.origin_id,
                    "destination_id": route.destination_id,
                    "risk_level": route.risk_level,
                    "base_profit_per_turn": route.base_profit_per_turn,
                    "heat_generation_per_turn": route.heat_generation_per_turn,
                    "contraband_types": route.contraband_types,
                    "is_active": route.is_active,
                    "turns_remaining": route.turns_remaining,
                    "established_turn": route.established_turn,
                    "total_profit": route.total_profit,
                    "detection_accumulator": route.detection_accumulator,
                    "investment": route.investment,
                }
                for route_id, route in self.routes.items()
            },
            "contraband_items": {
                item_id: {
                    "id": item.id,
                    "name": item.name,
                    "type": item.type.value,
                    "base_price": item.base_price,
                    "rarity": item.rarity.value,
                    "source_locations": item.source_locations,
                    "route_restrictions": item.route_restrictions,
                    "heat_risk": item.heat_risk,
                    "description": item.description,
                    "stock": item.stock,
                }
                for item_id, item in self.contraband_items.items()
            },
            "price_history": [
                {
                    "location_id": snap.location_id,
                    "item_id": snap.item_id,
                    "turn": snap.turn,
                    "final_price": snap.final_price,
                    "demand_factor": snap.demand_factor,
                    "supply_factor": snap.supply_factor,
                    "heat_penalty": snap.heat_penalty,
                    "faction_bonus": snap.faction_bonus,
                }
                for snap in self.price_history[-100:]
            ],
            "trade_log": self.trade_log[-200:],
            "current_turn": self.current_turn,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BlackMarketNetwork:
        instance = cls.__new__(cls)
        instance._initialized = True

        instance.economy = SkillEaterEconomySystem.get_instance()
        instance.audio = SkillEaterAudioSystem.get_instance()
        instance.presentation = SkillEaterPresentationSystem.get_instance()

        instance.locations = {}
        for loc_id, loc_data in data.get("locations", {}).items():
            instance.locations[loc_id] = BlackMarketLocation(
                id=loc_data["id"],
                name=loc_data["name"],
                district=DistrictType(loc_data["district"]),
                base_demand_factor=loc_data["base_demand_factor"],
                base_supply_factor=loc_data["base_supply_factor"],
                heat_penalty=loc_data["heat_penalty"],
                faction_rep_bonus=loc_data["faction_rep_bonus"],
                specialty_items=loc_data["specialty_items"],
                is_mobile=loc_data["is_mobile"],
                current_position=tuple(loc_data["current_position"]) if loc_data["current_position"] else None,
                unlock_condition=loc_data["unlock_condition"],
                is_unlocked=loc_data["is_unlocked"],
                level=loc_data["level"],
                max_level=loc_data["max_level"],
                total_trade_volume=loc_data["total_trade_volume"],
                upgrade_threshold=loc_data["upgrade_threshold"],
            )

        instance.routes = {}
        for route_id, route_data in data.get("routes", {}).items():
            instance.routes[route_id] = SmuggleRoute(
                id=route_data["id"],
                origin_id=route_data["origin_id"],
                destination_id=route_data["destination_id"],
                risk_level=route_data["risk_level"],
                base_profit_per_turn=route_data["base_profit_per_turn"],
                heat_generation_per_turn=route_data["heat_generation_per_turn"],
                contraband_types=route_data["contraband_types"],
                is_active=route_data["is_active"],
                turns_remaining=route_data["turns_remaining"],
                established_turn=route_data["established_turn"],
                total_profit=route_data["total_profit"],
                detection_accumulator=route_data["detection_accumulator"],
                investment=route_data["investment"],
            )

        instance.contraband_items = {}
        for item_id, item_data in data.get("contraband_items", {}).items():
            instance.contraband_items[item_id] = ContrabandItem(
                id=item_data["id"],
                name=item_data["name"],
                type=ContrabandType(item_data["type"]),
                base_price=item_data["base_price"],
                rarity=Rarity(item_data["rarity"]),
                source_locations=item_data["source_locations"],
                route_restrictions=item_data["route_restrictions"],
                heat_risk=item_data["heat_risk"],
                description=item_data["description"],
                stock=item_data["stock"],
            )

        instance.price_history = [
            MarketPriceSnapshot(**snap) for snap in data.get("price_history", [])
        ]
        instance.trade_log = data.get("trade_log", [])
        instance.current_turn = data.get("current_turn", 0)

        return instance

    def establish_smuggle_route(
        self,
        origin_id: str,
        destination_id: str,
        risk_level: int,
        initial_investment: int,
    ) -> tuple[bool, str]:
        origin = self.locations.get(origin_id)
        destination = self.locations.get(destination_id)
        if not origin or not destination:
            return False, "無効な拠点です"

        if not origin.is_unlocked or not destination.is_unlocked:
            return False, "解放されていない拠点が含まれています"

        if self.economy.aldo_currency < initial_investment:
            return False, f"投資資金が不足しています（必要: {initial_investment} アルド）"

        route_id = f"{origin_id}_to_{destination_id}"
        if route_id in self.routes and self.routes[route_id].is_active:
            return False, "同一ルートは既に確立済みです"

        success_rate = min(0.9, 0.3 + (initial_investment / 50000) * 0.6)
        if random.random() > success_rate:
            self.economy.aldo_currency -= initial_investment // 2
            return False, f"ルート確立に失敗（投資の半分を失った: {initial_investment // 2} アルド）"

        self.economy.aldo_currency -= initial_investment

        base_profit = 500
        heat_gen = 5
        contraband_types = ["illegal_skill", "forbidden_data_chip"]

        if origin_id == "underground_bazaar" and destination_id == "neon_data_haven":
            base_profit, heat_gen = 500, 5
            contraband_types = ["illegal_skill", "forbidden_data_chip"]
        elif origin_id == "neon_data_haven" and destination_id == "midas_black_vault":
            base_profit, heat_gen = 1200, 10
            contraband_types = ["forbidden_data_chip", "concept_crystal"]
        elif origin_id == "midas_black_vault" and destination_id == "underground_bazaar":
            base_profit, heat_gen = 2000, 15
            contraband_types = ["concept_crystal", "illegal_skill"]
        elif origin_id == "mobile_caravan" and destination_id == "mobile_caravan":
            base_profit, heat_gen = 800, 8
            contraband_types = ["illegal_skill", "concept_crystal", "forbidden_data_chip"]
        elif origin_id == "underground_bazaar" and destination_id == "midas_black_vault":
            base_profit, heat_gen = 3000, 20
            contraband_types = ["concept_crystal"]

        self.routes[route_id] = SmuggleRoute(
            id=route_id,
            origin_id=origin_id,
            destination_id=destination_id,
            risk_level=min(10, max(1, risk_level)),
            base_profit_per_turn=base_profit,
            heat_generation_per_turn=heat_gen,
            contraband_types=contraband_types,
            established_turn=self.current_turn,
            investment=initial_investment,
        )

        self.presentation.add_event(
            emote_file="emote_exclamations.png",
            audio_file="encrypted_comms.ogg",
            message=f"密輸ルート確立: {origin.name} → {destination.name} (リスク: {risk_level})",
        )

        return True, f"密輸ルート『{route_id}』を確立！ 投資: {initial_investment} アルド"

    def calculate_detection_risk(self, route: SmuggleRoute) -> float:
        base_detection = route.risk_level * 0.02
        time_bonus = route.detection_accumulator
        broker_rep = self.economy.factions.get("broker", FactionState("broker", "", 0)).reputation
        rep_reduction = min(0.3, max(0, broker_rep) * 0.015)

        detection_chance = base_detection + time_bonus - rep_reduction
        return max(0.01, min(0.5, detection_chance))

    def process_smuggle_routes_turn_end(self) -> list[dict]:
        results = []
        routes_to_remove = []

        for route_id, route in self.routes.items():
            if not route.is_active:
                continue

            if route_id == "emergency_evac":
                if route.turns_remaining > 0:
                    self.economy.heat_level = max(0, self.economy.heat_level + route.heat_generation_per_turn)
                    route.turns_remaining -= 1
                    results.append({
                        "route_id": route_id,
                        "type": "emergency_evac",
                        "heat_change": route.heat_generation_per_turn,
                        "message": f"緊急避難ルート進行中... 残り {route.turns_remaining} ターン (熱: {route.heat_generation_per_turn:+d})",
                    })
                    if route.turns_remaining == 0:
                        route.is_active = False
                        results.append({
                            "route_id": route_id,
                            "type": "evac_complete",
                            "message": "緊急避難完了！警戒度が大幅に低下した",
                        })
                continue

            detection_chance = self.calculate_detection_risk(route)
            route.detection_accumulator += 0.01

            if random.random() < detection_chance:
                route.is_active = False
                heat_increase = 30 + route.risk_level * 5
                self.economy.heat_level = min(100, self.economy.heat_level + heat_increase)
                loss = route.investment
                self.economy.aldo_currency = max(0, self.economy.aldo_currency - loss)

                self.presentation.add_event(
                    emote_file="emote_alert.png",
                    audio_file="metalLatch.ogg",
                    message=f"【発覚！】密輸ルート『{route_id}』がミダスに察知された！",
                )
                self.presentation.add_event(
                    emote_file="emote_alert.png",
                    audio_file="metalLatch.ogg",
                    message=f"投資損失: {loss} アルド、警戒度 +{heat_increase}",
                )
                self.presentation.add_event(
                    emote_file="emote_alert.png",
                    audio_file="metalLatch.ogg",
                    message="ルートが閉鎖されました",
                )

                results.append({
                    "route_id": route_id,
                    "type": "detected",
                    "heat_increase": heat_increase,
                    "investment_loss": loss,
                    "message": f"【発覚】ルート『{route_id}』が察知され閉鎖！ 損失: {loss} アルド, 熱 +{heat_increase}",
                })
                routes_to_remove.append(route_id)
                continue

            profit = route.base_profit_per_turn
            heat_increase = route.heat_generation_per_turn

            for item_id in route.contraband_types:
                pass

            self.economy.aldo_currency += profit
            self.economy.heat_level = min(100, self.economy.heat_level + heat_increase)
            route.total_profit += profit

            origin = self.locations.get(route.origin_id)
            dest = self.locations.get(route.destination_id)
            if origin:
                origin.total_trade_volume += profit
            if dest:
                dest.total_trade_volume += profit

            self.presentation.add_event(
                emote_file="emote_stars.png",
                audio_file="credits_transfer.ogg",
                message=f"密輸ルート『{route_id}』から {profit} アルドの利益！",
            )

            results.append({
                "route_id": route_id,
                "type": "profit",
                "profit": profit,
                "heat_increase": heat_increase,
                "total_profit": route.total_profit,
                "message": f"ルート『{route_id}』: +{profit} アルド (累計: {route.total_profit}), 熱 +{heat_increase}",
            })

            if route.turns_remaining > 0:
                route.turns_remaining -= 1
                if route.turns_remaining == 0:
                    route.is_active = False
                    results.append({
                        "route_id": route_id,
                        "type": "expired",
                        "message": f"ルート『{route_id}』の期限が切れました",
                    })

        for route_id in routes_to_remove:
            if route_id in self.routes:
                del self.routes[route_id]

        return results

    def abandon_smuggle_route(self, route_id: str) -> tuple[int, str]:
        route = self.routes.get(route_id)
        if not route or not route.is_active:
            return 0, "該当するアクティブなルートがありません"

        turns_elapsed = self.current_turn - route.established_turn
        expected_turns = 20
        recovery_rate = min(1.0, turns_elapsed / expected_turns)
        recovered = int(route.investment * recovery_rate * 0.7)

        self.economy.aldo_currency += recovered
        route.is_active = False

        self.economy.heat_level = min(100, self.economy.heat_level + 5)

        self.presentation.add_event(
            emote_file="emote_cross.png",
            audio_file="doorClose_1.ogg",
            message=f"密輸ルート『{route_id}』を撤退 (回収: {recovered} アルド)",
        )

        return recovered, f"ルート『{route_id}』を撤退。投資の {recovery_rate * 70:.0f}% を回収 ({recovered} アルド)"

    def upgrade_smuggle_route(self, route_id: str, additional_investment: int) -> tuple[bool, str]:
        route = self.routes.get(route_id)
        if not route or not route.is_active:
            return False, "該当するアクティブなルートがありません"

        if self.economy.aldo_currency < additional_investment:
            return False, f"追加投資資金が不足しています（必要: {additional_investment} アルド）"

        self.economy.aldo_currency -= additional_investment
        route.investment += additional_investment

        risk_reduction = min(3, additional_investment // 5000)
        route.risk_level = max(1, route.risk_level - risk_reduction)
        profit_increase = additional_investment // 10
        route.base_profit_per_turn += profit_increase

        return True, f"ルート『{route_id}』を強化！ リスク -{risk_reduction}, ターン利益 +{profit_increase}"

    def get_active_routes(self) -> list[dict]:
        active = []
        for route in self.routes.values():
            if route.is_active:
                origin = self.locations.get(route.origin_id)
                dest = self.locations.get(route.destination_id)
                detection = self.calculate_detection_risk(route)
                active.append({
                    "id": route.id,
                    "origin": origin.name if origin else route.origin_id,
                    "destination": dest.name if dest else route.destination_id,
                    "risk_level": route.risk_level,
                    "profit_per_turn": route.base_profit_per_turn,
                    "heat_per_turn": route.heat_generation_per_turn,
                    "detection_chance": f"{detection * 100:.1f}%",
                    "total_profit": route.total_profit,
                    "turns_active": self.current_turn - route.established_turn,
                    "turns_remaining": route.turns_remaining if route.turns_remaining > 0 else "無期限",
                    "investment": route.investment,
                    "contraband_types": route.contraband_types,
                })
        return active

    def get_available_routes(self, origin_id: str) -> list[dict]:
        available = []
        origin = self.locations.get(origin_id)
        if not origin or not origin.is_unlocked:
            return available

        for dest_id, dest in self.locations.items():
            if dest_id == origin_id or not dest.is_unlocked:
                continue

            route_id = f"{origin_id}_to_{dest_id}"
            if route_id in self.routes and self.routes[route_id].is_active:
                continue

            risk = 3
            if origin_id == "underground_bazaar" and dest_id == "neon_data_haven":
                risk = 3
            elif origin_id == "neon_data_haven" and dest_id == "midas_black_vault":
                risk = 5
            elif origin_id == "midas_black_vault" and dest_id == "underground_bazaar":
                risk = 7
            elif origin_id == "mobile_caravan":
                risk = 4
            elif origin_id == "underground_bazaar" and dest_id == "midas_black_vault":
                risk = 8

            available.append({
                "route_id": route_id,
                "origin": origin.name,
                "destination": dest.name,
                "risk_level": risk,
                "min_investment": risk * 1000,
                "expected_profit": risk * 200,
            })
        return available

    def check_contraband_route_restriction(self, item_id: str, route_id: str) -> bool:
        item = self.contraband_items.get(item_id)
        route = self.routes.get(route_id)
        if not item or not route:
            return False
        return route_id in item.route_restrictions or route_id == "caravan_cycle" or route_id == "emergency_evac"

    def activate_emergency_evacuation(self) -> tuple[bool, str]:
        if self.economy.heat_level < 80:
            return False, "警戒度が80未満のため緊急避難ルートを起動できません"

        if "emergency_evac" in self.routes and self.routes["emergency_evac"].is_active:
            return False, "既に緊急避難ルートが作動中です"

        self.routes["emergency_evac"] = SmuggleRoute(
            id="emergency_evac",
            origin_id="any",
            destination_id="safehouse",
            risk_level=10,
            base_profit_per_turn=0,
            heat_generation_per_turn=-30,
            contraband_types=["illegal_skill", "concept_crystal", "forbidden_data_chip"],
            turns_remaining=3,
            established_turn=self.current_turn,
            investment=0,
        )

        self.presentation.add_event(
            emote_file="emote_alert.png",
            audio_file="metalLatch.ogg",
            message="【緊急避難発動！】密輸ルートを全て切り、安全地帯へ移動します",
        )

        for route in self.routes.values():
            if route.id != "emergency_evac" and route.is_active:
                route.is_active = False

        return True, "緊急避難ルートを発動！ 3ターンで警戒度を大幅低下（他ルートは強制終了）"

    def generate_smuggle_report(self) -> str:
        active_routes = self.get_active_routes()
        if not active_routes:
            return "アクティブな密輸ルートはありません"

        total_profit_per_turn = sum(r["profit_per_turn"] for r in active_routes)
        total_heat_per_turn = sum(r["heat_per_turn"] for r in active_routes)
        total_investment = sum(r["investment"] for r in active_routes)
        total_accumulated = sum(r["total_profit"] for r in active_routes)

        lines = [
            "=== 密輸ルート収支レポート ===",
            f"アクティブルート数: {len(active_routes)}",
            f"ターン収益合計: {total_profit_per_turn} アルド/ターン",
            f"ターン熱上昇合計: {total_heat_per_turn} /ターン",
            f"累積投資額: {total_investment} アルド",
            f"累積利益: {total_accumulated} アルド",
            f"現在の警戒度: {self.economy.heat_level}/100",
            "",
            "--- ルート詳細 ---",
        ]

        for r in active_routes:
            lines.append(
                f"  {r['origin']} → {r['destination']}: "
                f"リスク{r['risk_level']}, 利益{r['profit_per_turn']}/T, "
                f"熱{r['heat_per_turn']}/T, 発覚率{r['detection_chance']}, "
                f"累積{r['total_profit']}, 経過{r['turns_active']}T"
            )

        if self.economy.heat_level >= 70:
            lines.append("")
            lines.append("⚠ 警告: 警戒度が危険水域です。緊急避難ルートの検討を推奨。")

        net_per_turn = total_profit_per_turn - (total_heat_per_turn * 10)
        if net_per_turn > 0:
            lines.append(f"\n推奨: 現在のルート継続でターンあたり実質 +{net_per_turn} アルド相当の利益")
        else:
            lines.append(f"\n推奨: 熱コスト考慮でターンあたり実質 {net_per_turn} アルドの損失。ルート見直しを推奨。")

        return "\n".join(lines)

    def buy_from_black_market(
        self,
        player: CharacterState,
        location_id: str,
        item_id: str,
        quantity: int = 1,
    ) -> tuple[bool, int, str, dict]:
        location = self.locations.get(location_id)
        item = self.contraband_items.get(item_id)
        if not location or not item:
            return False, 0, "無効な拠点またはアイテムです", {}

        if not location.is_unlocked:
            return False, 0, f"{location.name} はまだ解放されていません", {}

        if item_id not in location.specialty_items:
            return False, 0, f"{location.name} では {item.name} を取り扱っていません", {}

        player_faction_reps = {fid: fs.reputation for fid, fs in self.economy.factions.items()}
        unit_price, breakdown = self.calculate_dynamic_price(location, item, player_faction_reps)

        discount = 0.0
        if quantity >= 10:
            discount = 0.10
        elif quantity >= 5:
            discount = 0.05

        total_price = int(unit_price * quantity * (1 - discount))

        if self.economy.aldo_currency < total_price:
            return False, 0, f"アルドが不足しています（必要: {total_price} アルド, 所持: {self.economy.aldo_currency} アルド）", breakdown

        self.economy.aldo_currency -= total_price

        self.update_demand_supply(location_id, is_buy=True, quantity=quantity)

        self._record_price_snapshot(location_id, item_id, unit_price, breakdown)
        self._record_trade_log("buy", location_id, item_id, quantity, unit_price, total_price)

        location.total_trade_volume += total_price

        self._apply_faction_reputation_change(item.type.value, is_buy=True)

        self.economy.heat_level = min(100, self.economy.heat_level + item.heat_risk * quantity)

        self._play_buy_effect(item)

        msg = f"{item.name} を {quantity} 個購入！ 計 {total_price} アルド (単価: {unit_price} アルド)"
        if discount > 0:
            msg += f" [まとめ買い割引 {int(discount * 100)}%]"
        msg += f" (警戒度: {self.economy.heat_level})"

        return True, total_price, msg, breakdown

    def _play_buy_effect(self, item: ContrabandItem) -> None:
        if item.type == ContrabandType.ILLEGAL_SKILL:
            self.presentation.add_event(
                emote_file="emote_cash.png",
                audio_file="credits_transfer.ogg",
                message=f"違法スキル《{item.name}》を入手！",
            )
        elif item.type == ContrabandType.CONCEPT_CRYSTAL:
            self.presentation.add_event(
                emote_file="emote_heart.png",
                audio_file="encrypted_comms.ogg",
                message=f"概念結晶《{item.name}》が輝く…",
            )
        elif item.type == ContrabandType.FORBIDDEN_DATA_CHIP:
            self.presentation.add_event(
                emote_file="emote_graph_up.png",
                audio_file="hologram_ui_open.ogg",
                message=f"禁忌データ《{item.name}》を解読",
            )

    def sell_to_black_market(
        self,
        player: CharacterState,
        location_id: str,
        item_id: str,
        quantity: int = 1,
    ) -> tuple[bool, int, str]:
        location = self.locations.get(location_id)
        item = self.contraband_items.get(item_id)
        if not location or not item:
            return False, 0, "無効な拠点またはアイテムです"

        if not location.is_unlocked:
            return False, 0, f"{location.name} はまだ解放されていません"

        inventory = getattr(player, "contraband_inventory", {})
        if inventory.get(item_id, 0) < quantity:
            return False, 0, "所持数が足りません"

        player_faction_reps = {fid: fs.reputation for fid, fs in self.economy.factions.items()}
        unit_price, breakdown = self.calculate_dynamic_price(location, item, player_faction_reps)

        buyback_rate = 0.6
        if item.type == ContrabandType.ILLEGAL_SKILL:
            buyback_rate = 0.5
        elif item.type == ContrabandType.CONCEPT_CRYSTAL:
            buyback_rate = 0.7

        total_price = int(unit_price * buyback_rate * quantity)

        self.economy.aldo_currency += total_price

        self.update_demand_supply(location_id, is_buy=False, quantity=quantity)

        self._record_price_snapshot(location_id, item_id, int(unit_price * buyback_rate), breakdown)
        self._record_trade_log("sell", location_id, item_id, quantity, int(unit_price * buyback_rate), total_price)

        location.total_trade_volume += total_price

        self._apply_faction_reputation_change(item.type.value, is_buy=False)

        if item.type == ContrabandType.ILLEGAL_SKILL:
            self.economy.heat_level = min(100, self.economy.heat_level + 10 * quantity)
            self.presentation.add_event(
                emote_file="emote_cash.png",
                audio_file="doorClose_1.ogg",
                message=f"違法スキル《{item.name}》を密売完了（警戒度: {self.economy.heat_level}）",
            )
        else:
            self.presentation.add_event(
                emote_file="emote_cash.png",
                audio_file="handleCoins.ogg",
                message=f"{item.name} を売却: {total_price} アルド獲得",
            )

        msg = f"{item.name} を {quantity} 個売却！ 計 {total_price} アルド獲得 (買取率: {int(buyback_rate * 100)}%)"
        if item.type == ContrabandType.ILLEGAL_SKILL:
            msg += f" (警戒度: {self.economy.heat_level})"

        return True, total_price, msg

    def _record_price_snapshot(
        self,
        location_id: str,
        item_id: str,
        final_price: int,
        breakdown: dict,
    ) -> None:
        snapshot = MarketPriceSnapshot(
            location_id=location_id,
            item_id=item_id,
            turn=self.current_turn,
            final_price=final_price,
            demand_factor=breakdown.get("demand_factor", 0),
            supply_factor=breakdown.get("supply_factor", 0),
            heat_penalty=breakdown.get("heat_penalty", 0),
            faction_bonus=breakdown.get("faction_bonus", 0),
        )
        self.price_history.append(snapshot)
        if len(self.price_history) > 500:
            self.price_history = self.price_history[-500:]

    def _record_trade_log(
        self,
        trade_type: str,
        location_id: str,
        item_id: str,
        quantity: int,
        unit_price: int,
        total_price: int,
    ) -> None:
        log_entry = {
            "turn": self.current_turn,
            "type": trade_type,
            "location_id": location_id,
            "item_id": item_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
        }
        self.trade_log.append(log_entry)
        if len(self.trade_log) > 1000:
            self.trade_log = self.trade_log[-1000:]

    def _apply_faction_reputation_change(self, item_type: str, is_buy: bool) -> None:
        if is_buy:
            self.economy.factions["broker"].reputation = min(100, self.economy.factions["broker"].reputation + 1)
            if item_type == "forbidden_data_chip":
                self.economy.factions["resistance"].reputation = min(100, self.economy.factions["resistance"].reputation + 2)
            elif item_type == "concept_crystal":
                self.economy.factions["midas"].reputation = max(-100, self.economy.factions["midas"].reputation - 5)
        else:
            self.economy.factions["broker"].reputation = min(100, self.economy.factions["broker"].reputation + 2)

    def get_price_history(self, location_id: str, item_id: str, turns: int = 20) -> list[dict]:
        history = [
            {
                "turn": snap.turn,
                "price": snap.final_price,
                "demand": snap.demand_factor,
                "supply": snap.supply_factor,
                "heat": snap.heat_penalty,
                "faction": snap.faction_bonus,
            }
            for snap in self.price_history
            if snap.location_id == location_id and snap.item_id == item_id
        ]
        return history[-turns:]

    def get_trade_history(self, turns: int = 50) -> list[dict]:
        return self.trade_log[-turns:]

    def process_illegal_possession_heat(self, player: CharacterState) -> int:
        heat_increase = 0
        for skill_id in player.get_skill_ids():
            skill_def = self.economy.registry.get_skill(skill_id)
            if skill_def and skill_def.is_illegal:
                heat_increase += 2

        for item_id in getattr(player, "contraband_inventory", {}):
            item = self.contraband_items.get(item_id)
            if item:
                heat_increase += item.heat_risk

        if heat_increase > 0:
            self.economy.heat_level = min(100, self.economy.heat_level + heat_increase)
            if self.economy.heat_level >= 70:
                self.presentation.add_event(
                    emote_file="emote_alert.png",
                    audio_file="metalClick.ogg",
                    message=f"警戒度危険水域: {self.economy.heat_level}/100",
                )

        return heat_increase

    def cancel_trade(self, trade_log_index: int) -> tuple[bool, str]:
        if trade_log_index < 0 or trade_log_index >= len(self.trade_log):
            return False, "無効な取引履歴インデックスです"

        trade = self.trade_log[trade_log_index]
        if self.current_turn - trade["turn"] > 1:
            return False, "1ターン以上経過した取引はキャンセルできません"

        item = self.contraband_items.get(trade["item_id"])
        if item and item.type == ContrabandType.ILLEGAL_SKILL:
            return False, "違法スキルの取引はキャンセルできません"

        refund = int(trade["total_price"] * 0.8)
        self.economy.aldo_currency += refund

        location = self.locations.get(trade["location_id"])
        if location:
            reverse_buy = trade["type"] == "sell"
            self.update_demand_supply(trade["location_id"], is_buy=reverse_buy, quantity=trade["quantity"])

        self.trade_log.pop(trade_log_index)

        return True, f"取引をキャンセルし、{refund} アルドを返金しました (手数料20%)"

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

    def _get_audio_path(self, audio_file: str) -> Path:
        return self.audio.audio_dir / audio_file

    def _get_emote_path(self, emote_file: str) -> Path:
        return self.presentation.emote_dir / emote_file

    def verify_audio_assets(self) -> dict[str, bool]:
        required_audio = [
            "hologram_ui_open.ogg",
            "credits_transfer.ogg",
            "encrypted_comms.ogg",
            "handleCoins.ogg",
            "doorClose_1.ogg",
            "metalLatch.ogg",
            "metalClick.ogg",
            "doorOpen_2.ogg",
            "chop.ogg",
            "bookOpen.ogg",
            "handleCoins2.ogg",
            "metalPot1.ogg",
        ]
        results = {}
        for audio in required_audio:
            results[audio] = self._get_audio_path(audio).exists()
        return results

    def verify_emote_assets(self) -> dict[str, bool]:
        required_emotes = [
            "emote_graph_up.png",
            "emote_lock.png",
            "emote_cash.png",
            "emote_alert.png",
            "emote_cross.png",
            "emote_exclamations.png",
            "emote_stars.png",
            "emote_heart.png",
            "emote_idea.png",
            "emote_exclamation.png",
        ]
        results = {}
        for emote in required_emotes:
            results[emote] = self._get_emote_path(emote).exists()
        return results

    def play_location_enter(self, location_id: str) -> None:
        location = self.locations.get(location_id)
        if not location:
            return

        emote, audio = self.BLACK_MARKET_EVENTS["ui_open"]
        self.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message=f"《{location.name}》に接続中…",
            duration_ms=1500,
        )

        if location.is_mobile:
            pos = location.current_position
            self.presentation.add_event(
                emote_file="emote_idea.png",
                audio_file="bookOpen.ogg",
                message=f"移動型闇市場『MobileCaravan』を発見！ 現在地: {location.district.value}地区 座標: {pos}",
            )

    def play_location_exit(self, location_id: str) -> None:
        location = self.locations.get(location_id)
        if not location:
            return

        self.presentation.add_event(
            emote_file="emote_cross.png",
            audio_file="doorClose_1.ogg",
            message=f"{location.name} から切断",
            duration_ms=800,
        )

    def play_buy_effect(self, item: ContrabandItem, quantity: int = 1, discount: float = 0) -> None:
        if item.type == ContrabandType.ILLEGAL_SKILL:
            emote, audio = "emote_cash.png", "credits_transfer.ogg"
            msg = f"違法スキル《{item.name}》を {quantity} 個入手！"
        elif item.type == ContrabandType.CONCEPT_CRYSTAL:
            emote, audio = "emote_heart.png", "encrypted_comms.ogg"
            msg = f"概念結晶《{item.name}》が輝く… ({quantity} 個)"
        elif item.type == ContrabandType.FORBIDDEN_DATA_CHIP:
            emote, audio = "emote_graph_up.png", "hologram_ui_open.ogg"
            msg = f"禁忌データ《{item.name}》を解読 ({quantity} 個)"
        else:
            emote, audio = "emote_cash.png", "credits_transfer.ogg"
            msg = f"{item.name} を {quantity} 個購入"

        if discount > 0:
            msg += f" [割引 {int(discount * 100)}%]"

        self.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message=msg,
            duration_ms=2000,
        )

    def play_sell_effect(self, item: ContrabandItem, quantity: int, total_price: int, is_illegal: bool) -> None:
        if is_illegal:
            self.presentation.add_event(
                emote_file="emote_cash.png",
                audio_file="doorClose_1.ogg",
                message=f"違法スキル《{item.name}》を {quantity} 個密売完了 (獲得: {total_price} アルド, 警戒度: {self.economy.heat_level})",
                duration_ms=2000,
            )
        else:
            self.presentation.add_event(
                emote_file="emote_cash.png",
                audio_file="handleCoins.ogg",
                message=f"{item.name} を {quantity} 個売却: {total_price} アルド獲得",
                duration_ms=1500,
            )

    def play_route_establish_effect(self, origin_name: str, dest_name: str, risk_level: int) -> None:
        emote, audio = self.BLACK_MARKET_EVENTS["route_establish"]
        self.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message=f"密輸ルート確立: {origin_name} → {dest_name} (リスク: {risk_level})",
            duration_ms=2500,
        )

    def play_route_profit_effect(self, route_id: str, profit: int, total_profit: int) -> None:
        emote, audio = self.BLACK_MARKET_EVENTS["route_profit"]
        self.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message=f"密輸ルート『{route_id}』から {profit} アルドの利益！ (累計: {total_profit} アルド)",
            duration_ms=2000,
        )

    def play_route_detected_effect(self, route_id: str, heat_increase: int, loss: int) -> None:
        emote, audio = self.BLACK_MARKET_EVENTS["route_detected"]
        for i in range(3):
            self.presentation.add_event(
                emote_file=emote,
                audio_file=audio,
                message="【発覚！】" if i == 0 else "",
                duration_ms=1000,
            )
        self.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message=f"密輸ルート『{route_id}』がミダスに察知された！ 投資損失: {loss} アルド、警戒度 +{heat_increase}",
            duration_ms=3000,
        )

    def play_route_abandon_effect(self, route_id: str, recovered: int) -> None:
        emote, audio = self.BLACK_MARKET_EVENTS["route_abandon"]
        self.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message=f"密輸ルート『{route_id}』を撤退 (回収: {recovered} アルド)",
            duration_ms=1500,
        )

    def play_price_surge_effect(self, item_name: str, change_percent: float, current_price: int) -> None:
        if abs(change_percent) >= 20:
            emote, audio = self.BLACK_MARKET_EVENTS["price_surge"]
            direction = "急騰" if change_percent > 0 else "暴落"
            self.presentation.add_event(
                emote_file=emote,
                audio_file=audio,
                message=f"需給変動: 《{item_name}》が {abs(change_percent):.0f}% {direction} (現在: {current_price} アルド)",
                duration_ms=2500,
            )

    def play_heat_warning_effect(self) -> None:
        if self.economy.heat_level >= 70:
            emote, audio = self.BLACK_MARKET_EVENTS["heat_warning"]
            self.presentation.add_event(
                emote_file=emote,
                audio_file=audio,
                message=f"⚠ 警戒度危険水域: {self.economy.heat_level}/100",
                duration_ms=2000,
            )

    def play_caravan_encounter_effect(self, district: str, position: tuple[int, int]) -> None:
        emote, audio = self.BLACK_MARKET_EVENTS["caravan_encounter"]
        self.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message=f"移動闇市場『MobileCaravan』を発見！ 現在地: {district}地区 座標: {position}",
            duration_ms=2500,
        )

    def play_location_unlock_effect(self, location_name: str) -> None:
        emote, audio = self.BLACK_MARKET_EVENTS["location_unlock"]
        self.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message=f"新たな闇市場拠点『{location_name}』が解放された！",
            duration_ms=3000,
        )

    def play_location_upgrade_effect(self, location_name: str, new_level: int) -> None:
        emote, audio = self.BLACK_MARKET_EVENTS["location_upgrade"]
        self.presentation.add_event(
            emote_file=emote,
            audio_file=audio,
            message=f"【拠点強化】{location_name} が Lv.{new_level} に昇格！",
            duration_ms=2000,
        )
        self.audio.play_sound("metalPot1.ogg")

    def check_price_surges(self) -> None:
        for snap in self.price_history[-20:]:
            if len(self.price_history) < 2:
                break
            prev_snaps = [s for s in self.price_history if s.location_id == snap.location_id and s.item_id == snap.item_id and s.turn == snap.turn - 1]
            if prev_snaps:
                prev = prev_snaps[0]
                if prev.final_price > 0:
                    change = (snap.final_price - prev.final_price) / prev.final_price * 100
                    if abs(change) >= 20:
                        item = self.contraband_items.get(snap.item_id)
                        if item:
                            self.play_price_surge_effect(item.name, change, snap.final_price)

    def open_black_market(self, location_id: str, player: CharacterState) -> dict:
        if not self.check_location_unlock(location_id, player):
            location = self.locations.get(location_id)
            return {"success": False, "message": f"{location.name if location else '不明な拠点'} はまだ解放されていません"}

        location = self.locations[location_id]
        self.play_location_enter(location_id)

        status = self.get_location_status(location_id)
        return {"success": True, "location": status}

    def close_black_market(self, location_id: str) -> None:
        self.play_location_exit(location_id)

    def buy_contraband(
        self,
        player: CharacterState,
        location_id: str,
        item_id: str,
        quantity: int = 1,
    ) -> tuple[bool, str]:
        success, cost, msg, breakdown = self.buy_from_black_market(player, location_id, item_id, quantity)
        if success:
            if not hasattr(player, "contraband_inventory"):
                player.contraband_inventory = {}
            player.contraband_inventory[item_id] = player.contraband_inventory.get(item_id, 0) + quantity
            self.play_buy_effect(self.contraband_items[item_id], quantity, 0)
        return success, msg

    def sell_contraband(
        self,
        player: CharacterState,
        location_id: str,
        item_id: str,
        quantity: int = 1,
    ) -> tuple[bool, str]:
        inventory = getattr(player, "contraband_inventory", {})
        if inventory.get(item_id, 0) < quantity:
            return False, "所持数が足りません"

        success, gain, msg = self.sell_to_black_market(player, location_id, item_id, quantity)
        if success:
            player.contraband_inventory[item_id] -= quantity
            if player.contraband_inventory[item_id] <= 0:
                del player.contraband_inventory[item_id]
            self.play_sell_effect(
                self.contraband_items[item_id],
                quantity,
                gain,
                self.contraband_items[item_id].type == ContrabandType.ILLEGAL_SKILL,
            )
        return success, msg

    def establish_route(
        self,
        origin: str,
        dest: str,
        risk: int,
        investment: int,
    ) -> tuple[bool, str]:
        return self.establish_smuggle_route(origin, dest, risk, investment)

    def get_market_prices(self, location_id: str) -> dict:
        location = self.locations.get(location_id)
        if not location or not location.is_unlocked:
            return {"error": "拠点が存在しないか未解放です"}

        player_faction_reps = {fid: fs.reputation for fid, fs in self.economy.factions.items()}
        prices = {}
        for item_id in location.specialty_items:
            item = self.contraband_items.get(item_id)
            if item:
                price, breakdown = self.calculate_dynamic_price(location, item, player_faction_reps)
                prices[item_id] = {
                    "name": item.name,
                    "type": item.type.value,
                    "rarity": item.rarity.value,
                    "price": price,
                    "breakdown": breakdown,
                }
        return {"location_id": location_id, "prices": prices}

    def process_turn_end(self, player: CharacterState) -> list[dict]:
        self.current_turn += 1

        self.update_mobile_caravan_position()
        self.natural_recovery_demand_supply()

        route_results = self.process_smuggle_routes_turn_end()

        for route_result in route_results:
            if route_result["type"] == "profit":
                route = self.routes.get(route_result["route_id"])
                if route:
                    self.play_route_profit_effect(route_result["route_id"], route_result["profit"], route.total_profit)
            elif route_result["type"] == "detected":
                self.play_route_detected_effect(
                    route_result["route_id"],
                    route_result["heat_increase"],
                    route_result["investment_loss"],
                )
            elif route_result["type"] == "evac_complete":
                self.presentation.add_event(
                    emote_file="emote_stars.png",
                    audio_file="credits_transfer.ogg",
                    message="緊急避難完了！警戒度が大幅に低下した",
                )

        possession_heat = self.process_illegal_possession_heat(player)

        unlock_checks = []
        for loc_id, loc in self.locations.items():
            if not loc.is_unlocked and self.check_location_unlock(loc_id, player):
                unlock_checks.append(loc_id)
                self.play_location_unlock_effect(loc.name)

        self.check_price_surges()

        if self.economy.heat_level >= 70:
            self.play_heat_warning_effect()

        caravan = self.locations.get("mobile_caravan")
        if caravan and caravan.is_unlocked and self.current_turn % 5 == 1:
            self.play_caravan_encounter_effect(caravan.district.value, caravan.current_position)

        return {
            "turn": self.current_turn,
            "route_results": route_results,
            "possession_heat": possession_heat,
            "newly_unlocked": unlock_checks,
            "heat_level": self.economy.heat_level,
            "aldo_currency": self.economy.aldo_currency,
        }

    def add_faction_affinity(self, faction_id: str, amount: int) -> None:
        if faction_id in self.economy.factions:
            self.economy.factions[faction_id].reputation = max(-100, min(100, self.economy.factions[faction_id].reputation + amount))

    def check_inspector_raid_integration(self) -> tuple[bool, CharacterState | None, str]:
        if self.economy.heat_level >= 100:
            for route in self.routes.values():
                if route.is_active and route.id != "emergency_evac":
                    route.is_active = False

            self.economy.heat_level = 0
            self.presentation.add_event(
                emote_file="emote_alert.png",
                audio_file="metalLatch.ogg",
                message="【緊急警報！】ミダス特別監査局長がアジトを急襲！",
            )
            from skill_eater_system import CharacterState
            inspector = CharacterState(
                id="inspector_special",
                name="ミダス特別監査局長",
                hp=300,
                max_hp=300,
                mp=100,
                max_mp=100,
                atk=45,
                defense=35,
                intelligence=30,
                speed=25,
            )
            inspector.add_skill("rar_combat_012")
            inspector.add_skill("rar_utility_005")
            msg = "【緊急警報！】闇市場への違法スキル密売が発覚！ ミダス特別監査局長がアジトを急襲してきました！"
            return True, inspector, msg
        return False, None, f"警戒度: {self.economy.heat_level}/100"

    def apply_safehouse_rest(self, heat_reduction: int = 50) -> tuple[bool, str]:
        old_heat = self.economy.heat_level
        self.economy.heat_level = max(0, self.economy.heat_level - heat_reduction)

        for route in self.routes.values():
            if route.is_active and route.id != "emergency_evac":
                route.detection_accumulator = max(0, route.detection_accumulator - 0.05)

        self.presentation.add_event(
            emote_file="emote_sleep.png",
            audio_file="bookClose.ogg",
            message=f"セーフハウスで休息: 警戒度 {old_heat} → {self.economy.heat_level}",
        )

        return True, f"警戒度が {old_heat} から {self.economy.heat_level} に低下しました"

    def can_archive_skill(self, skill_id: str) -> tuple[bool, str]:
        skill_def = self.economy.registry.get_skill(skill_id)
        if not skill_def:
            return False, "スキルが見つかりません"

        if skill_def.is_illegal:
            return True, "違法スキルはアーカイブ可能ですが、所持中はターンごとに警戒度が上昇します"

        return True, "アーカイブ可能です"

    def get_contraband_drop_table(self, enemy_tier: str) -> list[dict]:
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

    def process_contraband_drop(self, enemy_tier: str) -> list[str]:
        drops = self.get_contraband_drop_table(enemy_tier)
        obtained = []
        for drop in drops:
            if random.random() < drop["chance"]:
                qty = random.randint(drop["min_quantity"], drop["max_quantity"])
                for _ in range(qty):
                    obtained.append(drop["item_id"])
        return obtained


# =============================================================================
# Steps 25〜35: ダーク・エコノミー＆脳拡張インプラント手術システム
# =============================================================================

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
        return {
            "high_demand": self.high_demand_tags,
            "low_demand": self.low_demand_tags,
        }


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


def sell_skill_to_black_market(
    character: CharacterState,
    skill_id: str,
    trends: MarketTrends | None = None,
) -> tuple[bool, int, str]:
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
        """Step 32: 指数関数的に跳ね上がる手術費用計算"""
        base_cost = 500
        step_count = max(0, (current_capacity_mb - 100) // 20)
        cost = int(base_cost * (1.6 ** step_count))
        return cost

    @staticmethod
    def perform_memory_expansion(
        character: CharacterState,
        credits_available: int,
        expansion_mb: int = 20,
        max_limit_mb: int = 300,
    ) -> tuple[bool, int, str]:
        """Step 33〜35: 手術実行とメモリ上限引き上げ"""
        if character.base_memory_capacity_mb >= max_limit_mb:
            return False, 0, f"脳インプラント拡張が物理限界（{max_limit_mb}MB）に達しています。"

        cost = CyberDoctorSurgery.calculate_expansion_cost(character.base_memory_capacity_mb, expansion_mb)
        if credits_available < cost:
            return False, 0, f"クレジット不足です。（必要: {cost} Cr / 所持: {credits_available} Cr）"

        old_cap = character.base_memory_capacity_mb
        character.base_memory_capacity_mb += expansion_mb
        character.calculate_memory_usage()

        return (
            True,
            cost,
            f"【手術成功】脳インプラント手術完了！ 脳容量が {old_cap}MB → {character.base_memory_capacity_mb}MB に拡張されました！（費用: {cost} Cr）",
        )
