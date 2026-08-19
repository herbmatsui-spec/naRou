from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path


@dataclass
class TileDrawCall:
    texture_id: int
    x: int
    y: int
    width: int
    height: int
    u0: float
    v0: float
    u1: float
    v1: float
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    rotation: float = 0.0
    scale: float = 1.0


@dataclass
class TextDrawCall:
    text: str
    x: int
    y: int
    font_size: int
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    alignment: str = "left"
    max_width: Optional[int] = None


@dataclass
class Viewport:
    x: int
    y: int
    width: int
    height: int


class RendererBase(ABC):
    @abstractmethod
    def begin_frame(self) -> None:
        pass

    @abstractmethod
    def end_frame(self) -> None:
        pass

    @abstractmethod
    def draw_tile(self, call: TileDrawCall) -> None:
        pass

    @abstractmethod
    def draw_text(self, call: TextDrawCall) -> None:
        pass

    @abstractmethod
    def set_viewport(self, viewport: Viewport) -> None:
        pass

    @abstractmethod
    def get_viewport(self) -> Viewport:
        pass

    @abstractmethod
    def create_texture(self, path: Path) -> int:
        pass

    @abstractmethod
    def destroy_texture(self, texture_id: int) -> None:
        pass

    @abstractmethod
    def get_texture_size(self, texture_id: int) -> Tuple[int, int]:
        pass

    @abstractmethod
    def clear(self, color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)) -> None:
        pass

    @abstractmethod
    def present(self) -> None:
        pass

    @abstractmethod
    def resize(self, width: int, height: int) -> None:
        pass

    @abstractmethod
    def get_framebuffer_size(self) -> Tuple[int, int]:
        pass