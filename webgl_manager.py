"""WebGLManager – ブラウザ側の WebGL2 コンテキストをサーバ側で一元管理するモジュール。
実際の WebGL コンテキストはブラウザ環境にのみ存在するため、サーバ側では
モックオブジェクトで代用し、取得・キャッシュのロジックだけを提供します。
"""

from __future__ import annotations

from typing import Any


class WebGLManager:
    """シングルトンラッパー。
    - `set_canvas(canvas)` でブラウザ側の Canvas オブジェクト（またはモック）を登録。
    - `get_context()` がキャッシュ済みの WebGL2RenderingContext（モック）を返す。
    - 2 回以上取得しても同一オブジェクトが返ることを保証。
    """

    _instance: WebGLManager | None = None

    def __new__(cls) -> WebGLManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._canvas: Any = None  # Canvas‑like object (must provide getContext)
        self._context: Any = None  # Cached WebGL2 context (mock)
        self._initialized = True

    def set_canvas(self, canvas: Any) -> None:
        """Canvas オブジェクトを登録し、`webgl2` コンテキストを取得・キャッシュする。"""
        self._canvas = canvas
        # 実際のブラウザでは `canvas.getContext('webgl2')` が返る。
        # ここではシンプルなモック文字列を保存。
        getter = getattr(canvas, "getContext", lambda _: None)
        self._context = getter("webgl2")

    def get_context(self) -> Any:
        """キャッシュされた WebGL2 コンテキストを返す。
        Canvas が未登録の場合は ``None`` を返す。
        """
        if self._context is None and self._canvas is not None:
            # 遅延取得（Canvas が後から設定されたケース）
            self.set_canvas(self._canvas)
        return self._context

    # テスト・デバッグ用にシングルトン取得を明示的にエクスポート
    @staticmethod
    def instance() -> WebGLManager:
        return WebGLManager()
