"""Template data model for meta intervention system."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RouteStep:
    flag: str
    turn: int
    actor: str
    on_fail: str


@dataclass
class ExploitWindow:
    id: str
    tier: int
    req_gold: int = 0
    req_skill: list[str] = field(default_factory=list)
    base_success: float = 0.5


@dataclass
class TemplateReward:
    karma_t1: int = 0
    karma_t2: int = 0
    stealable_skill: str = ""


@dataclass
class TemplateData:
    id: str
    archetype: str
    contexts: list[str]
    faction_weight: dict[str, float]
    route_steps: list[RouteStep]
    exploit_windows: list[ExploitWindow]
    reward: TemplateReward

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TemplateData:
        route_steps = [RouteStep(**rs) for rs in data.get("route_steps", [])]
        exploit_windows = [ExploitWindow(**ew) for ew in data.get("exploit_windows", [])]
        reward = TemplateReward(**data.get("reward", {}))
        return cls(
            id=data["id"],
            archetype=data["archetype"],
            contexts=data.get("contexts", []),
            faction_weight=data.get("faction_weight", {}),
            route_steps=route_steps,
            exploit_windows=exploit_windows,
            reward=reward,
        )


def load_templates(dir_path: str | Path) -> dict[str, TemplateData]:
    """Load all template YAML files from directory."""
    path = Path(dir_path)
    templates: dict[str, TemplateData] = {}
    for yaml_file in path.glob("*.yaml"):
        with yaml_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data:
            template = TemplateData.from_dict(data)
            templates[template.id] = template
    return templates
