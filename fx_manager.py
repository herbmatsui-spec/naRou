"""
FX & Presentation Management System
Decouples visual effects (particles, floating text, screen shake) from game logic via EventBus.
"""

from __future__ import annotations

import math
import random
from typing import Any

from core.tiny_rogue_tiles import get_effect_tile_id
from core_framework import EventBus
from feature_flags import is_enabled
from ui_fx_systems import FloatingText, Particle, ScreenShake


class FXManager:
    """エフェクトとプレゼンテーション層の統合管理クラス (商用MVC/MVP設計)"""

    def __init__(self, event_bus: EventBus | None = None):
        self.floating_texts: list[FloatingText] = []
        self.particles: list[Particle] = []
        self.screen_shake = ScreenShake()
        self.glitch_duration: int = 0  # Proposal 7: 次元干渉グリッチ残りフレーム
        self.hit_stop_frames: int = 0  # ヒットストップ残りフレーム
        self.event_bus = event_bus

        if self.event_bus:
            self._register_event_handlers()

    def _register_event_handlers(self) -> None:
        self.event_bus.subscribe("damage_dealt", self._on_damage_dealt)
        self.event_bus.subscribe("entity_killed", self._on_entity_killed)
        self.event_bus.subscribe("trap_triggered", self._on_trap_triggered)

    def _on_damage_dealt(self, data: Any) -> None:
        if not isinstance(data, dict):
            return
        dmg = data.get("damage", 0)
        x = data.get("x", 0)
        y = data.get("y", 0)
        is_crit = data.get("is_crit", False)
        is_kill = data.get("is_kill", False)

        color = (255, 230, 80) if is_crit else (255, 100, 100)
        self.add_floating_text(f"-{dmg}", x, y - 0.2, color)

        # Spawn blood splatter using TR_DECOR_BLOOD (or TR_DECOR_10) tile
        if is_enabled("ENABLE_TINY_ROGUE_GFX"):
            self.spawn_blood_splatter(x, y, is_crit=is_crit, is_kill=is_kill)

        if is_crit:
            # 衝撃方向を計算 (攻撃側から対象側へ)
            # 本来は攻撃者の座標が必要だが、ここでは簡易的にランダム方向または固定方向
            direction = (random.uniform(-1, 1), random.uniform(-1, 1))
            self.trigger_shake(intensity=1.5, duration=4, direction=direction)
            self.trigger_hit_stop(duration=6)
            self.spawn_shockwave(x, y, color=(255, 255, 200))
            # Screen flash on crit
            self.trigger_flash(x, y, color=(255, 255, 150), duration=3)

    def _on_entity_killed(self, data: Any) -> None:
        if not isinstance(data, dict):
            return
        x = data.get("x", 0)
        y = data.get("y", 0)
        monster_type = data.get("monster_type", "unknown")
        self.trigger_shake(intensity=1.2, duration=3)
        self.spawn_explosion(x, y, count=3)

        # Spawn blood pool on kill
        if is_enabled("ENABLE_TINY_ROGUE_GFX"):
            self.spawn_blood_pool(x, y)
            # Play death animation - spawn death frame then fade
            self.spawn_death_animation(x, y, monster_type)

    def spawn_death_animation(self, x: float, y: float, monster_type: str = "generic") -> None:
        """Spawn death animation using TR_MONSTER_* death frame then fade."""
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return

        # Map monster type to death effect
        death_effect_map = {
            "slime": "smoke",
            "goblin": "blood",
            "orc": "blood",
            "skeleton": "smoke",
            "ghost": "smoke",
            "dragon": "fire",
        }
        effect_type = death_effect_map.get(monster_type, "smoke")

        # Spawn death frame (monster collapsing)
        self.spawn_tile_effect(x, y, effect_type, count=1, life=20, vx=0, vy=0)

        # Fade out particles
        for i in range(3):
            self.spawn_tile_effect(
                x + random.uniform(-0.5, 0.5),
                y + random.uniform(-0.5, 0.5),
                "smoke",
                count=1,
                life=15 - i * 3,
                vx=random.uniform(-0.2, 0.2),
                vy=random.uniform(-0.2, 0.2),
                color=(100, 100, 100),
            )

    def _on_trap_triggered(self, data: Any) -> None:
        if not isinstance(data, dict):
            return
        dmg = data.get("damage", 0)
        x = data.get("x", 0)
        y = data.get("y", 0)
        self.trigger_shake(intensity=1.0, duration=3)
        self.add_floating_text(f"-{dmg}", x, y - 0.2, (255, 80, 80))

    def spawn_blood_splatter(
        self, x: float, y: float, is_crit: bool = False, is_kill: bool = False
    ) -> None:
        """Spawn blood splatter using TR_DECOR_BLOOD (TR_DECOR_10) tile."""
        # Use tile effect for blood - spawn at impact point
        self.spawn_tile_effect(x, y, "blood", count=1)
        # Also add some directional blood particles for crit/kill
        if is_crit or is_kill:
            for angle in range(0, 360, 90):
                rad = math.radians(angle)
                self.spawn_tile_effect(
                    x + math.cos(rad) * 0.5,
                    y + math.sin(rad) * 0.5,
                    "blood",
                    count=1,
                    vx=math.cos(rad) * 0.1,
                    vy=math.sin(rad) * 0.1,
                    life=8,
                )

    def spawn_blood_pool(self, x: float, y: float) -> None:
        """Spawn a persistent blood pool using TR_DECOR_BLOOD tile at the kill location."""
        # Spawn a larger blood pool that stays on the ground
        self.spawn_tile_effect(x, y, "blood", count=1, vx=0, vy=0, life=120)
        # Add some surrounding splatter
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            self.spawn_tile_effect(
                x + math.cos(rad) * 0.8,
                y + math.sin(rad) * 0.8,
                "blood",
                count=1,
                vx=0,
                vy=0,
                life=60,
            )

    def add_floating_text(self, text: str, x: float, y: float, color: tuple[int, int, int]) -> None:
        self.floating_texts.append(FloatingText(text, x, y, color))

    def spawn_explosion(self, x: float, y: float, count: int = 3) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    "💥",
                    x,
                    y,
                    (255, 180, 50),
                    life=3,
                    vx=random.uniform(-0.4, 0.4),
                    vy=random.uniform(-0.4, 0.4),
                )
            )

    def trigger_shake(
        self,
        intensity: float = 1.0,
        duration: int = 3,
        direction: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        self.screen_shake.trigger(intensity=intensity, duration=duration, direction=direction)

    def trigger_hit_stop(self, duration: int = 4) -> None:
        """攻撃命中時の瞬間停止をトリガー"""
        self.hit_stop_frames = duration

    def trigger_flash(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int] = (255, 255, 150),
        duration: int = 3,
    ) -> None:
        """画面フラッシュエフェクト (Tiny Rogue TR_EFFECT_09 sparkle + TR_EFFECT_01 magic_cast)"""
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return

        # Spawn sparkle particles at the impact point
        self.spawn_sparkle_effect(x, y, count=8)

        # Spawn a brief magic cast flash
        self.spawn_magic_cast(x, y, color=color, count=4)

        # Trigger a brief screen shake for impact feel
        self.trigger_shake(intensity=0.5, duration=2)

    def spawn_shockwave(
        self, x: float, y: float, color: tuple[int, int, int] = (255, 255, 255)
    ) -> None:
        """同心円状の衝撃波パーティクルを展開"""
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            self.particles.append(
                Particle(
                    char="*",
                    x=x,
                    y=y,
                    color=color,
                    life=5,
                    vx=math.cos(rad) * 0.6,
                    vy=math.sin(rad) * 0.6,
                )
            )

    def spawn_emotion_particles(self, x: float, y: float, emotion: str) -> None:
        """NPCの感情に応じたパーティクルを散布 (Proposal 6)"""
        emotion_map = {
            "angry": {
                "chars": ["💢", "🔥"],
                "colors": [(255, 50, 50), (255, 150, 0)],
                "count": 5,
            },
            "happy": {
                "chars": ["✨", "❤️", "♪"],
                "colors": [(255, 200, 200), (255, 255, 150)],
                "count": 8,
            },
            "confused": {
                "chars": ["❓", "🌀"],
                "colors": [(150, 150, 255), (200, 200, 200)],
                "count": 4,
            },
            "sad": {
                "chars": ["💧", "☁️"],
                "colors": [(100, 100, 255), (150, 150, 180)],
                "count": 5,
            },
        }
        cfg = emotion_map.get(emotion, emotion_map["confused"])
        for _ in range(cfg["count"]):
            self.particles.append(
                Particle(
                    char=random.choice(cfg["chars"]),
                    x=x,
                    y=y,
                    color=random.choice(cfg["colors"]),
                    life=random.randint(5, 10),
                    vx=random.uniform(-0.3, 0.3),
                    vy=random.uniform(-0.5, -0.1),
                )
            )

    def spawn_material_particles(self, x: float, y: float, material: str, count: int = 5) -> None:
        """材質に基づいた偏執的なパーティクル散布 (Proposal 2)"""
        # 材質別定義: (文字リスト, 色リスト, 速度範囲, 生存期間)
        mat_map = {
            "stone": (
                ["#", "·", "."],
                [(120, 120, 120), (100, 100, 100), (150, 150, 150)],
                (0.2, 0.6),
                (3, 6),
            ),
            "metal": (
                ["*", "✧", "·"],
                [(200, 200, 220), (255, 255, 255), (180, 180, 200)],
                (0.4, 0.8),
                (2, 5),
            ),
            "flesh": (
                ["o", "·", "."],
                [(200, 0, 0), (150, 0, 0), (100, 0, 0)],
                (0.1, 0.4),
                (4, 8),
            ),
            "crystal": (
                ["✦", "✧", "✨"],
                [(100, 200, 255), (200, 100, 255), (150, 255, 150)],
                (0.3, 0.7),
                (5, 10),
            ),
            "default": (
                ["·", "."],
                [(150, 150, 150), (100, 100, 100)],
                (0.2, 0.5),
                (3, 6),
            ),
        }
        cfg = mat_map.get(material, mat_map["default"])
        chars, colors, speed_range, life_range = cfg

        for _ in range(count):
            self.particles.append(
                Particle(
                    char=random.choice(chars),
                    x=x,
                    y=y,
                    color=random.choice(colors),
                    life=random.randint(*life_range),
                    vx=random.uniform(-speed_range[1], speed_range[1]),
                    vy=random.uniform(-speed_range[1], speed_range[1]),
                )
            )

    # --- Tiny Rogue Tile-based Effects ---

    def spawn_tile_effect(
        self, x: float, y: float, effect_type: str, count: int = 1, **kwargs
    ) -> None:
        """
        Spawn particles using Tiny Rogue TR_EFFECT_* tiles.
        Uses the new asset pack when ENABLE_TINY_ROGUE_GFX is enabled.

        Args:
            x, y: World coordinates
            effect_type: One of 'magic_cast', 'fire', 'ice', 'lightning', 'poison',
                        'heal', 'teleport', 'explosion', 'sparkle', 'smoke', 'slash', 'shockwave'
            count: Number of particles to spawn
            **kwargs: Additional Particle kwargs (vx, vy, life, etc.)
        """
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            # Fallback to existing particle methods
            fallback_map = {
                "fire": lambda: self.spawn_material_particles(x, y, "default", count),
                "ice": lambda: self.spawn_material_particles(x, y, "crystal", count),
                "magic_cast": lambda: self.spawn_emotion_particles(x, y, "happy"),
                "heal": lambda: self.spawn_emotion_particles(x, y, "happy"),
                "explosion": lambda: self.spawn_explosion(x, y, count),
                "slash": lambda: self.spawn_shockwave(x, y, (255, 100, 100)),
            }
            fallback_map.get(effect_type, lambda: None)()
            return

        tile_id = get_effect_tile_id(effect_type)

        for _ in range(count):
            self.particles.append(
                Particle(
                    char="",  # Empty char - will be rendered via tile
                    x=x,
                    y=y,
                    color=kwargs.get("color", (255, 255, 255)),
                    life=kwargs.get("life", 5),
                    vx=kwargs.get("vx", random.uniform(-0.3, 0.3)),
                    vy=kwargs.get("vy", random.uniform(-0.3, 0.3)),
                    tile_id=tile_id,  # Store tile ID for rendering
                )
            )

    def spawn_magic_cast(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int] = (100, 200, 255),
        count: int = 3,
    ) -> None:
        """Spawn magic cast effect using TR_EFFECT_01 (magic_cast)."""
        self.spawn_tile_effect(
            x,
            y,
            "magic_cast",
            count,
            color=color,
            life=8,
            vx=random.uniform(-0.2, 0.2),
            vy=random.uniform(-0.4, -0.1),
        )

    def spawn_fire_effect(self, x: float, y: float, count: int = 5) -> None:
        """Spawn fire effect using TR_EFFECT_02 (fire)."""
        self.spawn_tile_effect(
            x,
            y,
            "fire",
            count,
            color=(255, 100, 0),
            life=6,
            vx=random.uniform(-0.3, 0.3),
            vy=random.uniform(-0.5, -0.1),
        )

    def spawn_ice_effect(self, x: float, y: float, count: int = 4) -> None:
        """Spawn ice effect using TR_EFFECT_03 (ice)."""
        self.spawn_tile_effect(
            x,
            y,
            "ice",
            count,
            color=(100, 200, 255),
            life=7,
            vx=random.uniform(-0.2, 0.2),
            vy=random.uniform(-0.3, 0.1),
        )

    def spawn_lightning_effect(self, x: float, y: float, count: int = 3) -> None:
        """Spawn lightning effect using TR_EFFECT_04 (lightning)."""
        self.spawn_tile_effect(
            x,
            y,
            "lightning",
            count,
            color=(255, 255, 100),
            life=4,
            vx=random.uniform(-0.5, 0.5),
            vy=random.uniform(-0.5, 0.5),
        )

    def spawn_poison_effect(self, x: float, y: float, count: int = 6) -> None:
        """Spawn poison effect using TR_EFFECT_05 (poison)."""
        self.spawn_tile_effect(
            x,
            y,
            "poison",
            count,
            color=(100, 255, 100),
            life=10,
            vx=random.uniform(-0.2, 0.2),
            vy=random.uniform(-0.1, 0.2),
        )

    def spawn_heal_effect(self, x: float, y: float, count: int = 8) -> None:
        """Spawn heal effect using TR_EFFECT_06 (heal)."""
        self.spawn_tile_effect(
            x,
            y,
            "heal",
            count,
            color=(100, 255, 150),
            life=8,
            vx=random.uniform(-0.1, 0.1),
            vy=random.uniform(-0.4, -0.1),
        )

    def spawn_loot_sparkle(self, x: float, y: float, rarity: str = "common") -> None:
        """Spawn loot sparkle on item drop using TR_EFFECT_09 (sparkle)."""
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return

        rarity_colors = {
            "common": (200, 200, 200),
            "uncommon": (100, 255, 100),
            "rare": (100, 150, 255),
            "epic": (200, 100, 255),
            "legendary": (255, 215, 0),
        }
        color = rarity_colors.get(rarity, (200, 200, 200))

        # Main sparkle
        self.spawn_sparkle_effect(x, y, count=6)

        # Rising particles
        for i in range(4):
            self.spawn_tile_effect(
                x + random.uniform(-0.3, 0.3),
                y - i * 0.3,
                "sparkle",
                count=1,
                color=color,
                life=8,
                vx=random.uniform(-0.1, 0.1),
                vy=random.uniform(-0.3, -0.1),
            )

    def spawn_teleport_effect(self, x: float, y: float, count: int = 10) -> None:
        """Spawn teleport effect using TR_EFFECT_07 (teleport)."""
        self.spawn_tile_effect(
            x,
            y,
            "teleport",
            count,
            color=(200, 100, 255),
            life=6,
            vx=random.uniform(-0.4, 0.4),
            vy=random.uniform(-0.4, 0.4),
        )

    def spawn_explosion_effect(self, x: float, y: float, count: int = 12) -> None:
        """Spawn explosion effect using TR_EFFECT_08 (explosion)."""
        self.spawn_tile_effect(
            x,
            y,
            "explosion",
            count,
            color=(255, 150, 0),
            life=5,
            vx=random.uniform(-0.6, 0.6),
            vy=random.uniform(-0.6, 0.6),
        )

    def spawn_sparkle_effect(self, x: float, y: float, count: int = 5) -> None:
        """Spawn sparkle effect using TR_EFFECT_09 (sparkle)."""
        self.spawn_tile_effect(
            x,
            y,
            "sparkle",
            count,
            color=(255, 255, 200),
            life=4,
            vx=random.uniform(-0.2, 0.2),
            vy=random.uniform(-0.3, 0.1),
        )

    def spawn_smoke_effect(self, x: float, y: float, count: int = 6) -> None:
        """Spawn smoke effect using TR_EFFECT_10 (smoke)."""
        self.spawn_tile_effect(
            x,
            y,
            "smoke",
            count,
            color=(150, 150, 150),
            life=12,
            vx=random.uniform(-0.3, 0.3),
            vy=random.uniform(-0.2, 0.2),
        )

    def spawn_slash_effect(
        self,
        x: float,
        y: float,
        direction: tuple[float, float] = (1, 0),
        count: int = 3,
    ) -> None:
        """Spawn slash effect using TR_EFFECT_11 (slash) in a line."""
        dx, dy = direction
        for i in range(count):
            self.spawn_tile_effect(
                x + dx * i * 0.5,
                y + dy * i * 0.5,
                "slash",
                1,
                color=(255, 200, 100),
                life=3,
                vx=dx * 0.1,
                vy=dy * 0.1,
            )

    def spawn_shockwave_effect(self, x: float, y: float, count: int = 16) -> None:
        """Spawn shockwave effect using TR_EFFECT_12 (shockwave) in a circle."""
        self.spawn_tile_effect(x, y, "shockwave", count, color=(255, 255, 200), life=6, vx=0, vy=0)

    def spawn_water_splash(self, x: float, y: float, count: int = 4) -> None:
        """Spawn water splash using TR_EFFECT_02/03/04 (water frames)."""
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return
        for i in range(count):
            frame = i % 3 + 1  # Cycle through water frames
            self.spawn_tile_effect(
                x + random.uniform(-0.3, 0.3),
                y + random.uniform(-0.3, 0.3),
                f"water_{frame}",  # Will map to TR_EFFECT_02/03/04
                count=1,
                color=(100, 150, 255),
                life=4,
                vx=random.uniform(-0.4, 0.4),
                vy=random.uniform(-0.4, -0.1),
            )

    def spawn_lava_bubble(self, x: float, y: float, count: int = 3) -> None:
        """Spawn lava bubble using TR_EFFECT_05/06/07 (lava frames)."""
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return
        for i in range(count):
            frame = i % 3 + 1
            self.spawn_tile_effect(
                x + random.uniform(-0.2, 0.2),
                y + random.uniform(-0.2, 0.2),
                f"lava_{frame}",  # Will map to TR_EFFECT_05/06/07
                count=1,
                color=(255, 100, 0),
                life=5,
                vx=random.uniform(-0.1, 0.1),
                vy=random.uniform(-0.3, -0.1),
            )

    def spawn_footstep_particles(
        self,
        x: float,
        y: float,
        floor_type: str = "default",
        direction: tuple[float, float] = (0, 0),
    ) -> None:
        """Spawn footstep particles matching floor tile type."""
        if not is_enabled("ENABLE_TINY_ROGUE_GFX"):
            return

        # Different particle styles for different floor types
        if floor_type == "stone":
            self.spawn_material_particles(x, y, "stone", count=2)
        elif floor_type == "water":
            self.spawn_tile_effect(
                x,
                y,
                "fire",
                count=1,
                color=(100, 150, 255),
                life=3,
                vx=-direction[0] * 0.2,
                vy=-direction[1] * 0.2,
            )
        elif floor_type == "grass":
            self.spawn_material_particles(x, y, "default", count=1)
        elif floor_type == "dirt":
            self.spawn_material_particles(x, y, "stone", count=1)
        else:
            # Default small puff
            self.spawn_tile_effect(
                x,
                y,
                "smoke",
                count=1,
                color=(150, 150, 150),
                life=3,
                vx=-direction[0] * 0.1,
                vy=-direction[1] * 0.1,
            )

    def trigger_glitch(self, duration: int = 5) -> None:
        """Proposal 7: 精神世界・次元干渉グリッチをトリガー"""
        self.glitch_duration = duration

    def update(self, delta_time: float = 1.0) -> None:
        """エフェクトのフレーム更新"""
        if self.hit_stop_frames > 0:
            self.hit_stop_frames -= 1
            return  # ヒットストップ中は他のエフェクト更新を停止して静止感を出す

        self.floating_texts = [ft for ft in self.floating_texts if ft.update()]
        self.particles = [p for p in self.particles if p.update()]
        self.screen_shake.update()
        if self.glitch_duration > 0:
            self.glitch_duration -= 1
