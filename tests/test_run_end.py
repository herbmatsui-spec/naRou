"""run-end-state feature の契約テスト (docs/compose/spec/run-end-state.md [S2.1][S2.2][S2.4])

「ゲームが終わらない」([S1.1]) と 「ターンがフレーム数である」([S1.2]) の
リグレッションを防ぐ。T1・T2 の実装適用前は、各テストが [S2.1] / [S2.2] の契約
に対する失敗としてのみ落ちることを意図している。

Engine の生成は Kernel と 9 パッケージの読み込みで 4 秒弱かかるため、
module スコープで 1 つだけ生成して共有し、テストごとに可変状態だけ戻す。
"""

from __future__ import annotations

import copy
import inspect
import re
from typing import Any

import pytest

from constants import NATURAL_REGEN_INTERVAL, GameState
from game import Engine

# 死亡前に与える run の集計値。summary の「到達深度」「撃破数」「喰い得数」と
# 一対一で衝突しないよう、すべて異なる値にして照合の曖昧さを避ける。
RUN_DEPTH = 4
RUN_KILLS = 2
RUN_DEVOURED_SKILLS = ("alpha_skill", "beta_skill", "gamma_skill")
# 死亡させる前に進めるターン数。0 以外の値が入るようにする。
RUN_TURNS_BEFORE_DEATH = 7


# --------------------------------------------------------------- 共有 Engine


def _flat(obj: Any) -> dict[str, Any]:
    """オブジェクトの状態を dict で撮る。

    dict / list / set だけは 1 階層コピーを残す。テスト中の破壊（自然回復による
    hp 変化、`world_a_data["skills"]` への追加など）を戻せるようにするため。
    """
    return {
        name: copy.copy(value) if isinstance(value, (dict, list, set)) else value
        for name, value in vars(obj).items()
    }


def _replay(obj: Any, snapshot: dict[str, Any]) -> None:
    """_flat で撮った状態に戻す。テスト中に新しく増えた属性も削除する。"""
    for name in [name for name in vars(obj) if name not in snapshot]:
        delattr(obj, name)
    for name, value in snapshot.items():
        setattr(obj, name, value)


@pytest.fixture(scope="module")
def engine() -> Engine:
    """テスト対象の Engine を 1 つだけ生成する（生成が遅いため module スコープ）。"""
    return Engine()


@pytest.fixture(autouse=True)
def _reset(engine: Engine) -> Any:
    """各テストの前後で Engine の可変状態を初期値へ戻す。

    GAME_OVER の実装が Engine / GameStateData に新フィールド（死亡フラグや run
    summary など）を足した場合も、vars() 単位の復元で確実に巻き戻す。
    """
    snapshot = {
        "engine": _flat(engine),
        "state": _flat(engine.game_state_data),
        "survival": _flat(engine.survival),
        "entity_hp": {id(e): e.hp for e in engine.entity_manager.get_entities()},
        "player": _flat(engine.player),
    }
    yield engine
    _replay(engine, snapshot["engine"])
    _replay(engine.game_state_data, snapshot["state"])
    _replay(engine.survival, snapshot["survival"])
    for entity in engine.entity_manager.get_entities():
        if id(entity) in snapshot["entity_hp"]:
            entity.hp = snapshot["entity_hp"][id(entity)]
    _replay(engine.player, snapshot["player"])


def _kill_player(engine: Engine) -> None:
    """プレイヤーを戦闘で死なせずに HP 0 にしてから 1 ターン進める。

    [S2.1] は「死因が攻撃元の種類に依存しない」ことを要求しているため、NPC の攻撃は
    待たず HP を直接 0 にして `advance_world` の入口に死亡判定を当てる。
    NPC 攻撃で削ると死因が戦闘に固定され、テスト側から死因の種類を変えられなくなる。
    """
    engine.player.hp = 0
    engine.advance_world()


def _silence_hostiles(engine: Engine) -> None:
    """プレイヤーとペット以外の生存エンティティを戦闘不能にする。

    自然回復のテストでは「HP の変化は自然回復ゲートだけから来る」ようにしたい。
    HP を 0 にすると `turn_manager.py` の `e.hp > 0` フィルタでターン順から外れ、
    行動しなくなる。
    """
    for entity in engine.entity_manager.get_living_entities():
        if entity is not engine.player and entity is not engine.pet:
            entity.hp = 0


