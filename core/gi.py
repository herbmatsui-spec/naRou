from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np
from pathlib import Path


@dataclass
class DDGIProbe:
    """Single DDGI probe with 6-face depth + radiance."""
    position: np.ndarray  # float32[3]
    # 6 faces: +X, -X, +Y, -Y, +Z, -Z
    depth_maps: np.ndarray  # float16[6, 128, 128]
    radiance_maps: np.ndarray  # float16[6, 128, 128, 2]  # RG16F
    update_frame: int = 0
    needs_update: bool = True


class DDGIProbeGrid:
    """3D grid of DDGI probes for dynamic GI."""
    
    def __init__(
        self, 
        grid_size: Tuple[int, int, int] = (32, 32, 32),
        probe_spacing: float = 1.0,
        atlas_resolution: int = 128,
        world_bounds: Tuple[float, float, float, float, float, float] = (-50, 50, -50, 50, -10, 50)
    ):
        self.grid_size = grid_size
        self.probe_spacing = probe_spacing
        self.atlas_resolution = atlas_resolution
        self.world_bounds = world_bounds
        
        self.probes: List[DDGIProbe] = []
        self.probe_count = grid_size[0] * grid_size[1] * grid_size[2]
        self.atlas_size = atlas_resolution
        
        # Packed atlas for all probes (6 faces each)
        # Total: probe_count * 6 faces * 128x128
        self.depth_atlas = np.zeros(
            (self.probe_count, 6, atlas_resolution, atlas_resolution), 
            dtype=np.float16
        )
        self.radiance_atlas = np.zeros(
            (self.probe_count, 6, atlas_resolution, atlas_resolution, 2),
            dtype=np.float16
        )
        
        self.update_schedule: List[int] = []  # Probe indices to update this frame
        self.current_update_index = 0
        self.frame_count = 0
        
        self._initialize_probes()
    
    def _initialize_probes(self) -> None:
        min_x, max_x, min_y, max_y, min_z, max_z = self.world_bounds
        gx, gy, gz = self.grid_size
        
        for iz in range(gz):
            for iy in range(gy):
                for ix in range(gx):
                    # World position at grid center
                    world_x = min_x + (ix + 0.5) * (max_x - min_x) / gx
                    world_y = min_y + (iy + 0.5) * (max_y - min_y) / gy
                    world_z = min_z + (iz + 0.5) * (max_z - min_z) / gz
                    
                    probe_idx = iz * gy * gx + iy * gx + ix
                    probe = DDGIProbe(
                        position=np.array([world_x, world_y, world_z], dtype=np.float32),
                        depth_maps=np.full((6, self.atlas_size, self.atlas_size), 1.0, dtype=np.float16),
                        radiance_maps=np.zeros((6, self.atlas_size, self.atlas_size, 2), dtype=np.float16)
                    )
                    self.probes.append(probe)
                    self.update_schedule.append(probe_idx)
    
    def get_probe(self, index: int) -> DDGIProbe:
        return self.probes[index]
    
    def get_probe_at_world(self, world_pos: np.ndarray) -> Optional[DDGIProbe]:
        """Find nearest probe to world position."""
        min_x, max_x, min_y, max_y, min_z, max_z = self.world_bounds
        gx, gy, gz = self.grid_size
        
        # Normalize to grid coordinates
        nx = (world_pos[0] - min_x) / (max_x - min_x)
        ny = (world_pos[1] - min_y) / (max_y - min_y)
        nz = (world_pos[2] - min_z) / (max_z - min_z)
        
        ix = int(np.clip(nx * gx, 0, gx - 1))
        iy = int(np.clip(ny * gy, 0, gy - 1))
        iz = int(np.clip(nz * gz, 0, gz - 1))
        
        idx = iz * gy * gx + iy * gx + ix
        return self.probes[idx]
    
    def schedule_updates(self, probes_per_frame: int = 4096) -> None:
        """Schedule probe updates (1/8 of total per frame)."""
        self.frame_count += 1
        
        if self.current_update_index >= len(self.update_schedule):
            self.current_update_index = 0
            # Shuffle for temporal distribution
            np.random.shuffle(self.update_schedule)
        
        end = min(self.current_update_index + probes_per_frame, len(self.update_schedule))
        self.scheduled_this_frame = self.update_schedule[self.current_update_index:end]
        self.current_update_index = end
    
    def get_scheduled_probes(self) -> List[int]:
        return getattr(self, 'scheduled_this_frame', [])
    
    def mark_updated(self, probe_index: int) -> None:
        self.probes[probe_index].update_frame = self.frame_count
        self.probes[probe_index].needs_update = False
    
    def get_probe_data_for_shader(self, probe_index: int) -> dict:
        """Get probe data formatted for GPU upload."""
        probe = self.probes[probe_index]
        return {
            'position': probe.position,
            'depth': self.depth_atlas[probe_index],
            'radiance': self.radiance_atlas[probe_index],
        }
    
    def upload_probe_data(self, probe_index: int, depth: np.ndarray, radiance: np.ndarray) -> None:
        """Upload rendered probe data from GPU."""
        self.depth_atlas[probe_index] = depth
        self.radiance_atlas[probe_index] = radiance
        self.mark_updated(probe_index)
    
    def interpolate_irradiance(self, world_pos: np.ndarray, normal: np.ndarray) -> np.ndarray:
        """Trilinear interpolation of irradiance from 8 nearest probes."""
        # Find 8 surrounding probes
        min_x, max_x, min_y, max_y, min_z, max_z = self.world_bounds
        gx, gy, gz = self.grid_size
        
        # Grid coordinates
        nx = (world_pos[0] - min_x) / (max_x - min_x) * (gx - 1)
        ny = (world_pos[1] - min_y) / (max_y - min_y) * (gy - 1)
        nz = (world_pos[2] - min_z) / (max_z - min_z) * (gz - 1)
        
        ix0 = int(np.floor(nx))
        iy0 = int(np.floor(ny))
        iz0 = int(np.floor(nz))
        
        ix1 = min(ix0 + 1, gx - 1)
        iy1 = min(iy0 + 1, gy - 1)
        iz1 = min(iz0 + 1, gz - 1)
        
        fx = nx - ix0
        fy = ny - iy0
        fz = nz - iz0
        
        # Sample 8 probes (simplified - just return first probe's radiance)
        # Full implementation would trilinearly interpolate
        probe_idx = iz0 * gy * gx + iy0 * gx + ix0
        probe = self.probes[probe_idx]
        
        # Return average radiance across faces (hemisphere)
        radiance = np.mean(probe.radiance_maps, axis=(0, 1, 2))
        return radiance.astype(np.float32)


