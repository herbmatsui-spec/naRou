"""ゲーム本体の公開エントリポイント。

`Engine` の実装は `naRou.engine.engine` にあり、このモジュールは二つの役割を持つ。

1. 既存の `from naRou.game import Engine` / `from game import Engine` を壊さない再輸出
2. 出荷用の唯一の起動経路 `main()`

`pyproject.toml` のコンソールスクリプト `narou = "game:main"` と `Makefile` の
`run: python3 -m game` はどちらもここを指す。
"""

from __future__ import annotations

import os

from naRou.engine import Engine

__all__ = ["Engine", "main"]

_TRUTHY = ("1", "true", "yes", "on")


def _text_mode_requested(argv: list[str] | None) -> bool:
    """GPU/SDL を生成しないテキストモードを選ぶべきかを判定する。

    `run.py` はヘッドレス Linux を検出した時点で `NAROU_FORCE_TEXT=1` を設定する。
    """
    if argv is not None and "--text" in argv:
        return True
    return os.environ.get("NAROU_FORCE_TEXT", "").strip().lower() in _TRUTHY


def main(argv: list[str] | None = None) -> None:
    """ゲーム本体を起動する。

    既定は SDL/tcod を使う図形ループ。`--text` を指定するか、環境変数
    `NAROU_FORCE_TEXT` が真なら GPU/SDL を生成しないテキストモードで起動する。
    """
    if _text_mode_requested(argv):
        from naRou import main_text

        main_text.main()
        return

    from naRou.engine.engine import main as graphical_main

    graphical_main()


if __name__ == "__main__":
    # `python -m game` は統合システムメニューを起動する。main.py と同一の入口にするため
    # ここでも main.main() を呼ぶ。モジュール属性の main 関数と衝突しないよう別名で束縛する。
    from naRou import main as _menu

    _menu.main()