# ------------------------------------------------- [S2.1] 死が run を終わらせる


def test_zero_hp_switches_current_state_to_game_over(engine: Engine) -> None:
    """プレイヤーの HP を 0 にすると `current_state` が `GameState.GAME_OVER` になる。

    契約 [S2.1]。現状は `engine/engine.py` の NPC 攻撃分岐がログを 1 行出すのみで
    `GameStateData.current_state` は `EXPLORING` のまま。
    """
    assert engine.current_state is not GameState.GAME_OVER, "前提が崩れています: 既に GAME_OVER"

    _kill_player(engine)

    assert engine.game_state_data.current_state is GameState.GAME_OVER


def test_zero_hp_switches_legacy_game_state_string(engine: Engine) -> None:
    """死亡時に旧互換文字列 `game_state` も `"game_over"` になる。

    契約 [S2.1]。`Engine.render()` は `game_state` 文字列で分岐する（`skill_tree`,
    `job` など）ため、enum 側だけ変えても描画が追従しない。
    """
    assert engine.game_state != "game_over", "前提が崩れています: 既に game_over"

    _kill_player(engine)

    assert engine.game_state_data.game_state == "game_over"


def test_advance_world_stops_counting_turns_after_game_over(engine: Engine) -> None:
    """GAME_OVER 後も `advance_world` を呼んでも turn が増えない（冪等）。

    契約 [S2.1]。0 HP のプレイヤーは `turn_manager.py` の `e.hp > 0` でターン順に
    載らないため世界は止まるが、turn counter は増え続ける。
    """
    _kill_player(engine)
    after_death = engine.turns

    for _ in range(3):
        engine.advance_world()

    assert engine.turns == after_death, (
        f"死亡後に turn が増えている ({after_death} → {engine.turns})"
    )


# ------------------------------------------------- [S2.2] turn を turn に紐づける


@pytest.mark.parametrize("frames", [1, 3, 60])
def test_update_does_not_advance_turn_counter(engine: Engine, frames: int) -> None:
    """`Engine.update()` を N 回呼んでも turn が増えない。

    契約 [S2.2]。vsync ループは入力を読む前に毎フレーム `update()` を呼ぶため、
    現状は `engine/engine.py` の `update()` 末尾 `self.turns += 1` で
    1 プレイヤーアクションあたり数フレーム分 turn が進む。
    """
    before = engine.turns

    for _ in range(frames):
        engine.update()

    assert engine.turns == before, (
        f"update() を {frames} 回呼んで turn が {before} → {engine.turns} に増えた"
    )


def test_advance_world_advances_turn_counter_by_one(engine: Engine) -> None:
    """`advance_world()` を 1 回呼ぶと turn がちょうど 1 増える。

    契約 [S2.2]。`advance_world()` 側の `self.turns += 1` は本来就正しいので、
    `update()` 側の重複を消してもこちらが残っていることのガード。
    """
    before = engine.turns

    engine.advance_world()

    assert engine.turns == before + 1


def test_natural_regen_is_measured_in_turns_not_frames(engine: Engine) -> None:
    """自然回復は「何もしないフレーム」ではなく `advance_world` の回数で数える。

    契約 [S2.2]。`self.turns % NATURAL_REGEN_INTERVAL == 0` を基準にしているため、
    `update()` が turn を進めていると「入力待ち時間だけで回復」になる。
    ここでは NATURAL_REGEN_INTERVAL の倍数ではないフレーム数を空回ししてから、
    ちょうど NATURAL_REGEN_INTERVAL ターン目で回復が成立することを要求する。
    """
    _silence_hostiles(engine)
    engine.player.hp = engine.player.max_hp - 5
    before = engine.player.hp

    # vsync 1 秒ぶん（+ 1 フレーム）。フレームだけなら回復しない。
    for _ in range(NATURAL_REGEN_INTERVAL * 7 + 1):
        engine.update()
    assert engine.player.hp == before, "フレームの空回しだけで自然回復が成立した"

    # NATURAL_REGEN_INTERVAL ターン目より前はまだ回復しない。
    for _ in range(NATURAL_REGEN_INTERVAL - 1):
        engine.advance_world()
    assert engine.player.hp == before, (
        f"{NATURAL_REGEN_INTERVAL - 1} ターンで回復が成立した（frame 分まで turn が進んでいる）"
    )

    # ちょうど NATURAL_REGEN_INTERVAL ターン目で回復する。
    engine.advance_world()
    assert engine.player.hp == before + 1