class LPVFallback:
    """Light Propagation Volumes fallback for non-WebGPU environments."""
    
    def __init__(
        self,
        grid_size: Tuple[int, int, int] = (32, 32, 32),
        world_bounds: Tuple[float, float, float, float, float, float] = (-50, 50, -50, 50, -10, 50)
    ):
        self.grid_size = grid_size
        self.world_bounds = world_bounds
        gx, gy, gz = grid_size
        
        # LPV cells: flux (RGB) + incoming radiance
        self.flux = np.zeros((gz, gy, gx, 3), dtype=np.float16)
        self.incoming = np.zeros((gz, gy, gx, 3), dtype=np.float16)
        self.geometry = np.zeros((gz, gy, gx), dtype=np.float16)  # Occlusion
        
        # RSM (Reflective Shadow Map) from light
        self.rsm_depth = None
        self.rsm_normal = None
        self.rsm_flux = None
        self.rsm_resolution = 512
        
        self.propagation_iterations = 4
        self.injection_intensity = 1.0
    
    def inject_rsm(self, rsm_depth: np.ndarray, rsm_normal: np.ndarray, rsm_flux: np.ndarray) -> None:
        """Inject RSM data into LPV grid."""
        self.rsm_depth = rsm_depth
        self.rsm_normal = rsm_normal
        self.rsm_flux = rsm_flux
        
        # Splat RSM into LPV grid (simplified)
        # Full implementation would project each RSM texel into grid
        pass
    
    def propagate(self) -> None:
        """Propagate light through LPV grid."""
        gz, gy, gx = self.grid_size
        
        for _ in range(self.propagation_iterations):
            new_flux = self.flux.copy()
            new_incoming = self.incoming.copy()
            
            # 6-direction propagation
            for dz, dy, dx in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                # Shift and accumulate
                shifted_flux = np.roll(self.flux, (dz, dy, dx), axis=(0, 1, 2))
                shifted_incoming = np.roll(self.incoming, (dz, dy, dx), axis=(0, 1, 2))
                
                # Geometry occlusion
                occlusion = 1.0 - self.geometry
                
                new_flux += shifted_flux * occlusion * 0.25
                new_incoming += shifted_incoming * occlusion * 0.25
            
            self.flux = new_flux
            self.incoming = new_incoming
    
    def query_irradiance(self, world_pos: np.ndarray, normal: np.ndarray) -> np.ndarray:
        """Query irradiance at world position."""
        min_x, max_x, min_y, max_y, min_z, max_z = self.world_bounds
        gx, gy, gz = self.grid_size
        
        # Grid coordinates
        nx = (world_pos[0] - min_x) / (max_x - min_x) * (gx - 1)
        ny = (world_pos[1] - min_y) / (max_y - min_y) * (gy - 1)
        nz = (world_pos[2] - min_z) / (max_z - min_z) * (gz - 1)
        
        # Trilinear interpolation
        ix0 = int(np.clip(np.floor(nx), 0, gx - 2))
        iy0 = int(np.clip(np.floor(ny), 0, gy - 2))
        iz0 = int(np.clip(np.floor(nz), 0, gz - 2))
        
        fx = nx - ix0
        fy = ny - iy0
        fz = nz - iz0
        
        # Sample 8 corners
        result = np.zeros(3, dtype=np.float32)
        for dz in [0, 1]:
            for dy in [0, 1]:
                for dx in [0, 1]:
                    w = (1-fx if dx==0 else fx) * (1-fy if dy==0 else fy) * (1-fz if dz==0 else fz)
                    iz = iz0 + dz
                    iy = iy0 + dy
                    ix = ix0 + dx
                    if 0 <= iz < gz and 0 <= iy < gy and 0 <= ix < gx:
                        result += self.incoming[iz, iy, ix] * w
        
        # Cosine weighted by normal
        result = result * max(np.dot(normal, [0, 1, 0]), 0.0)
        return result


