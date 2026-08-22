"""Graphics, Lighting, Animation, and Particle FX System (Steps 49 - 72).

Implements graphics and environmental enhancements:
- Dynamic 2D lighting, torch flickering & darkness layer (Steps 49-56)
- Squash & Stretch sprite deformation and Screen Shake (Steps 57-64)
- Environmental particles & footstep decal trail system (Steps 65-72)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any


# ==========================================
# Step 49 - Step 56: Dynamic 2D Lighting System
# ==========================================
@dataclass
class LightSource:
    """Step 54: Light source definition (player torch, campfire, etc.)."""

    x: float
    y: float
    base_radius: float = 60.0
    color: tuple[int, int, int] = (255, 200, 100)
    intensity: float = 1.0
    flicker: bool = True

    def get_current_radius(self, ticks: int) -> float:
        """Step 56: Smooth flickering calculation using sine wave and subtle noise."""
        if not self.flicker:
            return self.base_radius
        flicker_noise = (math.sin(ticks * 0.15) * 3.0) + (random.uniform(-1.0, 1.0) * 1.5)
        return max(5.0, self.base_radius + flicker_noise)


class LightingManager:
    """Steps 49-55: Ambient darkness layer with cutout light rendering."""

    def __init__(self, ambient_darkness: int = 200):
        self.ambient_darkness: int = ambient_darkness  # Step 49: Alpha 0-255
        self.lights: list[LightSource] = []

    def add_light(self, light: LightSource) -> None:
        self.lights.append(light)

    def draw_light(
        self, x: float, y: float, radius: float, intensity: float = 1.0
    ) -> dict[str, Any]:
        """Step 52 & 53: Calculate cutout mask circle parameter."""
        return {
            "center": (x, y),
            "radius": radius,
            "intensity": intensity,
            "blend_mode": "cutout_additive",
        }

    def generate_frame_lighting(
        self, player_x: float, player_y: float, ticks: int
    ) -> dict[str, Any]:
        """Step 51 & 55: Generate darkness layer and compute all active light masks."""
        # Player personal lantern/vision
        active_masks = [
            self.draw_light(
                player_x, player_y, radius=75.0 + math.sin(ticks * 0.08) * 2.0, intensity=1.0
            )
        ]
        # Map environment lights (Step 55)
        for light in self.lights:
            cur_r = light.get_current_radius(ticks)
            active_masks.append(
                self.draw_light(light.x, light.y, radius=cur_r, intensity=light.intensity)
            )

        return {
            "ambient_alpha": self.ambient_darkness,
            "light_cutouts": active_masks,
        }


# ==========================================
# Step 57 - Step 64: Squash/Stretch & Screen Shake
# ==========================================
@dataclass
class CameraShakeManager:
    """Step 57 & 58: Camera offset manager for screen shake."""

    shake_offset_x: float = 0.0
    shake_offset_y: float = 0.0
    shake_duration: int = 0
    shake_magnitude: float = 3.0

    def trigger_shake(self, duration: int = 10, magnitude: float = 3.0) -> None:
        """Step 63: Trigger screen shake upon heavy hit."""
        self.shake_duration = duration
        self.shake_magnitude = magnitude

    def update(self) -> tuple[float, float]:
        """Step 58 & 59: Calculate and return current camera shake offset."""
        if self.shake_duration > 0:
            self.shake_offset_x = random.uniform(-self.shake_magnitude, self.shake_magnitude)
            self.shake_offset_y = random.uniform(-self.shake_magnitude, self.shake_magnitude)
            self.shake_duration -= 1
        else:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0
        return self.shake_offset_x, self.shake_offset_y


@dataclass
class SpriteDeformation:
    """Step 60 - 64: Squash & stretch animation component."""

    scale_x: float = 1.0
    scale_y: float = 1.0

    def on_windup(self) -> None:
        """Step 62: Stretch vertically on attack windup."""
        self.scale_x = 0.85
        self.scale_y = 1.25

    def on_impact(self) -> None:
        """Step 63: Squash horizontally on attack impact."""
        self.scale_x = 1.30
        self.scale_y = 0.75

    def update(self, recovery_rate: float = 0.1) -> None:
        """Step 64: Smoothly restore natural 1.0 scale."""
        self.scale_x += (1.0 - self.scale_x) * recovery_rate
        self.scale_y += (1.0 - self.scale_y) * recovery_rate


# ==========================================
# Step 65 - Step 72: Particle System & Footprint Decals
# ==========================================
@dataclass
class Particle:
    """Step 65: General purpose environmental particle."""

    x: float
    y: float
    vel_x: float
    vel_y: float
    color: tuple[int, int, int, int]
    size: float
    lifetime: int
    max_lifetime: int

    def update(self) -> bool:
        """Update particle physics and lifetime."""
        self.x += self.vel_x
        self.y += self.vel_y
        self.lifetime -= 1
        return self.lifetime > 0

    @property
    def alpha(self) -> float:
        return max(0.0, self.lifetime / float(self.max_lifetime))


@dataclass
class FootprintDecal:
    """Step 68: Temporary footprint decal left on soft terrain."""

    x: float
    y: float
    angle: float = 0.0
    lifetime: int = 180  # stays for ~3 seconds at 60fps
    max_lifetime: int = 180

    def update(self) -> bool:
        self.lifetime -= 1
        return self.lifetime > 0

    @property
    def alpha(self) -> float:
        return max(0.0, self.lifetime / float(self.max_lifetime))


class EnvironmentFXManager:
    """Step 66, 67, 68, 71, 72: Environmental particle and footprint manager."""

    def __init__(self):
        self.particles: list[Particle] = []
        self.footprints: list[FootprintDecal] = []

    def spawn_ambient_dust(self, screen_width: int, screen_height: int) -> None:
        """Step 66: Spawn floating dungeon dust / motes."""
        if len(self.particles) < 30 and random.random() < 0.2:
            p = Particle(
                x=random.uniform(0, screen_width),
                y=random.uniform(0, screen_height),
                vel_x=random.uniform(-0.2, 0.2),
                vel_y=random.uniform(0.1, 0.4),
                color=(220, 220, 240, 150),
                size=random.uniform(1.0, 2.5),
                lifetime=random.randint(90, 180),
                max_lifetime=180,
            )
            self.particles.append(p)

    def on_character_step(self, x: float, y: float, terrain_type: str, angle: float = 0.0) -> None:
        """Step 67, 69, 70, 71: Spawn footprint if stepping on snow, mud, or sand."""
        soft_terrains = {"snow", "mud", "sand", "dirt"}
        if terrain_type.lower() in soft_terrains:
            self.footprints.append(FootprintDecal(x=x, y=y, angle=angle))

    def update(self, screen_width: int = 640, screen_height: int = 480) -> None:
        """Step 72: Update all FX particles and decals."""
        self.spawn_ambient_dust(screen_width, screen_height)
        self.particles = [p for p in self.particles if p.update()]
        self.footprints = [f for f in self.footprints if f.update()]


# ==========================================
# Step 66: Time-of-Day Visual Effects
# ==========================================
from time_system import TimePhase

try:
    from naRou.time_system import TimePhase
except ImportError:
    from time_system import TimePhase


class TimeOfDayFXManager:
    """時間帯別ビジュアルエフェクト管理 (Step 66)"""

    # 時間帯別パレット調整 (R, G, B乗算係数 + オフセット)
    PHASE_PALETTE_MODIFIERS = {
        TimePhase.DAWN: {
            "multiply": (1.0, 1.0, 1.2),  # 青みがかった朝
            "add": (-20, -10, 30),
            "fog_density": 0.3,
            "fog_color": (200, 200, 255),
            "description": "朝霧が立ち込める夜明け",
        },
        TimePhase.DAY: {
            "multiply": (1.0, 1.0, 1.0),  # 通常
            "add": (0, 0, 0),
            "fog_density": 0.0,
            "fog_color": (0, 0, 0),
            "description": "明るい昼間",
        },
        TimePhase.DUSK: {
            "multiply": (1.3, 1.0, 0.7),  # 赤みがかった夕暮れ
            "add": (30, 0, -20),
            "fog_density": 0.1,
            "fog_color": (255, 150, 100),
            "description": "夕焼けに染まる空",
        },
        TimePhase.NIGHT: {
            "multiply": (0.5, 0.6, 0.8),  # 暗い夜
            "add": (-30, -20, 0),
            "fog_density": 0.2,
            "fog_color": (20, 20, 60),
            "description": "星空の夜",
        },
    }

    def __init__(self):
        self.current_phase = TimePhase.DAY
        self.transition_progress = 0.0  # 0.0-1.0 (フェーズ遷移中の補間用)
        self.transition_from = None
        self.transition_to = None

    def set_phase(self, phase: TimePhase, instant: bool = False) -> None:
        """フェーズ設定"""
        if instant or self.current_phase == phase:
            self.current_phase = phase
            self.transition_progress = 0.0
            self.transition_from = None
            self.transition_to = None
        else:
            # 遷移開始
            self.transition_from = self.current_phase
            self.transition_to = phase
            self.transition_progress = 0.0

    def update_transition(self, delta: float = 0.02) -> None:
        """遷移進行 (呼び出しごとに進行)"""
        if self.transition_to is not None:
            self.transition_progress = min(1.0, self.transition_progress + delta)
            if self.transition_progress >= 1.0:
                self.current_phase = self.transition_to
                self.transition_from = None
                self.transition_to = None
                self.transition_progress = 0.0

    def get_palette_modifier(self) -> dict:
        """現在のパレット修正値取得 (遷移中は補間)"""
        if self.transition_to is not None:
            from_mod = self.PHASE_PALETTE_MODIFIERS.get(self.transition_from, {})
            to_mod = self.PHASE_PALETTE_MODIFIERS.get(self.transition_to, {})
            t = self.transition_progress

            # 線形補間
            def lerp(a, b):
                return a + (b - a) * t

            return {
                "multiply": tuple(
                    lerp(
                        from_mod.get("multiply", (1, 1, 1))[i], to_mod.get("multiply", (1, 1, 1))[i]
                    )
                    for i in range(3)
                ),
                "add": tuple(
                    lerp(from_mod.get("add", (0, 0, 0))[i], to_mod.get("add", (0, 0, 0))[i])
                    for i in range(3)
                ),
                "fog_density": lerp(from_mod.get("fog_density", 0), to_mod.get("fog_density", 0)),
                "fog_color": tuple(
                    int(
                        lerp(
                            from_mod.get("fog_color", (0, 0, 0))[i],
                            to_mod.get("fog_color", (0, 0, 0))[i],
                        )
                    )
                    for i in range(3)
                ),
                "description": to_mod.get("description", ""),
            }
        else:
            return self.PHASE_PALETTE_MODIFIERS.get(
                self.current_phase,
                {
                    "multiply": (1.0, 1.0, 1.0),
                    "add": (0, 0, 0),
                    "fog_density": 0.0,
                    "fog_color": (0, 0, 0),
                    "description": "",
                },
            )

    def apply_to_palette(self, base_palette: dict[str, tuple]) -> dict[str, tuple]:
        """ベースパレットに時間帯修正を適用"""
        mod = self.get_palette_modifier()
        mul = mod["multiply"]
        add = mod["add"]

        result = {}
        for name, color in base_palette.items():
            r = int(max(0, min(255, color[0] * mul[0] + add[0])))
            g = int(max(0, min(255, color[1] * mul[1] + add[1])))
            b = int(max(0, min(255, color[2] * mul[2] + add[2])))
            result[name] = (r, g, b)
        return result
