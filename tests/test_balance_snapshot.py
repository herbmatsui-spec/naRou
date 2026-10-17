"""Balance snapshots.

Numbers the redesign will move on purpose. Each one is pinned here so that a
change is a *deliberate diff* against this file rather than a surprise three
phases later. Step 22 updates the exp row when the curve is designed; every
other update must say in the commit why the number changed.

T33 R3案C からは難易度カーブ検証を追加。「曲線の性質」(単調増加・隣接比・
プレイヤー×敵の比率帯) は data/balance_standards.yaml の difficulty_curve を
判定基準とし、「現行値の記録」は baseline.json の balance_snapshot との一致で
検証する。バランス変更を意図したときだけ
``python3 balance_tool.py --update-baseline`` でベースラインを更新する。
"""

from __future__ import annotations

import random
import statistics

import pytest
import yaml

from balance_tool import (
    ENEMY_SCALE_STEP,
    _expected_player_stats,
    _floor_monster_pool,
    compute_balance_snapshot,
    diff_balance_snapshot,
    load_balance_baseline,
)
from ecs.entity import Entity
from map_engine import GameMap

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((REPO_ROOT / "config.yaml").read_text(encoding="utf-8"))
MONSTERS = yaml.safe_load((REPO_ROOT / "data" / "monsters.yaml").read_text(encoding="utf-8"))
STANDARDS = yaml.safe_load(
    (REPO_ROOT / "data" / "balance_standards.yaml").read_text(encoding="utf-8")
)


def _player_entity() -> Entity:
    """Build the player exactly as core/world_state_manager.py:33-40 does.

    The `god_id = "jure"` line matters: calculate_max_hp grants +10 for it
    (ecs/entity.py:1157), so a player built without it is not the shipping one.
    """
    cfg = CONFIG["player"]
    entity = Entity(
        x=cfg["start_x"],
        y=cfg["start_y"],
        char=cfg["char"],
        color=tuple(cfg["color"]),
        name=cfg["name"],
        is_player=True,
        speed=cfg["speed"],
        attributes=cfg["attributes"],
    )
    entity.god_id = "jure"  # packages/character/package.py:11
    entity.recalculate_stats()
    return entity


def test_starting_max_hp_is_55():
    """endurance*2 + strength + level*5 + jure bonus = 13*2 + 14 + 5 + 10."""
    assert _player_entity().max_hp == 55


def test_starting_kit_is_seven_items():
    """packages/gameplay/package.py:8-33 returns 7 items."""
    from packages.gameplay.package import _create_starter_items

    class _Kernel:
        def get_system(self, name, default=None):
            return default

        def has_system(self, name):
            return False

    kit = _create_starter_items(_Kernel())
    assert len(kit) == 7


def test_monster_hp_span():
    """The deepest monster has max HP of 500."""
    hp = sorted(body["max_hp"] for body in MONSTERS.values())
    assert hp[0] == 10
    assert hp[-1] == 500


def test_exp_next_is_120():
    """`exp_next` is pinned to 120 based on balance adjustments."""
    entity = _player_entity()
    assert entity.exp_next == 120
    assert entity.exp_next == _player_entity().exp_next


def test_monsters_per_floor_is_about_6_7():
    """0.6 spawn chance per room x ~11 rooms, measured over 60 generated floors."""
    rng = random.Random(20261004)
    random.seed(20261004)
    counts: list[int] = []
    for _ in range(60):
        game_map = GameMap(80, 50)
        game_map.generate_dungeon()
        # rooms[0] is the start room and never spawns monsters (package.py:58)
        counts.append(round(0.6 * max(0, len(game_map.rooms) - 1)))
    mean = statistics.mean(counts)
    assert 5.5 <= mean <= 8.0, f"monsters per floor drifted to {mean:.2f}"


# ------------------------------------------------------------------
# 難易度カーブ検証 (T33 R3案C)
#
# 判定基準の数値はコードに埋めず data/balance_standards.yaml の
# difficulty_curve を参照する (balance_simulator と同じ方針)。
# 現行バランスが歪んでいる項目は xfail (警告) で記録し、修正後に xpass する。
# ------------------------------------------------------------------


