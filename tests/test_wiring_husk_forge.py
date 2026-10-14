"""改善案6 機能2: Husk 鍛冶 (Puppet Forge) のゲームフロー配線テスト。

配線対象:
- 喰らいで抜け殻 (is_husk) になった敵の撃破時に HuskComponent が
  プレイヤーの HuskInventoryComponent へ入る (feature flag で gate)。
- engine.execute_husk_forge が鍛冶 (スキル注入 → ユニット生成 → 抜け殻消費) を行う。
- WorldAPackage が PuppetForgeSystem を kernel へ登録する。
- naRou.skill_eater_husk_ui の UI 関数が ECS (get_component) のプレイヤーで動く。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from naRou.ecs.components.components import HuskInventoryComponent
from naRou.ecs.entity import Entity
from naRou.feature_flags import set_flag
from naRou.skill_eater.skill_eater_husk_system import create_husk


class _CombatHandlerStub:
    def __init__(self):
        self.killed: list = []

    def handle_kill(self, entity):
        self.killed.append(entity)


class _KernelStub:
    def __init__(self, systems: dict | None = None):
        self._systems = dict(systems or {})

    def get_system(self, name, default=None):
        return self._systems.get(name, default)

    def has_system(self, name: str) -> bool:
        return name in self._systems


class _GameStateStub:
    def __init__(self, player):
        self.player = player


def _make_engine(player: Entity, systems: dict | None = None):
    import engine.engine as engine_mod

    engine = engine_mod.Engine.__new__(engine_mod.Engine)
    engine.kernel = _KernelStub(systems)
    engine.combat_handler = _CombatHandlerStub()
    engine.game_state_data = _GameStateStub(player)
    engine.logs: list[str] = []

    def log(msg, color=(255, 255, 255), level="INFO"):
        engine.logs.append(str(msg))

    engine.log = log
    return engine


def _make_player_with_husk(husk=None) -> Entity:
    player = Entity(name="テストプレイヤー", is_player=True)
    inv = player.get_component(HuskInventoryComponent)
    if husk is not None:
        inv.husks.append(husk)
    return player


@pytest.fixture
def husk_flag_on():
    set_flag("ENABLE_HUSK_PUPPET_HACKING", True)
    yield
    set_flag("ENABLE_HUSK_PUPPET_HACKING", False)


# --- 配線 1: 撃破時の抜け殻入手 ---


@pytest.mark.xfail(strict=True, reason="未配線: is_husk 敵の撃破で Husk を入手できない")
def test_kill_of_husk_entity_grants_husk(husk_flag_on):
    player = _make_player_with_husk()
    engine = _make_engine(player)

    corpse = Entity(name="テストスライム", is_player=False)
    corpse.is_husk = True
    corpse.level = 2
    engine._on_kill(corpse)

    inv = player.get_component(HuskInventoryComponent)
    assert len(inv.husks) == 1
    assert inv.husks[0].source_monster == "テストスライム"
    assert inv.husks[0].slots == 2


def test_husk_acquisition_gated_by_flag():
    player = _make_player_with_husk()
    engine = _make_engine(player)
    corpse = Entity(name="テストスライム", is_player=False)
    corpse.is_husk = True
    corpse.level = 2

    engine._on_kill(corpse)  # フラグ OFF
    assert player.get_component(HuskInventoryComponent).husks == []


def test_normal_kill_does_not_grant_husk(husk_flag_on):
    player = _make_player_with_husk()
    engine = _make_engine(player)
    corpse = Entity(name="ただのゴブリン", is_player=False)
    corpse.level = 1

    engine._on_kill(corpse)
    assert player.get_component(HuskInventoryComponent).husks == []


# --- 配線 2: 鍛冶の実行 ---


@pytest.mark.xfail(strict=True, reason="未配線: execute_husk_forge が存在しない")
def test_execute_husk_forge_creates_unit_and_consumes_husk(husk_flag_on):
    husk = create_husk("テストスライム", 2)
    player = _make_player_with_husk(husk)
    engine = _make_engine(player)

    ok = engine.execute_husk_forge(skill="fire_bolt")
    assert ok is True

    inv = player.get_component(HuskInventoryComponent)
    assert inv.husks == []  # 抜け殻はユニット化で消費される
    assert any("鍛冶" in m or "unit" in m.lower() for m in engine.logs)


@pytest.mark.xfail(strict=True, reason="未配線: execute_husk_forge が存在しない")
def test_execute_husk_forge_without_husks_fails_gracefully(husk_flag_on):
    player = _make_player_with_husk()
    engine = _make_engine(player)
    assert engine.execute_husk_forge() is False


@pytest.mark.xfail(strict=True, reason="未配線: execute_husk_forge が存在しない")
def test_execute_husk_forge_gated_by_flag():
    husk = create_husk("テストスライム", 2)
    player = _make_player_with_husk(husk)
    engine = _make_engine(player)
    assert engine.execute_husk_forge() is False  # フラグ OFF
    assert player.get_component(HuskInventoryComponent).husks != []  # 消費されない


# --- 配線 3: kernel 登録 ---


@pytest.mark.xfail(strict=True, reason="未配線: PuppetForgeSystem が kernel に登録されない")
def test_world_a_registers_husk_forge_system():
    import os

    os.environ["NAROU_HEADLESS"] = "1"
    from packages.core.kernel.kernel import Kernel
    from packages.world_a.package import WorldAPackage
    from naRou.skill_eater.skill_eater_husk_forge import PuppetForgeSystem

    kernel = Kernel()
    WorldAPackage().setup(kernel)
    forge = kernel.get_system("skill_eater_husk_forge")
    assert isinstance(forge, PuppetForgeSystem)


# --- 配線 4: UI 関数の ECS 対応 ---


@pytest.mark.xfail(strict=True, reason="未配線: husk UI 関数が ECS プレイヤーで動かない")
def test_husk_ui_functions_work_with_ecs_player():
    from naRou.skill_eater_husk_ui import forge_status, list_husks, ui_inject

    husk = create_husk("テストスライム", 2)
    player = _make_player_with_husk(husk)

    assert list_husks(player) == ["husk_テストスライム_2(テストスライム)"]
    ui_inject(player, "husk_テストスライム_2", "fire_bolt")
    assert husk.injected_skills == ["fire_bolt"]
    assert "load=" in forge_status(husk)
