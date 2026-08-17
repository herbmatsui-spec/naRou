"""
FX & Presentation Management System
Decouples visual effects (particles, floating text, screen shake) from game logic via EventBus.
"""

from __future__ import annotations
import random
from typing import List, Tuple, Optional, Any
from ui_fx_systems import FloatingText, Particle, ScreenShake
from core_framework import EventBus


class FXManager:
    """エフェクトとプレゼンテーション層の統合管理クラス (商用MVC/MVP設計)"""
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.floating_texts: List[FloatingText] = []
        self.particles: List[Particle] = []
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
        
        color = (255, 230, 80) if is_crit else (255, 100, 100)
        self.add_floating_text(f"-{dmg}", x, y - 0.2, color)
        
        if is_crit:
            self.trigger_shake(intensity=1.5, duration=4)
            self.trigger_hit_stop(duration=6)
            self.spawn_shockwave(x, y, color=(255, 255, 200))

    def _on_entity_killed(self, data: Any) -> None:
        if not isinstance(data, dict):
            return
        x = data.get("x", 0)
        y = data.get("y", 0)
        self.trigger_shake(intensity=1.2, duration=3)
        self.spawn_explosion(x, y, count=3)

    def _on_trap_triggered(self, data: Any) -> None:
        if not isinstance(data, dict):
            return
        dmg = data.get("damage", 0)
        x = data.get("x", 0)
        y = data.get("y", 0)
        self.trigger_shake(intensity=1.0, duration=3)
        self.add_floating_text(f"-{dmg}", x, y - 0.2, (255, 80, 80))

    def add_floating_text(self, text: str, x: float, y: float, color: Tuple[int, int, int]) -> None:
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
                    vy=random.uniform(-0.4, 0.4)
                )
            )

    def trigger_shake(self, intensity: float = 1.0, duration: int = 3) -> None:
        self.screen_shake.trigger(intensity=intensity, duration=duration)

    def trigger_hit_stop(self, duration: int = 4) -> None:
        """攻撃命中時の瞬間停止をトリガー"""
        self.hit_stop_frames = duration

    def spawn_shockwave(self, x: float, y: float, color: Tuple[int, int, int] = (255, 255, 255)) -> None:
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
                    vy=math.sin(rad) * 0.6
                )
            )

    def spawn_emotion_particles(self, x: float, y: float, emotion: str) -> None:
        """NPCの感情に応じたパーティクルを散布 (Proposal 6)"""
        emotion_map = {
            "angry": {"chars": ["💢", "🔥"], "colors": [(255, 50, 50), (255, 150, 0)], "count": 5},
            "happy": {"chars": ["✨", "❤️", "♪"], "colors": [(255, 200, 200), (255, 255, 150)], "count": 8},
            "confused": {"chars": ["❓", "🌀"], "colors": [(150, 150, 255), (200, 200, 200)], "count": 4},
            "sad": {"chars": ["💧", "☁️"], "colors": [(100, 100, 255), (150, 150, 180)], "count": 5},
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
                    vy=random.uniform(-0.5, -0.1)
                )
            )

    def trigger_glitch(self, duration: int = 5) -> None:
        """Proposal 7: 精神世界・次元干渉グリッチをトリガー"""
        self.glitch_duration = duration

    def update(self) -> None:
        """エフェクトのフレーム更新"""
        if self.hit_stop_frames > 0:
            self.hit_stop_frames -= 1
            return  # ヒットストップ中は他のエフェクト更新を停止して静止感を出す

        self.floating_texts = [ft for ft in self.floating_texts if ft.update()]
        self.particles = [p for p in self.particles if p.update()]
        self.screen_shake.update()
        if self.glitch_duration > 0:
            self.glitch_duration -= 1
