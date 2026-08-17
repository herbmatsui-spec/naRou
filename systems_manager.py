"""
Elona Roguelike Clone - SystemManager (フェーズ1: アーキテクチャの再構築)
Step 1, 2: システムの動的登録・取得・ライフサイクル管理
"""

from __future__ import annotations
from typing import Dict, Any, Optional, Iterator


class SystemManager:
    """システムマネージャー (Step 1-7, 14, 15)
    エンジン内の各マネージャー（スキル、ジョブ、ギルド、派閥等）を一元管理し、疎結合化を実現する。
    """
    def __init__(self):
        self.systems: Dict[str, Any] = {}

    def register(self, name: str, system: Any) -> Any:
        """システムを登録する"""
        self.systems[name] = system
        return system

    def unregister(self, name: str) -> Optional[Any]:
        """システムを登録解除する"""
        return self.systems.pop(name, None)

    def get(self, name: str, default: Any = None) -> Any:
        """登録されたシステムを取得する"""
        return self.systems.get(name, default)

    def has(self, name: str) -> bool:
        """システムの存在確認"""
        return name in self.systems

    def initialize_all(self, engine: Any) -> None:
        """登録されている全 BaseSystem の initialize() を一括実行 (Step 14)"""
        for name, system in self.systems.items():
            if hasattr(system, "initialize") and callable(system.initialize):
                try:
                    system.initialize(engine)
                except TypeError:
                    system.initialize()

    def update_all(self, engine: Any, delta_time: float = 1.0) -> None:
        """登録されている全 BaseSystem の update() を一括実行 (Step 15)"""
        for name, system in self.systems.items():
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
