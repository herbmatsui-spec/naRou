"""バランス計測器の「正直さ」リグレッションテスト。

対象仕様: ``docs/compose/spec/run-end-state.md`` の [S1.3] / [S2.3] / [S2.4]。

計測器が「絶対勝利」をバランス良好と判定していた問題を固定する。
各テストは 1 つの契約に対応する。

1. ``test_lopsided_setup_is_not_reported_balanced``    -> [S2.3] 明示的に偏った設定は FAIL
2. ``test_fair_setup_is_reported_balanced``            -> [S2.3] 正しい設定は PASS（全部を FAIL にするのは是正ではない）
3. ``test_check_standards_reports_yaml_violations``    -> [S2.3] check_standards が YAML 違反を issues に列挙する
4. ``test_fresh_full_validation_does_not_claim_pass`` -> [S2.3] 現状の数値で走らせると PASS が返らない
5. ``test_committed_balance_report_is_not_stale``      -> [S2.4] コミット済みレポートが再実行結果と一致する
6. ``test_simulate_battle_is_not_a_bare_arena``        -> [S2.3] 敵 AI と turn ベース自然回復を含む実戦ループ

``balance_report.json`` / ``balance_report.html`` は git 追跡対象なので、
本ファイルは CWD をリポジトリルートに固定したまま、生成物を必ず復元する。
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import random
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from tests.balance_simulator import BalanceChecker, BalanceSimulator

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STANDARDS_PATH = os.path.join(REPO_ROOT, "data", "balance_standards.yaml")
COMMITTED_REPORT_PATH = os.path.join(REPO_ROOT, "balance_report.json")

# git 追跡対象。テスト中に書き換えてはならない。
TRACKED_REPORT_FILES = ("balance_report.json", "balance_report.html")

# 乱数は Python 標準の random モジュール (systems.CombatSystem.calculate_melee_attack が使用)。
# 特定の結果に依存するテストはここで固定する。
SEED = 20261004

# [S2.3] の「明示的に偏った設定」。
# 実測: Lv10 プレイヤーは Lv1 オークに対して与ダメージ約51 / 被ダメージ約3.4（約15倍）、
#       勝率 1.0 だが、現行実装はこれを "is_balanced": true に stamped する。
LOPSIDED_PLAYER_LEVEL = 10
LOPSIDED_MONSTER = "orc"

# [S2.3] の「正しい設定」の候補。
# いずれも現状の計測でもモンスターがプレイヤーへ実質的なダメージを与え、
# 戦闘が長引かない（100ターンで打ち切られない）組合せ。
FAIR_MATCHUPS = (
    (3, "minotaur"),
    (5, "minotaur"),
    (1, "orc"),
    (5, "orc"),
    (5, "goblin"),
)

# check_standards に渡す実測値obsの候補形。
# 実装がどのシグネチャ／どのデータ形を取るかは実装次第なので、複数試す。
OUT_OF_RANGE_HIGH = 99999
OUT_OF_RANGE_LOW = 1

# 「実戦ループ」であって「アリーナ近似」ではないことを判定するための目印。
# 実エンジン側の呼び出し名 (engine/engine.py) と、
# 両者が互いを直接叩いてしまう場合に現れる呼び出し名。
PLAYER_ACTION_HOOKS = ("player_act",)
WORLD_ADVANCE_HOOKS = ("advance_world", "process_ai")
BARE_ARENA_CALL = "calculate_melee_attack"


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _repo_root_cwd():
    """エンティティ生成は ``config.yaml`` / ``data/monsters.yaml`` を CWD 相対で読む。

    CWD を変えると計測値そのものが変わるため、計測は必ずリポジトリルートで行う。
    """
    previous = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        yield
    finally:
        os.chdir(previous)


@pytest.fixture(scope="module")
def fresh_validation(tmp_path_factory):
    """``run_full_validation()`` を 1 度だけ実行して最新レポートを返す。

    ``balance_report.json`` は ``output_path`` で一時ディレクトリへ逃がす。
    ``generate_html_report`` は出力先に CWD をハードコードしているため、
    追跡対象ファイルは実行前後で必ず復元する（失敗時も finally で復元される）。
    """
    out_dir = tmp_path_factory.mktemp("balance_validation")
    snapshots = {
        name: _read_bytes_or_none(os.path.join(REPO_ROOT, name)) for name in TRACKED_REPORT_FILES
    }
    previous = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        random.seed(SEED)
        simulator = BalanceSimulator()
        report = simulator.run_full_validation(output_path=str(out_dir / "balance_report.json"))
        yield report
    finally:
        os.chdir(previous)
        for name, blob in snapshots.items():
            _restore_bytes(os.path.join(REPO_ROOT, name), blob)


def _read_bytes_or_none(path: str) -> bytes | None:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as handle:
        return handle.read()


def _restore_bytes(path: str, blob: bytes | None) -> None:
    if blob is None:
        if os.path.exists(path):
            os.remove(path)
        return
    with open(path, "wb") as handle:
        handle.write(blob)


# ---------------------------------------------------------------------------
# 1. 偏った設定は FAIL になること [S2.3]
# ---------------------------------------------------------------------------


def test_lopsided_setup_is_not_reported_balanced():
    """プレイヤーがモンスターを決定的に凌駕する設定は「バランス良好」であってはならない。

    契約 ([S2.3]): 「明示的に偏った状況を渡すと FAIL になる」
    ／「勝率が 1.0 に張り付く場合は FAIL とする」「絶対勝利」を PASS と扱わない。

    現行実装は Lv10 vs オークでも win_rate 1.0・与/被ダメージ比 約15倍のまま
    ``"is_balanced": true`` を返すため、このテストは現状 FAIL する。
    """
    random.seed(SEED)
    simulator = BalanceSimulator()
    result = simulator.simulate_battle(
        player_level=LOPSIDED_PLAYER_LEVEL,
        monster_type=LOPSIDED_MONSTER,
        trials=12,
        expected_win_rate=0.7,
    )

    dealt = result["avg_dmg_dealt"]
    taken = result["avg_dmg_taken"]
    ratio = dealt / taken if taken else float("inf")

    assert not result["is_balanced"], (
        f"Lv{LOPSIDED_PLAYER_LEVEL} vs {LOPSIDED_MONSTER} は与/被ダメージ比 {ratio:.1f} 倍・"
        f"勝率 {result['win_rate']} と著しく偏っているのに "
        f'"is_balanced": true と判定された。{json.dumps(result, ensure_ascii=False)}'
    )


# ---------------------------------------------------------------------------
# 2. 正しい設定は PASS になること [S2.3]
# ---------------------------------------------------------------------------


def test_fair_setup_is_reported_balanced():
    """「全部を FAIL にする判定器」は是正ではなく、同じ故障を別の形で持つゴム印である。

    契約 ([S2.3]): 判定器は「バランス良好」と「プレイヤーが常に勝つ」を区別できる。

    現状の実測では、この 5 組合せのうち Lv3 vs ミノタウラスのみが
    ``expected_win_rate=0.5`` に対して ``is_balanced: true`` になる
    （他は勝率 1.0 で張り付く）。したがってこのテストは現状 PASS する。
    判定器が全部を FAIL にする変更をした場合に落ちる。
    """
    simulator = BalanceSimulator()
    verdicts: dict[tuple[int, str], dict] = {}

    for level, monster in FAIR_MATCHUPS:
        random.seed(SEED)
        verdicts[(level, monster)] = simulator.simulate_battle(
            player_level=level,
            monster_type=monster,
            trials=8,
            expected_win_rate=0.5,
        )

    balanced = [key for key, res in verdicts.items() if res["is_balanced"]]

    assert balanced, (
        "対等な（互角に近い）設定が 1 つも PASS と判定されなかった。"
        "判定が全部を FAIL にするゴム印に変わっていないか確認する。"
        f" 判定結果: {json.dumps({f'lv{k[0]}_{k[1]}': v['is_balanced'] for k, v in verdicts.items()}, ensure_ascii=False)}"
    )


# ---------------------------------------------------------------------------
# 3. check_standards が YAML 違反を列挙すること [S2.3]
# ---------------------------------------------------------------------------


def test_check_standards_reports_yaml_violations():
    """``data/balance_standards.yaml`` の基準値と実測値を照合し、違反を issues に列挙すること。

    契約 ([S2.3]): 「``BalanceChecker.check_standards`` を実装し、YAML の基準値と実測値を照合する。
    最低限 ``standards.levels`` の min/max HP・攻撃と、``economy.max_gold_per_dungeon_floor``
    を実際に比較し、違反を ``issues`` に列挙する」

    現状の実装は ``issues = []`` とコメントだけの stub で、実測値を受け取る経路が無く
    常に PASS を返すため、このテストは現状 FAIL する。
    実測値の渡し方は実装に委ねられているので、引数名とデータ形を反射で探す。
    """
    checker = BalanceChecker(standards_path=STANDARDS_PATH)
    levels = checker.standards["standards"]["levels"]
    assert levels, "data/balance_standards.yaml の standards.levels が読めていない"

    result = _check_standards_with_observations(checker)

    assert result["status"] != "PASS", (
        "基準値を大きく外れた実測値を渡したのに PASS が返った。"
        f" 戻り値: {json.dumps(result, ensure_ascii=False, default=str)}"
    )
    assert result["issues"], (
        "違反があるのに issues が空だった。"
        f" 戻り値: {json.dumps(result, ensure_ascii=False, default=str)}"
    )

    issues_text = json.dumps(result["issues"], ensure_ascii=False, default=str)
    assert "10" in issues_text or str(OUT_OF_RANGE_HIGH) in issues_text, (
        f"issues が外れ値を指していない: {issues_text}"
    )


def _out_of_range_observations() -> list[dict]:
    """上限・下限を両方大きく外れた統計（実測値の候補形）を返す。"""
    high = {
        "level": 10,
        "hp": OUT_OF_RANGE_HIGH,
        "max_hp": OUT_OF_RANGE_HIGH,
        "min_hp": OUT_OF_RANGE_HIGH,
        "attack": OUT_OF_RANGE_HIGH,
        "max_attack": OUT_OF_RANGE_HIGH,
        "min_attack": OUT_OF_RANGE_HIGH,
    }
    low = {
        "level": 5,
        "hp": OUT_OF_RANGE_LOW,
        "max_hp": OUT_OF_RANGE_LOW,
        "min_hp": OUT_OF_RANGE_LOW,
        "attack": OUT_OF_RANGE_LOW,
        "max_attack": OUT_OF_RANGE_LOW,
        "min_attack": OUT_OF_RANGE_LOW,
    }
    return [
        {"levels": {10: high, 5: low}},
        {10: high, 5: low},
        {"10": high, "5": low},
        [high, low],
        {"entities": [high, low]},
    ]


def _injection_param_names(func) -> list[str]:
    return [name for name in inspect.signature(func).parameters if name != "self"]


def _check_standards_with_observations(checker: BalanceChecker) -> dict:
    """``check_standards`` に実測値を渡して結果を返す。

    実測値の渡し方は実装に委ねられているので、
    ``check_standards`` の追加引数 → ``__init__`` の追加引数の順に反射で探す。
    """
    attempts: list[tuple[str, object]] = []
    for name in _injection_param_names(BalanceChecker.check_standards):
        attempts.append(("check_standards", name))
    for name in _injection_param_names(BalanceChecker.__init__):
        if name != "standards_path":
            attempts.append(("__init__", name))

    if not attempts:
        pytest.fail(
            "BalanceChecker.check_standards に実測値を受け取る引数が存在しない。"
            " [S2.3] は「YAML の基準値と実測値を照合すること」を要求しているため、"
            " 観測統計を受け取る経路（check_standards の引数、またはコンストラクタの引数）が要る。"
            f" 現在のシグネチャ: check_standards{inspect.signature(BalanceChecker.check_standards)}, "
            f"__init__{inspect.signature(BalanceChecker.__init__)}"
        )

    method_names = [name for where, name in attempts if where == "check_standards"]
    ctor_names = [name for where, name in attempts if where == "__init__"]

    for payload in _out_of_range_observations():
        for name in ctor_names:
            try:
                return BalanceChecker(
                    standards_path=STANDARDS_PATH, **{name: payload}
                ).check_standards()
            except TypeError:
                continue
        for name in method_names:
            try:
                return checker.check_standards(**{name: payload})
            except TypeError:
                continue

    pytest.fail(
        "実測値を受け取る引数が見つかったが、どのデータ形でも受け付けられなかった。"
        f" 試行した引数: {attempts}"
    )


# ---------------------------------------------------------------------------
# 4. 現状の数値で PASS が返らないこと / 古い PASS を残さないこと [S2.3][S2.4]
# ---------------------------------------------------------------------------


def test_fresh_full_validation_does_not_claim_pass(fresh_validation):
    """計測器が結果を PASS に固定している仕組みをやめること。

    契約 ([S2.3]): 「測定器が PASS を返す仕組みをやめる」
    ／「現状の数値で走らせると PASS が返らない」

    現状のコードは3シナリオすべてを balanced とし、check_standards も無条件 PASS を返すため
    ``summary`` は常に "PASS" になる。このテストは現状 FAIL する。
    """
    assert fresh_validation["summary"] != "PASS", (
        'run_full_validation() が "summary": "PASS" を返した。'
        " 現在の数値（Lv1 スライム / Lv3 ゴブリン / Lv5 オークはいずれも勝率 1.0）で"
        " バランス良好は成立しない。summary と各シナリオの判定を確認すること: "
        f"{json.dumps(fresh_validation, ensure_ascii=False, indent=2)}"
    )


def test_committed_balance_report_is_not_stale(fresh_validation):
    """コミット済み ``balance_report.json`` の summary が再実行結果と一致すること。

    契約 ([S2.4]): 「コミット済み ``balance_report.json`` の ``summary`` が
    再実行結果と一致すること（古い PASS を残さない）」

    計測器を正直にした後、コミット済みファイルが古い "PASS" のままだとここが落ちる。
    """
    with open(COMMITTED_REPORT_PATH, encoding="utf-8") as handle:
        committed = json.load(handle)

    assert committed["summary"] == fresh_validation["summary"], (
        f'コミット済み balance_report.json は summary="{committed["summary"]}" だが、'
        f'再実行結果は summary="{fresh_validation["summary"]}"。'
        " 古い PASS を再コミットしていないか確認する。"
    )


# ---------------------------------------------------------------------------
# 5. simulate_battle が実戦ループを反映していること [S2.3]
# ---------------------------------------------------------------------------


def _analyze_calls(cls: type) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """クラス内のメソッドが呼び出ている名前を集める (AST ベース)。

    戻り値は ``(全メソッド→呼び出し名, ``self`` への呼び出し名)``。
    コメントと docstring は AST に現れないので、ソース文字列の ``count`` と
    違って「書いただけ」で判定を満たさない。
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(cls)))
    calls: dict[str, set[str]] = {}
    local: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        called: set[str] = set()
        on_self: set[str] = set()
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            func = inner.func
            if isinstance(func, ast.Attribute):
                called.add(func.attr)
                if isinstance(func.value, ast.Name) and func.value.id == "self":
                    on_self.add(func.attr)
            elif isinstance(func, ast.Name):
                called.add(func.id)
        calls[node.name] = called
        local[node.name] = on_self
    return calls, local