def _difficulty_curve() -> dict:
    """data/balance_standards.yaml の難易度カーブ評価テーブルを返す。"""
    return STANDARDS.get("difficulty_curve") or {}


def test_exp_curve_adjacent_ratio_in_jrpg_band():
    """隣接レベルの必要 EXP 比が標準 JRPG 曲線の帯内で単調増加すること。"""
    snapshot = compute_balance_snapshot()
    band = _difficulty_curve()["player_levels"]["adjacent_exp_ratio"]
    levels = snapshot["exp_curve"]
    for level in range(1, len(levels)):
        prev = levels[str(level)]["exp_next"]
        current = levels[str(level + 1)]["exp_next"]
        assert current > prev, f"L{level} で必要 EXP が減少しています ({prev} -> {current})"
        ratio = current / prev
        assert band["min"] <= ratio <= band["max"], (
            f"L{level}->{level + 1} の必要 EXP 比 {ratio:.3f} が帯 "
            f"[{band['min']}, {band['max']}] 外 (急増/急減)"
        )


def test_cumulative_exp_is_monotonic_and_smooth():
    """レベル N 到達までの累積 EXP が単調増加し、伸びが次第に緩やかになること。

    累積 EXP の隣接比が単調非増加 (= 曲線が上に凸で平滑) というのが
    標準 JRPG 曲線の性質。急に必要 EXP が跳ねるカーブを検出する。
    """
    snapshot = compute_balance_snapshot()
    cumulative = [
        snapshot["exp_curve"][str(level)]["cumulative"] for level in range(1, 21)
    ]
    for before, after in zip(cumulative, cumulative[1:]):
        assert after > before, f"累積 EXP が減少しています ({before} -> {after})"
    ratios = [after / before for before, after in zip(cumulative, cumulative[1:])]
    for i, (before, after) in enumerate(zip(ratios, ratios[1:])):
        assert after <= before + 1e-9, (
            f"L{i + 3} 付近で累積 EXP の伸びが急増しています (隣接比 {before:.3f} -> {after:.3f})"
        )


def test_enemy_curve_is_monotonic_by_floor():
    """敵の平均 HP・平均攻撃・撃破 EXP が階層に対して単調増加すること (1-10F)。"""
    snapshot = compute_balance_snapshot()
    enemy = snapshot["enemy_curve"]
    floors = sorted(enemy, key=int)
    for lower, upper in zip(floors, floors[1:]):
        assert (
            enemy[upper]["enemy_hp_mean"] > enemy[lower]["enemy_hp_mean"]
        ), f"{lower}->{upper}F で敵平均 HP が減少しています"
        assert (
            enemy[upper]["enemy_attack_mean"] > enemy[lower]["enemy_attack_mean"]
        ), f"{lower}->{upper}F で敵平均攻撃が減少しています"
        assert enemy[upper]["enemy_exp"] > enemy[lower]["enemy_exp"], (
            f"{lower}->{upper}F で撃破 EXP が減少しています"
        )


def test_enemy_curve_matches_standards_table():
    """実計算の敵カーブが評価テーブル (±5%) と一致し、期待プレイヤーレベルも単調増加すること。"""
    snapshot = compute_balance_snapshot()
    table = _difficulty_curve()["dungeon_levels"]
    for floor_str, stats in snapshot["enemy_curve"].items():
        expected = table[int(floor_str)]
        assert stats["enemy_exp"] == expected["enemy_exp"], (
            f"{floor_str}F の撃破 EXP が評価テーブルと不一致"
        )
        assert stats["enemy_hp_mean"] == pytest.approx(expected["enemy_hp"], rel=0.05), (
            f"{floor_str}F の敵平均 HP {stats['enemy_hp_mean']} が評価テーブル "
            f"{expected['enemy_hp']} から 5% 以上乖離 (monsters.yaml かスケーリング式が変わった)"
        )
        assert stats["enemy_attack_mean"] == pytest.approx(
            expected["enemy_attack"], rel=0.05
        ), (
            f"{floor_str}F の敵平均攻撃 {stats['enemy_attack_mean']} が評価テーブル "
            f"{expected['enemy_attack']} から 5% 以上乖離"
        )
    expected_levels = [table[floor]["expected_player_level"] for floor in range(1, 11)]
    assert all(
        upper > lower for lower, upper in zip(expected_levels, expected_levels[1:])
    ), "期待プレイヤーレベルが階層に対して単調増加していません"


