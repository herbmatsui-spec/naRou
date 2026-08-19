from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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
class EntityDrawCall:
    """エンティティ描画コール（方向別・状態別アニメーション対応）"""
    tile_id: str              # "PLAYER", "PET", "ENEMY_GOBLIN" 等
    x: int                    # タイル座標X
    y: int                    # タイル座標Y
    direction: int = 0        # 0:下, 1:左, 2:右, 3:上
    state: str = "idle"       # "idle", "walk", "attack", "dead"
    frame: int = 0            # 現在フレーム（内部管理用）
    variant: int = 0          # バリアント（通常0）
    tint: Tuple[int, int, int] = (255, 255, 255)  # 色調補正
    bounce: float = 0.0       # 呼吸アニメ用Yオフセット


@dataclass
class LightingDrawCall:
    """ライティング描画コール"""
    light_map: Optional[Any] = None
    light_sources: List[Any] = field(default_factory=list)
    enemy_cones: List[Any] = field(default_factory=list)
    ambient_light: float = 0.08
    time: float = 0.0


@dataclass
class ParticleDrawCall:
    """パーティクル描画コール"""
    particles: List[Any] = field(default_factory=list)


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
    def draw_entity(self, call: EntityDrawCall) -> None:
        pass

    @abstractmethod
    def draw_lighting(self, call: LightingDrawCall) -> None:
        pass

    @abstractmethod
    def draw_particles(self, call: ParticleDrawCall) -> None:
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