from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .package import IPackage


@dataclass
class Kernel:
    """薄いカーネル：システム登録・依存解決・イベント配送のみ"""

    _systems: dict[str, Any] = field(default_factory=dict)
    _packages: dict[str, IPackage] = field(default_factory=dict)
    _load_order: list[str] = field(default_factory=list)
    _event_bus: Any = None

    def register_system(self, name: str, system: Any) -> Any:
        if name in self._systems:
            raise ValueError(f"System already registered: {name}")
        self._systems[name] = system
        return system

    def get_system(self, name: str, default: Any = None) -> Any:
        if name in self._systems:
            return self._systems[name]
        if default is not None:
            return default
        raise KeyError(f"System not found: {name}")

    def get_system_strict(self, name: str) -> Any:
        """Backward-compatible alias that always raises when missing."""
        if name not in self._systems:
            raise KeyError(f"System not found: {name}")
        return self._systems[name]

    def has_system(self, name: str) -> bool:
        return name in self._systems

    def set_event_bus(self, bus: Any) -> None:
        self._event_bus = bus

    def get_event_bus(self) -> Any:
        return self._event_bus

    # --- パッケージ管理 ---
    def load_package(self, package: IPackage) -> None:
        meta = package.metadata
        if meta.name in self._packages:
            raise ValueError(f"Package already loaded: {meta.name}")

        # 依存チェック
        for dep in meta.dependencies or []:
            if dep not in self._packages:
                raise RuntimeError(f"Missing dependency: {dep} (required by {meta.name})")

        # 必須システムチェック
        for req in meta.requires or []:
            if not self.has_system(req):
                raise RuntimeError(f"Required system not available: {req} (for {meta.name})")

        package.on_load(self)
        package.setup(self)
        self._packages[meta.name] = package
        self._load_order.append(meta.name)

    def unload_package(self, name: str) -> None:
        if name not in self._packages:
            return
        package = self._packages[name]
        package.teardown(self)
        del self._packages[name]
        self._load_order.remove(name)

    def get_package(self, name: str) -> IPackage | None:
        return self._packages.get(name)

    # --- 依存性解決（トポロジカルソート） ---
    def resolve_load_order(self, package_names: list[str]) -> list[str]:
        return [n for n in self._load_order if n in package_names]
