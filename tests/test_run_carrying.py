"""run の成果が次へ残ることの回帰テスト (docs/compose/spec/run-carrying.md)

`feature/run-end` でゲームは終わるようになったが、その結果がどこにも残らない。
死亡してもなお記録は画面から消え、次の run は前回と同一である。本テストは
「終わるだけで終わらせない」状態Him fixed する。

- run を終えると記録が書かれ、次の起動で読み込まれる
- 履歴が壊れていても起動は成功し、理由が明示される
- 永続報酬トークンが「実読される」か「保留と明記されている」かのどちらかであって、
  定義だけある無言の状態に残っていない
- 本テスト自身が追跡対象のファイル(savegame.bin / balance_report.*)を汚さない
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# テストが触ってはいけない追跡ファイル。Engine の構築とオートセーブが書き換える。
_TRACKED_ARTIFACTS = (
    "savegame.bin",
    "savegame.bin.bak1",
    "savegame.bin.bak2",
    "savegame.bin.bak3",
    "balance_report.json",
    "balance_report.html",
)


def _digest(name: str) -> str | None:
    path = REPO_ROOT / name
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module", autouse=True)
def _preserve_tracked_artifacts():
    """このモジュールのテストが追跡ファイルを汚していないことを保証する。

    先に退避し、テストがどう書いても `finally` で元に戻す。したがって
    「汚さない」は本テストの前提条件であり、テスト対象ではない。
    """
    before = {name: _digest(name) for name in _TRACKED_ARTIFACTS}
    try:
        yield
    finally:
        for name, digest in before.items():
            path = REPO_ROOT / name
            if digest is None:
                if path.exists():
                    path.unlink()
                continue
            if not path.exists() or _digest(name) != digest:
                payload = _ORIGINALS.get(name)
                if payload is not None:
                    path.write_bytes(payload)


_ORIGINALS: dict[str, bytes] = {}


@pytest.fixture(scope="module", autouse=True)
def _snapshot_bytes():
    _ORIGINALS.update(
        {
            name: (REPO_ROOT / name).read_bytes()
            for name in _TRACKED_ARTIFACTS
            if (REPO_ROOT / name).exists()
        }
    )
    yield


def _engine():
    """既存のテストと同じ方法で Engine を構築する (tests/test_run_end.py を参照)。"""
    from game import Engine

    return Engine()


def _kill(engine) -> None:
    """プレイヤーを死亡させ、run を終える。"""
    engine.player.hp = 0
    engine.advance_world()


# --- S2.1: run の結果が書き出され、次の起動で読み込まれる ---------------------------------------


def test_ending_a_run_writes_a_history_record(tmp_path, monkeypatch):
    """契約 S2.1: run を終えると履歴ファイルが生成される"""
    from run_history import RunHistoryStore

    monkeypatch.chdir(tmp_path)
    store = RunHistoryStore()
    engine = _engine()
    engine.dungeon_level = 7
    _kill(engine)

    assert engine.run_summary is not None, "前提: 死亡で run summary が作られていること"
    assert engine.run_summary.depth == 7, (
        f"前提: summary の深度が 7 であること: {engine.run_summary}"
    )

    store.record(engine.run_summary)

    assert store.path.exists(), f"履歴が書き出されていない: {store.path}"
    assert "7" in store.path.read_text(encoding="utf-8")


def test_history_survives_a_process_boundary(tmp_path, monkeypatch):
    """契約 S2.1: 記録は別のプロセス境界を越えて残る。

    同じオブジェクト-oxo メモリ経由で read するだけのテストでは
    「ディスクに書けている」ことが証明できないので、store のインスタンスを
    作り直してから読む。
    """
    from run_history import RunHistory, RunHistoryStore

    monkeypatch.chdir(tmp_path)
    engine = _engine()
    engine.dungeon_level = 4
    _kill(engine)

    RunHistoryStore().record(engine.run_summary)

    # 新しいプロセスで起動したつもり: 完全に新しい store インスタンス
    fresh_store = RunHistoryStore()
    history = fresh_store.load()
    assert history is not None, "別インスタンスから履歴が読めなかった"
    assert isinstance(history, RunHistory)
    assert history.last_depth == 4, f"前回深度が保存されていない: {history}"


def test_next_startup_reports_previous_depth_and_personal_best(tmp_path, monkeypatch):
    """契約 S2.1: 次の起動で前回深度と自己最高記録が提示される"""
    from run_history import RunHistoryStore

    monkeypatch.chdir(tmp_path)

    for depth in (3, 11, 6):
        engine = _engine()
        engine.dungeon_level = depth
        _kill(engine)
        RunHistoryStore().record(engine.run_summary)

    presented = RunHistoryStore().startup_lines()

    text = "\n".join(presented)
    assert "11" in text, f"自己最高記録の 11 が提示されていない: {presented}"
    assert "6" in text, f"前回深度の 6 が提示されていない: {presented}"


def test_personal_best_survives_a_worse_run(tmp_path, monkeypatch):
    """契約 S2.1: 自己最高記録は shallower な run で down しない"""
    from run_history import RunHistoryStore

    monkeypatch.chdir(tmp_path)

    engine = _engine()
    engine.dungeon_level = 12
    _kill(engine)
    RunHistoryStore().record(engine.run_summary)

    engine2 = _engine()
    engine2.dungeon_level = 2
    _kill(engine2)
    RunHistoryStore().record(engine2.run_summary)

    history = RunHistoryStore().load()
    assert history is not None
    assert history.best_depth == 12, f"自己最高記録が 2 に落ちてしまった: {history}"
    assert history.last_depth == 2, f"前回深度が最新であるべき: {history}"


def test_missing_history_is_reported_as_a_first_run(tmp_path, monkeypatch):
    """契約 S2.1: 履歴が無いのは初回起動であり、黙って無視しない"""
    from run_history import RunHistoryStore

    monkeypatch.chdir(tmp_path)
    store = RunHistoryStore()

    assert store.load() is None
    lines = store.startup_lines()
    assert lines, "初回起動である旨を示す行が無い"


def test_corrupt_history_does_not_prevent_startup(tmp_path, monkeypatch):
    """契約 S2.1: 履歴が壊れていても起動は成功し、理由が明示される"""
    from run_history import RunHistoryStore

    monkeypatch.chdir(tmp_path)
    store = RunHistoryStore()
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{これは壊れた JSON です", encoding="utf-8")

    # 壊れた読取りは例外を投げない
    history = store.load()
    assert history is None, "壊れた履歴からは None を返すこと"

    lines = store.startup_lines()
    text = "\n".join(lines)
    assert lines, "履歴が読めなかった旨を示す行が無い"
    assert "履歴" in text or "読" in text, f"理由が示されていない: {lines}"


def test_history_round_trips_the_devoured_skills(tmp_path, monkeypatch):
    """契約 S2.1: 喰い得たスキルも履歴に残る"""
    from run_history import RunHistoryStore

    monkeypatch.chdir(tmp_path)
    engine = _engine()
    engine.game_state_data.world_a_data.setdefault("skills", []).extend(["throw_stone", "roar"])
    _kill(engine)

    RunHistoryStore().record(engine.run_summary)
    history = RunHistoryStore().load()
    assert history is not None
    assert "throw_stone" in history.devoured_skills, f"喰いスキルが保存されていない: {history}"


# --- S2.2: 永続報酬トークンは実読されるか保留と明記されている ---------------------------------------


def test_persistent_reward_tokens_are_implemented_or_marked_reserved():
    """契約 S2.2: 各トークンが「実読」か「保留明記」のどちらかで、無言の放置が残らない。

    ハードコードされた一覧ではなく、データファイルを走査して対象を導出する。
    """
    import re

    import yaml

    root = REPO_ROOT
    py_sources = {
        path: path.read_text(encoding="utf-8", errors="replace")
        for path in root.glob("*.py")
        if "build" not in path.parts and ".worktrees" not in path.parts
    }

    reserved_keys: set[str] = set()
    for name in ("data/meta_progression.yaml", "data/meta_goals.yaml"):
        raw = yaml.safe_load((root / name).read_text(encoding="utf-8")) or {}
        for marker in ("reserved", "unimplemented", "pending"):
            for value in _walk_strings(raw, marker):
                reserved_keys.add(value)

    unaccounted: dict[str, str] = {}

    def check(tokens, origin: str) -> None:
        for token in tokens:
            if token in reserved_keys:
                continue
            pattern = re.compile(rf"""["']{re.escape(token)}["']""")
            read = any(pattern.search(src) for src in py_sources.values())
            if not read:
                unaccounted[token] = origin

    progression = yaml.safe_load((root / "data/meta_progression.yaml").read_text(encoding="utf-8"))
    check(_collect_named(progression, ("reward_bonus", "permanent_bonus")), "meta_progression.yaml")

    goals = yaml.safe_load((root / "data/meta_goals.yaml").read_text(encoding="utf-8"))
    check(_collect_named(goals, ("permanent_bonus",)), "meta_goals.yaml")

    assert not unaccounted, (
        "以下のトークンは定義はあるが実装も保留の明記もなく、到達不能のまま放置されている: "
        f"{unaccounted}"
    )


def _walk_strings(node, marker: str):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == marker:
                yield str(value)
            yield from _walk_strings(value, marker)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_strings(value, marker)


def _collect_named(node, keys: tuple[str, ...]) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key in keys and isinstance(value, (str, int, float)):
                found.add(str(value))
            found |= _collect_named(value, keys)
    elif isinstance(node, list):
        for value in node:
            found |= _collect_named(value, keys)
    return found


# --- S2.4: テスト自身が追跡ファイルを汚さない -----------------------------------------------------

# 「汚さない」は本 module の `_preserve_tracked_artifacts` fixture が保証する。
# それは fixture である以上テスト対象にならず、自己参照のアサーションは
# 何の証拠にもならないため、テストではなく実行時の `git status --short` で確認する。
