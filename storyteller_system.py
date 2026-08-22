"""
Procedural Storyteller System Module (Steps 33-40)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml
from typing_extensions import Self

if TYPE_CHECKING:
    from ecs.entity import Entity


# Step 37: ChoiceConsequenceData
@dataclass
class ChoiceConsequenceData:
    """選択肢結果データ (Step 37)"""

    id: str
    description: str = ""
    immediate_effects: list[dict[str, Any]] = field(default_factory=list)
    long_term_effects: list[dict[str, Any]] = field(default_factory=list)
    world_state_changes: dict[str, Any] = field(default_factory=dict)


# Step 36: StoryChoiceData
@dataclass
class StoryChoiceData:
    """ストーリー選択肢データ (Step 36)"""

    id: str
    description: str = ""
    consequence: str = ""


# Step 35: StoryChapterData
@dataclass
class StoryChapterData:
    """ストーリー章データ (Step 35)"""

    id: str
    name: str = ""
    type: str = "dungeon_incursion"
    objectives: dict[str, Any] = field(default_factory=dict)
    choices: list[StoryChoiceData] = field(default_factory=list)


# Step 34: StoryScenarioData
@dataclass
class StoryScenarioData:
    """プロシージャルシナリオデータ (Step 34)"""

    id: str
    name: str = ""
    description: str = ""
    chapters: list[StoryChapterData] = field(default_factory=list)


# Step 38, 39: StorytellerRegistry
class StorytellerRegistry:
    """ストーリーテラーレジストリ (Step 38, 39)"""

    _instance: StorytellerRegistry | None = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._scenarios = {}
        return cls._instance

    def load(self, file_path: str = "data/procedural_scenarios.yaml") -> None:
        """YAMLからプロシージャルシナリオを読み込む (Step 39)"""
        self._scenarios = {}
        if not os.path.exists(file_path):
            self._scenarios["goblin_invasion"] = StoryScenarioData(
                id="goblin_invasion",
                name="ゴブリンの侵略",
                description="ゴブリン部隊の襲撃",
            )
            return

        with open(file_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        s_dict = raw.get("scenario_templates", {})
        for sid, sdata in s_dict.items():
            chapters = []
            for ch in sdata.get("chapters", []):
                choices = [
                    StoryChoiceData(
                        c.get("id", ""),
                        c.get("description", ""),
                        c.get("consequence", ""),
                    )
                    for c in ch.get("choices", [])
                ]
                chapters.append(
                    StoryChapterData(
                        id=ch.get("id", ""),
                        name=ch.get("name", ""),
                        type=ch.get("type", "dungeon_incursion"),
                        objectives=ch.get("objectives", {}),
                        choices=choices,
                    )
                )

            self._scenarios[sid] = StoryScenarioData(
                id=sid,
                name=sdata.get("name", sid),
                description=sdata.get("description", ""),
                chapters=chapters,
            )

    def get(self, scenario_id: str) -> StoryScenarioData | None:
        return self._scenarios.get(scenario_id)

    def all_scenarios(self) -> dict[str, StoryScenarioData]:
        return dict(self._scenarios)


REGISTRY = StorytellerRegistry()


# Step 40: StorytellerManager
class StorytellerManager:
    """ストーリーテラー進行・判定管理 (Step 40)"""

    def __init__(self, registry: StorytellerRegistry | None = None):
        self.registry = registry or REGISTRY

    def check_scenario_triggers(
        self, player: Entity, engine: Any | None = None
    ) -> list[StoryScenarioData]:
        """発生可能なシナリオを判定 (Step 40)"""
        available = []
        for sid, scen in self.registry.all_scenarios().items():
            if sid not in player.completed_storylines and sid not in player.available_storylines:
                available.append(scen)
                player.available_storylines.append(sid)
        return available

    def activate_scenario(
        self, player: Entity, scenario_id: str, engine: Any | None = None
    ) -> bool:
        """シナリオを開始・進行 (Step 40)"""
        scen = self.registry.get(scenario_id)
        if not scen or not player:
            return False

        player.story_flags[f"{scenario_id}_active"] = True
        if engine:
            from sound_manager import SoundManager

            SoundManager.play_se("level_up")
            engine.log(
                f"📖【物語の幕開け】シナリオ「{scen.name}」が開始された！",
                (255, 215, 0),
            )

        return True

    def process_choice(self, player: Entity, choice_id: str, engine: Any | None = None) -> bool:
        """選択肢の決定を処理 (Step 40)"""
        if choice_id not in player.story_choices_made:
            player.story_choices_made.append(choice_id)

        from choice_system import REGISTRY as CHOICE_REG
        from choice_system import ChoiceManager

        cmgr = ChoiceManager(CHOICE_REG)
        CHOICE_REG.load()
        return cmgr.apply_consequence(player, choice_id, engine)
