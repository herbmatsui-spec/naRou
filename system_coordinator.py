"""
Elona Roguelike - System Coordinator
Step 9: SystemCoordinator 抽出
システム間の依存性解決と初期化順序の管理を担当するクラス
Kernel の薄い互換ラッパーとして機能
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from packages.core.kernel.kernel import Kernel


class SystemCoordinator:
    """
    Kernel の薄い互換ラッパー。
    既存コードが systems_coordinator を通じてシステム登録・取得できるようにする。
    """

    def __init__(self, engine: Any):
        """
        Args:
            engine: ゲームエンジンインスタンス（Kernel 保持元）
        """
        self.engine = engine
        self._kernel: Kernel = engine.kernel
        self._registration_order: list[str] = []

    def register_system(
        self, name: str, system: Any, dependencies: list[str] | None = None
    ) -> Any:
        """
        システムを Kernel に登録する。
        dependencies は互換性のために受け取るが、Kernel 側ではパッケージ単位で管理されるためここでは無視。
        """
        self._registration_order.append(name)
        return self._kernel.register_system(name, system)

    def initialize_all(self, engine: Any) -> None:
        """パッケージ経由で初期化されるため、ここでは何もしない（互換用空実装）"""

    def update_all(self, engine: Any, delta_time: float = 1.0) -> None:
        """パッケージ経由で更新されるため、ここでは何もしない（互換用空実装）"""

    def get_system(self, name: str) -> Any:
        return self._kernel.get_system(name)

    def has_system(self, name: str) -> bool:
        return self._kernel.has_system(name)
