"""`naRou` パッケージ `__init__.py` のガード契約のリグレッションテスト。

`naRou/__init__.py` はソースチェックアウトでのみ `__path__` をリポジトリルートへ拡張し、
インストール済み wheel では発火してはならない。加えて `<root>/__init__.py` と
`<root>/naRou/__init__.py` は `[tool.setuptools.package-dir] naRou = "."` によって
wheel 上の同じパス `naRou/__init__.py` に重なるため、**どちらが採用されても**同じ結果に
なること（= 内容が一致していること）を固定する。この一致が崩れると採用順次第でガードが
黙って消え、仕様書が「ガードは出荷される」と主張しているのに wheel の中身がコメント 1 行
だけの状態に戻る。

wheel のビルド・展開は行わない（ネットワーク依存で数十秒）。代わりに、出荷時に
`naRou/__init__.py` へ置かれるファイルを site-packages 模倣ディレクトリへ直接コピーして
ガードの挙動を検証する。2 つの候補が同一内容である前提のもと、どちらが wheel に入るか
（setuptools の走査順）を決定する必要がない。
"""

from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_INIT = REPO_ROOT / "naRou" / "__init__.py"
ROOT_INIT = REPO_ROOT / "__init__.py"

# package-dir マッピング `naRou = "."` のもとで同じ wheel パスへ収束する 2 つのファイル。
# どちらが `naRou/__init__.py` として出荷されるか分からないため、両方を検証対象にする。
CANDIDATE_INITS = (PACKAGE_INIT, ROOT_INIT)

# spec S2.1 の契約にある、フラットレイアウトのルートモジュールを名前空間経由で到達する代表。
_CONTRACT_MODULES = ("constants", "engine", "item_system", "core_framework")

# site-packages には無関係な第三者が同居している状況を再現するための兄弟モジュール。ガードが
# インストール先で発火すると `import naRou.unrelated_thirdparty` が成功し、site-packages
# 全体が naRou の名前空間として露出していることが観測できる。
_SIBLING_MODULE = "unrelated_thirdparty"

_PROBE_PREFIX = "NAROU_PROBE:"

_PROBE_SOURCE_CHECKOUT = """
    import importlib
    import json
    import os

    import naRou

    _result = {
        "file": os.path.realpath(naRou.__file__),
        "path": [os.path.realpath(p) for p in naRou.__path__],
        "modules": {
            _name: os.path.realpath(importlib.import_module("naRou." + _name).__file__)
            for _name in ("constants", "engine", "item_system", "core_framework")
        },
    }

    print("NAROU_PROBE:" + json.dumps(_result))
    """

_PROBE_INSTALLED = """
    import importlib
    import json
    import os

    import naRou

    _result = {
        "file": os.path.realpath(naRou.__file__),
        "path": [os.path.realpath(p) for p in naRou.__path__],
    }

    _result["sibling_importable_directly"] = (
        importlib.import_module("unrelated_thirdparty").VALUE == 1
    )
    try:
        importlib.import_module("naRou.unrelated_thirdparty")
    except ModuleNotFoundError:
        _result["sibling_leaked_into_narou"] = False
    else:
        _result["sibling_leaked_into_narou"] = True

    print("NAROU_PROBE:" + json.dumps(_result))
    """


def _real(path: Path) -> str:
    return os.path.realpath(path)


