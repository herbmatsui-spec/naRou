from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List
import numpy as np
from pathlib import Path


@dataclass
class LightVolume:
    """Light volume parameters for deferred lighting."""
    light_type: str  # "point", "spot", "decal"
    position: Tuple[float, float, float]
    color: Tuple[float, float, float]
    radius: float
    intensity: float
    # Spot light
    direction: Tuple[float, float, float] = (0.0, -1.0, 0.0)
    inner_cone: float = 0.5
    outer_cone: float = 1.0
    # Decal
    size: Tuple[float, float] = (1.0, 1.0)
    rotation: float = 0.0


@dataclass
class GBuffer:
    """G-Buffer for deferred rendering."""
    width: int
    height: int
    
    # Albedo (RGBA)
    albedo: Optional[np.ndarray] = None
    # Normal (RG) - packed XY, Z reconstructed in shader
    normal: Optional[np.ndarray] = None
    # Material: R=Roughness, G=Metallic, B=Emissive, A=AO
    material: Optional[np.ndarray] = None
    # Depth
    depth: Optional[np.ndarray] = None
    
    def __post_init__(self):
        self.resize(self.width, self.height)
    
    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.albedo = np.zeros((height, width, 4), dtype=np.float16)
        self.normal = np.zeros((height, width, 2), dtype=np.float16)
        self.material = np.zeros((height, width, 4), dtype=np.float16)
        self.depth = np.full((height, width), 1.0, dtype=np.float32)
    
    def clear(self) -> None:
        self.albedo.fill(0)
        self.normal.fill(0)
        self.material.fill(0)
        self.depth.fill(1.0)
    
    def get_textures(self) -> List[np.ndarray]:
        return [self.albedo, self.normal, self.material, self.depth]


class ShadowAtlas:
    """Shadow map atlas for multiple lights."""
    
    def __init__(self, atlas_size: int = 2048, max_lights: int = 64):
        self.atlas_size = atlas_size
        self.max_lights = max_lights
        self.atlas = np.zeros((atlas_size, atlas_size), dtype=np.float16)
        self.light_regions: List[Tuple[int, int, int, int]] = []  # x, y, w, h
        self.light_types: List[str] = []
    
    def allocate_light(self, light_type: str, resolution: int = 256) -> Optional[Tuple[int, int, int, int]]:
        """Allocate region in atlas for light shadow map."""
        if len(self.light_regions) >= self.max_lights:
            return None
        
        # Simple grid packing
        cols = self.atlas_size // resolution
        row = len(self.light_regions) // cols
        col = len(self.light_regions) % cols
        
        if row * resolution >= self.atlas_size:
            return None
        
        x = col * resolution
        y = row * resolution
        self.light_regions.append((x, y, resolution, resolution))
        self.light_types.append(light_type)
        
        return (x, y, resolution, resolution)
    
    def get_light_region(self, light_index: int) -> Optional[Tuple[int, int, int, int]]:
        if 0 <= light_index < len(self.light_regions):
            return self.light_regions[light_index]
        return None
    
    def clear(self) -> None:
        self.atlas.fill(1.0)  # Far depth = 1.0
        self.light_regions.clear()
        self.light_types.clear()


class TileCulling:
    """Tile-based light culling for forward+ rendering."""
    
    def __init__(self, tile_size: int = 16, max_lights_per_tile: int = 256):
        self.tile_size = tile_size
        self.max_lights_per_tile = max_lights_per_tile
    
    def build_light_grid(self, width: int, height: int, 
                         lights: List[LightVolume],
                         view_proj_matrix: np.ndarray) -> np.ndarray:
        """
        Build light index grid for tiled culling.
        Returns: (grid_h, grid_w, max_lights_per_tile) uint32 array
        """
        grid_w = (width + self.tile_size - 1) // self.tile_size
        grid_h = (height + self.tile_size - 1) // self.tile_size
        
        # Light index list per tile (flattened)
        light_grid = np.full((grid_h, grid_w, self.max_lights_per_tile), 
                            0xFFFFFFFF, dtype=np.uint32)
        light_counts = np.zeros((grid_h, grid_w), dtype=np.uint16)
        
        for light_idx, light in enumerate(lights):
            # Compute screen-space AABB of light
            tile_min, tile_max = self._compute_light_tiles(
                light, grid_w, grid_h, width, height, view_proj_matrix)
            
            for ty in range(tile_min[1], tile_max[1] + 1):
                for tx in range(tile_min[0], tile_max[0] + 1):
                    count = light_counts[ty, tx]
                    if count < self.max_lights_per_tile:
                        light_grid[ty, tx, count] = light_idx
                        light_counts[ty, tx] = count + 1
        
        return light_grid
    
    def _compute_light_tiles(self, light: LightVolume, 
                            grid_w: int, grid_h: int,
                            width: int, height: int,
                            view_proj: np.ndarray) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Compute tile range covered by light."""
        # For simplicity, use screen-space approximation without full projection
        # In production, this would use proper view-projection
        px = light.position[0]
        py = light.position[1]
        
        # Clamp to screen
        px = np.clip(px, 0, width)
        py = np.clip(py, 0, height)
        
        # Project radius to screen space (simplified)
        radius_pixels = light.radius * min(width, height) / max(width, height)
        
        tile_min_x = max(0, int((px - radius_pixels) / self.tile_size))
        tile_max_x = min(grid_w - 1, int((px + radius_pixels) / self.tile_size))
        tile_min_y = max(0, int((py - radius_pixels) / self.tile_size))
        tile_max_y = min(grid_h - 1, int((py + radius_pixels) / self.tile_size))
        
        return ((tile_min_x, tile_min_y), (tile_max_x, tile_max_y))


class MaterialSystem:
    """Tile material definitions and lookup."""
    
    def __init__(self, material_file: str = "data/tile_materials.json"):
        self.material_file = material_file
        self.materials: dict = {}
        self.default_material = {
            "albedo": [1.0, 1.0, 1.0, 1.0],
            "normal": [0.5, 0.5, 1.0, 1.0],
            "roughness": 0.5,
            "metallic": 0.0,
            "emissive": 0.0,
            "ao": 1.0
        }
        self.load_materials()
    
    def load_materials(self) -> None:
        import json
        path = Path(self.material_file)
        if path.exists():
            with open(path) as f:
                self.materials = json.load(f)
    
    def get_material(self, tile_id: str) -> dict:
        return self.materials.get(tile_id, self.default_material)
    
    def get_material_array(self, tile_ids: List[str]) -> np.ndarray:
        """Get material parameters as array for GPU upload."""
        result = np.zeros((len(tile_ids), 4), dtype=np.float16)
        for i, tid in enumerate(tile_ids):
            mat = self.get_material(tid)
            result[i, 0] = mat.get("roughness", 0.5)
            result[i, 1] = mat.get("metallic", 0.0)
            result[i, 2] = mat.get("emissive", 0.0)
            result[i, 3] = mat.get("ao", 1.0)
        return result