def test_player_enemy_ratio_within_curve_band():
    """期待プレイヤーレベル同士で 敵の強さ/プレイヤーの強さ 比率がカーブ帯内であること (1-10F)。"""
    snapshot = compute_balance_snapshot()
    band = _difficulty_curve()["player_enemy_ratio"]
    for floor_str, ratio in snapshot["player_enemy_ratio"].items():
        assert band["hp"]["min"] <= ratio["hp"] <= band["hp"]["max"], (
            f"{floor_str}F の敵平均 HP / プレイヤー最大 HP = {ratio['hp']} が帯 "
            f"[{band['hp']['min']}, {band['hp']['max']}] 外"
        )
        assert band["attack"]["min"] <= ratio["attack"] <= band["attack"]["max"], (
            f"{floor_str}F の敵平均攻撃 / プレイヤー攻撃 = {ratio['attack']} が帯 "
            f"[{band['attack']['min']}, {band['attack']['max']}] 外"
        )


@pytest.mark.xfail(
    reason=(
        "現行は撃破 EXP が 35×階層の線形のため、必要 EXP (1.35 倍/レベル) に対して "
        "1 レベル上に必要な撃破数が L3: 2.1 匹 → L10: 5.1 匹 → L20: 51.3 匹と増え続ける "
        "(EXP インフレ)。撃破 EXP を敵の強さ連動にする修正後に xpass する。"
    ),
    strict=False,
)
def test_kills_per_level_within_band():
    """1 レベル上に必要な撃破数が許容帯に収まること (現行は帯外 → xfail)。"""
    snapshot = compute_balance_snapshot()
    band = _difficulty_curve()["player_levels"]["kills_per_level"]
    worst_level, worst_kills = max(
        snapshot["kills_per_level"].items(), key=lambda item: item[1]
    )
    assert band["min"] <= worst_kills <= band["max"], (
        f"L{worst_level} の撃破数/レベル {worst_kills} が帯 "
        f"[{band['min']}, {band['max']}] 外 (必要 EXP のインフレ)"
    )


@pytest.mark.xfail(
    reason=(
        "2→3F (+47%, オーク出現) と 6→7F (+37%, ミノタウロス出現) で敵平均 HP の段差が "
        "上限 25% を超える (「特定階層で急に辛い」)。ティア出現階層の緩和後に xpass する。"
    ),
    strict=False,
)
def test_tier_entry_mean_hp_spike_bounded():
    """隣接階層の敵平均 HP が急増しないこと (現行はティア出現階層で超過 → xfail)。"""
    snapshot = compute_balance_snapshot()
    limit = _difficulty_curve()["floor_step"]["max_mean_hp_step_ratio"]
    enemy = snapshot["enemy_curve"]
    floors = sorted(enemy, key=int)
    for lower, upper in zip(floors, floors[1:]):
        step = enemy[upper]["enemy_hp_mean"] / enemy[lower]["enemy_hp_mean"]
        assert step <= limit, (
            f"{lower}->{upper}F の敵平均 HP が {step:.2f} 倍 (上限 {limit}) の段差"
        )


