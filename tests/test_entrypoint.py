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

# メニュー 1 番を選んだときだけ出る文。0 番・3 番では出ない。
_MENU_ONE_LAUNCH = "ゲーム本編を起動します"

# engine.main() が SDL コンテキストを作れずテキストモードへ落としたときのログ。
# 図形ループまで到達した証拠であり、メニュー 3 番（main_text 直叩き）には出ない。
_SDL_TEXT_MODE_FALLBACK = "falling back to text mode"

# MSDF アトラス生成に使う TTF の探索先。固定パスに依存せず辞書順で最初の一致を採る。
_FONT_DIRS = (
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "~/.fonts",
    "~/.local/share/fonts",
    "/Library/Fonts",
    "/System/Library/Fonts",
    "C:/Windows/Fonts",
)

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


# naRou.__path__ がインストール時に site-packages を露出しないことの回帰試験は
# tests/test_narou_package_init.py にある（ソースチェックアウトと導入済みレイアウトの両方）。


def _distribution_names(requirements: list[str]) -> set[str]:
    """`tcod>=21.2.1` のような requirement 文字列から配布名だけを取り出す。"""
    return {
        re.split(r"[<>=!~\[; ]", requirement, maxsplit=1)[0].strip() for requirement in requirements
    }


def _parse_requirements_file(filename: str) -> set[str]:
    text = (REPO_ROOT / filename).read_text(encoding="utf-8")
    return _distribution_names(
        [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
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


def _ttf_fonts() -> list[Path]:
    """探索先ディレクトリの順に走査し、各ディレクトリ内で辞書順に TTF を列挙する。"""
    found: dict[str, Path] = {}
    for directory in _FONT_DIRS:
        for candidate in sorted(Path(directory).expanduser().rglob("*.ttf")):
            found.setdefault(str(candidate), candidate)
    return list(found.values())


def test_msdf_atlas_builds_without_missing_dependency():
    """フォントアトラス生成が宣言済み依存だけで完了する。"""
    try:
        import scipy
    except ImportError as exc:
        pytest.fail(f"宣言済み依存 scipy が import できない: {exc}")

    from core.msdf_atlas import MSDFAtlas

    fonts = _ttf_fonts()
    if not fonts:
        pytest.fail("TTF フォントが 1 つも無い: " + " / ".join(_FONT_DIRS) + " を導入する")

    rejected = []
    for font in fonts:
        atlas = MSDFAtlas(64, 2)
        try:
            atlas.generate_atlas(str(font), "Hello naRou", 16, 2)
        except Exception as exc:  # 候補が実装に対応しないだけなので次へ回す
            rejected.append(f"{font}: {type(exc).__name__}: {exc}")
            continue
        if not atlas.glyphs or atlas.texture is None:
            rejected.append(f"{font}: グリフまたはテクスチャが空")
            continue
        return

    pytest.fail("どの TTF からもアトラスを生成できなかった:\n" + "\n".join(rejected))


def test_python_dash_m_game_opens_the_menu():
    """Makefile の run: と pyproject の narou スクリプトが前提とする起動経路。"""
    result = _run(["-m", "game"], stdin="0\n")
    assert result.returncode == 0, result.stderr
    assert "統合システムメニュー" in result.stdout


def test_menu_option_one_enters_the_game_in_text_mode():
    """README の手順通り: メニュー 1 番でゲームループに入れる。

    1 番は `prompt_accessibility()` -> `game.main()` を呼び、`game.main()` は
    `engine.main()` の図形ループへ入る。SDL を殺すと例外ハンドラが
    `get_text_mode_enabled()` を見てテキストモードへ落とす。

    `prompt_accessibility()` が触るのは色覚と難易度だけで `accessibility.text_mode` を
    書かないため、テキストモードは `feature_flags.set_text_mode_enabled()`（
    `get_text_mode_enabled()` が最初に見る方）で有効化してからメニューを起動する。
    """
    result = _run(
        [
            "-c",
            "import feature_flags; feature_flags.set_text_mode_enabled(True); import main; main.main()",
        ],
        stdin="1\n\n\nq\n0\n",
        env_overrides={"SDL_VIDEODRIVER": "__invalid__", "NAROU_FORCE_TEXT": ""},
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "重大なエラー" not in combined, combined
    assert "module 'game' has no attribute 'main'" not in combined, combined
    assert _MENU_ONE_LAUNCH in combined, combined
    assert _SDL_TEXT_MODE_FALLBACK in combined, combined
    assert _TEXT_MODE_GUIDE in combined, combined


def test_menu_other_choices_never_enter_the_game_loop():
    """メニュー 0/3 番ではゲームループに入らないことの対照群。

    対照群が空振りしないよう、3 番が実際に `main_text` まで到達したことと、0 番が
    何も起動しなかったことをを確認する。3 番も同じガイド文字列を出すため、ここでは
    `falling back to text mode`（1 番だけの経路）が現れないことを対照の根拠にする。
    """
    for choice, stdin in (("3", "3\n\n\nq\n0\n"), ("0", "0\n")):
        result = _run(
            [
                "-c",
                "import feature_flags; feature_flags.set_text_mode_enabled(True); import main; main.main()",
            ],
            stdin=stdin,
            env_overrides={"SDL_VIDEODRIVER": "__invalid__", "NAROU_FORCE_TEXT": ""},
        )
        combined = result.stdout + result.stderr
        assert result.returncode == 0, combined
        assert _MENU_ONE_LAUNCH not in combined, combined
        assert _SDL_TEXT_MODE_FALLBACK not in combined, combined
        assert (_TEXT_MODE_GUIDE in combined) is (choice == "3"), combined


def test_game_main_text_mode_is_selected_by_command_line_flag():
    """`narou --text` は main() を引数なしで呼ぶため sys.argv から判定される。"""
    result = _run(
        ["-c", "import game; game.main()", "--text"],
        stdin="q\n",
        env_overrides={"SDL_VIDEODRIVER": "__invalid__", "NAROU_FORCE_TEXT": ""},
        timeout=45,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
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