def test_natural_regen_lands_exactly_on_interval_turn(engine: Engine) -> None:
    """フレームを挟まない場合、回復はちょうど NATURAL_REGEN_INTERVAL ターン目にしか来ない。

    契約 [S2.2]。上のテストが「早すぎる」を禁じるのに対し、こちらは
    「遅くならない・ちょうどよい」を守るガード。
    """
    _silence_hostiles(engine)
    engine.player.hp = engine.player.max_hp - 5
    before = engine.player.hp

    for _ in range(NATURAL_REGEN_INTERVAL - 1):
        engine.advance_world()
    assert engine.player.hp == before, "NATURAL_REGEN_INTERVAL ターン前に回復した"

    engine.advance_world()
    assert engine.player.hp == before + 1


# ------------------------------------------------------------- [S2.1] run summary

# run summary は実装者が形（dict / dataclass / 独自オブジェクト / 描画文字列）を
# 自由に選べる前提のため、summary という名前の実体を engine / game_state_data から
# 探し、(キー, 値) のペアに正規化して照合する。フィールド名そのものは固定しない。
_SUMMARY_NAME = re.compile(r"summary|result|stats|report", re.IGNORECASE)

# summary が属性ではなく引数不要メソッドとして実装された場合のために試す名前。
_SUMMARY_METHODS = (
    "run_summary",
    "build_run_summary",
    "create_run_summary",
    "make_run_summary",
    "get_run_summary",
    "last_run_summary",
    "game_over_summary",
    "run_result",
    "build_run_result",
    "get_run_result",
    "run_stats",
    "get_run_stats",
    "summary",
    "get_summary",
)


def _resolve_summary(engine: Engine) -> Any:
    """Engine から run summary の実体を取り出す。見つからなければ None。

    summary 名の属性が 1 つだけとは限らないため、複数候補を全部評価して
    「(キー, 値) として中身のあるもの」を最初に採用する。
    """
    candidates: list[Any] = []
    for holder in (engine, engine.game_state_data):
        candidates.extend(
            value for name, value in vars(holder).items() if _SUMMARY_NAME.search(name)
        )
    candidates.extend(
        attr for name in _SUMMARY_METHODS if callable(attr := getattr(engine, name, None))
    )

    resolved: list[Any] = []
    for value in candidates:
        if callable(value):
            try:
                params = inspect.signature(value).parameters.values()
            except (TypeError, ValueError):
                continue
            required = [
                p
                for p in params
                if p.default is inspect.Parameter.empty
                and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
            ]
            if required:
                continue
            try:
                value = value()
            except Exception:  # noqa: BLE001 - summary 以外の候補を弾くため
                continue
        if value is not None:
            resolved.append(value)

    for value in resolved:
        if len(_summary_pairs(value)) >= 2:
            return value
    return resolved[0] if resolved else None


