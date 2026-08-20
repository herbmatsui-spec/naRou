"""
Story Choice and Consequence System Module (Steps 41-46)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from entity import Entity


# Step 42: ChoiceConsequenceData
@dataclass
class ChoiceConsequenceData:
    """選択肢結果データ (Step 42)"""

    id: str
    description: str = ""
    immediate_effects: list[dict[str, Any]] = field(default_factory=list)
    long_term_effects: list[dict[str, Any]] = field(default_factory=list)
    world_state_changes: dict[str, Any] = field(default_factory=dict)


# Step 43, 44: ChoiceRegistry
class ChoiceRegistry:
    """選択肢結果レジストリ (Step 43, 44)"""

    _instance: ChoiceRegistry | None = None

    def __new__(cls) -> ChoiceRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._consequences = {}
        return cls._instance

    def load(self, file_path: str = "data/story_choices.yaml") -> None:
        """YAMLから選択肢結果を読み込む (Step 44)"""
        self._consequences = {}
        if not os.path.exists(file_path):
            self._consequences["farm_survivor_saved"] = ChoiceConsequenceData(
                id="farm_survivor_saved", description="農民たちを救出"
            )
            return

        with open(file_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        c_dict = raw.get("choice_consequences", {})
        for cid, cdata in c_dict.items():
            self._consequences[cid] = ChoiceConsequenceData(
                id=cid,
                description=cdata.get("description", ""),
                immediate_effects=cdata.get("immediate_effects", []),
                long_term_effects=cdata.get("long_term_effects", []),
                world_state_changes=cdata.get("world_state_changes", {}),
            )

    def get(self, consequence_id: str) -> ChoiceConsequenceData | None:
        return self._consequences.get(consequence_id)

    def all_consequences(self) -> dict[str, ChoiceConsequenceData]:
        return dict(self._consequences)


REGISTRY = ChoiceRegistry()


# Step 45, 46: ChoiceManager
class ChoiceManager:
    """選択肢結果適用管理 (Steps 45, 46)"""

    def __init__(self, registry: ChoiceRegistry | None = None):
        self.registry = registry or REGISTRY

    def get_consequence(self, consequence_id: str) -> ChoiceConsequenceData | None:
        return self.registry.get(consequence_id)

    def apply_consequence(
        self, player: Entity, consequence_id: str, engine: Any | None = None
    ) -> bool:
        """選択肢結果を適用 (Step 46)"""
        data = self.get_consequence(consequence_id)
        if not data or not player:
            return False

        # 即時効果
        for eff in data.immediate_effects:
            eff_type = eff.get("type")
            val = eff.get("value", 0)
            if eff_type == "gain_gold":
                if hasattr(player, "gold"):
                    player.gold += val
                if engine and hasattr(engine, "survival"):
                    engine.survival.gold += val
            elif eff_type == "gain_karma":
                player.karma_good_evil = max(
                    -100, min(100, player.karma_good_evil + val)
                )
            elif eff_type == "gain_exp":
                player.gain_exp(val)
            elif eff_type == "gain_piety":
                player.piety += val

        # ワールド状態変更
        for k, v in data.world_state_changes.items():
            player.story_variables[k] = v

        if engine:
            from sound_manager import SoundManager

            SoundManager.play_se("level_up")
            engine.log(f"⚖️【決断の刻】{data.description}", (255, 220, 100))

        return True
