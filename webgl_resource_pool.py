"""WebGLResourcePool – WebGL 関連リソース（シェーダ・バッファ等）をプール管理するモジュール。
Python 側では実際の GPU オブジェクトは持てないため、簡易的なモックオブジェクト
（文字列や辞書）を格納し、同一キーで再取得した際に同一インスタンスが返ることを
保証します。"""

from __future__ import annotations
from typing import Any, Callable, Dict, Tuple

class WebGLResourcePool:
    """リソースプール。
    - `rtype` はリソース種別（例: "shader", "buffer"）
    - `key` はリソースの識別子（例: シェーダ名）
    - `creator` はリソースが未キャッシュの場合に呼び出すコールバック。
    """

    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], Any] = {}

    def acquire(self, rtype: str, key: str, creator: Callable[[], Any]) -> Any:
        """リソースを取得。未登録なら ``creator`` で生成しキャッシュ。"""
        lookup = (rtype, key)
        if lookup not in self._store:
            self._store[lookup] = creator()
        return self._store[lookup]

    def release(self, rtype: str, key: str) -> None:
        """プールからリソースを削除（明示的に解放したいとき）。"""
        self._store.pop((rtype, key), None)

    def clear(self) -> None:
        """全リソースを破棄。テストのリセット等に使用。"""
        self._store.clear()

    # デバッグ・テスト用に現在保持しているキー一覧を取得
    def keys(self) -> list[Tuple[str, str]]:
        return list(self._store.keys())
