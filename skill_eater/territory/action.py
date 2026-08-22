
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
from .system import TerritoryState
class PatrolAction(TerritoryActionBase):
    def __init__(self):
        super().__init__(TerritoryActionType.PATROL)

    def can_execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> tuple[bool, str]:
        district = territory.districts.get(target_district_id)
        if not district:
            return False, "区画が存在しません"
        if district.controlling_faction != actor_faction:
            return False, "自派閥支配区画のみパトロール可能です"
        return True, ""

    def calculate_success_rate(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> float:
        return self.base_success

    def execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> ActionResult:
        district = territory.districts[target_district_id]
        district.stability = min(100, district.stability + 5)
        district.resource_output = int(district.resource_output * 1.05)

        return ActionResult(
            success=True,
            message=f"{district.name} をパトロールしました。安定度+5、資源出力+5%",
            effects={"stability_change": 5, "resource_output_multiplier": 1.05},
            audio_cue=self.get_audio_cue(),
            emote_cue=self.get_emote_cue(),
        )


class RaidAction(TerritoryActionBase):
    def __init__(self):
        super().__init__(TerritoryActionType.RAID)

    def can_execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> tuple[bool, str]:
        district = territory.districts.get(target_district_id)
        if not district:
            return False, "区画が存在しません"
        if district.controlling_faction == actor_faction:
            return False, "自派閥支配区画を襲撃できません"
        if district.controlling_faction == "neutral":
            return False, "中立区画は襲撃できません（プロパガンダを使用してください）"
        return True, ""

    def calculate_success_rate(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> float:
        district = territory.districts[target_district_id]
        actor_faction_state = territory._get_faction_state(actor_faction)
        target_faction_state = territory._get_faction_state(district.controlling_faction)

        attack_power = actor_faction_state.influence_points // 100 if actor_faction_state else 10
        defense_power = district.defense_level * 20
        if target_faction_state:
            defense_power += target_faction_state.influence_points // 200

        rate = (attack_power - defense_power + 50) / 100
        return max(0.1, min(0.9, rate))

    def execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> ActionResult:
        district = territory.districts[target_district_id]
        success_rate = self.calculate_success_rate(territory, actor_faction, target_district_id)
        success = random.random() < success_rate

        if success:
            old_faction = district.controlling_faction
            district.controlling_faction = actor_faction
            district.stability = max(0, district.stability - 15)
            district.turn_controlled = 0
            district.exclusive_shop_unlocked = False

            actor_faction_state = territory._get_faction_state(actor_faction)
            if actor_faction_state:
                actor_faction_state.influence_points += 50

            target_faction_state = territory._get_faction_state(old_faction)
            if target_faction_state:
                target_faction_state.influence_points = max(0, target_faction_state.influence_points - 50)

            if random.random() < 0.3:
                territory._declare_war(actor_faction, old_faction)

            return ActionResult(
                success=True,
                message=f"{district.name} を制圧しました！ {old_faction} から奪取",
                effects={
                    "district_captured": True,
                    "old_faction": old_faction,
                    "stability_change": -15,
                    "influence_gain": 50,
                },
                audio_cue=self.get_audio_cue(),
                emote_cue=self.get_emote_cue(),
            )
        else:
            return ActionResult(
                success=False,
                message=f"{district.name} への襲撃は失敗しました",
                effects={},
                audio_cue="metalClick.ogg",
                emote_cue="emote_cross.png",
            )


class PropagandaAction(TerritoryActionBase):
    def __init__(self):
        super().__init__(TerritoryActionType.PROPAGANDA)

    def can_execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> tuple[bool, str]:
        district = territory.districts.get(target_district_id)
        if not district:
            return False, "区画が存在しません"
        if district.controlling_faction == actor_faction:
            return False, "自派閥支配区画にプロパガンダは不要です"

        adjacent_owned = False
        for adj_id in district.adjacent_districts:
            adj = territory.districts.get(adj_id)
            if adj and adj.controlling_faction == actor_faction:
                adjacent_owned = True
                break
        if not adjacent_owned:
            return False, "隣接する自派閥支配区画が必要です"
        return True, ""

    def calculate_success_rate(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> float:
        district = territory.districts[target_district_id]
        actor_faction_state = territory._get_faction_state(actor_faction)

        rep_bonus = actor_faction_state.reputation * 0.5 if actor_faction_state else 0
        adjacent_count = sum(1 for adj_id in district.adjacent_districts
                           if territory.districts.get(adj_id) and territory.districts[adj_id].controlling_faction == actor_faction)
        adjacent_bonus = adjacent_count * 10

        target_faction_state = territory._get_faction_state(district.controlling_faction)
        target_stability_penalty = district.stability * 0.3

        rate = (self.base_success * 100 + rep_bonus + adjacent_bonus - target_stability_penalty) / 100
        return max(0.05, min(0.85, rate))

    def execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> ActionResult:
        district = territory.districts[target_district_id]
        success_rate = self.calculate_success_rate(territory, actor_faction, target_district_id)
        success = random.random() < success_rate

        if success:
            old_faction = district.controlling_faction
            if district.controlling_faction == "neutral":
                district.controlling_faction = actor_faction
                district.turn_controlled = 0
                district.exclusive_shop_unlocked = False
                msg = f"{district.name} が {actor_faction} の影響下に入りました"
            else:
                district.stability = max(0, district.stability - 20)
                msg = f"{district.name} の {old_faction} への忠誠心が揺らぎました"

            if actor_faction_state := territory._get_faction_state(actor_faction):
                actor_faction_state.reputation = min(100, actor_faction_state.reputation + 5)

            return ActionResult(
                success=True,
                message=msg,
                effects={"stability_change": -20 if old_faction != "neutral" else 0, "faction_change": old_faction != "neutral"},
                audio_cue=self.get_audio_cue(),
                emote_cue=self.get_emote_cue(),
            )
        else:
            if actor_faction_state := territory._get_faction_state(actor_faction):
                actor_faction_state.reputation = max(-100, actor_faction_state.reputation - 5)
            target_faction_state = territory._get_faction_state(district.controlling_faction)
            if target_faction_state and district.controlling_faction != "neutral":
                target_faction_state.reputation = min(100, target_faction_state.reputation + 5)

            return ActionResult(
                success=False,
                message=f"プロパガンダは逆効果でした。{district.name} の住民は反発しています",
                effects={"reputation_penalty": -5},
                audio_cue="metalClick.ogg",
                emote_cue="emote_cross.png",
            )


class SabotageAction(TerritoryActionBase):
    def __init__(self):
        super().__init__(TerritoryActionType.SABOTAGE)

    def can_execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> tuple[bool, str]:
        district = territory.districts.get(target_district_id)
        if not district:
            return False, "区画が存在しません"
        if district.controlling_faction == actor_faction:
            return False, "自派閥支配区画を破壊できません"
        if district.controlling_faction == "neutral":
            return False, "中立区画は破壊できません"
        if district.sabotage_remaining > 0:
            return False, "既に破壊工作の効果中です"
        return True, ""

    def calculate_success_rate(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> float:
        district = territory.districts[target_district_id]
        rate = self.base_success
        rate -= district.defense_level * 0.05
        rate -= district.stability * 0.002
        return max(0.05, min(0.6, rate))

    def execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> ActionResult:
        district = territory.districts[target_district_id]
        success_rate = self.calculate_success_rate(territory, actor_faction, target_district_id)
        success = random.random() < success_rate

        if success:
            sabotage = SabotageEffect(
                district_id=target_district_id,
                remaining_turns=3,
                original_output=district.resource_output,
                original_defense=district.defense_level,
            )
            territory.sabotage_effects.append(sabotage)
            district.sabotage_remaining = 3
            district.resource_output = district.resource_output // 2
            district.defense_level = max(1, district.defense_level - 1)

            if random.random() < 0.3:
                if actor_faction_state := territory._get_faction_state(actor_faction):
                    actor_faction_state.reputation = max(-100, actor_faction_state.reputation - 20)
                from skill_eater_economy_system import SkillEaterEconomySystem
                economy = SkillEaterEconomySystem()
                economy.heat_level += 15

            return ActionResult(
                success=True,
                message=f"{district.name} で破壊工作成功！ 資源出力半減、防御力低下（3ターン）",
                effects={"sabotage_applied": True, "duration": 3},
                audio_cue=self.get_audio_cue(),
                emote_cue=self.get_emote_cue(),
            )
        else:
            if random.random() < 0.5:
                if actor_faction_state := territory._get_faction_state(actor_faction):
                    actor_faction_state.reputation = max(-100, actor_faction_state.reputation - 20)
                from skill_eater_economy_system import SkillEaterEconomySystem
                economy = SkillEaterEconomySystem()
                economy.heat_level += 15
                return ActionResult(
                    success=False,
                    message="破壊工作が発覚しました！ 評判-20、警戒度+15",
                    effects={"discovered": True, "reputation_penalty": -20, "heat_increase": 15},
                    audio_cue="metalLatch.ogg",
                    emote_cue="emote_cross.png",
                )
            return ActionResult(
                success=False,
                message="破壊工作は失敗しました",
                effects={},
                audio_cue="metalClick.ogg",
                emote_cue="emote_cross.png",
            )


class NegotiateCeasefireAction(TerritoryActionBase):
    def __init__(self):
        super().__init__(TerritoryActionType.NEGOTIATE_CEASEFIRE)

    def can_execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> tuple[bool, str]:
        target_faction = kwargs.get("target_faction")
        if not target_faction:
            return False, "交渉相手の派閥を指定してください"
        actor_faction_state = territory._get_faction_state(actor_faction)
        target_faction_state = territory._get_faction_state(target_faction)
        if not actor_faction_state or not target_faction_state:
            return False, "派閥が存在しません"
        if not actor_faction_state.is_at_war or actor_faction_state.war_target != target_faction:
            return False, "戦争状態ではありません"
        return True, ""

    def calculate_success_rate(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> float:
        target_faction = kwargs.get("target_faction")
        actor_faction_state = territory._get_faction_state(actor_faction)
        target_faction_state = territory._get_faction_state(target_faction)

        if not actor_faction_state or not target_faction_state:
            return 0.0

        actor_districts = len(territory.get_districts_by_faction(actor_faction))
        target_districts = len(territory.get_districts_by_faction(target_faction))

        war_pressure = (target_districts - actor_districts) * 2
        morale_factor = (actor_faction_state.morale + target_faction_state.morale) / 200
        relation = territory.get_relation(actor_faction, target_faction)

        rate = (self.base_success * 100 + morale_factor * 50 + relation * 0.5 - war_pressure) / 100
        return max(0.1, min(0.9, rate))

    def execute(self, territory: TerritoryState, actor_faction: str, target_district_id: str, **kwargs) -> ActionResult:
        target_faction = kwargs.get("target_faction")
        success_rate = self.calculate_success_rate(territory, actor_faction, target_district_id, **kwargs)
        success = random.random() < success_rate

        if success:
            actor_faction_state = territory._get_faction_state(actor_faction)
            target_faction_state = territory._get_faction_state(target_faction)

            actor_faction_state.is_at_war = False
            actor_faction_state.war_target = None
            target_faction_state.is_at_war = False
            target_faction_state.war_target = None

            actor_faction_state.reputation = min(100, actor_faction_state.reputation + 10)
            target_faction_state.reputation = min(100, target_faction_state.reputation + 10)

            ceasefire = CeasefireAgreement(
                faction_a=actor_faction,
                faction_b=target_faction,
                remaining_turns=10,
                terms={"mutual_non_aggression": True},
            )
            territory.ceasefire_agreements.append(ceasefire)

            return ActionResult(
                success=True,
                message=f"{actor_faction} と {target_faction} の間で停戦が成立しました（10ターン）",
                effects={"ceasefire_established": True, "duration": 10, "reputation_gain": 10},
                audio_cue=self.get_audio_cue(),
                emote_cue=self.get_emote_cue(),
            )
        else:
            return ActionResult(
                success=False,
                message="停戦交渉は決裂しました。戦争は続きます",
                effects={},
                audio_cue="metalClick.ogg",
                emote_cue="emote_cross.png",
            )


