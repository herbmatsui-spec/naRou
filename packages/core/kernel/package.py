from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .kernel import Kernel


@dataclass
class PackageMetadata:
    name: str
    version: str = "1.0.0"
    dependencies: list[str] | None = None
    provides: list[str] | None = None
    requires: list[str] | None = None


class IPackage(ABC):
    @property
    @abstractmethod
    def metadata(self) -> PackageMetadata: ...

    @abstractmethod
    def setup(self, kernel: Kernel) -> None: ...

    @abstractmethod
    def teardown(self, kernel: Kernel) -> None: ...

    def on_load(self, kernel: Kernel) -> None:
        pass
