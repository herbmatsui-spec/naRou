"""TextRenderer - GPU不要のテキスト(ASCII)描画クラス。

Step 1-8 で構築。ANSI エスケープシーケンスを用いて端末に直接描画するため、
SDL/WebGL/WebGPU などの GPU 依存コンポーネントを一切使わずにゲームを表示できる。
"""

from __future__ import annotations


class TextRenderer:
    """Step1: GPU不要のテキスト(ASCII)レンダラ。"""

    def __init__(self, width: int, height: int) -> None:
        # Step2: 描画グリッド（文字と色）を保持
        self.width = width
        self.height = height
        self.chars: list[list[str]] = [[" "] * width for _ in range(height)]
        self.colors: list[list[tuple[int, int, int]]] = [
            [(255, 255, 255)] * width for _ in range(height)
        ]
        # Step8: ルックカーソル位置
        self.cursor: tuple[int, int] | None = None

    # Step3: 単一タイル描画
    def draw_tile(
        self, x: int, y: int, char: str, color: tuple[int, int, int] = (255, 255, 255)
    ) -> None:
        if 0 <= y < self.height and 0 <= x < self.width:
            self.chars[y][x] = char[:1]
            self.colors[y][x] = color

    # Step4: 文字列描画
    def draw_text(
        self, x: int, y: int, string: str, color: tuple[int, int, int] = (255, 255, 255)
    ) -> None:
        for i, ch in enumerate(string):
            self.draw_tile(x + i, y, ch, color)

    # Step5: クリア
    def clear(self) -> None:
        for y in range(self.height):
            for x in range(self.width):
                self.chars[y][x] = " "
                self.colors[y][x] = (255, 255, 255)

    # Step7: RGB -> 最寄り256色コード
    def _nearest_256(self, r: int, g: int, b: int) -> int:
        def to_6(v: int) -> int:
            return min(5, max(0, round(v / 255.0 * 5)))

        return 16 + 36 * to_6(r) + 6 * to_6(g) + to_6(b)

    # Step6 + Step8: 端末へ出力
    def present(self) -> None:
        lines: list[str] = []
        for y in range(self.height):
            line: list[str] = []
            for x in range(self.width):
                r, g, b = self.colors[y][x]
                code = self._nearest_256(r, g, b)
                ch = self.chars[y][x]
                if self.cursor == (x, y):
                    line.append(f"\x1b[7m{ch}\x1b[0m")
                else:
                    line.append(f"\x1b[38;5;{code}m{ch}\x1b[0m")
            lines.append("".join(line))
        print("\n".join(lines))

    # Step8: ルックカーソル設定
    def set_cursor(self, x: int, y: int) -> None:
        if 0 <= y < self.height and 0 <= x < self.width:
            self.cursor = (x, y)


# Step17: テキスト入力からアクション辞書を取得
_MOVE_KEYS = {
    "w": (0, -1),
    "k": (0, -1),
    "up": (0, -1),
    "s": (0, 1),
    "j": (0, 1),
    "down": (0, 1),
    "a": (-1, 0),
    "h": (-1, 0),
    "left": (-1, 0),
    "d": (1, 0),
    "l": (1, 0),
    "right": (1, 0),
}


def get_text_action(prompt: str = "> ") -> dict:
    """Step17: 1行入力からアクション辞書を返す。

    戻り値例: {"move": (dx, dy)} / {"wait": True} / {"quit": True}
    """
    try:
        raw = input(prompt).strip().lower()
    except EOFError:
        return {"quit": True}
    if raw in ("q", "quit", "exit"):
        return {"quit": True}
    if raw in (".", " ", "wait"):
        return {"wait": True}
    if raw in _MOVE_KEYS:
        return {"move": _MOVE_KEYS[raw]}
    if raw == "":
        return {"wait": True}
    return {"unknown": raw}
