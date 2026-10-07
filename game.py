"""ゲーム本体の公開エントリポイント。

`Engine` の実装は `naRou.engine.engine` にあり、このモジュールは二つの役割を持つ。

1. 既存の `from naRou.game import Engine` / `from game import Engine` を壊さない再輸出
2. 出荷用の唯一の起動経路 `main()`

`pyproject.toml` のコンソールスクリプト `narou = "game:main"` と `Makefile` の
`run: python3 -m game` はどちらもここを指す。
"""

from __future__ import annotations

import os
import sys

from naRou.engine import Engine

__all__ = ["Engine", "main"]

# TODO: Achievement check - achievement_manager.check_all_achievements to be integrated in naRou.engine.engine

def use_pet_evolution_stone(player, stone_id):
    """ペット進化石を使用するフック (Step 46)"""
    # Actual implementation in naRou.engine.engine
    pass


def use_alchemy_lab(player, recipe_id):
    """錬金術実験室を使用するフック (Step 68)"""
    # Actual implementation in naRou.engine.engine
    pass


# TODO: Reincarnation option - reincarnation_system.start_reincarnation to be integrated in naRou.engine.engine

# TODO: Reincarnation dungeon manager - reincarnation_dungeon_manager to be integrated in naRou.engine.engine

# TODO: Reincarnation XP penalty - reincarnation_system.apply_xp_penalty to be integrated in naRou.engine.engine
_TRUTHY = ("1", "true", "yes", "on")


def _text_mode_requested(argv: list[str] | None) -> bool:
    """GPU/SDL を生成しないテキストモードを選ぶべきかを判定する。

    `run.py` はヘッドレス Linux を検出した時点で `NAROU_FORCE_TEXT=1` を設定する。
    """
    if argv is None:
        # コンソールスクリプトは `main()` を引数なしで呼ぶので、自身は syscall の
        # 引数を見ずに --text を受け取れない。ここでは sys.argv へ委譲する。
        argv = sys.argv[1:]
    if "--text" in argv:
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
