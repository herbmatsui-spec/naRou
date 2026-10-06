"""tutorial_controller.py - チュートリアル手順の進行管理（Step 38）。

data/tutorial_steps.json を読み込み、現在の手順を返したり前後に進めたりする。

さらに data/tutorial_guides.yaml の動的ガイドについて、発動条件の判定そのものを
このモジュールが持つ（``TutorialGuideEvaluator``）。以前は各ガイドの条件を
engine/engine.py 側から個別に呼び出すしかなく、呼び出し側が無いガイドは
発動条件を満たしていても永久に発動しなかった。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ui_fx_systems import TutorialGuide


class TutorialController:
    def __init__(self, path: str = "data/tutorial_steps.json") -> None:
        self.path = Path(path)
        self.steps: list[dict[str, Any]] = self._load()
        self.index: int = 0

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []

    def current(self) -> dict[str, Any] | None:
        if 0 <= self.index < len(self.steps):
            return self.steps[self.index]
        return None

    def current_text(self) -> str:
        cur = self.current()
        return cur.get("text", "") if cur else ""

    def advance(self) -> dict[str, Any] | None:
        if self.index < len(self.steps) - 1:
            self.index += 1
        return self.current()

    def back(self) -> dict[str, Any] | None:
        if self.index > 0:
            self.index -= 1
        return self.current()

    def total(self) -> int:
        return len(self.steps)

    def is_last(self) -> bool:
        return self.index >= len(self.steps) - 1


# --- 動的ガイドの発動条件判定 ------------------------------------------------

# 空腹判定の境界は systems.SurvivalSystem.pass_turn と揃える
HUNGER_HUNGRY_THRESHOLD = 1000
HP_LOW_RATIO = 0.5
TOXICITY_WARNING_THRESHOLD = 40
SKILL_EATER_WORLD = "skill_eater"
SYNTHESIS_SKILL_MINIMUM = 2


def _world_clock(engine: Any) -> Any:
    return getattr(getattr(engine, "time_system", None), "world_clock", None)


def _active_npc_ids(clock: Any) -> tuple[str, ...]:
    """現在の時間帯に出ている NPC の ID を集める。

    ``naRou.time_system`` と ``time_system`` が別モジュールとして二重読み込みされると
    ``TimePhase`` の Enum 同一性が崩れ、公開 API の
    ``phase in schedule.active_phases`` が常に False になる。
    そのため時間帯の名称で突き合わせる。
    """
    if clock is None:
        return ()
    registry = getattr(clock, "npc_registry", None)
    if registry is None:
        return ()
    phase = getattr(clock, "current_phase", None)
    phase_name = getattr(phase, "name", None)
    if phase_name is None:
        return ()
    return tuple(
        schedule.npc_id
        for schedule in getattr(registry, "_schedules", {}).values()
        if phase_name
        in {getattr(p, "name", p) for p in getattr(schedule, "active_phases", ())}
    )


@dataclass(frozen=True)
class GuideContext:
    """1 ティック分のゲーム状態を、ガイド判定に必要な形だけに写したもの。

    evaluator はこの写しだけを見る。エンジンや各システムへ直接触らないので、
    「どの状態を条件の土台にしているか」がここから一意に読める。
    """

    run_started: bool = False
    turns: int = 0
    clock_ticks: int = 0
    active_npcs: tuple[str, ...] = ()
    hp: int = 0
    max_hp: int = 0
    hunger: int = HUNGER_HUNGRY_THRESHOLD
    dungeon_depth: int = 0
    max_dungeon_depth: int = 0
    current_world: str = ""
    toxicity: int = 0
    can_reincarnate: bool = False
    fusion_material_count: int = 0
    has_scan_result: bool = False
    devoured_skill_count: int = 0

    @classmethod
    def from_engine(cls, engine: Any) -> GuideContext:
        """実物の Engine から状態を採取する"""
        player = getattr(engine, "player", None)
        if player is None:
            return cls()
        clock = _world_clock(engine)
        toxicity_mgr = getattr(engine, "skill_eater_toxicity_manager", None)
        world_a_data = getattr(getattr(engine, "game_state_data", None), "world_a_data", None)
        survival = getattr(engine, "survival", None)
        return cls(
            run_started=getattr(engine, "game_state", "") == "play",
            turns=int(getattr(engine, "turns", 0) or 0),
            clock_ticks=int(getattr(clock, "total_ticks", 0) or 0),
            active_npcs=_active_npc_ids(clock),
            hp=int(getattr(player, "hp", 0) or 0),
            max_hp=int(getattr(player, "max_hp", 0) or 0),
            hunger=int(getattr(survival, "hunger", HUNGER_HUNGRY_THRESHOLD)),
            dungeon_depth=int(getattr(engine, "dungeon_level", 0) or 0),
            max_dungeon_depth=int(getattr(player, "max_dungeon_depth", 0) or 0),
            current_world=str(
                getattr(getattr(engine, "game_state_data", None), "current_world", "") or ""
            ),
            toxicity=int(getattr(getattr(toxicity_mgr, "state", None), "current_toxicity", 0) or 0),
            can_reincarnate=_can_reincarnate(engine, player),
            fusion_material_count=len(getattr(player, "skill_fusion_materials", None) or {}),
            has_scan_result=getattr(engine, "last_scan_result", None) is not None,
            devoured_skill_count=len(world_a_data.get("skills", ()) or ()),
        )


def _can_reincarnate(engine: Any, player: Any) -> bool:
    manager = getattr(engine, "reincarnation_manager", None)
    if manager is None:
        return False
    return bool(manager.can_reincarnate(player))


# 発動条件キー -> 判定関数。data/tutorial_guides.yaml に増える条件は
# ここに必ず evaluator を足すこと（無い条件は永久に発動しない）。
CONDITION_EVALUATORS: dict[str, Callable[[GuideContext], bool]] = {
    "game_start": lambda c: c.run_started,
    "first_action": lambda c: c.turns >= 1,
    "first_time_check": lambda c: c.clock_ticks > 0,
    "first_npc_check": lambda c: bool(c.active_npcs),
    "hp_below_50": lambda c: c.max_hp > 0 and c.hp < c.max_hp * HP_LOW_RATIO,
    "hunger_hungry": lambda c: c.hunger < HUNGER_HUNGRY_THRESHOLD,
    "reach_depth_10": lambda c: max(c.dungeon_depth, c.max_dungeon_depth) >= 10,
    "reincarnate_ready": lambda c: c.can_reincarnate,
    "open_menu_fusion": lambda c: c.fusion_material_count > 0,
    "switch_world_skill_eater": lambda c: c.current_world == SKILL_EATER_WORLD,
    "first_scan": lambda c: c.has_scan_result,
    "first_devour_attempt": lambda c: c.devoured_skill_count > 0,
    "toxicity_above_40": lambda c: c.toxicity >= TOXICITY_WARNING_THRESHOLD,
    "first_synthesis_open": lambda c: c.devoured_skill_count >= SYNTHESIS_SKILL_MINIMUM,
}


class TutorialGuideEvaluator:
    """動的ガイドの発動条件を自分で判定する。

    呼び出し側が各条件を個別に叩いていたため、呼び出しの無いガイドは
    条件を満たしていても永久に発動しなかった。ここでは全ガイドを毎ティック
    評価し、発動したものをまとめて返す。
    """

    CONDITION_EVALUATORS = CONDITION_EVALUATORS

    def __init__(self, guides_path: str = "data/tutorial_guides.yaml") -> None:
        from ui_fx_systems import TutorialManager

        self.manager = TutorialManager(guides_path)
        self.guides: dict[str, TutorialGuide] = self.manager.guides

    def unevaluable_conditions(self) -> set[str]:
        """evaluator の無い条件キーを返す（guides.yaml に足した forgot の検出用）"""
        return {g.trigger_condition for g in self.guides.values()} - set(self.CONDITION_EVALUATORS)

    def evaluate(self, context: GuideContext, completed: set[str]) -> list[TutorialGuide]:
        """未完了の発動条件を満たすガイドをすべて返す"""
        fired: list[TutorialGuide] = []
        for guide in self.guides.values():
            if guide.id in completed:
                continue
            check = self.CONDITION_EVALUATORS.get(guide.trigger_condition)
            if check is not None and check(context):
                fired.append(guide)
        return fired
