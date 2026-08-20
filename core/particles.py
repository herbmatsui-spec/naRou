from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np


class ParticleFlags(IntEnum):
    ALIVE = 1
    RIBBON = 2
    TRAIL = 4
    MESH = 8
    COLLIDE = 16
    EMIT_LIGHT = 32


@dataclass
class Particle:
    """Single particle data (matches GPU struct layout)."""

    # Position (xyz) + padding
    position: np.ndarray  # float32[3]
    # Velocity (xyz) + padding
    velocity: np.ndarray  # float32[3]
    # Life: x=current, y=max, z=padding, w=padding
    life: np.ndarray  # float32[4]
    # Color (rgba)
    color: np.ndarray  # float32[4]
    # Size: x=start, y=end, z=current, w=padding
    size: np.ndarray  # float32[4]
    # Rotation: x=start, y=speed, z=current, w=padding
    rotation: np.ndarray  # float32[4]
    # Flags
    flags: int = 0
    # Material ID
    material_id: int = 0
    # Emitter ID (for sorting)
    emitter_id: int = 0
    # Ribbon/Trail
    prev_position: np.ndarray = None  # float32[3]
    ribbon_length: float = 0.0


class ParticleBuffer:
    """GPU particle buffer with double-ended queue for alive/dead management."""

    def __init__(self, max_particles: int = 1_048_576):
        self.max_particles = max_particles
        self.count = 0

        # Structured arrays (SoA for GPU efficiency)
        self.position = np.zeros((max_particles, 3), dtype=np.float32)
        self.velocity = np.zeros((max_particles, 3), dtype=np.float32)
        self.life = np.zeros((max_particles, 4), dtype=np.float32)  # x=current, y=max
        self.color = np.zeros((max_particles, 4), dtype=np.float32)
        self.size = np.zeros((max_particles, 4), dtype=np.float32)  # x=start, y=end
        self.rotation = np.zeros(
            (max_particles, 4), dtype=np.float32
        )  # x=start, y=speed
        self.flags = np.zeros(max_particles, dtype=np.uint32)
        self.material_id = np.zeros(max_particles, dtype=np.uint32)
        self.emitter_id = np.zeros(max_particles, dtype=np.uint32)
        self.prev_position = np.zeros((max_particles, 3), dtype=np.float32)
        self.ribbon_length = np.zeros(max_particles, dtype=np.float32)

        # Free list (indices of dead particles)
        self.free_list = list(range(max_particles))
        self.alive_indices = []  # Indices of alive particles

    def allocate(self, count: int) -> np.ndarray:
        """Allocate particle indices from free list."""
        if len(self.free_list) < count:
            # Recycle oldest alive particles if needed
            self._recycle_oldest(count - len(self.free_list))

        if len(self.free_list) < count:
            return np.array([], dtype=np.uint32)

        indices = np.array(self.free_list[:count], dtype=np.uint32)
        self.free_list = self.free_list[count:]
        self.alive_indices.extend(indices.tolist())
        self.count += count
        return indices

    def free(self, indices: np.ndarray) -> None:
        """Return particle indices to free list."""
        self.free_list.extend(indices.tolist())
        for idx in indices:
            if idx in self.alive_indices:
                self.alive_indices.remove(idx)
            self.flags[idx] = 0
        self.count -= len(indices)

    def _recycle_oldest(self, count: int) -> None:
        """Recycle oldest particles by life."""
        if not self.alive_indices:
            return

        # Sort alive by life (oldest first)
        alive_life = [
            (i, self.life[i, 0] / self.life[i, 1]) for i in self.alive_indices
        ]
        alive_life.sort(key=lambda x: x[1], reverse=True)  # Oldest first

        recycle_count = min(count, len(alive_life))
        for i in range(recycle_count):
            idx = alive_life[i][0]
            self.free(np.array([idx]))

    def get_alive_count(self) -> int:
        return self.count

    def get_alive_indices(self) -> np.ndarray:
        return np.array(self.alive_indices, dtype=np.uint32)

    def update_particle_data(self, indices: np.ndarray, **kwargs) -> None:
        """Update particle attributes for given indices."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                attr = getattr(self, key)
                if attr.ndim == 2:
                    attr[indices] = value
                else:
                    attr[indices] = value

    def get_particle_data(self, indices: np.ndarray) -> dict:
        """Get particle attributes for given indices."""
        return {
            "position": self.position[indices].copy(),
            "velocity": self.velocity[indices].copy(),
            "life": self.life[indices].copy(),
            "color": self.color[indices].copy(),
            "size": self.size[indices].copy(),
            "rotation": self.rotation[indices].copy(),
            "flags": self.flags[indices].copy(),
            "material_id": self.material_id[indices].copy(),
            "emitter_id": self.emitter_id[indices].copy(),
            "prev_position": self.prev_position[indices].copy(),
            "ribbon_length": self.ribbon_length[indices].copy(),
        }

    def clear(self) -> None:
        """Reset buffer."""
        self.count = 0
        self.free_list = list(range(self.max_particles))
        self.alive_indices = []
        self.flags.fill(0)


class CurlNoise:
    """3D Curl noise for divergence-free velocity fields."""

    def __init__(self, seed: int = 0):
        self.seed = seed
        self.perm = self._generate_permutation(seed)

    def _generate_permutation(self, seed: int) -> np.ndarray:
        """Generate permutation table for noise."""
        np.random.seed(seed)
        perm = np.arange(256, dtype=np.uint8)
        np.random.shuffle(perm)
        return np.concatenate([perm, perm])  # 512 for easy indexing

    def noise3d(self, x: float, y: float, z: float) -> float:
        """3D Perlin noise."""
        # Integer coordinates
        xi = int(np.floor(x)) & 255
        yi = int(np.floor(y)) & 255
        zi = int(np.floor(z)) & 255

        # Fractional coordinates
        xf = x - np.floor(x)
        yf = y - np.floor(y)
        zf = z - np.floor(z)

        # Fade curves
        u = self._fade(xf)
        v = self._fade(yf)
        w = self._fade(zf)

        # Hash coordinates
        aaa = self.perm[self.perm[self.perm[xi] + yi] + zi]
        aba = self.perm[self.perm[self.perm[xi] + yi] + zi + 1]
        aab = self.perm[self.perm[self.perm[xi] + yi + 1] + zi]
        abb = self.perm[self.perm[self.perm[xi] + yi + 1] + zi + 1]
        baa = self.perm[self.perm[self.perm[xi + 1] + yi] + zi]
        bba = self.perm[self.perm[self.perm[xi + 1] + yi] + zi + 1]
        bab = self.perm[self.perm[self.perm[xi + 1] + yi + 1] + zi]
        bbb = self.perm[self.perm[self.perm[xi + 1] + yi + 1] + zi + 1]

        # Gradient dot products
        def grad(hash_val, x, y, z):
            h = hash_val & 15
            u = x if h < 8 else y
            v = y if h < 4 else (x if h in (12, 14) else z)
            return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

        x1 = self._lerp(grad(aaa, xf, yf, zf), grad(baa, xf - 1, yf, zf), u)
        x2 = self._lerp(grad(aba, xf, yf - 1, zf), grad(bba, xf - 1, yf - 1, zf), u)
        y1 = self._lerp(x1, x2, v)

        x1 = self._lerp(grad(aab, xf, yf, zf - 1), grad(bab, xf - 1, yf, zf - 1), u)
        x2 = self._lerp(
            grad(abb, xf, yf - 1, zf - 1), grad(bbb, xf - 1, yf - 1, zf - 1), u
        )
        y2 = self._lerp(x1, x2, v)

        return self._lerp(y1, y2, w) * 2.0

    def _fade(self, t: float) -> float:
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + t * (b - a)

    def curl_noise_3d(
        self, x: float, y: float, z: float, eps: float = 0.01
    ) -> np.ndarray:
        """Compute curl of 3D noise (divergence-free velocity)."""
        # Curl = ∇ × N = (∂Nz/∂y - ∂Ny/∂z, ∂Nx/∂z - ∂Nz/∂x, ∂Ny/∂x - ∂Nx/∂y)
        n_x = self.noise3d(x, y, z)
        n_y = self.noise3d(x + 1000, y, z)
        n_z = self.noise3d(x + 2000, y, z)

        n_x_eps_y = self.noise3d(x, y + eps, z)
        self.noise3d(x + 1000, y + eps, z)
        n_z_eps_y = self.noise3d(x + 2000, y + eps, z)

        n_x_eps_z = self.noise3d(x, y, z + eps)
        n_y_eps_z = self.noise3d(x + 1000, y, z + eps)
        self.noise3d(x + 2000, y, z + eps)

        self.noise3d(x + eps, y, z)
        n_y_eps_x = self.noise3d(x + 1000 + eps, y, z)
        n_z_eps_x = self.noise3d(x + 2000 + eps, y, z)

        dx = (n_z_eps_y - n_z) / eps - (n_y_eps_z - n_y) / eps
        dy = (n_x_eps_z - n_x) / eps - (n_z_eps_x - n_z) / eps
        dz = (n_y_eps_x - n_y) / eps - (n_x_eps_y - n_x) / eps

        return np.array([dx, dy, dz], dtype=np.float32)


class SDFCollision:
    """Signed Distance Field collision for particles."""

    def __init__(
        self, grid_size: int = 128, world_bounds: tuple = (-50, 50, -50, 50, -10, 50)
    ):
        self.grid_size = grid_size
        self.world_bounds = world_bounds  # (min_x, max_x, min_y, max_y, min_z, max_z)
        self.sdf = None
        self.cell_size = 0.0
        self.heightmap_shape = None

    def build_from_heightmap(
        self, heightmap: np.ndarray, wall_height: float = 10.0
    ) -> None:
        """Build SDF from 2D heightmap (walls extruded to wall_height)."""
        h, w = heightmap.shape
        self.grid_size = max(h, w, 32)
        self.heightmap_shape = (h, w)

        # Update world bounds to match heightmap
        min_x, max_x, min_y, max_y, min_z, max_z = self.world_bounds
        # Scale X/Y to match heightmap aspect
        self.world_bounds = (min_x, max_x, min_y, max_y, min_z, max_z)

        self.sdf = np.zeros(
            (self.grid_size, self.grid_size, self.grid_size), dtype=np.float32
        )

        self.cell_size = (max_x - min_x) / self.grid_size

        # Build SDF using jump flood algorithm (simplified)
        for z in range(self.grid_size):
            world_z = min_z + (z + 0.5) * (max_z - min_z) / self.grid_size
            for y in range(self.grid_size):
                for x in range(self.grid_size):
                    world_x = min_x + (x + 0.5) * self.cell_size
                    world_y = min_y + (y + 0.5) * self.cell_size

                    # Sample heightmap - map world coords to heightmap
                    hm_x = int(
                        np.clip((world_x - min_x) / (max_x - min_x) * (w - 1), 0, w - 1)
                    )
                    hm_y = int(
                        np.clip((world_y - min_y) / (max_y - min_y) * (h - 1), 0, h - 1)
                    )
                    height = heightmap[hm_y, hm_x]

                    if world_z < height:
                        # Inside wall
                        self.sdf[z, y, x] = height - world_z
                    elif world_z < height + wall_height:
                        # Inside wall volume
                        self.sdf[z, y, x] = min(
                            world_z - height, height + wall_height - world_z
                        )
                    else:
                        # Outside
                        self.sdf[z, y, x] = world_z - (height + wall_height)

        # Fix signs (negative = inside)
        self.sdf = -self.sdf

    def query(self, pos: np.ndarray) -> float:
        """Query SDF at world position."""
        if self.sdf is None:
            return 1e6  # No collision

        min_x, _max_x, min_y, _max_y, min_z, _max_z = self.world_bounds

        # Convert to grid coordinates
        gx = (pos[0] - min_x) / self.cell_size
        gy = (pos[1] - min_y) / self.cell_size
        gz = (pos[2] - min_z) / self.cell_size

        # Bounds check - use grid_size for all dims since SDF is cubic
        if not (
            0 <= gx < self.grid_size - 1
            and 0 <= gy < self.grid_size - 1
            and 0 <= gz < self.grid_size - 1
        ):
            return 1e6

        # Trilinear interpolation
        x0, y0, z0 = int(gx), int(gy), int(gz)
        fx, fy, fz = gx - x0, gy - y0, gz - z0

        # Clamp
        x0 = np.clip(x0, 0, self.grid_size - 2)
        y0 = np.clip(y0, 0, self.grid_size - 2)
        z0 = np.clip(z0, 0, self.grid_size - 2)
        x1, y1, z1 = x0 + 1, y0 + 1, z0 + 1

        # 8 corners
        c000 = self.sdf[z0, y0, x0]
        c100 = self.sdf[z0, y0, x1]
        c010 = self.sdf[z0, y1, x0]
        c110 = self.sdf[z0, y1, x1]
        c001 = self.sdf[z1, y0, x0]
        c101 = self.sdf[z1, y0, x1]
        c011 = self.sdf[z1, y1, x0]
        c111 = self.sdf[z1, y1, x1]

        # Interpolate
        c00 = c000 * (1 - fx) + c100 * fx
        c01 = c010 * (1 - fx) + c110 * fx
        c10 = c001 * (1 - fx) + c101 * fx
        c11 = c011 * (1 - fx) + c111 * fx

        c0 = c00 * (1 - fy) + c01 * fy
        c1 = c10 * (1 - fy) + c11 * fy

        return c0 * (1 - fz) + c1 * fz

    def collide_particle(
        self, pos: np.ndarray, vel: np.ndarray, radius: float, restitution: float = 0.3
    ) -> tuple:
        """Collide particle with SDF. Returns (new_pos, new_vel, collided)."""
        dist = self.query(pos)

        if dist < radius:
            # Penetration - push out along gradient
            eps = 0.01
            grad = (
                np.array(
                    [
                        self.query(pos + np.array([eps, 0, 0])) - dist,
                        self.query(pos + np.array([0, eps, 0])) - dist,
                        self.query(pos + np.array([0, 0, eps])) - dist,
                    ]
                )
                / eps
            )

            grad_norm = np.linalg.norm(grad)
            if grad_norm > 1e-6:
                grad = grad / grad_norm
            else:
                grad = np.array([0, 1, 0])  # Default up

            # Push out
            new_pos = pos + grad * (radius - dist)

            # Reflect velocity
            v_dot_n = np.dot(vel, grad)
            if v_dot_n < 0:
                new_vel = vel - grad * (1 + restitution) * v_dot_n
            else:
                new_vel = vel

            return new_pos, new_vel, True

        return pos, vel, False


class Emitter:
    """Particle emitter with various shapes."""

    class Type(IntEnum):
        POINT = 0
        LINE = 1
        RING = 2
        SPHERE = 3
        BOX = 4
        MESH = 5

    def __init__(
        self,
        emitter_type: Type = Type.POINT,
        rate: float = 100.0,
        position: np.ndarray = None,
        direction: np.ndarray = None,
        params: dict | None = None,
    ):
        self.type = emitter_type
        self.rate = rate  # Particles per second
        self.position = (
            position if position is not None else np.zeros(3, dtype=np.float32)
        )
        self.direction = (
            direction
            if direction is not None
            else np.array([0, 1, 0], dtype=np.float32)
        )
        self.params = params if params is not None else {}
        self.accumulator = 0.0
        self.active = True

    def update(
        self,
        dt: float,
        particle_buffer: ParticleBuffer,
        base_velocity: np.ndarray,
        base_color: np.ndarray,
        base_size: float,
        base_life: float,
        material_id: int = 0,
    ) -> int:
        """Emit particles. Returns number emitted."""
        if not self.active:
            return 0

        self.accumulator += self.rate * dt
        count = int(self.accumulator)
        self.accumulator -= count

        if count <= 0:
            return 0

        indices = particle_buffer.allocate(count)
        if len(indices) == 0:
            return 0

        # Initialize particles based on emitter type
        for idx in indices:
            self._init_particle(
                idx,
                particle_buffer,
                base_velocity,
                base_color,
                base_size,
                base_life,
                material_id,
            )

        return count

    def _init_particle(
        self,
        idx: int,
        buffer: ParticleBuffer,
        base_vel: np.ndarray,
        base_color: np.ndarray,
        base_size: float,
        base_life: float,
        material_id: int,
    ) -> None:
        """Initialize single particle."""
        pos = self.position.copy()
        vel = base_vel.copy()

        if self.type == Emitter.Type.POINT:
            pass  # Already at position
        elif self.type == Emitter.Type.LINE:
            t = np.random.random()
            pos += self.direction * t * self.params.get("length", 1.0)
        elif self.type == Emitter.Type.RING:
            angle = np.random.random() * 2 * np.pi
            radius = self.params.get("radius", 1.0)
            pos += (
                np.array([np.cos(angle), 0, np.sin(angle)], dtype=np.float32) * radius
            )
        elif self.type == Emitter.Type.SPHERE:
            # Uniform sphere
            u = np.random.random()
            v = np.random.random()
            theta = 2 * np.pi * u
            phi = np.arccos(2 * v - 1)
            radius = self.params.get("radius", 1.0)
            pos += radius * np.array(
                [np.sin(phi) * np.cos(theta), np.cos(phi), np.sin(phi) * np.sin(theta)],
                dtype=np.float32,
            )
        elif self.type == Emitter.Type.BOX:
            size = self.params.get("size", np.ones(3))
            pos += np.random.uniform(-0.5, 0.5, 3) * size

        # Add velocity variation
        vel += np.random.normal(0, self.params.get("vel_spread", 0.1), 3)

        # Set buffer data
        buffer.position[idx] = pos
        buffer.velocity[idx] = vel
        buffer.life[idx] = np.array([0.0, base_life, 0.0, 0.0], dtype=np.float32)
        buffer.color[idx] = base_color
        buffer.size[idx] = np.array(
            [base_size, base_size, base_size, 0.0], dtype=np.float32
        )
        buffer.rotation[idx] = np.array(
            [0.0, self.params.get("rot_speed", 0.0), 0.0, 0.0], dtype=np.float32
        )
        buffer.flags[idx] = ParticleFlags.ALIVE
        buffer.material_id[idx] = material_id
        buffer.emitter_id[idx] = self.params.get("emitter_id", 0)
        buffer.prev_position[idx] = pos.copy()
        buffer.ribbon_length[idx] = 0.0


def simulate_particles_cpu(
    buffer: ParticleBuffer,
    dt: float,
    curl_noise: CurlNoise | None = None,
    sdf_collision: SDFCollision | None = None,
    gravity: np.ndarray = None,
    global_wind: np.ndarray = None,
) -> None:
    """CPU particle simulation (fallback for tcod)."""
    if buffer.count == 0:
        return

    alive = buffer.get_alive_indices()
    if len(alive) == 0:
        return

    if gravity is None:
        gravity = np.array([0.0, -9.81, 0.0], dtype=np.float32)
    if global_wind is None:
        global_wind = np.zeros(3, dtype=np.float32)

    for idx in alive:
        # Update life
        buffer.life[idx, 0] += dt
        if buffer.life[idx, 0] >= buffer.life[idx, 1]:
            buffer.free(np.array([idx]))
            continue

        # Life ratio (0 to 1)
        life_ratio = buffer.life[idx, 0] / buffer.life[idx, 1]

        # Velocity
        vel = buffer.velocity[idx].copy()

        # Gravity
        vel += gravity * dt

        # Global wind
        vel += global_wind * dt

        # Curl noise
        if curl_noise is not None:
            pos = buffer.position[idx]
            t = buffer.life[idx, 0]
            noise_vel = curl_noise.curl_noise_3d(pos[0] + t, pos[1] + t, pos[2] + t)
            vel += noise_vel * dt * 5.0  # Scale factor

        # Update position
        new_pos = buffer.position[idx] + vel * dt

        # SDF Collision
        if sdf_collision is not None:
            new_pos, vel, _collided = sdf_collision.collide_particle(
                new_pos, vel, buffer.size[idx, 2]
            )

        # Update ribbon/trail
        if buffer.flags[idx] & ParticleFlags.RIBBON:
            buffer.prev_position[idx] = buffer.position[idx].copy()
            buffer.ribbon_length[idx] += np.linalg.norm(new_pos - buffer.position[idx])

        # Update rotation
        buffer.rotation[idx, 2] += buffer.rotation[idx, 1] * dt

        # Size interpolation
        buffer.size[idx, 2] = (
            buffer.size[idx, 0]
            + (buffer.size[idx, 1] - buffer.size[idx, 0]) * life_ratio
        )

        # Color interpolation (fade out)
        alpha = 1.0 - life_ratio
        buffer.color[idx, 3] = (
            base_alpha * alpha if (base_alpha := buffer.color[idx, 3]) > 0 else alpha
        )

        buffer.position[idx] = new_pos
        buffer.velocity[idx] = vel
