"""
meta_goals.yaml の permanent_bonus キーについての契約テスト:

1. YAML に定義された全てのキーが「実装済み」または「明示的に予約済み」に分類されていること
2. 実装済みキーは『ゲームが実際に参照する値』を変化させ、
   その値を再計算する Entity.recalculate_stats() を経ても保持されること
3. 予約済みキーはゲーム値を一切変化させないこと（定義だけ残った嘘を置かないこと）
4. 実装済みキーについて個別の実害テスト（移動速度 / 全主能力）があること

本テストは meta_goals.yaml からキーを動的に取得する。
ハードコードしたキー一覧を持ち込まないことで、データ側と実装側の乖離を検出する。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ecs.components import AchievementComponent
from ecs.entity import Entity
from meta_progression_system import (
    APPLIED_PERMANENT_BONUS_KEYS,
    RESERVED_PERMANENT_BONUSES,
    MetaGoalData,
    MetaProgressionManager,
    MetaProgressionRegistry,
)

META_GOALS_PATH = Path(__file__).resolve().parent.parent / "data" / "meta_goals.yaml"

# ゲーム中に観測される値（ボーナスで変化しうるもの）
_SCALAR_FIELDS = (
    "speed",
    "max_hp",
    "max_mp",
    "max_stamina",
    "hp",
    "mp",
    "stamina",
    "exp",
    "job_exp",
    "level",
    "skill_points",
    "karma_law_chaos",
    "karma_good_evil",
)
_ATTRIBUTE_FIELDS = (
    "strength",
    "endurance",
    "dexterity",
    "perception",
    "learning",
    "will",
    "magic",
    "charisma",
)
_RESISTANCE_FIELDS = ("fire", "cold", "lightning", "darkness", "chaos", "magic")


def _load_yaml_text() -> str:
    return META_GOALS_PATH.read_text(encoding="utf-8")


def _load_yaml_goals() -> dict:
    return yaml.safe_load(_load_yaml_text())["meta_goals"]


def _bonus_keys_from_yaml() -> set[str]:
    """meta_goals.yaml から permanent_bonus のキーを動的に抽出する"""
    keys: set[str] = set()
    for goal in _load_yaml_goals().values():
        keys.update((goal.get("permanent_bonus") or {}).keys())
    return keys


def _bonus_values_from_yaml() -> dict[str, float]:
    """キー -> YAML上の値 の対応表を動的に構築する"""
    values: dict[str, float] = {}
    for goal in _load_yaml_goals().values():
        for key, value in (goal.get("permanent_bonus") or {}).items():
            values[key] = float(value)
    return values


def _yaml_block_of_key(key: str) -> str:
    """指定キー行と、その直上にある連続コメント行のテキスト（予約コメント判定用）"""
    lines = _load_yaml_text().splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith(f"{key}:"):
            block = [line]
            for previous in reversed(lines[:index]):
                stripped = previous.strip()
                if stripped.startswith("#"):
                    block.insert(0, previous)
                else:
                    break
            return "\n".join(block)
    raise AssertionError(f"meta_goals.yaml に {key} がありません")


def _gameplay_snapshot(player: Entity) -> dict[str, object]:
    """ボーナスで変化しうるゲーム値のスナップショットを取得する"""
    snap: dict[str, object] = {name: getattr(player, name, None) for name in _SCALAR_FIELDS}
    for name in _ATTRIBUTE_FIELDS:
        snap[f"attr.{name}"] = getattr(player.attributes, name)
    resistances = getattr(player, "resistances", None)
    for name in _RESISTANCE_FIELDS:
        snap[f"res.{name}"] = getattr(resistances, name, None)
    for skill_key, skill in getattr(player, "skills", {}).items():
        snap[f"skill.{skill_key}.potential"] = skill.potential
        snap[f"skill.{skill_key}.experience"] = skill.experience
    return snap


def _changed_fields(before: dict[str, object], after: dict[str, object]) -> set[str]:
    return {name for name, value in before.items() if after[name] != value}


def _probe_effect(reg: MetaProgressionRegistry, key: str, value: float) -> set[str]:
    """
    1つの permanent_bonus キーだけを付与し、
    Entity.recalculate_stats()（ゲーム内で実際に呼ばれる再計算）を経て
    なお変化しているフィールド名集合を返す。
    """
    reg.meta_goals = {
        "probe": MetaGoalData(
            id="probe",
            name="プローブ",
            description="",
            target_metric="probe_metric",
            target_value=1,
            permanent_bonus={key: value},
        )
    }
    manager = MetaProgressionManager(registry=reg)
    player = Entity(name="BonusProbe")

    # ボーナス無し（引擎初期化時と同じ再計算経路を通す）
    manager.recalculate_and_apply_bonuses(player)
    player.recalculate_stats()
    baseline = _gameplay_snapshot(player)

    player.get_component(AchievementComponent).meta_progression["probe"] = 1
    manager.recalculate_and_apply_bonuses(player)
    player.recalculate_stats()
    return _changed_fields(baseline, _gameplay_snapshot(player))


@pytest.fixture
def registry_guard():
    """REGISTRY はシングルトンのためテスト間で内容を退避・復元する"""
    reg = MetaProgressionRegistry()
    saved = (dict(reg.meta_goals), list(reg.cycle_modifiers), dict(reg.fragment_templates))
    yield reg
    reg.meta_goals, reg.cycle_modifiers, reg.fragment_templates = saved


@pytest.fixture
def effective_keys(registry_guard) -> set[str]:
    """『実装，且つ再計算後も実ゲーム値に残っている』キー集合"""
    values = _bonus_values_from_yaml()
    return {key for key, value in values.items() if _probe_effect(registry_guard, key, value)}


def test_yaml_defines_permanent_bonus_keys():
    """前提確認: YAML から permanent_bonus キーを取得できていること"""
    assert _bonus_keys_from_yaml(), "meta_goals.yaml に permanent_bonus が定義されていません"


def test_every_bonus_key_is_applied_or_reserved(registry_guard):
    """
    YAML の permanent_bonus キーは全て『実装済み』または『明示的に予約済み』に分類されている。
    どちらにも属さないキー（定義されたが読まれないキー）が 1 つも無いことを保証する。
    """
    yaml_keys = _bonus_keys_from_yaml()
    applied = set(APPLIED_PERMANENT_BONUS_KEYS)
    reserved = set(RESERVED_PERMANENT_BONUSES)

    assert applied & reserved == set(), "同じキーが実装済みと予約済みの両方に分類されています"
    assert applied | reserved == yaml_keys, (
        "分類されていない permanent_bonus キーがあります: "
        f"{sorted(yaml_keys - (applied | reserved))}"
    )


def test_reserved_keys_have_reason(registry_guard):
    """予約済みキーには『何が欠けているか』の理由が必ず書かれていること"""
    for key, reason in RESERVED_PERMANENT_BONUSES.items():
        assert reason.strip(), f"予約理由が空です: {key}"


def test_reserved_keys_are_documented_in_yaml():
    """予約済みキーは YAML 側にも『予約』コメントで明示されていること"""
    for key in RESERVED_PERMANENT_BONUSES:
        assert "予約" in _yaml_block_of_key(key), f"YAML の {key} に予約コメントがありません"


def test_reserved_keys_have_no_gameplay_effect(effective_keys):
    """
    予約済みキーはゲーム値を変化させてはならない。
    変化するなら『予約』ではなく実装済みであるべき。
    """
    leaked = set(RESERVED_PERMANENT_BONUSES) & effective_keys
    assert leaked == set(), f"予約済みキーがゲーム値に影響しています: {sorted(leaked)}"


def test_applied_keys_have_survivable_gameplay_effect(effective_keys):
    """
    実装済みと宣言されたキーは、実際にゲーム値を変化させ、
    Entity.recalculate_stats() で打ち消されないことを確認する。
    """
    missing = set(APPLIED_PERMANENT_BONUS_KEYS) - effective_keys
    assert missing == set(), (
        f"実装済みと宣言されたキーが実ゲーム値に影響しません: {sorted(missing)}"
    )


def test_no_bonus_key_is_silently_ignored(effective_keys):
    """
    YAML に存在するキーのうち『ゲーム値に影響しない』ものは
    全て予約済みとして明示されていること（黙って無視されるキーが無いこと）。
    """
    yaml_keys = _bonus_keys_from_yaml()
    silent = yaml_keys - effective_keys
    assert silent == set(RESERVED_PERMANENT_BONUSES), (
        "ゲーム値に影響しないのに予約されていないキーがあります: "
        f"{sorted(silent - set(RESERVED_PERMANENT_BONUSES))}"
    )


def test_speed_bonus_is_applied_to_player_speed(registry_guard):
    """speed: 新しい周回ではプレイヤーの移動速度が_yaml上の値だけ上がること"""
    player = Entity(name="SpeedProbe")
    manager = MetaProgressionManager(registry=registry_guard)
    manager.recalculate_and_apply_bonuses(player)
    base_speed = player.speed

    for goal in _load_yaml_goals().values():
        bonus = goal.get("permanent_bonus") or {}
        if "speed" in bonus:
            player.get_component(AchievementComponent).meta_progression[goal["id"]] = 1
    manager.recalculate_and_apply_bonuses(player)

    expected = sum(
        float(b["speed"])
        for b in (_load_yaml_goals()[g].get("permanent_bonus") or {} for g in _load_yaml_goals())
        if "speed" in b
    )
    assert player.speed == base_speed + expected


def test_speed_bonus_changes_turn_order():
    """speed: 実際の TurnQueue で手番に差が出ることを実証する（エネルギーが speed ずつ蓄積する）"""
    from turn_manager import TimeSystem, TurnQueue

    bonus = _bonus_values_from_yaml()["speed"]
    queue = TurnQueue(TimeSystem())

    def surplus_after_acting(speed: float) -> float:
        """行動可能になるまで溜まったエネルギー（行動時に threshold 分を消費する）"""
        hero = Entity(name="Hero", speed=speed)
        hero.hp = hero.max_hp
        hero.energy = 0
        actor, _ = queue.step_next_actor([hero])
        assert actor is hero
        return hero.energy

    # 速度が高いほど行動時の余剰エネルギーが多くなり、次の行動に有利になる
    assert surplus_after_acting(70 + bonus) > surplus_after_acting(70)

    # エネルギー蓄積量が同じなら、速度の速い側が手番を先取る
    slow = Entity(name="Slime", speed=70)
    slow.hp = slow.max_hp
    slow.energy = 1000
    fast = Entity(name="Hero", speed=70 + bonus)
    fast.hp = fast.max_hp
    fast.energy = 1000
    assert queue.step_next_actor([slow, fast])[0] is fast


def test_all_attributes_bonus_is_applied_to_attributes(registry_guard):
    """all_attributes: 全8主能力が_yaml上の値だけ上がること"""
    player = Entity(name="AttrProbe")
    manager = MetaProgressionManager(registry=registry_guard)
    manager.recalculate_and_apply_bonuses(player)
    base = {name: getattr(player.attributes, name) for name in _ATTRIBUTE_FIELDS}

    for goal in _load_yaml_goals().values():
        bonus = goal.get("permanent_bonus") or {}
        if "all_attributes" in bonus:
            player.get_component(AchievementComponent).meta_progression[goal["id"]] = 1
    manager.recalculate_and_apply_bonuses(player)

    expected = _bonus_values_from_yaml()["all_attributes"]
    for name in _ATTRIBUTE_FIELDS:
        assert getattr(player.attributes, name) == base[name] + expected, (
            f"{name} が加算されていません"
        )


def test_all_attributes_bonus_survives_recalculate_stats(registry_guard):
    """
    all_attributes: Entity.recalculate_stats()（レベルアップ・ジョブ・称号で呼ばれる）
    が属性を _base_attributes から復元してもボーナスが残ること。
    """
    player = Entity(name="AttrProbe")
    manager = MetaProgressionManager(registry=registry_guard)
    manager.recalculate_and_apply_bonuses(player)
    player.get_component(AchievementComponent).meta_progression["reincarnation_master"] = 1
    manager.recalculate_and_apply_bonuses(player)
    player.recalculate_stats()

    expected = _bonus_values_from_yaml()["all_attributes"]
    for name in _ATTRIBUTE_FIELDS:
        base_value = getattr(Entity(name="AttrBase").attributes, name)
        assert getattr(player.attributes, name) == base_value + expected, (
            f"recalculate_stats() 後に {name} のボーナスが消えています"
        )
