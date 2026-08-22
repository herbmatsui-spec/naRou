"""
Elona Roguelike Clone - SystemManager (フェーズ1: アーキテクチャの再構築)
Step 1, 2: システムの動的登録・取得・ライフサイクル管理
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol, TypeVar, overload


class SystemProtocol(Protocol):
    """システムの最小プロトコル。initialize/update を持つ任意のオブジェクトを許容する。"""

    def initialize(self, engine: Any) -> None: ...
    def update(self, engine: Any, delta_time: float) -> None: ...


SystemT = TypeVar("SystemT", bound=SystemProtocol)


class SystemManager:
    """システムマネージャー (Step 1-7, 14, 15)
    エンジン内の各マネージャー（スキル、ジョブ、ギルド、派閥等）を一元管理し、疎結合化を実現する。
    """

    def __init__(self):
        self.systems: dict[str, Any] = {}

    def register(self, name: str, system: SystemT) -> SystemT:
        """システムを登録する"""
        self.systems[name] = system
        return system

    def unregister(self, name: str) -> Any | None:
        """システムを登録解除する"""
        return self.systems.pop(name, None)

    @overload
    def get(self, name: str, system_type: type[SystemT]) -> SystemT | None: ...
    @overload
    def get(self, name: str, system_type: None = None, default: Any = None) -> Any: ...

    def get(self, name: str, system_type: type[SystemT] | None = None, default: Any = None) -> Any:
        """登録されたシステムを取得する。

        Args:
            name: システム名
            system_type: 型ヒント用のシステムクラス。指定すると型安全な取得が可能。
            default: 見つからなかった場合のデフォルト値（system_type未指定時のみ有効）
        """
        result = self.systems.get(name, default)
        # 実行時の型チェックは行わず、型ヒントのみを提供
        return result

    def has(self, name: str) -> bool:
        """システムの存在確認"""
        return name in self.systems

    def initialize_all(self, engine: Any) -> None:
        """登録されている全 BaseSystem の initialize() を一括実行 (Step 14)"""
        for system in self.systems.values():
            if hasattr(system, "initialize") and callable(system.initialize):
                try:
                    system.initialize(engine)
                except TypeError:
                    system.initialize()

    def update_all(self, engine: Any, delta_time: float = 1.0) -> None:
        """登録されている全 BaseSystem の update() を一括実行 (Step 15)"""
        for system in self.systems.values():
            if hasattr(system, "update") and callable(system.update):
                try:
                    system.update(engine, delta_time)
                except TypeError:
                    try:
                        system.update(engine)
                    except TypeError:
                        system.update()

    def __iter__(self) -> Iterator[str]:
        return iter(self.systems)

    def __len__(self) -> int:
        return len(self.systems)