class GICompositor:
    """GI integration with HDR pipeline."""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        self.ddgi = DDGIProbeGrid()
        self.lpv = LPVFallback()
        self.gi_mode = "ddgi"  # "ddgi", "lpv", "ssao", "none"
        
        self.gi_intensity = 1.0
        self.gi_bounce_count = 2
        self.gi_enabled = True
        
        # Debug
        self.debug_probes = False
        self.debug_probe_index = 0
    
    def begin_frame(self) -> None:
        self.ddgi.schedule_updates()
        self.ddgi.frame_count = getattr(self.ddgi, 'frame_count', 0) + 1
    
    def update_ddgi_probes(self, gbuffer, scene_lights) -> None:
        """Render scheduled DDGI probes (would call GPU raytracing)."""
        scheduled = self.ddgi.get_scheduled_probes()
        for probe_idx in scheduled:
            probe = self.ddgi.get_probe(probe_idx)
            # In real implementation: dispatch raytracing for this probe
            # For now, mark as updated
            self.ddgi.mark_updated(probe_idx)
    
    def update_lpv(self, gbuffer, scene_lights) -> None:
        """Update LPV fallback."""
        if self.gi_mode == "lpv":
            # Generate RSM from main light
            # self.lpv.inject_rsm(...)
            self.lpv.propagate()
    
    def compose_gi(self, direct_lighting: np.ndarray, gbuffer, world_pos: np.ndarray, normal: np.ndarray) -> np.ndarray:
        """Composite GI with direct lighting."""
        if not self.gi_enabled:
            return direct_lighting
        
        gi = np.zeros_like(direct_lighting)
        
        if self.gi_mode == "ddgi":
            gi = self.ddgi.interpolate_irradiance(world_pos, normal)
        elif self.gi_mode == "lpv":
            gi = self.lpv.query_irradiance(world_pos, normal)
        elif self.gi_mode == "ssao":
            # SSAO fallback - ambient occlusion only
            gi = np.array([0.1, 0.1, 0.1], dtype=np.float32)
        
        # Combine: direct + GI * intensity
        result = direct_lighting + gi * self.gi_intensity
        return np.clip(result, 0, 10.0)  # HDR range
    
    def set_gi_mode(self, mode: str) -> None:
        if mode in ("ddgi", "lpv", "ssao", "none"):
            self.gi_mode = mode
            self.gi_enabled = mode != "none"
    
    def set_quality_preset(self, preset: str) -> None:
        presets = {
            "low": {"ddgi_probes": (16, 16, 16), "atlas": 64, "update_rate": 2048},
            "medium": {"ddgi_probes": (32, 32, 32), "atlas": 128, "update_rate": 4096},
            "high": {"ddgi_probes": (32, 32, 32), "atlas": 256, "update_rate": 8192},
            "ultra": {"ddgi_probes": (64, 64, 32), "atlas": 256, "update_rate": 16384},
        }
        if preset in presets:
            p = presets[preset]
            self.ddgi = DDGIProbeGrid(grid_size=p["ddgi_probes"], atlas_resolution=p["atlas"])
            self.ddgi.schedule_updates(p["update_rate"])


def generate_ddgi_probe_positions(grid_size: Tuple[int, int, int], world_bounds: Tuple[float, ...]) -> np.ndarray:
    """Generate all probe world positions for shader upload."""
    min_x, max_x, min_y, max_y, min_z, max_z = world_bounds
    gx, gy, gz = grid_size
    
    positions = []
    for iz in range(gz):
        for iy in range(gy):
            for ix in range(gx):
                x = min_x + (ix + 0.5) * (max_x - min_x) / gx
                y = min_y + (iy + 0.5) * (max_y - min_y) / gy
                z = min_z + (iz + 0.5) * (max_z - min_z) / gz
                positions.append([x, y, z])
    
    return np.array(positions, dtype=np.float32)