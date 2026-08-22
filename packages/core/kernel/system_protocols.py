from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ISystem(Protocol):
    """Kernel に登録されるシステムの最小インターフェース。"""

    name: str

    def initialize(self, engine: Any) -> None: ...

    def update(self, engine: Any, dt: float = 1.0) -> None: ...