def _run_probe(probe: str, *, cwd: Path, search_path: Path) -> dict:
    """隔離した副プロセスでプローブを実行し、観測結果を dict で返す。

    PYTHONPATH は `search_path` のみで上書きする。`sys.path` の先頭は cwd ('') で、
    PYTHONPATH はそれより後だがシステム site-packages より前なので、
    `import naRou` は必ずモック/チェックアウト側を掴む。掴んでいない場合は
    観測した `file` の realpath で必ず検出できる。
    """
    env = dict(os.environ)
    env.update(
        PYTHONPATH=str(search_path),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONIOENCODING="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(probe)],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert completed.returncode == 0, (
        f"probe failed (rc={completed.returncode})\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    for line in completed.stdout.splitlines():
        if line.startswith(_PROBE_PREFIX):
            return json.loads(line[len(_PROBE_PREFIX) :])
    pytest.fail(
        f"probe did not report a result\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )


def _fake_install(tmp_path: Path, init_source: Path) -> tuple[Path, Path]:
    """wheel から展開された `naRou/__init__.py` を模した site-packages を作る。"""
    site_packages = tmp_path / "site-packages"
    package_dir = site_packages / "naRou"
    package_dir.mkdir(parents=True)
    shutil.copyfile(init_source, package_dir / "__init__.py")
    (site_packages / f"{_SIBLING_MODULE}.py").write_text("VALUE = 1\n", encoding="utf-8")
    # ''（cwd）が sys.path の先頭になるため、ここに naRou を置かないことが
    # 「モジュールの出所が site-packages だけである」証明になる。
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    return site_packages, cwd


def test_root_modules_are_not_reachable_from_the_package_dir_alone() -> None:
    """ガードが本質であることの確認: `naRou/` だけを探しても root モジュールは解決されない。

    これが成り立たない（= naRou/ 内に 루ートモジュールが複製された）場合、
    下のソースチェックアウトのテストはガード無しでも通ってしまい空振りになる。
    """
    for name in _CONTRACT_MODULES:
        spec = importlib.machinery.PathFinder.find_spec(name, [str(REPO_ROOT / "naRou")])
        assert spec is None, (
            f"naRou/ から {name} が解決できてしまうため __path__ 拡張の検証が空振りになる"
        )


def test_source_checkout_extends_path_to_repo_root() -> None:
    """spec S2.1: ソースチェックアウトでは __path__ にリポジトリルートが入り契約を満たす。"""
    result = _run_probe(_PROBE_SOURCE_CHECKOUT, cwd=REPO_ROOT, search_path=REPO_ROOT)

    assert result["file"] == _real(PACKAGE_INIT), (
        f"ソースチェックアウトでは naRou/__init__.py が読まれる想定。実際: {result['file']}"
    )
    assert _real(REPO_ROOT) in result["path"], (
        f"naRou.__path__ にリポジトリルートが無い: {result['path']}"
    )
    root_prefix = _real(REPO_ROOT) + os.sep
    package_prefix = _real(PACKAGE_INIT.parent) + os.sep
    for name in _CONTRACT_MODULES:
        module_file = result["modules"][name]
        assert module_file.startswith(root_prefix), (
            f"naRou.{name} がリポジトリルート外から解決された: {module_file}"
        )
        assert not module_file.startswith(package_prefix), (
            f"naRou/{name}.py を naRou ディレクトリ内から拾った: {module_file}"
        )


@pytest.mark.parametrize(
    "init_source",
    CANDIDATE_INITS,
    ids=[p.relative_to(REPO_ROOT).as_posix() for p in CANDIDATE_INITS],
)
def test_installed_layout_does_not_extend_path(tmp_path: Path, init_source: Path) -> None:
    """spec S2.1: インストール済み wheel ではガードが発火せず、__path__ はパッケージ自身のみ。

    出荷時に `naRou/__init__.py` へ来るのは 2 候補のどちらでも構わないため、両方を
    パラメータ化して検証する。
    """
    site_packages, cwd = _fake_install(tmp_path, init_source)
    result = _run_probe(_PROBE_INSTALLED, cwd=cwd, search_path=site_packages)

    assert result["file"] == _real(site_packages / "naRou" / "__init__.py"), (
        "site-packages 側の naRou/__init__.py が読まれなかった"
        f"（リポジトリのコピーを掴んでいる疑い）: {result['file']}"
    )
    assert result["path"] == [_real(site_packages / "naRou")], (
        f"インストール済みでは __path__ はパッケージ自身のみを指すべき: {result['path']}"
    )
    assert _real(site_packages) not in result["path"], (
        "site-packages 全体が naRou の名前空間に漏出した"
    )
    assert result["sibling_importable_directly"] is True, "兄弟モジュールの配置が実演できていない"
    assert result["sibling_leaked_into_narou"] is False, (
        f"site-packages の {_SIBLING_MODULE} が naRou 名前空間から解決できてしまった"
    )


def test_candidate_inits_are_byte_identical() -> None:
    """2 つの候補は同一内容。乖離が採用順による黙っての欠落を生むため固定する。"""
    root_bytes = ROOT_INIT.read_bytes()
    package_bytes = PACKAGE_INIT.read_bytes()
    assert root_bytes == package_bytes, (
        f"{ROOT_INIT.name} と {PACKAGE_INIT.name} の内容が不一致。両者は wheel 上の "
        "naRou/__init__.py に重なるため、編集時は必ず両方を同期させること。"
    )
    shared = root_bytes.decode("utf-8")
    assert "__path__" in shared, "ガード（__path__ の拡張）が内容に含まれない"
    assert ".append(" in shared, "__path__ へ追加する処理が内容に含まれない"
    assert "pyproject.toml" in shared, "ソースチェックアウト判定の目印が内容に含まれない"


@pytest.mark.parametrize("init_source", CANDIDATE_INITS, ids=lambda p: p.name)
def test_guard_survives_import_as_a_plain_module(init_source: Path) -> None:
    """素のモジュールとして読んでも例外を出さない（`__path__` が無い実行を許容する）。

    `tests/` がリポジトリの `__init__.py` を親パッケージに持つため、pytest は
    `init_mod = importtestmodule(self.path / "__init__.py")` でルートの `__init__.py` を
    素のモジュール `__init__` として読み込む（`_pytest/python.py` の Package.setup）。
    このとき `__path__` は定義されておらず、ガードがそれに触れると `tests/` 配下の
    全テストが collection error になる。
    """
    spec = importlib.util.spec_from_file_location(
        "narou_init_plain_module_probe",
        init_source,
        submodule_search_locations=None,  # __init__.py でも package 扱いしない = __path__ 無し
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert not hasattr(module, "__path__"), "素のモジュールとして読めたことの前提が崩れた"
    # 自己位置付けの成果: どちらの配置でも同じリポジトリルートを導出する。
    assert module._SOURCE_ROOT == _real(REPO_ROOT)
    assert list(module.__dict__.get("__path__", [])) == [], "__path__ を生成してはいけない"