def _reachable_methods(calls: dict[str, set[str]], root: str) -> set[str]:
    """``root`` から呼び出し経由で到達できるメソッド名 (``root`` 自身を含む)。"""
    seen: set[str] = set()
    pending = [root]
    while pending:
        name = pending.pop()
        if name in seen or name not in calls:
            continue
        seen.add(name)
        pending.extend(calls[name])
    return seen


def test_simulate_battle_is_not_a_bare_arena():
    """``simulate_battle`` が敵 AI と turn ベース自然回復を含む実戦ループであること。

    契約 ([S2.3]): 「``simulate_battle`` は実際の戦闘ループの要素を含める。
    敵の AI 行動選択と、自然回復（S2.2 の turn ベース規則）を入れ…
    専用のアリーナ近似（両者が ``calculate_melee_attack`` を交互に呼ぶだけ）はやめる」

    判定はソース文字列ではなく **AST の呼び出し位置** で行う。
    ``inspect.getsource`` の ``str.count`` では、コメントや docstring に
    メソッド名を書いておくだけで通ってしまう (``calculate_melee_attack`` の
    出現回数が 0 でも ``< 2`` は成立する)。AST ならコメントは解析対象にならない。

    さらに ``simulate_battle`` から**到達できる**メソッドだけを調べるので、
    呼ばれていない残骸メソッドに呼び出しを追加しても通らない。
    実戦ループの入口 (``player_act`` と世界進行) は ``self`` 以外への呼び出しを
    要求するため、ローカルに同名メソッドを定義して凌ぐこともできない。

    数値として観測できない指標 (自然回復の実効量など) は計測側で公開されていないため、
    ここが構造の保証である。実戦ループの実挙動は
    ``test_balance_simulator_execution`` (被与ダメージ比) が数値で押さえる。
    """
    calls, local = _analyze_calls(BalanceSimulator)
    reachable = _reachable_methods(calls, "simulate_battle")

    for label, hooks in (
        ("プレイヤー行動", PLAYER_ACTION_HOOKS),
        ("世界進行 (敵 AI と自然回復)", WORLD_ADVANCE_HOOKS),
    ):
        called = sorted(
            hook for hook in hooks if any(hook in calls[name] - local[name] for name in reachable)
        )
        assert called, (
            f"simulate_battle から到達できるコードが実戦ループの{label}の入口 "
            f"({' / '.join(hooks)}) を誰も呼んでいない。"
            " マップ・敵 AI・turn 進行を含まないアリーナ計算のままである。"
        )

    # 両者が直接 ``calculate_melee_attack`` を叩き合うアリーナ近似は禁止。
    arena_sites = sum(1 for name in reachable if BARE_ARENA_CALL in calls[name])
    assert arena_sites < 2, (
        f"simulate_battle から到達できるコードに {BARE_ARENA_CALL} の呼び出しが "
        f"{arena_sites} 箇所ある。"
        " 両者が互いを直接叩くアリーナ近似のままで、実戦ループを含んでいない。"
    )
