"""
Facility System
Steps 29-33: FacilityType, FacilitySchedule, Registry
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

try:
    from naRou.time_system import TimePhase
except ImportError:
    from time_system import TimePhase


class FacilityType(Enum):
    """施設タイプ"""
    LAB = "lab"              # 研究室
    WORKSHOP = "workshop"    # 工房
    MEDICAL_BAY = "medical_bay"  # 医療ベイ
    ARENA = "arena"          # 闘技場
    SHOP = "shop"            # 店
    GUILD = "guild"          # ギルド


@dataclass
class FacilitySchedule:
    """施設稼働スケジュール"""
    facility_id: str
    name: str
    facility_type: FacilityType
    base_efficiency: float = 1.0
    phase_modifiers: dict[TimePhase, float] = field(default_factory=dict)
    is_24h: bool = False
    active_phases: list[TimePhase] = field(default_factory=list)
    conditions: dict[str, Any] = field(default_factory=dict)


class FacilityRegistry:
    """施設レジストリ (シングルトン)"""

    _instance: FacilityRegistry | None = None

    def __new__(cls) -> FacilityRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._facilities: dict[str, FacilitySchedule] = {}
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_facilities"):
            self._facilities = {}

    # --- 登録 ---
    def register(self, schedule: FacilitySchedule) -> None:
        self._facilities[schedule.facility_id] = schedule

    # --- 取得 ---
    def get_facility(self, facility_id: str) -> FacilitySchedule | None:
        return self._facilities.get(facility_id)

    def get_all_facilities(self) -> list[FacilitySchedule]:
        return list(self._facilities.values())

    def get_facilities_by_type(self, facility_type: FacilityType) -> list[FacilitySchedule]:
        return [f for f in self._facilities.values() if f.facility_type == facility_type]

    # --- 効率計算 ---
    def get_efficiency(self, facility_id: str, phase: TimePhase) -> float:
        """指定フェーズでの施設効率取得"""
        facility = self._facilities.get(facility_id)
        if not facility:
            return 0.0

        # 24時間施設は常に基本効率
        if facility.is_24h:
            return facility.base_efficiency

        # 非アクティブフェーズ
        if facility.active_phases and phase not in facility.active_phases:
            return 0.0

        # フェーズ修正値適用
        modifier = facility.phase_modifiers.get(phase, 1.0)
        return facility.base_efficiency * modifier

    def is_active(self, facility_id: str, phase: TimePhase) -> bool:
        """施設が稼働中か判定"""
        return self.get_efficiency(facility_id, phase) > 0

    # --- YAML読み込み ---
    def load_from_yaml(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            return

        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        for fac_data in data.get("facilities", []):
            facility_type = FacilityType(fac_data.get("type", "shop"))

            phases = []
            for phase_str in fac_data.get("active_phases", []):
                try:
                    phases.append(TimePhase[phase_str.upper()])
                except KeyError:
                    pass

            modifiers = {}
            for phase_str, value in fac_data.get("phase_modifiers", {}).items():
                try:
                    modifiers[TimePhase[phase_str.upper()]] = float(value)
                except KeyError:
                    pass

            schedule = FacilitySchedule(
                facility_id=fac_data["facility_id"],
                name=fac_data.get("name", fac_data["facility_id"]),
                facility_type=facility_type,
                base_efficiency=fac_data.get("base_efficiency", 1.0),
                phase_modifiers=modifiers,
                is_24h=fac_data.get("is_24h", False),
                active_phases=phases,
                conditions=fac_data.get("conditions", {}),
            )
            self.register(schedule)

    # --- セーブ/ロード ---
    def to_dict(self) -> dict:
        return {
            "facilities": {
                fid: {
                    "facility_id": f.facility_id,
                    "name": f.name,
                    "type": f.facility_type.value,
                    "base_efficiency": f.base_efficiency,
                    "phase_modifiers": {p.name: v for p, v in f.phase_modifiers.items()},
                    "is_24h": f.is_24h,
                    "active_phases": [p.name for p in f.active_phases],
                    "conditions": f.conditions,
                }
                for fid, f in self._facilities.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> FacilityRegistry:
        registry = cls()
        for fid, f_data in data.get("facilities", {}).items():
            facility_type = FacilityType(f_data.get("type", "shop"))

            phases = []
            for phase_str in f_data.get("active_phases", []):
                try:
                    phases.append(TimePhase[phase_str])
                except KeyError:
                    pass

            modifiers = {}
            for phase_str, value in f_data.get("phase_modifiers", {}).items():
                try:
                    modifiers[TimePhase[phase_str]] = float(value)
                except KeyError:
                    pass

            schedule = FacilitySchedule(
                facility_id=f_data["facility_id"],
                name=f_data["name"],
                facility_type=facility_type,
                base_efficiency=f_data.get("base_efficiency", 1.0),
                phase_modifiers=modifiers,
                is_24h=f_data.get("is_24h", False),
                active_phases=phases,
                conditions=f_data.get("conditions", {}),
            )
            registry.register(schedule)

        return registry
