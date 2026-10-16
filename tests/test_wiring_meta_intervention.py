"""改善案6 機能1: メタ介入 (meta intervention) のゲームループ配線テスト。

配線対象:
- WorldAPackage が InterventionEngine に実体の rule_engine / meta_state を渡す
  (None のままでは apply_rewards が AttributeError でクラッシュする)。
- GameLoopHandler が Aの世界の turn 進行でテンプレートイベントを発生させ、
  介入されないまま期限が過ぎたイベントを完遂扱いで消す。
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from naRou.skill_eater.skill_eater_meta_intervention_system import (
    InterventionAction,
    TemplateEventGenerator,
)
from naRou.skill_eater.skill_eater_template_model import load_templates

from skill_eater_audio_system import SkillEaterAudioSystem
from skill_eater_meta_quest_system import ReincarnationMetaState
from skill_eater_presentation_system import SkillEaterPresentationSystem


class MockPlayer:
    """InterventionEngine が触る属性だけを持つプレイヤー代替。"""

    def __init__(self):
        self.gold = 1000
        self.skills = set()
        self.karma_good_evil = 0
        self.template_exposure = 0

    def has_skill(self, skill_id: str) -> bool:
        return skill_id in self.skills

    def add_skill(self, skill_id: str):
        self.skills.add(skill_id)


class _ExplorationStub:
    """ループ配線が参照する探索システム側の最小属性。"""

    def __init__(self):
        self.current_room_id = "underground_market"

        class _Rank:
            rank = 3

        self.exploration_rank = _Rank()


class _GameStateStub:
    def __init__(self, world: str):
        self.current_world = world


class _KernelStub:
    def __init__(self, systems: dict):
        self._systems = systems

    def get_system(self, name, default=None):
        return self._systems.get(name, default)

    def has_system(self, name: str) -> bool:
        return name in self._systems


class _EngineStub:
    def __init__(self, systems: dict, world: str = "skill_eater"):
        self.kernel = _KernelStub(systems)
        self.game_state_data = _GameStateStub(world)
        self.turns = 0
        self.logs: list[tuple[str, tuple, str]] = []

    def log(self, msg, color=(255, 255, 255), level="INFO"):
        self.logs.append((msg, color, level))


def _kernel_systems() -> dict:
    gen = TemplateEventGenerator(load_templates("data/templates"), rng=random.Random(42))
    pres = SkillEaterPresentationSystem(
        audio_system=SkillEaterAudioSystem(enable_real_audio=False), is_mock_only=True
    )
    explore = _ExplorationStub()
    return {
        "skill_eater_meta_intervention": gen,
        "skill_eater_presentation_system": pres,
        "skill_eater_exploration_system": explore,
    }


# --- 配線 1: kernel 登録時の meta_state / rule_engine 束縛 ---


def test_world_a_binds_meta_state_and_rule_engine():
    from packages.core.kernel.kernel import Kernel
    from packages.world_a.package import WorldAPackage

    os_env = pytest.importorskip("os")
    os_env.environ["NAROU_HEADLESS"] = "1"
    kernel = Kernel()
    WorldAPackage().setup(kernel)

    engine = kernel.get_system("skill_eater_intervention_engine")
    assert engine is not None
    assert engine.meta_state is not None
    assert engine.rule_engine is not None
    assert isinstance(engine.meta_state, ReincarnationMetaState)


def test_meta_state_registered_in_kernel():
    import os

    from packages.core.kernel.kernel import Kernel
    from packages.world_a.package import WorldAPackage

    os.environ["NAROU_HEADLESS"] = "1"
    kernel = Kernel()
    WorldAPackage().setup(kernel)
    meta_state = kernel.get_system("skill_eater_meta_state")
    assert isinstance(meta_state, ReincarnationMetaState)


def test_intervention_via_exploration_applies_rewards():
    """探索システム経由の介入が報酬適用までクラッシュせず通る。"""
    import os

    from packages.core.kernel.kernel import Kernel
    from packages.world_a.package import WorldAPackage

    os.environ["NAROU_HEADLESS"] = "1"
    kernel = Kernel()
    WorldAPackage().setup(kernel)

    gen = kernel.get_system("skill_eater_meta_intervention")
    explore = kernel.get_system("skill_eater_exploration_system")
    engine = kernel.get_system("skill_eater_intervention_engine")
    gen.rng = random.Random(42)  # 決定化 (最初の roll で expel が確定する)
    engine.rng = random.Random(1)  # 常に成功

    event = gen.maybe_spawn("slum", 10, 1, spawn_chance=1.0)
    assert event is not None
    explore.active_template_events.append(event)

    player = MockPlayer()
    result = explore.trigger_intervention(event, InterventionAction(tier=1, window_id="buy_cheap"), player)
    assert result is not None
    assert result.success is True
    meta_state = kernel.get_system("skill_eater_meta_state")
    assert meta_state.total_karma_points > 0


# --- 配線 2: ゲームループのテンプレートイベント進行 ---


def _make_handler(systems: dict, world: str = "skill_eater"):
    from engine.systems.game_loop import GameLoopHandler

    engine = _EngineStub(systems, world)
    handler = GameLoopHandler(engine)
    # 決定化: 最初の判定で必ず発生させる
    handler._template_spawn_chance = 1.0
    handler._template_event_cadence_turns = 20
    handler._template_event_lifetime_turns = 40
    return handler, engine


def test_game_loop_spawns_template_event_on_cadence():
    handler, engine = _make_handler(_kernel_systems())
    engine.turns = 20
    handler._tick_skill_eater_template_events()

    assert len(handler._loop_template_events) == 1
    event = handler._loop_template_events[0]
    assert event.archetype  # expel / betray など
    assert event.turn_spawned == 20
    assert any("テンプレ" in msg for msg, _c, _l in engine.logs)


def test_game_loop_expires_unintervened_template_event():
    handler, engine = _make_handler(_kernel_systems())
    engine.turns = 20
    handler._tick_skill_eater_template_events()
    assert len(handler._loop_template_events) == 1

    engine.turns = 20 + 40  # 期限 (40) 経過
    handler._tick_skill_eater_template_events()
    assert handler._loop_template_events == []
    assert any("完遂" in msg for msg, _c, _l in engine.logs)


def test_game_loop_skips_non_skill_eater_world():
    handler, engine = _make_handler(_kernel_systems(), world="main")
    engine.turns = 20
    handler._tick_skill_eater_template_events()
    assert handler._loop_template_events == []


def test_game_loop_no_spawn_off_cadence():
    handler, engine = _make_handler(_kernel_systems())
    engine.turns = 21  # 20 刻みではない
    handler._tick_skill_eater_template_events()
    assert handler._loop_template_events == []