@pytest.mark.xfail(
    reason=(
        "7F のミノタウロス (HP 2.5 倍 / 攻撃 1.7 倍) や 10F 同 (2.1 倍 / 3.2 倍) が "
        "期待プレイヤーに対し過大で一撃死圏。ティア出現階層の敵調整後に xpass する。"
    ),
    strict=False,
)
def test_worst_case_monster_ratio_bounded():
    """プール内で最も強い個体が期待プレイヤーに対する比率の上限内であること (現行は超過 → xfail)。"""
    curve = _difficulty_curve()
    limits = curve["floor_step"]
    table = curve["dungeon_levels"]
    worst_report: list[str] = []
    for floor in range(1, 11):
        scale = 1.0 + (floor - 1) * ENEMY_SCALE_STEP
        pool = _floor_monster_pool(MONSTERS, floor)
        worst_hp = max(int(body.get("max_hp", 0) * scale) for body in pool)
        worst_attack = max(
            int((body.get("attributes") or {}).get("strength", 0) * scale) for body in pool
        )
        expected_level = int(table[floor]["expected_player_level"])
        player = _expected_player_stats(CONFIG, expected_level)
        hp_ratio = worst_hp / player["max_hp"]
        attack_ratio = worst_attack / player["attack"]
        if hp_ratio > limits["worst_case_hp_ratio_max"]:
            worst_report.append(f"{floor}F 最強個体 HP 比 {hp_ratio:.2f}")
        if attack_ratio > limits["worst_case_attack_ratio_max"]:
            worst_report.append(f"{floor}F 最強個体 攻撃比 {attack_ratio:.2f}")
    assert not worst_report, "最強個体の比率が上限を超過: " + ", ".join(worst_report)


def test_snapshot_matches_baseline():
    """現行カーブが baseline.json の balance_snapshot と一致すること。

    乖離はバランスが動いた証拠。意図した変更なら
    ``python3 balance_tool.py --update-baseline`` でベースラインを更新し、
    コミットメッセージで変更意図を説明する。意図していない場合は
    monsters.yaml / balance_standards.yaml / スケーリング式の変更を調査する。
    """
    baseline = load_balance_baseline()
    assert baseline, (
        "baseline.json に balance_snapshot セクションが無い "
        "(python3 balance_tool.py --update-baseline で生成すること)"
    )
    lines = diff_balance_snapshot(compute_balance_snapshot(), baseline)
    assert not lines, (
        "バランス値がベースラインと乖離しています。意図した変更なら "
        "`python3 balance_tool.py --update-baseline` でベースラインを更新すること:\n"
        + "\n".join(lines)
    )


def test_difficulty_presets_consistent_with_curve_table():
    """DifficultyManager の通常難易度が乗数 1.0 で difficulty_curve テーブルと整合すること。

    テーブルは「通常」基準の期待値なので、normal の enemy_hp /
    player_damage_taken が 1.0 からずれると評価が無意味になる。
    easy < normal < hard の単調性も難易度として必須。
    """
    from core.difficulty import DifficultyManager

    normal = DifficultyManager("normal")
    assert normal.multipliers["enemy_hp"] == 1.0
    assert normal.multipliers["player_damage_taken"] == 1.0

    easy = DifficultyManager("easy")
    hard = DifficultyManager("hard")
    assert (
        easy.multipliers["enemy_hp"]
        < normal.multipliers["enemy_hp"]
        < hard.multipliers["enemy_hp"]
    ), "enemy_hp 乗数が easy < normal < hard の順になっていません"
    assert (
        easy.multipliers["player_damage_taken"]
        < normal.multipliers["player_damage_taken"]
        < hard.multipliers["player_damage_taken"]
    ), "player_damage_taken 乗数が easy < normal < hard の順になっていません"

    # config.yaml 側 (実行中ゲームの auto 解決用プリセット) も同じ構造を保つ。
    # テーブルは通常基準なので config の normal が 1.0 を外さないこと。
    presets = CONFIG["game"]["difficulty_presets"]
    assert presets["normal"]["enemy_hp"] == 1.0
    assert presets["normal"]["player_damage_taken"] == 1.0
    assert (
        presets["easy"]["enemy_hp"]
        < presets["normal"]["enemy_hp"]
        < presets["hard"]["enemy_hp"]
    ), "config.yaml の enemy_hp プリセットが easy < normal < hard の順になっていません"
