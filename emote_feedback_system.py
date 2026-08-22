"""Visual Emotes and Feedback System (Steps 25 - 48).

Implements visual polish and feedback features:
- Diegetic emotion/status indicators (Steps 25-32)
- Interaction anticipation with bounce animations (Steps 33-40)
- Combat feedback with floating text & icons (Steps 41-48)
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any

# ==========================================
# Step 25: Load emote icon resources
# ==========================================
EMOTE_PATHS: dict[str, str] = {
    "exclamation": os.path.join("emote", "PNG", "Pixel", "style_1", "emote_exclamation.png"),
    "question": os.path.join("emote", "PNG", "Pixel", "style_1", "emote_question.png"),
    "anger": os.path.join("emote", "PNG", "Pixel", "style_1", "emote_anger.png"),
    "swirl": os.path.join("emote", "PNG", "Pixel", "style_1", "emote_swirl.png"),
    "sleep": os.path.join("emote", "PNG", "Pixel", "style_1", "emote_sleep.png"),
    "heart": os.path.join("emote", "PNG", "Pixel", "style_1", "emote_heart.png"),
    "star": os.path.join("emote", "PNG", "Pixel", "style_1", "emote_star.png"),
    "drops": os.path.join("emote", "PNG", "Pixel", "style_1", "emote_drops.png"),
}


# ==========================================
# Step 26 - Step 32: Emote Component & System
# ==========================================
@dataclass
class EmoteComponent:
    """Step 26: Character emote state and timer."""

    current_emote: str | None = None
    emote_timer: int = 0
    max_duration: int = 60
    offset_y: float = -20.0

    def set_emote(self, emote_type: str, duration: int = 60) -> None:
        """Step 27 & 32: Set emote type and duration (e.g. 'exclamation' on spotted)."""
        self.current_emote = emote_type
        self.emote_timer = duration
        self.max_duration = duration

    def update(self) -> None:
        """Step 30: Decrement timer and clear emote when expired."""
        if self.emote_timer > 0:
            self.emote_timer -= 1
            if self.emote_timer == 0:
                self.current_emote = None

    def get_render_info(self, char_x: float, char_y: float) -> dict[str, Any] | None:
        """Step 29: Calculate render position above character."""
        if not self.current_emote or self.emote_timer <= 0:
            return None
        # subtle float effect based on remaining time
        progress = 1.0 - (self.emote_timer / max(1, self.max_duration))
        pop_scale = 1.2 if progress < 0.2 else 1.0
        return {
            "emote": self.current_emote,
            "path": EMOTE_PATHS.get(self.current_emote),
            "render_x": char_x,
            "render_y": char_y + self.offset_y - (2.0 * math.sin(progress * math.pi)),
            "scale": pop_scale,
            "alpha": min(1.0, self.emote_timer / 10.0),
        }


# ==========================================
# Step 33 - Step 40: Interaction Anticipation
# ==========================================
@dataclass
class InteractableObject:
    """Step 33: Object with interaction anticipation."""

    object_id: str
    x: float
    y: float
    is_interactable: bool = False
    interaction_radius: float = 2.5
    icon_type: str = "question"

    def check_player_distance(self, player_x: float, player_y: float) -> bool:
        """Step 35 & 36: Update is_interactable based on distance."""
        dist = math.hypot(self.x - player_x, self.y - player_y)
        self.is_interactable = dist <= self.interaction_radius
        return self.is_interactable

    def get_prompt_render_info(self, ticks: int) -> dict[str, Any] | None:
        """Steps 34, 37, 38, 39: Calculate bouncing prompt icon above object."""
        if not self.is_interactable:
            return None
        # Step 34 & 38: Smooth sine wave bounce (-5px to +5px)
        bounce_offset = 5.0 * math.sin(ticks * 0.1)
        return {
            "icon": self.icon_type,
            "path": EMOTE_PATHS.get(self.icon_type),
            "render_x": self.x,
            "render_y": self.y - 18.0 + bounce_offset,
            "bounce_offset": bounce_offset,
        }


# ==========================================
# Step 41 - Step 48: Floating Combat Feedback
# ==========================================
@dataclass
class FloatingFeedback:
    """Step 41 & 42: Floating combat damage / icon feedback element."""

    x: float
    y: float
    text: str
    icon: str | None = None
    color: str = "#ffffff"
    is_crit: bool = False
    vel_x: float = 0.0
    vel_y: float = -1.5
    lifetime: int = 45
    max_lifetime: int = 45

    def update(self) -> bool:
        """Step 43: Update movement and fade out. Returns True if still alive."""
        self.x += self.vel_x
        self.y += self.vel_y
        self.vel_y *= 0.92  # gentle deceleration
        self.lifetime -= 1
        return self.lifetime > 0

    @property
    def alpha(self) -> float:
        return max(0.0, self.lifetime / float(self.max_lifetime))


class CombatFeedbackManager:
    """Step 44: Manager maintaining all floating feedback instances."""

    def __init__(self):
        self.feedbacks: list[FloatingFeedback] = []

    def add_hit_feedback(
        self, x: float, y: float, damage: int, is_crit: bool = False
    ) -> FloatingFeedback:
        """Step 45, 46, 47, 48: Create damage feedback (standard or critical with icon)."""
        if is_crit:
            # Step 48: Critical feedback with star/anger icon, red color, larger pop
            fb = FloatingFeedback(
                x=x,
                y=y - 10.0,
                text=f"CRIT! {damage}",
                icon="star",
                color="#ff3333",
                is_crit=True,
                vel_y=-2.5,
                lifetime=60,
                max_lifetime=60,
            )
        else:
            # Step 46: Regular damage feedback
            fb = FloatingFeedback(
                x=x,
                y=y - 10.0,
                text=str(damage),
                icon=None,
                color="#ffffff",
                is_crit=False,
                vel_y=-1.5,
                lifetime=40,
                max_lifetime=40,
            )
        self.feedbacks.append(fb)
        return fb

    def update(self) -> None:
        """Update all active feedback particles."""
        self.feedbacks = [fb for fb in self.feedbacks if fb.update()]
