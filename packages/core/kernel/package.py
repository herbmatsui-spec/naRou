from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class PackageMetadata:
    name: str
    version: str = "1.0.0"
    dependencies: Optional[List[str]] = None
    provides: Optional[List[str]] = None
    requires: Optional[List[str]] = None


class IPackage(ABC):
    @property
    @abstractmethod
    def metadata(self) -> PackageMetadata:
        ...

    @abstractmethod
    def setup(self, kernel: "Kernel") -> None:
        ...

    @abstractmethod
    def teardown(self, kernel: "Kernel") -> None:
        ...

    def on_load(self, kernel: "Kernel") -> None:
        pass