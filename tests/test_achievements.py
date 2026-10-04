"""実績・称号が「実際に到達できる」ことの契約テスト

このファイルが守るのは到達可能性であって判定式そのものではない。

- 実績は run 終了というイベントで判定され、run 履歴の確定値から獲得される。
  (`AchievementManager.check_run_end` = engine の run 終了処理が呼ぶ入口)
- 称号は engine が既に呼んでいる `TitleManager.check_all_titles` で獲得される。
  リモコンのロード漏れで「Called されているが常に空振り」にならないこと。
- 称号の条件は YAML に書かれたとおりに読み込まれる。読み飛ばされた
  キー (`skill`) は、どのスキルも見ていない空振り条件になる。

期待値はすべて `data/achievements.yaml` / `data/titles.yaml` から引き、
判定式をテスト側で書き写さない。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from achievement_system import AchievementManager, AchievementRegistry
from ecs.components.components import Skill
from ecs.entity import Entity
from run_history import RunHistory
from title_system import MANAGER as TITLE_MANAGER
from title_system import TitleManager, TitleRegistry

REPO_ROOT = Path(__file__).resolve().parents[1]
ACHIEVEMENTS_YAML = REPO_ROOT / "data" / "achievements.yaml"
TITLES_YAML = REPO_ROOT / "data" / "titles.yaml"


# --------------------------------------------------------------- 定義の読み込み


def _declared() -> dict[str, Any]:
    return yaml.safe_load(ACHIEVEMENTS_YAML.read_text(encoding="utf-8"))["achievements"]


def _declared_titles() -> dict[str, Any]:
    return yaml.safe_load(TITLES_YAML.read_text(encoding="utf-8"))["titles"]


def _achievement_id_by_condition_type(cond_type: str) -> str:
    """条件aldi type を持つ実績の id を YAML から取り出す"""
    matches = [
        ach_id
        for ach_id, data in _declared().items()
        if data.get("condition", {}).get("type") == cond_type
    ]
    assert len(matches) == 1, f"{cond_type} の実績が 1 件である前提が崩れた: {matches}"
    return matches[0]


def _achievement_target(ach_id: str) -> int:
    return _declared()[ach_id]["condition"]["target"]


# --------------------------------------------------------------- 実物の組み立て


def _player() -> Entity:
    """初期状態から何も達成していないプレイヤー"""
    return Entity(0, 0, "@", name="試しの冒険者", is_player=True)


def _achievement_manager() -> AchievementManager:
    """`packages/meta/package.py` と同じ手順（レジストリを読み込んでから生成）"""
    registry = AchievementRegistry()
    registry.load(str(ACHIEVEMENTS_YAML))
    return AchievementManager(registry)


# --------------------------------------------------------------- 実績


def test_run_end_grants_depth_achievement_from_run_history() -> None:
    """run 終了の判定で、履歴の深さから深度実績が実際に獲得される

    これは配線そのもののテスト。`AchievementManager.check_run_end` を
    呼び出し側（engine の run 終了処理）から外すと成立しなくなる。
    """
    ach_id = _achievement_id_by_condition_type("dungeon_floors")
    target = _achievement_target(ach_id)
    player = _player()
    manager = _achievement_manager()

    # 履歴の `best_depth` が YAML の閾値に届いた、という実際の run 結果
    history = RunHistory(
        runs=1,
        last_depth=target,
        last_kills=0,
        last_turns=3,
        last_cause="戦闘",
        best_depth=target,
        best_kills=0,
    )

    granted = manager.check_run_end(player, history)

    assert ach_id in granted, f"{ach_id} が run 終了で獲得されていない: {granted}"
    assert ach_id in player.achievements


def test_run_end_applies_reward_from_yaml() -> None:
    """獲得した実績の報酬が YAML の宣言どおり支払われる

    run 終了では複数の実績が同時に成立しうるので、獲得した実績の宣言値を
    合計したものと実際の増分を突き合わせる（1 件だけと決めつけない）。
    """
    ach_id = _achievement_id_by_condition_type("dungeon_floors")
    player = _player()
    manager = _achievement_manager()
    gold_before = player.gold
    points_before = player.skill_points

    history = RunHistory(runs=1, best_depth=_achievement_target(ach_id), last_cause="戦闘")
    granted = manager.check_run_end(player, history)

    assert ach_id in granted
    declared = _declared()
    assert player.gold - gold_before == sum(
        declared[a].get("reward_gold", 0) for a in granted
    )
    assert player.skill_points - points_before == sum(
        declared[a].get("reward_skill_points", 0) for a in granted
    )
    for a in granted:
        reward_title = declared[a].get("reward_title")
        if reward_title:
            assert reward_title in player.titles


def test_run_end_grants_only_once_per_run() -> None:
    """同じ run 終了が二重に観測されても報酬は二重に支払わない"""
    ach_id = _achievement_id_by_condition_type("dungeon_floors")
    player = _player()
    manager = _achievement_manager()
    history = RunHistory(runs=1, best_depth=_achievement_target(ach_id), last_cause="戦闘")

    manager.check_run_end(player, history)
    gold_after_first = player.gold
    granted_again = manager.check_run_end(player, history)

    assert ach_id not in granted_again
    assert player.gold == gold_after_first


def test_fresh_player_earns_nothing_at_run_end() -> None:
    """何も造血していない run からは実績が獲得されない（過剰付与の防止）"""
    player = _player()
    manager = _achievement_manager()

    granted = manager.check_run_end(player, RunHistory(runs=1, last_cause="戦闘"))

    assert "dungeon_explorer" not in player.achievements
    assert "dungeon_explorer" not in granted


# --------------------------------------------------------------- 称号


def test_title_is_granted_by_the_shipped_call_pattern() -> None:
    """engine と同じ呼び出し（レジストリをロードしない）で称号が獲得される

    engine/engine.py と managers/world_news_manager.py は `load()` を呼ばずに
    `check_all_titles` を呼ぶ。レジストリが空のままでは必ず空振りしていた。
    """
    title_id = "level_50"
    declared_value = _declared_titles()[title_id]["condition"]["value"]
    player = _player()
    player.level = declared_value

    granted = TITLE_MANAGER.check_all_titles(player)

    assert title_id in granted, f"{title_id} が獲得されていない: {granted}"
    assert title_id in player.titles


def test_skill_title_condition_is_read_from_yaml_skill_key() -> None:
    """`condition.skill` が読み落とされると条件が空振りになる

    YAML は `skill:` で宣言しているが、loader が `target:` しか見ていないと
    「どのスキルの Lv も見ていない」称号になり永久に獲得できない。
    """
    declared = _declared_titles()["master_swordsman"]["condition"]
    skill_id = declared["skill"]
    level = declared["level"]

    manager = TitleManager(TitleRegistry())
    title = manager.registry.get("master_swordsman")

    assert title is not None
    assert title.condition.target == skill_id
    assert title.condition.level == level

    player = _player()
    player.skills[skill_id] = Skill(skill_id, level=level)

    granted = manager.check_all_titles(player)

    assert "master_swordsman" in granted, f"skill 条件の称号が獲得されない: {granted}"


def test_title_below_threshold_is_not_granted() -> None:
    """閾値を下回るだけの state では称号が獲得されない（過剰付与の防止）"""
    title_id = "level_50"
    declared_value = _declared_titles()[title_id]["condition"]["value"]
    player = _player()
    player.level = declared_value - 1

    granted = TITLE_MANAGER.check_all_titles(player)

    assert title_id not in granted
    assert title_id not in player.titles


@pytest.mark.parametrize(
    ("filename", "loader", "count_key"),
    [
        (ACHIEVEMENTS_YAML, _achievement_manager, "achievement"),
        (TITLES_YAML, lambda: TitleManager(TitleRegistry()), "title"),
    ],
)
def test_all_declared_definitions_load(
    filename: Path, loader: Any, count_key: str
) -> None:
    """定義ファイルに書かれた数が、そのまま実体として読み込まれる"""
    text = filename.read_text(encoding="utf-8")
    declared_count = len(yaml.safe_load(text)[count_key + "s"])

    if count_key == "achievement":
        loaded = loader().registry.all()
    else:
        loaded = loader().registry.all()

    assert len(loaded) == declared_count