def _summary_pairs(summary: Any) -> list[tuple[str, str]]:
    """summary を (小文字キー, 小文字値) のリストへ正規化する。

    dict / オブジェクト / シーケンス / 描画済み文字列のどれでも同じ照合ができる
    ようにし、区切り記号が無い chunk はキーと値の両方に採用する
    （"到達深度 4" のような表記でも数値照合できる）。
    """
    if isinstance(summary, dict):
        text = "\n".join(f"{key}: {value}" for key, value in summary.items())
    elif isinstance(summary, (list, tuple, set)):
        text = "\n".join(str(item) for item in summary)
    elif isinstance(summary, str):
        text = summary
    elif hasattr(summary, "__dict__"):
        text = "\n".join(f"{key}: {value}" for key, value in vars(summary).items())
    else:
        text = str(summary)

    pairs: list[tuple[str, str]] = []
    for chunk in re.split(r"[\n\r;、,]+", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        matched = re.match(r"^([^:=：]{1,48}?)\s*[:=：]\s*(.*)$", chunk)
        if matched:
            pairs.append((matched.group(1).strip().lower(), matched.group(2).strip().lower()))
        else:
            lowered = chunk.lower()
            pairs.append((lowered, lowered))
    return pairs


def _values_for(pairs: list[tuple[str, str]], pattern: str) -> list[str]:
    """キーが pattern に一致するエントリの値だけを返す。"""
    rx = re.compile(pattern, re.IGNORECASE)
    return [value for key, value in pairs if rx.search(key)]


def test_run_summary_reports_run_information(engine: Engine) -> None:
    """run summary から到達深度・撃破数・喰い得スキル数・経過ターン・死因が引ける。

    契約 [S2.1]。summary の形（dict / dataclass / 文字列）やキー名は実装の選択で
    あるため、ここでは「その情報が summary から取得できること」だけを契約にする。
    値の照合は、集計が既存の state から引かれる（[S2.1]「新たな追跡機構を増やさない」）
    ことを前提に、テスト側で用意した state との一致で見る。

    GAME_OVER への遷移そのものはこのテストの契約ではない（`test_zero_hp_*` が担当）
    なので前提として assert せず、summary の契約だけで落とす。
    """
    engine.dungeon_level = RUN_DEPTH
    engine.player.kill_counts = {"Test Slug": RUN_KILLS}
    engine.game_state_data.world_a_data["skills"] = list(RUN_DEVOURED_SKILLS)
    for _ in range(RUN_TURNS_BEFORE_DEATH):
        engine.advance_world()

    _kill_player(engine)

    summary = _resolve_summary(engine)
    assert summary is not None, (
        "run summary が見つからない。engine / game_state_data に summary 名（S2.1）の"
        "属性か、引数不要メソッド（例: run_summary）を用意する必要がある。"
        f"試した名前: {_SUMMARY_METHODS}"
    )
    pairs = _summary_pairs(summary)

    depth = _values_for(pairs, r"depth|level|dungeon|階層|深度|到達")
    assert depth, f"run summary に到達深度がない: {pairs}"
    assert any(str(RUN_DEPTH) in value for value in depth), (
        f"到達深度 {RUN_DEPTH} が summary にない: {depth}"
    )

    kills = _values_for(pairs, r"kill|撃破|討伐|討滅|撃殺")
    assert kills, f"run summary に撃破数がない: {pairs}"
    assert any(str(RUN_KILLS) in value for value in kills), (
        f"撃破数 {RUN_KILLS} が summary にない: {kills}"
    )

    devoured = _values_for(pairs, r"devour|devoured|obtained|喰|捕食|吞噬|获得")
    assert devoured, f"run summary に喰い得スキル数がない: {pairs}"
    assert any(
        str(len(RUN_DEVOURED_SKILLS)) in value
        or all(skill in value for skill in RUN_DEVOURED_SKILLS)
        for value in devoured
    ), f"喰い得スキル数 {len(RUN_DEVOURED_SKILLS)} 件が summary にない: {devoured}"

    elapsed = _values_for(pairs, r"turn|ターン|経過")
    assert elapsed, f"run summary に経過ターンがない: {pairs}"
    # 死亡した瞬間の turn 数は実装が死亡判定を入口のどこへ置くかで 1 差出うるため、
    # engine のカウンタと一致することを見る（engine.turns の値自体は硬記しない）。
    assert any(str(engine.turns) in value for value in elapsed), (
        f"経過ターン {engine.turns} が summary にない: {elapsed}"
    )

    cause = _values_for(pairs, r"cause|death|死因|死亡|死")
    assert cause, f"run summary に死因がない: {pairs}"
    assert any(value not in {"", "none", "null", "nan", "-"} for value in cause), (
        f"死因が空欄: {cause}"
    )
