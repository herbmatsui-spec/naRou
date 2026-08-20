"""main_text.py - GPU/SDL 不要のテキストモード専用エントリ。

`python main_text.py` で起動。内部的に game.py(=tcod ライブラリ) を import するが、
SDL/WebGL/WebGPU コンテキストは一切生成しないため、GPU のない環境でも動作する。
"""

from __future__ import annotations


def main() -> None:
    import game
    from core.text_renderer import TextRenderer

    engine = game.Engine()
    tr = TextRenderer(80, 50)
    # 初回描画
    engine.render_to_text(tr)
    # テキスト入力ループへ
    engine.run_text_mode(80, 50)


if __name__ == "__main__":
    main()
