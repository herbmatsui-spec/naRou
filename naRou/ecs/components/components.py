from dataclasses import dataclass, field
from typing import Any


@dataclass
class HuskComponent:
    """スキルを奪われた敵の残骸（Husk）コンポーネント"""

    husk_id: str
    source_monster: str
    tier: int = 1
    decay: int = 0
    max_decay: int = 100
    corruption: int = 0
    loyalty: int = 0
    slots: int = 1
    injected_skills: list[str] = field(default_factory=list)
    injected_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "husk_id": self.husk_id,
            "source_monster": self.source_monster,
            "tier": self.tier,
            "decay": self.decay,
            "max_decay": self.max_decay,
            "corruption": self.corruption,
            "loyalty": self.loyalty,
            "slots": self.slots,
            "injected_skills": self.injected_skills,
            "injected_codes": self.injected_codes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HuskComponent":
        return cls(
            husk_id=data.get("husk_id", ""),
            source_monster=data.get("source_monster", ""),
            tier=data.get("tier", 1),
            decay=data.get("decay", 0),
            max_decay=data.get("max_decay", 100),
            corruption=data.get("corruption", 0),
            loyalty=data.get("loyalty", 0),
            slots=data.get("slots", 1),
            injected_skills=data.get("injected_skills", []),
            injected_codes=data.get("injected_codes", []),
        )


@dataclass
class HuskInventoryComponent:
    """プレイヤーが所持するHuskのリスト"""

    husks: list[HuskComponent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "husks": [husk.to_dict() for husk in self.husks]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HuskInventoryComponent":
        return cls(
            husks=[HuskComponent.from_dict(husk_data) for husk_data in data.get("husks", [])]
        )


@dataclass
class PuppetUnitComponent:
    """操り人形ユニットコンポーネント"""

    unit_id: str
    role: str
    husk_ref: str
    state: str = "sleep"
    loyalty: int = 0
    corruption: int = 0
    hp: int = 10
    max_hp: int = 10
    order: str = "follow"
    location: str = "base"
    route: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "role": self.role,
            "husk_ref": self.husk_ref,
            "state": self.state,
            "loyalty": self.loyalty,
            "corruption": self.corruption,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "order": self.order,
            "location": self.location,
            "route": self.route
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PuppetUnitComponent":
        return cls(
            unit_id=data.get("unit_id", ""),
            role=data.get("role", ""),
            husk_ref=data.get("husk_ref", ""),
            state=data.get("state", "sleep"),
            loyalty=data.get("loyalty", 0),
            corruption=data.get("corruption", 0),
            hp=data.get("hp", 10),
            max_hp=data.get("max_hp", 10),
            order=data.get("order", "follow"),
            location=data.get("location", "base"),
            route=data.get("route", [])
        )