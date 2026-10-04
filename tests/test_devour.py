"""
test_devour.py
《喰らい》(devour) の配線リグレッションテスト — devour-wiring / S2.1〜S2.3

検証対象は production 経路である `engine/engine.py` の `Engine.execute_devour()`
(`input_actions.py` のキー入力から到達する実装)。
`skill_eater/combat/engine.py` の `SkillEaterCombatSystem.execute_devour()` は
完成度の高い実装だが呼び出し元はテストだけであり、本ファイルでは検証しない。

前提: 奪取が必ず成功するよう、解析レベルと対象の HP をテスト側で固定する。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest
import yaml

from data_manager import DataManager
from game import Engine
from renderer import NullRenderer

MONSTERS_YAML = Path(_ROOT) / "data" / "monsters.yaml"

# 喰らい成功率を最大に固定するための解析レベル。
# 対象の HP も 1 まで落としてあるので rate == 1.0 になり、乱数ロールに依存しない。
ANALYSIS_LEVEL = 5


@pytest.fixture(scope="module")
def dm() -> DataManager:
    """モジュール共有の DataManager（yaml 読み込みは重いため 1 度だけ）"""
    return DataManager()


def _engine_with_adjacent_monster(dm: DataManager, monster_id: str) -> tuple[Engine, object]:
    """プレイヤー隣接に production 経路のモンスターを1体だけ配置した Engine を返す。

    モンスターは `DataManager.create_monster()` で生成する。これは `data_manager.py` が
    `data/monsters.yaml` から `mob.skills`（id 文字列のリスト）を実体へ流し込む経路そのもの。
    """
    engine = Engine(renderer=NullRenderer())
    engine.player.analysis_level = ANALYSIS_LEVEL
    monster = dm.create_monster(monster_id, x=engine.player.x + 1, y=engine.player.y)
    monster.hp = 1
    engine.entity_manager.add_entity(monster)
    return engine, monster


def _devour_once(dm: DataManager, monster_id: str) -> tuple[str | None, list[str]]:
    """1 体だけ；《喰らい》を1回実行して (記録された奪取スキルid, モンスターの宣言スキル) を返す。"""
    engine, monster = _engine_with_adjacent_monster(dm, monster_id)
    engine.execute_devour()
    recorded = list(engine.game_state_data.world_a_data.get("skills", []))
    return (recorded[-1] if recorded else None), list(monster.skills)


def _devoured_ids(engine: Engine) -> list[str]:
    """devour が run 記録として残した奪取スキル id の列"""
    return list(engine.game_state_data.world_a_data.get("skills", []))


def _monster_referenced_skill_ids(dm: DataManager) -> set[str]:
    """`data/monsters.yaml` が参照するスキル id 全体をハードコードせず導出する。

    生 yaml から読んだ集合と、`DataManager.create_monster()` が実際に Entity へ渡す集合が
    一致することも確認する。これにより期待値のリストが正確であることも同時に検証できる。
    """
    raw = yaml.safe_load(MONSTERS_YAML.read_text(encoding="utf-8")) or {}

    from_yaml: set[str] = set()
    for entry in raw.values():
        for skill_id in entry.get("skills") or []:
            from_yaml.add(getattr(skill_id, "root", skill_id))

    from_entities: set[str] = set()
    for monster_id in raw:
        for skill_id in dm.create_monster(monster_id).skills or []:
            from_entities.add(getattr(skill_id, "root", skill_id))

    assert from_yaml == from_entities, (
        f"yaml と DataManager が渡すスキル id が食い違う: "
        f"yaml_only={sorted(from_yaml - from_entities)} dm_only={sorted(from_entities - from_yaml)}"
    )
    return from_yaml


# --- S2.1: 倒した敵の実データから奪取対象を選ぶ -------------------------------------------------


def test_devour_steals_the_skill_of_the_defeated_monster(dm: DataManager) -> None:
    """契約 S2.1: 宣言スキルの異なる 2 体を倒すと、記録される奪取 id も異なる"""
    goblin_id, goblin_skills = _devour_once(dm, "goblin")
    orc_id, orc_skills = _devour_once(dm, "orc")

    assert goblin_skills and orc_skills, "前提: 両方ともスキルを持つモンスターである"
    assert set(goblin_skills) != set(orc_skills), "前提: 2 体の宣言スキルが異なる"

    assert goblin_id != orc_id, (
        f"何を倒しても同じスキルが奪われる: goblin -> {goblin_id!r}, orc -> {orc_id!r}"
    )
    assert goblin_id in goblin_skills, f"奪取 id はゴブリンの宣言スキルに含まれるべき: {goblin_id!r}"
    assert orc_id in orc_skills, f"奪取 id はオークの宣言スキルに含まれるべき: {orc_id!r}"


def test_devour_grants_nothing_from_a_skillless_monster(dm: DataManager) -> None:
    """契約 S2.1: `skills: []` の敵を倒しても奪取は不成立になり、スキルが増えない"""
    engine, monster = _engine_with_adjacent_monster(dm, "slime")

    assert list(monster.skills) == [], "前提: スライムは data/monsters.yaml 上 skills が空である"
    owned_before = dict(engine.player.skills)

    engine.execute_devour()

    assert _devoured_ids(engine) == [], (
        f"スキルのない敵から奪取が成立してはいけない: 記録された {engine.game_state_data.world_a_data.get('skills')}"
    )
    assert dict(engine.player.skills) == owned_before, (
        "スキルのない敵を倒してもプレイヤーのスキル集合は増えてはならない"
    )


# --- S2.2: 奪取したスキルは唱えられる形で得る ---------------------------------------------------


def test_devoured_skill_becomes_castable(dm: DataManager) -> None:
    """契約 S2.2: 奪取成功後、プレイヤーの実行可能スキル集合に奪った id が含まれる"""
    engine, _ = _engine_with_adjacent_monster(dm, "goblin")

    engine.execute_devour()

    recorded = _devoured_ids(engine)
    assert len(recorded) == 1, f"奪取が1回だけ記録されるべき: {recorded}"
    stolen_id = recorded[0]

    # ecs/entity.py の gain_skill_exp が読むのは Entity.skills（dict）である。
    player_skills = engine.player.skills
    assert stolen_id in player_skills, (
        f"奪取した {stolen_id!r} が唱えられるスキル集合に入っていない: "
        f"登録済み={sorted(player_skills)}"
    )
    slot = player_skills[stolen_id]
    for attr in ("name", "level", "experience", "potential"):
        assert hasattr(slot, attr), f"実行可能スキルの要素は {attr} を持つべき: {slot!r}"


def test_repeated_devour_does_not_duplicate_skills(dm: DataManager) -> None:
    """契約 S2.2: 同じ敵を2回倒してもプレイヤーのスキル集合は増えない（重複排除）"""
    engine, _ = _engine_with_adjacent_monster(dm, "goblin")
    before = len(engine.player.skills)

    engine.execute_devour()
    engine.execute_devour()

    recorded = _devoured_ids(engine)
    assert recorded, "前提: 1体目の奪取は記録されている"
    stolen_id = recorded[0]
    owned = list(engine.player.skills)

    assert stolen_id in owned, f"まず1体目の奪取が登録されていること: {stolen_id!r} not in {owned}"
    assert owned.count(stolen_id) == 1, f"重複して獲得している: {stolen_id!r} x{owned.count(stolen_id)}"
    assert len(engine.player.skills) == before + 1, (
        f"スキル集合は1体目のときだけ増えるべき: {before} -> {len(engine.player.skills)}"
    )


# --- S2.3: モンスターが参照するスキルが解決できる -------------------------------------------------


def test_data_manager_skill_repository_is_populated(dm: DataManager) -> None:
    """契約 S2.3: `DataManager().skills` が空でない"""
    registered = dm.skills.get_all()
    assert len(registered) > 0, "DataManager().skills が空リポジトリのままになっている"


def test_every_monster_referenced_skill_resolves(dm: DataManager) -> None:
    """契約 S2.3: `data/monsters.yaml` が参照するすべての id が SkillRepository で解決できる"""
    declared = _monster_referenced_skill_ids(dm)
    assert declared, "前提: monsters.yaml からスキル id を読み出せたこと"

    unresolved = sorted(skill_id for skill_id in declared if dm.skills.get(skill_id) is None)
    assert not unresolved, (
        f"monsters.yaml が参照する {len(declared)} 個のスキル id のうち "
        f"{len(unresolved)} 個が SkillRepository で解決できない: {unresolved}"
    )