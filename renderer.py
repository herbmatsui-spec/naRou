"""
Elona Roguelike - Renderer Interface (Step 3)
描画抽象化インターフェース。tcod 実装と Web 実装を切り替え可能にする。
"""

from __future__ import annotations

from typing import Protocol

from ecs.entity import Entity


class Renderer(Protocol):
    """描画バックエンドの最小プロトコル。"""

    def clear(self) -> None:
        """画面をクリア"""
        ...

    def present(self) -> None:
        """フレームを表示"""
        ...

    def draw_char(
        self,
        x: int,
        y: int,
        char: str,
        fg: tuple[int, int, int],
        bg: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """単一キャラクターを描画"""
        ...

    def draw_str(
        self,
        x: int,
        y: int,
        text: str,
        fg: tuple[int, int, int] = (255, 255, 255),
        bg: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """文字列を描画"""
        ...

    def draw_entity(self, entity: Entity, camera_x: int, camera_y: int) -> None:
        """エンティティを描画（カメラ座標系）"""
        ...

    def draw_map(
        self,
        tiles: list[list[str]],
        camera_x: int,
        camera_y: int,
        visible: list[list[bool]],
        explored: list[list[bool]],
    ) -> None:
        """マップを描画"""
        ...

    def draw_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        fg: tuple[int, int, int],
        bg: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """矩形を描画"""
        ...

    def draw_bar(
        self,
        x: int,
        y: int,
        width: int,
        current: int,
        maximum: int,
        fg: tuple[int, int, int],
        bg: tuple[int, int, int],
        label: str = "",
    ) -> None:
        """ゲージバーを描画"""
        ...

    def get_size(self) -> tuple[int, int]:
        """描画領域のサイズを取得 (width, height)"""
        ...

    def flush(self) -> None:
        """バッファをフラッシュ（ダブルバッファリング用）"""
        ...


class TcodRenderer:
    """tcod コンソール実装 (Renderer プロトコル準拠)"""

    def __init__(self, console):
        self.console = console

    def clear(self) -> None:
        self.console.clear()

    def present(self) -> None:
        # 実際の表示は context.present で行われるためここでは何もしない
        pass

    def draw_char(
        self,
        x: int,
        y: int,
        char: str,
        fg: tuple[int, int, int],
        bg: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        self.console.print(x=x, y=y, string=char, fg=fg, bg=bg)

    def draw_str(
        self,
        x: int,
        y: int,
        text: str,
        fg: tuple[int, int, int] = (255, 255, 255),
        bg: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        self.console.print(x=x, y=y, string=text, fg=fg, bg=bg)

    def draw_entity(self, entity: Entity, camera_x: int, camera_y: int) -> None:
        # 重い描画は RenderSystem が担当するためここでは何もしない
        pass

    def draw_map(
        self,
        tiles: list[list[str]],
        camera_x: int,
        camera_y: int,
        visible: list[list[bool]],
        explored: list[list[bool]],
    ) -> None:
        pass

    def draw_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        fg: tuple[int, int, int],
        bg: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        self.console.draw_rect(x=x, y=y, width=w, height=h, ch=0, fg=fg, bg=bg)

    def draw_bar(
        self,
        x: int,
        y: int,
        width: int,
        current: int,
        maximum: int,
        fg: tuple[int, int, int],
        bg: tuple[int, int, int],
        label: str = "",
    ) -> None:
        pass

    def get_size(self) -> tuple[int, int]:
        return (self.console.width, self.console.height)

    def flush(self) -> None:
        pass


class NullRenderer:
    """何もしないレンダラ（テスト用・ヘッドレス実行用）"""

    def clear(self) -> None:
        pass

    def present(self) -> None:
        pass

    def draw_char(
        self,
        x: int,
        y: int,
        char: str,
        fg: tuple[int, int, int],
        bg: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        pass

    def draw_str(
        self,
        x: int,
        y: int,
        text: str,
        fg: tuple[int, int, int] = (255, 255, 255),
        bg: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        pass

    def draw_entity(self, entity: Entity, camera_x: int, camera_y: int) -> None:
        pass

    def draw_map(
        self,
        tiles: list[list[str]],
        camera_x: int,
        camera_y: int,
        visible: list[list[bool]],
        explored: list[list[bool]],
    ) -> None:
        pass

    def draw_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        fg: tuple[int, int, int],
        bg: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        pass

    def draw_bar(
        self,
        x: int,
        y: int,
        width: int,
        current: int,
        maximum: int,
        fg: tuple[int, int, int],
        bg: tuple[int, int, int],
        label: str = "",
    ) -> None:
        pass

    def get_size(self) -> tuple[int, int]:
        return (80, 50)

    def flush(self) -> None:
        pass


# グローバルレンダラインスタンス（後方互換用）
_renderer_instance: Renderer | None = None


def get_renderer() -> Renderer:
    """現在のレンダラインスタンスを取得"""
    global _renderer_instance
    if _renderer_instance is None:
        _renderer_instance = NullRenderer()
    return _renderer_instance


def set_renderer(renderer: Renderer) -> None:
    """レンダラインスタンスを設定"""
    global _renderer_instance
    _renderer_instance = renderer
