from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class GBuffer:
    """G-Buffer for deferred rendering with MRT support."""

    width: int
    height: int

    # Color attachment 0: Albedo (RGBA8)
    albedo: np.ndarray | None = None
    # Color attachment 1: Normal (RG16F - view space XY, Z reconstructed)
    normal: np.ndarray | None = None
    # Color attachment 2: Material (RGBA8 - R=Rough, G=Metal, B=Emissive, A=AO)
    material: np.ndarray | None = None
    # Depth attachment (DEPTH24_STENCIL8)
    depth: np.ndarray | None = None

    def __post_init__(self):
        self.resize(self.width, self.height)

    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

        # Albedo: RGBA8
        self.albedo = np.zeros((height, width, 4), dtype=np.uint8)
        # Normal: RG16F (view space XY, Z reconstructed in shader)
        self.normal = np.zeros((height, width, 2), dtype=np.float16)
        # Material: RGBA8
        self.material = np.zeros((height, width, 4), dtype=np.uint8)
        # Depth: float32
        self.depth = np.full((height, width), 1.0, dtype=np.float32)

    def clear(
        self,
        albedo: tuple[int, int, int, int] = (0, 0, 0, 0),
        normal: tuple[float, float] = (0.0, 0.0),
        material: tuple[int, int, int, int] = (128, 0, 0, 255),
        depth: float = 1.0,
    ) -> None:
        self.albedo[:, :] = albedo
        self.normal[:, :] = normal
        self.material[:, :] = material
        self.depth[:, :] = depth

    def get_attachments(self) -> list[np.ndarray]:
        """Get all color attachments for MRT."""
        return [self.albedo, self.normal, self.material]

    def get_depth(self) -> np.ndarray:
        return self.depth


def pack_normal_xy(normal: np.ndarray) -> np.ndarray:
    """Pack view-space normal XY to RG16F (Z reconstructed)."""
    # normal: (H, W, 3) float32 view-space normals
    # Output: (H, W, 2) float16
    return normal[:, :, :2].astype(np.float16)


def unpack_normal_xy(packed: np.ndarray) -> np.ndarray:
    """Reconstruct view-space normal from packed XY."""
    # packed: (H, W, 2) float16
    # Output: (H, W, 3) float32
    x = packed[:, :, 0].astype(np.float32)
    y = packed[:, :, 1].astype(np.float32)
    z_sq = 1.0 - x * x - y * y
    z = np.sqrt(np.maximum(z_sq, 0.0))
    return np.stack([x, y, z], axis=-1)


def pack_material(
    roughness: np.ndarray, metallic: np.ndarray, emissive: np.ndarray, ao: np.ndarray
) -> np.ndarray:
    """Pack material parameters to RGBA8."""
    # All inputs: (H, W) float32 [0,1]
    # Output: (H, W, 4) uint8
    result = np.zeros((*roughness.shape, 4), dtype=np.uint8)
    result[:, :, 0] = (np.clip(roughness, 0, 1) * 255).astype(np.uint8)
    result[:, :, 1] = (np.clip(metallic, 0, 1) * 255).astype(np.uint8)
    result[:, :, 2] = (np.clip(emissive, 0, 1) * 255).astype(np.uint8)
    result[:, :, 3] = (np.clip(ao, 0, 1) * 255).astype(np.uint8)
    return result


def unpack_material(
    packed: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Unpack RGBA8 material to float components."""
    roughness = packed[:, :, 0].astype(np.float32) / 255.0
    metallic = packed[:, :, 1].astype(np.float32) / 255.0
    emissive = packed[:, :, 2].astype(np.float32) / 255.0
    ao = packed[:, :, 3].astype(np.float32) / 255.0
    return roughness, metallic, emissive, ao


class GBufferRenderer:
    """CPU-side G-Buffer construction for testing/fallback."""

    def __init__(self, width: int, height: int):
        self.gbuffer = GBuffer(width, height)

    def render_tile(self, x: int, y: int, tile_data: dict) -> None:
        """Render single tile to G-Buffer."""
        if 0 <= x < self.gbuffer.width and 0 <= y < self.gbuffer.height:
            # Albedo
            albedo = tile_data.get("albedo", [255, 255, 255, 255])
            self.gbuffer.albedo[y, x] = albedo

            # Normal (pack XY)
            normal = tile_data.get("normal", [0.0, 0.0, 1.0])
            self.gbuffer.normal[y, x] = normal[:2]

            # Material
            roughness = tile_data.get("roughness", 0.5)
            metallic = tile_data.get("metallic", 0.0)
            emissive = tile_data.get("emissive", 0.0)
            ao = tile_data.get("ao", 1.0)
            self.gbuffer.material[y, x] = [
                int(roughness * 255),
                int(metallic * 255),
                int(emissive * 255),
                int(ao * 255),
            ]

            # Depth
            depth = tile_data.get("depth", 1.0)
            self.gbuffer.depth[y, x] = depth

    def get_gbuffer(self) -> GBuffer:
        return self.gbuffer
