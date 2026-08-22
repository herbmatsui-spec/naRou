
"""
skill_eater_territory_system.py
Aの世界（スキル喰い） 派閥テリトリー・勢力図システム
Phase 1: データ構造定義 (Steps 1-12)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from skill_eater_economy_system import FactionState


from .base import (
    TerritoryActionType,
    District,
    ActionResult,
    SabotageEffect,
    CeasefireAgreement,
    ActionLog,
    DynamicEventType,
    DynamicEvent,
)
class TerritoryState:
    _instance: TerritoryState | None = None

    def __init__(self):
        self.districts: dict[str, District] = {}
        self.faction_relations: dict[tuple[str, str], int] = {}
        self.turn_counter: int = 0
        self.active_events: list[DynamicEvent] = []
        self.sabotage_effects: list[SabotageEffect] = []
        self.ceasefire_agreements: list[CeasefireAgreement] = []
        self.action_history: list[ActionLog] = []
        self.event_history: list[dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> TerritoryState:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def load_from_yaml(self, file_path: str | Path) -> None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Territory definition file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "districts" not in data:
            return

        for district_data in data["districts"]:
            district = District.from_dict(district_data)
            self.districts[district.id] = district

        if "faction_relations" in data:
            for rel_key, value in data["faction_relations"].items():
                faction_a, faction_b = rel_key.split("|")
                self.faction_relations[(faction_a, faction_b)] = value
                self.faction_relations[(faction_b, faction_a)] = value

    def get_controlling_faction(self, district_id: str) -> str | None:
        district = self.districts.get(district_id)
        return district.controlling_faction if district else None

    def is_controlled_by(self, district_id: str, faction_id: str) -> bool:
        district = self.districts.get(district_id)
        return district is not None and district.controlling_faction == faction_id

    def get_districts_by_faction(self, faction_id: str) -> list[District]:
        return [d for d in self.districts.values() if d.controlling_faction == faction_id]

    def get_neutral_districts(self) -> list[District]:
        return [d for d in self.districts.values() if d.controlling_faction == "neutral"]

    def calculate_stability(self, district: District) -> int:
        base_stability = district.stability
        faction = self._get_faction_state(district.controlling_faction)
        if faction:
            morale_bonus = (faction.morale - 50) // 10
            base_stability += morale_bonus

        adjacent_hostile = 0
        for adj_id in district.adjacent_districts:
            adj_district = self.districts.get(adj_id)
            if adj_district and adj_district.controlling_faction != district.controlling_faction:
                adj_faction = self._get_faction_state(adj_district.controlling_faction)
                if adj_faction and self.get_relation(district.controlling_faction, adj_district.controlling_faction) < -50:
                    adjacent_hostile += 1
        base_stability -= adjacent_hostile * 5

        if district.sabotage_remaining > 0:
            base_stability -= 10

        return max(0, min(100, base_stability))

    def calculate_resource_output(self, district: District) -> int:
        if district.sabotage_remaining > 0:
            return district.resource_output // 2
        stability_mod = district.stability / 100.0
        faction = self._get_faction_state(district.controlling_faction)
        faction_bonus = 1.0
        if faction:
            faction_bonus = 1.0 + (faction.morale - 50) / 200.0
        return int(district.resource_output * stability_mod * faction_bonus)

    def _get_faction_state(self, faction_id: str):
        from skill_eater_economy_system import SkillEaterEconomySystem
        economy = SkillEaterEconomySystem()
        return economy.factions.get(faction_id)

    def get_relation(self, faction_a: str, faction_b: str) -> int:
        return self.faction_relations.get((faction_a, faction_b), 0)

    def set_relation(self, faction_a: str, faction_b: str, value: int) -> None:
        value = max(-100, min(100, value))
        self.faction_relations[(faction_a, faction_b)] = value
        self.faction_relations[(faction_b, faction_a)] = value

    def calculate_turn_income(self, faction_id: str) -> int:
        total = 0
        for district in self.get_districts_by_faction(faction_id):
            total += self.calculate_resource_output(district)
        return total

    def is_safe_passage(self, district_id: str, faction_id: str) -> bool:
        district = self.districts.get(district_id)
        if not district:
            return False
        if district.controlling_faction == faction_id:
            return True
        if district.controlling_faction == "neutral":
            return True
        if self.get_relation(faction_id, district.controlling_faction) >= 0:
            return True
        for ceasefire in self.ceasefire_agreements:
            if (ceasefire.faction_a == faction_id and ceasefire.faction_b == district.controlling_faction) or \
               (ceasefire.faction_b == faction_id and ceasefire.faction_a == district.controlling_faction):
                return True
        return False

    def check_exclusive_shop_unlock(self, district_id: str, faction_id: str) -> bool:
        district = self.districts.get(district_id)
        if not district or district.controlling_faction != faction_id:
            return False
        if district.exclusive_shop_unlocked:
            return True
        return district.turn_controlled >= 10 and district.stability >= 70

    def check_hidden_dungeon_reveal(self, district_id: str, faction_id: str) -> bool:
        district = self.districts.get(district_id)
        if not district or district.controlling_faction != faction_id:
            return False
        if district.hidden_dungeon_entrance:
            return True
        return district.hidden_dungeon_entrance and district.turn_controlled >= 20 and district.stability >= 80

    def _declare_war(self, faction_a: str, faction_b: str) -> None:
        from skill_eater_economy_system import SkillEaterEconomySystem
        economy = SkillEaterEconomySystem()
        faction_a_state = economy.factions.get(faction_a)
        faction_b_state = economy.factions.get(faction_b)
        if faction_a_state:
            faction_a_state.is_at_war = True
            faction_a_state.war_target = faction_b
            faction_a_state.morale = max(0, faction_a_state.morale - 10)
        if faction_b_state:
            faction_b_state.is_at_war = True
            faction_b_state.war_target = faction_a
            faction_b_state.morale = max(0, faction_b_state.morale - 10)

    def on_turn_start(self, turn_number: int) -> None:
        self.turn_counter = turn_number
        self._distribute_turn_income()
        self._update_stability()
        self._check_district_loss()
        self._check_shop_unlocks()
        self._check_dungeon_reveals()
        self._process_sabotage_effects()
        self._process_ceasefire_countdown()
        self._update_faction_morale()

    def on_turn_end(self) -> dict[str, Any]:
        stats = {
            "turn": self.turn_counter,
            "faction_income": {},
            "district_changes": [],
            "events_triggered": [],
        }
        for faction_id in ["midas", "resistance", "bank", "broker"]:
            income = self.calculate_turn_income(faction_id)
            stats["faction_income"][faction_id] = income
        return stats

    def _distribute_turn_income(self) -> None:
        from skill_eater_economy_system import SkillEaterEconomySystem
        economy = SkillEaterEconomySystem()
        for faction_id, faction in economy.factions.items():
            income = self.calculate_turn_income(faction_id)
            faction.territory_income_per_turn = income
            faction.influence_points += income
            if faction_id == "player":
                self._notify_income(faction_id, income)

    def _notify_income(self, faction_id: str, income: int) -> None:
        from skill_eater_presentation_system import SkillEaterPresentationSystem
        presentation = SkillEaterPresentationSystem.get_instance()
        presentation.add_event(
            emote_file="emote_cash.png",
            audio_file="handleCoins2.ogg",
            message=f"領土収入: {income} アルド",
        )

    def _update_stability(self) -> None:
        for district in self.districts.values():
            if district.controlling_faction == "neutral":
                continue
            faction = self._get_faction_state(district.controlling_faction)
            if faction:
                if faction.morale > 50:
                    district.stability = min(100, district.stability + 1)
                elif faction.morale < 30:
                    district.stability = max(0, district.stability - 2)
            adjacent_hostile = sum(1 for adj_id in district.adjacent_districts
                                   if (adj := self.districts.get(adj_id))
                                   and adj.controlling_faction != district.controlling_faction
                                   and adj.controlling_faction != "neutral"
                                   and self.get_relation(district.controlling_faction, adj.controlling_faction) < -50)
            district.stability = max(0, district.stability - adjacent_hostile)
            if district.sabotage_remaining > 0:
                district.stability = max(0, district.stability - 5)

    def _check_district_loss(self) -> None:
        lost_districts = []
        for district in self.districts.values():
            if district.stability <= 0 and district.controlling_faction != "neutral":
                old_faction = district.controlling_faction
                district.controlling_faction = "neutral"
                district.stability = 20
                district.turn_controlled = 0
                district.exclusive_shop_unlocked = False
                lost_districts.append((district.id, old_faction))

        for district_id, old_faction in lost_districts:
            adjacent_factions = {}
            for adj_id in self.districts[district_id].adjacent_districts:
                adj = self.districts.get(adj_id)
                if adj and adj.controlling_faction != "neutral":
                    adjacent_factions[adj.controlling_faction] = adjacent_factions.get(adj.controlling_faction, 0) + 1
            if adjacent_factions:
                strongest = max(adjacent_factions, key=adjacent_factions.get)
                if adjacent_factions[strongest] >= 2:
                    self.districts[district_id].controlling_faction = strongest
                    self.districts[district_id].turn_controlled = 0

            self.event_history.append({
                "turn": self.turn_counter,
                "type": "territory_lost",
                "district": district_id,
                "old_faction": old_faction,
            })

    def _check_shop_unlocks(self) -> None:
        from skill_eater_presentation_system import SkillEaterPresentationSystem
        presentation = SkillEaterPresentationSystem.get_instance()
        for district in self.districts.values():
            if district.controlling_faction != "neutral" and not district.exclusive_shop_unlocked:
                if district.turn_controlled >= 10 and district.stability >= 70:
                    district.exclusive_shop_unlocked = True
                    presentation.add_event(
                        emote_file="emote_stars.png",
                        audio_file="handleCoins2.ogg",
                        message=f"{district.name} で専用ショップが解放されました！",
                    )
                    self.event_history.append({
                        "turn": self.turn_counter,
                        "type": "shop_unlocked",
                        "district": district.id,
                        "faction": district.controlling_faction,
                    })

    def _check_dungeon_reveals(self) -> None:
        from skill_eater_presentation_system import SkillEaterPresentationSystem
        presentation = SkillEaterPresentationSystem.get_instance()
        for district in self.districts.values():
            if district.controlling_faction != "neutral" and district.hidden_dungeon_entrance and not district.exclusive_shop_unlocked:
                if district.turn_controlled >= 20 and district.stability >= 80:
                    presentation.add_event(
                        emote_file="emote_exclamations.png",
                        audio_file="territory_capture_fanfare.ogg",
                        message=f"{district.name} で隠しダンジョン入口を発見！",
                    )
                    self.event_history.append({
                        "turn": self.turn_counter,
                        "type": "dungeon_revealed",
                        "district": district.id,
                        "faction": district.controlling_faction,
                    })

    def _process_sabotage_effects(self) -> None:
        from skill_eater_presentation_system import SkillEaterPresentationSystem
        presentation = SkillEaterPresentationSystem.get_instance()
        remaining = []
        for effect in self.sabotage_effects:
            effect.remaining_turns -= 1
            district = self.districts.get(effect.district_id)
            if effect.remaining_turns <= 0:
                if district:
                    district.resource_output = effect.original_output
                    district.defense_level = effect.original_defense
                    district.sabotage_remaining = 0
                    presentation.add_event(
                        emote_file="emote_stars.png",
                        audio_file="chop.ogg",
                        message=f"{district.name} の破壊工作効果が解除されました",
                    )
            else:
                if district:
                    district.sabotage_remaining = effect.remaining_turns
                remaining.append(effect)
        self.sabotage_effects = remaining

    def _process_ceasefire_countdown(self) -> None:
        from skill_eater_presentation_system import SkillEaterPresentationSystem
        presentation = SkillEaterPresentationSystem.get_instance()
        remaining = []
        for ceasefire in self.ceasefire_agreements:
            ceasefire.remaining_turns -= 1
            if ceasefire.remaining_turns <= 0:
                presentation.add_event(
                    emote_file="emote_alert.png",
                    audio_file="metalLatch.ogg",
                    message=f"{ceasefire.faction_a} と {ceasefire.faction_b} の停戦が終了しました",
                )
                self.event_history.append({
                    "turn": self.turn_counter,
                    "type": "ceasefire_ended",
                    "faction_a": ceasefire.faction_a,
                    "faction_b": ceasefire.faction_b,
                })
            else:
                remaining.append(ceasefire)
        self.ceasefire_agreements = remaining

    def _update_faction_morale(self) -> None:
        from skill_eater_economy_system import SkillEaterEconomySystem
        economy = SkillEaterEconomySystem()
        for faction_id, faction in economy.factions.items():
            controlled = len(self.get_districts_by_faction(faction_id))
            faction.morale = min(100, faction.morale + controlled)
            if faction.is_at_war:
                faction.morale = max(0, faction.morale - 2)
            if faction.territory_income_per_turn > 0:
                faction.morale = min(100, faction.morale + 2)
            else:
                faction.morale = max(0, faction.morale - 3)
            faction.morale = max(0, min(100, faction.morale))

    def check_event_triggers(self) -> list[DynamicEvent]:
        triggered = []

        war_event = self._check_faction_war_trigger()
        if war_event:
            triggered.append(war_event)

        betrayal_event = self._check_betrayal_trigger()
        if betrayal_event:
            triggered.append(betrayal_event)

        third_party_event = self._check_third_party_trigger()
        if third_party_event:
            triggered.append(third_party_event)

        midas_raid_event = self._check_midas_raid_trigger()
        if midas_raid_event:
            triggered.append(midas_raid_event)

        for event in triggered:
            self.apply_event(event)

        return triggered

    def _check_faction_war_trigger(self) -> DynamicEvent | None:
        factions = ["midas", "resistance", "bank", "broker"]
        for i, f1 in enumerate(factions):
            for f2 in factions[i+1:]:
                f1_state = self._get_faction_state(f1)
                f2_state = self._get_faction_state(f2)
                if not f1_state or not f2_state:
                    continue
                if f1_state.is_at_war or f2_state.is_at_war:
                    continue

                inf_diff = abs(f1_state.influence_points - f2_state.influence_points)
                max_inf = max(f1_state.influence_points, f2_state.influence_points)
                if max_inf == 0:
                    continue

                adjacent_count = 0
                for district in self.districts.values():
                    if district.controlling_faction == f1:
                        for adj_id in district.adjacent_districts:
                            adj = self.districts.get(adj_id)
                            if adj and adj.controlling_faction == f2:
                                adjacent_count += 1

                if inf_diff / max_inf < 0.2 and adjacent_count >= 3:
                    return DynamicEvent(
                        id=f"faction_war_{f1}_{f2}_{self.turn_counter}",
                        name=f"派閥戦争: {f1_state.name} vs {f2_state.name}",
                        description=f"勢力均衡と国境摩擦により {f1_state.name} と {f2_state.name} の全面戦争勃発！",
                        event_type=DynamicEventType.FACTION_WAR,
                        trigger_condition={"factions": [f1, f2], "adjacent_borders": adjacent_count},
                        duration=random.randint(10, 30),
                        effects={"war_declared": True, "raid_success_bonus": 0.2, "propaganda_disabled": True},
                        faction_scope=[f1, f2],
                    )
        return None

    def _check_betrayal_trigger(self) -> DynamicEvent | None:
        from skill_eater_economy_system import SkillEaterEconomySystem
        economy = SkillEaterEconomySystem()
        for faction_id, faction in economy.factions.items():
            if faction.morale < 20 and len(self.get_districts_by_faction(faction_id)) >= 3:
                controlled = self.get_districts_by_faction(faction_id)
                rebel_districts = controlled[:random.randint(1, min(2, len(controlled)))]
                rebel_id = f"rebel_{faction_id}_{self.turn_counter}"

                return DynamicEvent(
                    id=f"betrayal_{faction_id}_{self.turn_counter}",
                    name=f"裏切り: {faction.name} から {rebel_id} が分裂",
                    description=f"士気低下により {faction.name} の一部区画が反乱派閥 {rebel_id} として独立！",
                    event_type=DynamicEventType.BETRAYAL,
                    trigger_condition={"parent_faction": faction_id, "rebel_districts": [d.id for d in rebel_districts]},
                    duration=0,
                    effects={
                        "rebel_faction_created": rebel_id,
                        "rebel_districts": [d.id for d in rebel_districts],
                        "parent_influence_loss": 300,
                        "parent_reputation_loss": 15,
                    },
                    faction_scope=[faction_id, rebel_id],
                )
        return None

    def _check_third_party_trigger(self) -> DynamicEvent | None:
        neutral_count = len(self.get_neutral_districts())
        total_influence = sum(self._get_faction_state(f).influence_points for f in ["midas", "resistance", "bank", "broker"] if self._get_faction_state(f))

        if neutral_count >= 5 and total_influence < 5000:
            third_party_names = ["mercenary_guild", "ancient_order", "shadow_syndicate", "tech_cult"]
            tp_name = random.choice(third_party_names)
            tp_id = f"third_party_{tp_name}"

            neutral_districts = self.get_neutral_districts()
            target_districts = random.sample(neutral_districts, min(3, len(neutral_districts)))

            return DynamicEvent(
                id=f"third_party_{tp_name}_{self.turn_counter}",
                name=f"第三勢力介入: {tp_name}",
                description=f"謎の勢力 {tp_name} が出現し、中立区画を制圧し始めた！",
                event_type=DynamicEventType.THIRD_PARTY,
                trigger_condition={"third_party_id": tp_id, "target_districts": [d.id for d in target_districts]},
                duration=random.randint(15, 40),
                effects={
                    "new_faction": tp_id,
                    "initial_districts": [d.id for d in target_districts],
                    "high_morale": 80,
                    "high_resources": True,
                },
                faction_scope=[tp_id],
            )
        return None

    def _check_midas_raid_trigger(self) -> DynamicEvent | None:
        from skill_eater_economy_system import SkillEaterEconomySystem
        economy = SkillEaterEconomySystem()

        if economy.heat_level >= 80:
            illegal_districts = []
            for district in self.districts.values():
                if district.controlling_faction in ["broker", "rebel_"] or (district.controlling_faction == "midas" and district.stability < 30):
                    illegal_districts.append(district)

            if len(illegal_districts) >= 2:
                return DynamicEvent(
                    id=f"midas_raid_{self.turn_counter}",
                    name="ミダス一斉検挙",
                    description="ミダス特別監査局が違法スキル保有区画・闇市場区画を一斉検挙！",
                    event_type=DynamicEventType.MIDAS_RAID,
                    trigger_condition={"heat_level": economy.heat_level, "target_districts": [d.id for d in illegal_districts]},
                    duration=1,
                    effects={
                        "heat_reset": True,
                        "confiscate_illegal_skills": True,
                        "confiscate_aldo_half": True,
                        "neutralize_districts": [d.id for d in illegal_districts],
                        "npc_influence_loss": 500,
                        "npc_reputation_loss": 30,
                    },
                    faction_scope=["midas", "broker", "resistance"],
                )
        return None

    def apply_event(self, event: DynamicEvent) -> None:
        if any(e.id == event.id for e in self.active_events):
            return

        event.is_active = True
        event.remaining_turns = event.duration
        self.active_events.append(event)

        if event.event_type == DynamicEventType.FACTION_WAR:
            self._apply_faction_war(event)
        elif event.event_type == DynamicEventType.BETRAYAL:
            self._apply_betrayal(event)
        elif event.event_type == DynamicEventType.THIRD_PARTY:
            self._apply_third_party(event)
        elif event.event_type == DynamicEventType.MIDAS_RAID:
            self._apply_midas_raid(event)

        self._notify_event(event)

    def _apply_faction_war(self, event: DynamicEvent) -> None:
        factions = event.effects.get("factions", event.faction_scope)
        if len(factions) >= 2:
            f1, f2 = factions[0], factions[1]
            f1_state = self._get_faction_state(f1)
            f2_state = self._get_faction_state(f2)
            if f1_state:
                f1_state.is_at_war = True
                f1_state.war_target = f2
                f1_state.morale = max(0, f1_state.morale - 10)
            if f2_state:
                f2_state.is_at_war = True
                f2_state.war_target = f1
                f2_state.morale = max(0, f2_state.morale - 10)

    def _apply_betrayal(self, event: DynamicEvent) -> None:
        from skill_eater_economy_system import SkillEaterEconomySystem
        economy = SkillEaterEconomySystem()

        parent_faction = event.trigger_condition.get("parent_faction")
        rebel_faction = event.effects.get("rebel_faction_created")
        rebel_districts = event.effects.get("rebel_districts", [])

        parent_state = economy.factions.get(parent_faction)
        if parent_state:
            parent_state.influence_points = max(0, parent_state.influence_points - event.effects.get("parent_influence_loss", 300))
            parent_state.reputation = max(-100, parent_state.reputation - event.effects.get("parent_reputation_loss", 15))

        for district_id in rebel_districts:
            district = self.districts.get(district_id)
            if district:
                district.controlling_faction = rebel_faction
                district.turn_controlled = 0
                district.stability = max(20, district.stability - 10)

        rebel_state = FactionState(
            id=rebel_faction,
            name=rebel_faction.replace("_", " ").title(),
            reputation=0,
            influence_points=500,
            is_hostile=False,
            morale=50,
        )
        economy.factions[rebel_faction] = rebel_state

    def _apply_third_party(self, event: DynamicEvent) -> None:
        from skill_eater_economy_system import SkillEaterEconomySystem
        economy = SkillEaterEconomySystem()

        tp_id = event.effects.get("new_faction")
        initial_districts = event.effects.get("initial_districts", [])

        for district_id in initial_districts:
            district = self.districts.get(district_id)
            if district:
                district.controlling_faction = tp_id
                district.turn_controlled = 0
                district.stability = 60

        tp_state = FactionState(
            id=tp_id,
            name=tp_id.replace("_", " ").title(),
            reputation=0,
            influence_points=3000,
            is_hostile=True,
            morale=event.effects.get("high_morale", 80),
        )
        economy.factions[tp_id] = tp_state

        for existing_id in ["midas", "resistance", "bank", "broker"]:
            self.set_relation(tp_id, existing_id, 0)

    def _apply_midas_raid(self, event: DynamicEvent) -> None:
        from skill_eater_economy_system import SkillEaterEconomySystem
        economy = SkillEaterEconomySystem()

        economy.heat_level = 0

        target_districts = event.effects.get("neutralize_districts", [])
        for district_id in target_districts:
            district = self.districts.get(district_id)
            if district:
                old_faction = district.controlling_faction
                district.controlling_faction = "neutral"
                district.stability = 15
                district.turn_controlled = 0
                district.exclusive_shop_unlocked = False

                old_faction_state = economy.factions.get(old_faction)
                if old_faction_state:
                    old_faction_state.influence_points = max(0, old_faction_state.influence_points - event.effects.get("npc_influence_loss", 500))
                    old_faction_state.reputation = max(-100, old_faction_state.reputation - event.effects.get("npc_reputation_loss", 30))

    def update_events(self) -> None:
        remaining = []
        for event in self.active_events:
            if event.remaining_turns > 0:
                event.remaining_turns -= 1
                self._process_event_ongoing_effects(event)
                remaining.append(event)
            else:
                self._remove_event(event)
        self.active_events = remaining

    def _process_event_ongoing_effects(self, event: DynamicEvent) -> None:
        if event.event_type == DynamicEventType.FACTION_WAR:
            for faction_id in event.faction_scope:
                faction = self._get_faction_state(faction_id)
                if faction:
                    faction.morale = max(0, faction.morale - 1)

    def _remove_event(self, event: DynamicEvent) -> None:
        event.is_active = False
        self.event_history.append({
            "turn": self.turn_counter,
            "type": "event_ended",
            "event_id": event.id,
            "event_name": event.name,
        })

        if event.event_type == DynamicEventType.FACTION_WAR:
            self._resolve_faction_war(event)
        elif event.event_type == DynamicEventType.THIRD_PARTY:
            self._resolve_third_party(event)

    def _resolve_faction_war(self, event: DynamicEvent) -> None:
        factions = event.faction_scope
        if len(factions) >= 2:
            f1, f2 = factions[0], factions[1]
            f1_state = self._get_faction_state(f1)
            f2_state = self._get_faction_state(f2)

            f1_districts = len(self.get_districts_by_faction(f1))
            f2_districts = len(self.get_districts_by_faction(f2))

            winner = f1 if f1_districts > f2_districts else f2
            loser = f2 if winner == f1 else f1

            winner_state = self._get_faction_state(winner)
            if winner_state:
                winner_state.is_at_war = False
                winner_state.war_target = None
                winner_state.morale = min(100, winner_state.morale + 20)
                winner_state.influence_points += 500

            loser_state = self._get_faction_state(loser)
            if loser_state:
                loser_state.is_at_war = False
                loser_state.war_target = None
                loser_state.morale = max(0, loser_state.morale - 10)

            self.event_history.append({
                "turn": self.turn_counter,
                "type": "faction_war_ended",
                "winner": winner,
                "loser": loser,
            })

    def _resolve_third_party(self, event: DynamicEvent) -> None:
        tp_id = event.effects.get("new_faction")
        tp_state = self._get_faction_state(tp_id)
        tp_districts = len(self.get_districts_by_faction(tp_id))

        if tp_districts == 0:
            from skill_eater_economy_system import SkillEaterEconomySystem
            economy = SkillEaterEconomySystem()
            if tp_id in economy.factions:
                del economy.factions[tp_id]

            for faction_id in ["midas", "resistance", "bank", "broker"]:
                faction = self._get_faction_state(faction_id)
                if faction:
                    faction.morale = min(100, faction.morale + 10)
                    faction.reputation = min(100, faction.reputation + 10)

            self.event_history.append({
                "turn": self.turn_counter,
                "type": "third_party_defeated",
                "third_party": tp_id,
            })

    def _notify_event(self, event: DynamicEvent) -> None:
        from skill_eater_presentation_system import SkillEaterPresentationSystem
        presentation = SkillEaterPresentationSystem.get_instance()

        audio = EVENT_AUDIO_MAP.get(event.event_type.value, "")
        emote = EVENT_EMOTE_MAP.get(event.event_type.value, "")

        if isinstance(audio, list):
            for a in audio:
                presentation.add_event(emote_file=emote, audio_file=a, message=event.name)
        else:
            presentation.add_event(emote_file=emote, audio_file=audio, message=event.name)

    def trigger_event(self, event_id: str) -> DynamicEvent | None:
        if event_id == "faction_war":
            event = self._check_faction_war_trigger()
        elif event_id == "betrayal":
            event = self._check_betrayal_trigger()
        elif event_id == "third_party":
            event = self._check_third_party_trigger()
        elif event_id == "midas_raid":
            event = self._check_midas_raid_trigger()
        else:
            return None

        if event:
            self.apply_event(event)
        return event

    def get_player_choices(self, event: DynamicEvent) -> list[dict[str, Any]]:
        if event.event_type == DynamicEventType.FACTION_WAR:
            return [
                {"id": "intervene_a", "text": f"{event.faction_scope[0]} を支援", "effect": "support_faction_a"},
                {"id": "intervene_b", "text": f"{event.faction_scope[1]} を支援", "effect": "support_faction_b"},
                {"id": "mediate", "text": "仲裁を試みる", "effect": "mediate"},
                {"id": "observe", "text": "様子見", "effect": "observe"},
            ]
        elif event.event_type == DynamicEventType.BETRAYAL:
            return [
                {"id": "suppress", "text": "反乱を鎮圧支援", "effect": "support_parent"},
                {"id": "accept", "text": "反乱を容認", "effect": "accept_rebel"},
                {"id": "exploit", "text": "第三勢力として利用", "effect": "exploit_third_party"},
            ]
        return []

    def apply_player_choice(self, event: DynamicEvent, choice_id: str) -> ActionResult:
        if event.event_type == DynamicEventType.FACTION_WAR:
            if choice_id == "intervene_a":
                return self._intervene_war(event, event.faction_scope[0])
            elif choice_id == "intervene_b":
                return self._intervene_war(event, event.faction_scope[1])
            elif choice_id == "mediate":
                return self._mediate_war(event)
        elif event.event_type == DynamicEventType.BETRAYAL:
            if choice_id == "suppress":
                return self._suppress_betrayal(event)
            elif choice_id == "accept":
                return self._accept_betrayal(event)
        return ActionResult(success=False, message="無効な選択", effects={})

    def _intervene_war(self, event: DynamicEvent, supported_faction: str) -> ActionResult:
        other_faction = event.faction_scope[1] if event.faction_scope[0] == supported_faction else event.faction_scope[0]
        supported = self._get_faction_state(supported_faction)
        other = self._get_faction_state(other_faction)
        if supported:
            supported.influence_points += 300
            supported.reputation = min(100, supported.reputation + 10)
        if other:
            other.reputation = max(-100, other.reputation - 10)
        return ActionResult(success=True, message=f"{supported_faction} を支援しました", effects={"supported": supported_faction})

    def _mediate_war(self, event: DynamicEvent) -> ActionResult:
        f1, f2 = event.faction_scope[0], event.faction_scope[1]
        f1_state = self._get_faction_state(f1)
        f2_state = self._get_faction_state(f2)
        if f1_state and f2_state:
            f1_state.is_at_war = False
            f1_state.war_target = None
            f2_state.is_at_war = False
            f2_state.war_target = None
            ceasefire = CeasefireAgreement(faction_a=f1, faction_b=f2, remaining_turns=5)
            self.ceasefire_agreements.append(ceasefire)
            return ActionResult(success=True, message="仲裁成功！一時停戦成立", effects={"ceasefire": True})
        return ActionResult(success=False, message="仲裁失敗", effects={})

    def _suppress_betrayal(self, event: DynamicEvent) -> ActionResult:
        parent_faction = event.trigger_condition.get("parent_faction")
        rebel_faction = event.effects.get("rebel_faction_created")
        rebel_districts = event.effects.get("rebel_districts", [])

        for district_id in rebel_districts:
            district = self.districts.get(district_id)
            if district:
                district.controlling_faction = parent_faction

        from skill_eater_economy_system import SkillEaterEconomySystem
        economy = SkillEaterEconomySystem()
        if rebel_faction in economy.factions:
            del economy.factions[rebel_faction]

        parent = self._get_faction_state(parent_faction)
        if parent:
            parent.influence_points += 200
            parent.reputation = min(100, parent.reputation + 5)

        return ActionResult(success=True, message=f"反乱鎮圧支援完了。{parent_faction} が区画を取り戻しました", effects={"rebel_suppressed": True})

    def _accept_betrayal(self, event: DynamicEvent) -> ActionResult:
        return ActionResult(success=True, message="反乱を容認しました。新派閥が独立します", effects={"rebel_accepted": True})

    def to_dict(self) -> dict[str, Any]:
        return {
            "districts": {k: v.to_dict() for k, v in self.districts.items()},
            "faction_relations": {f"{a}|{b}": v for (a, b), v in self.faction_relations.items() if a < b},
            "turn_counter": self.turn_counter,
            "active_events": [e.to_dict() for e in self.active_events],
            "sabotage_effects": [s.to_dict() for s in self.sabotage_effects],
            "ceasefire_agreements": [c.to_dict() for c in self.ceasefire_agreements],
            "action_history": [a.to_dict() for a in self.action_history],
            "event_history": self.event_history,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TerritoryState:
        state = cls()
        state.districts = {k: District.from_dict(v) for k, v in data.get("districts", {}).items()}
        for rel_key, value in data.get("faction_relations", {}).items():
            a, b = rel_key.split("|")
            state.faction_relations[(a, b)] = value
            state.faction_relations[(b, a)] = value
        state.turn_counter = data.get("turn_counter", 0)
        state.active_events = [DynamicEvent.from_dict(e) for e in data.get("active_events", [])]
        state.sabotage_effects = [SabotageEffect.from_dict(s) for s in data.get("sabotage_effects", [])]
        state.ceasefire_agreements = [CeasefireAgreement.from_dict(c) for c in data.get("ceasefire_agreements", [])]
        state.action_history = [ActionLog.from_dict(a) for a in data.get("action_history", [])]
        state.event_history = data.get("event_history", [])
        return state


from abc import ABC, abstractmethod


class TerritoryController:
    ACTION_CLASSES = {
        TerritoryActionType.PATROL: PatrolAction,
        TerritoryActionType.RAID: RaidAction,
        TerritoryActionType.PROPAGANDA: PropagandaAction,
        TerritoryActionType.SABOTAGE: SabotageAction,
        TerritoryActionType.NEGOTIATE_CEASEFIRE: NegotiateCeasefireAction,
    }

    def __init__(self, territory: TerritoryState | None = None):
        self.territory = territory or TerritoryState.get_instance()
        self.action_cooldowns: dict[str, dict[TerritoryActionType, int]] = {}

    def execute_action(
        self,
        actor_faction: str,
        action_type: TerritoryActionType,
        target_district_id: str,
        **kwargs
    ) -> ActionResult:
        cooldowns = self.action_cooldowns.setdefault(actor_faction, {})
        if cooldowns.get(action_type, 0) > 0:
            return ActionResult(
                success=False,
                message=f"{action_type.value} はクールダウン中です（残り {cooldowns[action_type]} ターン）",
                effects={},
            )

        action_class = self.ACTION_CLASSES.get(action_type)
        if not action_class:
            return ActionResult(success=False, message="不明なアクション", effects={})

        action = action_class()
        can_exec, reason = action.can_execute(self.territory, actor_faction, target_district_id, **kwargs)
        if not can_exec:
            return ActionResult(success=False, message=reason, effects={})

        result = action.execute(self.territory, actor_faction, target_district_id, **kwargs)

        if result.success:
            cooldowns[action_type] = self.ACTION_CLASSES[action_type]().costs["cooldown"]
            self._log_action(actor_faction, action_type, target_district_id, result)
        else:
            self._log_action(actor_faction, action_type, target_district_id, result)

        return result

    def _log_action(self, actor_faction: str, action_type: TerritoryActionType, target_district_id: str, result: ActionResult):
        log = ActionLog(
            turn=self.territory.turn_counter,
            actor_faction=actor_faction,
            action_type=action_type.value,
            target_district=target_district_id,
            target_faction=self.territory.districts.get(target_district_id, District(id="", name="")).controlling_faction,
            success=result.success,
            message=result.message,
        )
        self.territory.action_history.append(log)
        if len(self.territory.action_history) > 100:
            self.territory.action_history = self.territory.action_history[-100:]

    def decrement_cooldowns(self, actor_faction: str):
        cooldowns = self.action_cooldowns.get(actor_faction, {})
        for action_type in list(cooldowns.keys()):
            cooldowns[action_type] = max(0, cooldowns[action_type] - 1)

    def get_recent_actions(self, limit: int = 10) -> list[ActionLog]:
        return self.territory.action_history[-limit:]
