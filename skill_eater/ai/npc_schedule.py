"""
NPC Schedule System
Steps 13-17: NPCSchedule, Registry, YAML definitions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

try:
    from naRou.time_system import TimePhase
except ImportError:
    from time_system import TimePhase


@dataclass
class NPCSchedule:
    """NPCスケジュール定義"""
    npc_id: str
    name: str
    active_phases: list[TimePhase] = field(default_factory=list)
    location: str = ""
    conditions: dict[str, Any] = field(default_factory=dict)
    raid_chance: float = 0.0  # 襲撃確率 (検査官用)


@dataclass
class MerchantRoute:
    """移動商人ルート定義"""
    npc_id: str
    name: str
    stops: list[tuple[TimePhase, str]] = field(default_factory=list)  # (フェーズ, 場所)

    def get_current_location(self, phase: TimePhase) -> str:
        """現在フェーズでの商人の場所を取得"""
        for stop_phase, location in self.stops:
            if stop_phase == phase:
                return location
        return ""


class NPCScheduleRegistry:
    """NPCスケジュールレジストリ (シングルトン)"""

    _instance: NPCScheduleRegistry | None = None

    def __new__(cls) -> NPCScheduleRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._schedules: dict[str, NPCSchedule] = {}
            cls._instance._merchant_routes: dict[str, MerchantRoute] = {}
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_schedules"):
            self._schedules = {}
            self._merchant_routes = {}

    # --- 登録 ---
    def register(self, schedule: NPCSchedule) -> None:
        self._schedules[schedule.npc_id] = schedule

    def register_merchant_route(self, route: MerchantRoute) -> None:
        self._merchant_routes[route.npc_id] = route

    # --- 取得 ---
    def get_schedule(self, npc_id: str) -> NPCSchedule | None:
        return self._schedules.get(npc_id)

    def get_merchant_route(self, npc_id: str) -> MerchantRoute | None:
        return self._merchant_routes.get(npc_id)

    def get_active_npcs(self, phase: TimePhase) -> list[NPCSchedule]:
        """指定フェーズでアクティブなNPC一覧取得"""
        return [s for s in self._schedules.values() if phase in s.active_phases]

    def get_active_npc_ids(self, phase: TimePhase) -> list[str]:
        """指定フェーズでアクティブなNPC ID一覧取得"""
        return [s.npc_id for s in self._schedules.values() if phase in s.active_phases]

    def get_merchant_location(self, npc_id: str, phase: TimePhase) -> str:
        """移動商人の現在地取得"""
        route = self._merchant_routes.get(npc_id)
        if route:
            return route.get_current_location(phase)
        schedule = self._schedules.get(npc_id)
        if schedule:
            return schedule.location
        return ""

    # --- 条件チェック ---
    def check_conditions(self, schedule: NPCSchedule, player: Any) -> bool:
        """出現条件チェック"""
        if not schedule.conditions:
            return True

        for key, value in schedule.conditions.items():
            if key == "faction_reputation":
                # 派閥評判チェック
                faction_id = value.get("faction")
                min_rep = value.get("min", 0)
                if not player:
                    return False
                rep = player.faction_reputation.get(faction_id, 0)
                if rep < min_rep:
                    return False

            elif key == "player_level":
                min_level = value.get("min", 1)
                if not player or player.level < min_level:
                    return False

            elif key == "quest_flag":
                flag = value.get("flag")
                required = value.get("value", True)
                if not player:
                    return False
                player_value = player.story_variables.get(flag)
                if player_value != required:
                    return False

            elif key == "time_window":
                # 時間帯指定 (既にフェーズで判定済みなので追加チェック用)
                pass

        return True

    # --- YAML読み込み ---
    def load_from_yaml(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            return

        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # NPCスケジュール
        for npc_data in data.get("npc_schedules", []):
            phases = []
            for phase_str in npc_data.get("active_phases", []):
                try:
                    phases.append(TimePhase[phase_str.upper()])
                except KeyError:
                    pass

            schedule = NPCSchedule(
                npc_id=npc_data["npc_id"],
                name=npc_data.get("name", npc_data["npc_id"]),
                active_phases=phases,
                location=npc_data.get("location", ""),
                conditions=npc_data.get("conditions", {}),
                raid_chance=npc_data.get("raid_chance", 0.0),
            )
            self.register(schedule)

        # 移動商人ルート
        for route_data in data.get("merchant_routes", []):
            stops = []
            for stop in route_data.get("stops", []):
                try:
                    phase = TimePhase[stop["phase"].upper()]
                    stops.append((phase, stop["location"]))
                except KeyError:
                    pass

            route = MerchantRoute(
                npc_id=route_data["npc_id"],
                name=route_data.get("name", route_data["npc_id"]),
                stops=stops,
            )
            self.register_merchant_route(route)

    # --- セーブ/ロード ---
    def to_dict(self) -> dict:
        return {
            "schedules": {
                npc_id: {
                    "npc_id": s.npc_id,
                    "name": s.name,
                    "active_phases": [p.name for p in s.active_phases],
                    "location": s.location,
                    "conditions": s.conditions,
                    "raid_chance": s.raid_chance,
                }
                for npc_id, s in self._schedules.items()
            },
            "merchant_routes": {
                npc_id: {
                    "npc_id": r.npc_id,
                    "name": r.name,
                    "stops": [{"phase": p.name, "location": loc} for p, loc in r.stops],
                }
                for npc_id, r in self._merchant_routes.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> NPCScheduleRegistry:
        registry = cls()
        for npc_id, s_data in data.get("schedules", {}).items():
            phases = []
            for phase_str in s_data.get("active_phases", []):
                try:
                    phases.append(TimePhase[phase_str])
                except KeyError:
                    pass
            schedule = NPCSchedule(
                npc_id=s_data["npc_id"],
                name=s_data["name"],
                active_phases=phases,
                location=s_data["location"],
                conditions=s_data.get("conditions", {}),
                raid_chance=s_data.get("raid_chance", 0.0),
            )
            registry.register(schedule)

        for npc_id, r_data in data.get("merchant_routes", {}).items():
            stops = []
            for stop in r_data.get("stops", []):
                try:
                    phase = TimePhase[stop["phase"]]
                    stops.append((phase, stop["location"]))
                except KeyError:
                    pass
            route = MerchantRoute(
                npc_id=r_data["npc_id"],
                name=r_data["name"],
                stops=stops,
            )
            registry.register_merchant_route(route)

        return registry
