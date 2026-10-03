"""出荷経路の回帰テスト。

clone 直後に「捐款のゲームが起動できるか」を固定する。
以下の不具合の再現試験として機能する:

- `naRou` が未追跡のシンボリックリンクしか無く、fresh clone でインポートが全滅する
- `game.main()` が存在せず、統合メニューの 1 番が `AttributeError` で落ちる
- `python -m game` / `narou` コマンドが no-op になる
- 宣言済み依存が実装に存在せず、フォントアトラス生成が ModuleNotFoundError で落ちる
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# テキストモードの操作ガイド。run_text_mode が出す描画なので、テキストモードが
# 実際に一周したことを的唯一に観測できる目印になる（engine.log() は画面内ログで
# stdout には出ない）。
_TEXT_MODE_GUIDE = "q:終了"

# ディストリビューション名 -> インポート名
_IMPORT_NAMES = {
    "tcod": "tcod",
    "PyYAML": "yaml",
    "cryptography": "cryptography",
    "numpy": "numpy",
    "pydantic": "pydantic",
    "python-dotenv": "dotenv",
    "Pillow": "PIL",
    "scipy": "scipy",
}

# 依存を宣言するファイル
_REQUIREMENT_FILES = ("pyproject.toml", "requirements.txt")


def _run(args, stdin: str, env_overrides: dict[str, str] | None = None, timeout: int = 120):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    if env_overrides:
        env.update(env_overrides)
    result = subprocess.run(
        [sys.executable, *args],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=timeout,
    )
    result.stdout = _ANSI.sub("", result.stdout)
    result.stderr = _ANSI.sub("", result.stderr)
    return result


def test_narou_package_is_a_directory_not_a_symlink():
    narou_dir = REPO_ROOT / "naRou"
    assert narou_dir.exists(), "naRou パッケージディレクトリが存在しない"
    assert not narou_dir.is_symlink(), "naRou は依然としてシンボリックリンク。fresh clone で壊れる"


def test_narou_import_resolves_root_modules():
    """pyproject と同じ名前空間で、naRou 配下に無いルートモジュールを import できる。"""
    import naRou.constants
    import naRou.core_framework
    import naRou.engine
    import naRou.item_system

    assert Path(naRou.engine.__file__).resolve().parent.parent == REPO_ROOT
    assert naRou.constants.MAP_WIDTH > 0


def test_game_module_exposes_callable_main():
    import game

    assert callable(game.main), "game.main が存在しないため narou コマンドとメニュー 1 番が壊れる"


def test_narou_dunder_path_stays_inside_package_when_installed():
    """インストール済み wheel では site-packages 全体が naRou に露出してはいけない。"""
    import naRou

    for entry in naRou.__path__:
        assert Path(entry).resolve() != REPO_ROOT.parent, (
            "naRou.__path__ がリポジトリの外へ漏れている。インストール後に site-packages を"
            "naRou の名前空間として公開してしまう"
        )


def _distribution_names(requirements: list[str]) -> set[str]:
    """`tcod>=21.2.1` のような requirement 文字列から配布名だけを取り出す。"""
    return {re.split(r"[<>=!~\[; ]", requirement, maxsplit=1)[0].strip() for requirement in requirements}


def _parse_requirements_file(filename: str) -> set[str]:
    text = (REPO_ROOT / filename).read_text(encoding="utf-8")
    return _distribution_names(
        [
            line
            for line in text.splitlines()
            if line.strip() and not line.startswith("#")
        ]
    )


def _declared_dependencies() -> set[str]:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = _distribution_names(pyproject["project"]["dependencies"])
    for filename in ("requirements.txt", "requirements-lock.txt"):
        listed = _parse_requirements_file(filename)
        assert listed == declared, (
            f"pyproject.toml と {filename} の依存が不一致: 差分={declared ^ listed}"
        )
    return declared


def test_declared_dependencies_are_importable():
    """3つの宣言ファイルと実際の import が食い違わない。"""
    for dist_name in sorted(_declared_dependencies()):
        module_name = _IMPORT_NAMES.get(dist_name)
        if module_name is None:
            continue
        try:
            __import__(module_name)
        except ImportError as exc:  # pragma: no cover - 失敗時に初めて通る
            pytest.fail(f"宣言済み依存 {dist_name} ({module_name}) を import できない: {exc}")


def test_msdf_atlas_builds_without_missing_dependency():
    """フォントアトラス生成が宣言済み依存だけで完了する。"""
    pytest.importorskip("scipy")
    from core.msdf_atlas import MSDFAtlas

    font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    if not font.exists():
        pytest.skip("システムに TTF フォントが無い")

    atlas = MSDFAtlas(64, 2)
    atlas.generate_atlas(str(font), "Hello naRou", 16, 2)
    assert atlas.glyphs, "アトラスにグリフが1つも登録されていない"
    assert atlas.texture is not None, "アトラステクスチャが生成されていない"


def test_python_dash_m_game_opens_the_menu():
    """Makefile の run: と pyproject の narou スクリプトが前提とする起動経路。"""
    result = _run(["-m", "game"], stdin="0\n")
    assert result.returncode == 0, result.stderr
    assert "統合システムメニュー" in result.stdout


def test_menu_option_one_enters_the_game_in_text_mode():
    """README の手順通り: メニュー 1 番でゲームループに入れる。"""
    result = _run(
        ["main.py"],
        stdin="1\n\n\nq\n",
        env_overrides={"NAROU_FORCE_TEXT": "1"},
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "重大なエラー" not in combined, combined
    assert "module 'game' has no attribute 'main'" not in combined, combined
    assert _TEXT_MODE_GUIDE in combined, combined


def test_game_main_text_mode_is_selected_by_environment():
    """run.py がヘッドレスで設定する環境変数が、実装側で効いていること。"""
    result = _run(
        ["-c", "import game; game.main()"],
        stdin="q\n",
        env_overrides={"NAROU_FORCE_TEXT": "1"},
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert _TEXT_MODE_GUIDE in combined, combined
