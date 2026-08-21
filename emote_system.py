"""
Emote System Module
Handles emote animations and display for entities.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[EMOTE] %(levelname)s: %(message)s'))
    logger.addHandler(handler)


@dataclass
class EmoteAnimation:
    """Represents a single emote animation."""
    name: str
    frames: list[str]  # List of sprite paths
    fps: int = 8
    loop: bool = False
    duration: float = 1.0  # seconds

    def __post_init__(self):
        if self.frames and self.duration <= 0:
            self.duration = len(self.frames) / self.fps


@dataclass
class EmoteState:
    """Tracks the current emote state of an entity."""
    current_emote: str | None = None
    start_time: float = 0.0
    frame_index: int = 0
    animation: EmoteAnimation | None = None
    
    def is_playing(self) -> bool:
        return self.current_emote is not None and self.animation is not None
    
    def update(self, dt: float) -> bool:
        """Update emote animation. Returns True if still playing."""
        if not self.is_playing() or not self.animation:
            return False
        
        elapsed = time.time() - self.start_time
        if elapsed >= self.animation.duration:
            if self.animation.loop:
                self.start_time = time.time()
                self.frame_index = 0
                return True
            else:
                self.stop()
                return False
        
        self.frame_index = int(elapsed * self.animation.fps) % len(self.animation.frames)
        return True
    
    def stop(self) -> None:
        self.current_emote = None
        self.start_time = 0.0
        self.frame_index = 0
        self.animation = None
    
    def get_current_frame(self) -> str | None:
        if not self.is_playing() or not self.animation or not self.animation.frames:
            return None
        idx = min(self.frame_index, len(self.animation.frames) - 1)
        return self.animation.frames[idx]


class EmoteSystem:
    """Manages emote animations for all entities."""
    
    # Predefined emote animations mapped to sprite paths
    EMOTE_DEFINITIONS: dict[str, dict[str, Any]] = {
        "anger": {"pattern": "emote_anger", "fps": 10, "duration": 0.5},
        "exclamation": {"pattern": "emote_exclamation", "fps": 8, "duration": 0.6},
        "question": {"pattern": "emote_question", "fps": 8, "duration": 0.6},
        "idea": {"pattern": "emote_idea", "fps": 6, "duration": 1.0},
        "heart": {"pattern": "emote_heart", "fps": 4, "duration": 1.5},
        "heart_broken": {"pattern": "emote_heartBroken", "fps": 4, "duration": 1.5},
        "sleep": {"pattern": "emote_sleep", "fps": 2, "duration": 2.0, "loop": True},
        "laugh": {"pattern": "emote_laugh", "fps": 10, "duration": 0.8},
        "sad": {"pattern": "emote_faceSad", "fps": 4, "duration": 1.0},
        "happy": {"pattern": "emote_faceHappy", "fps": 4, "duration": 1.0},
        "angry_face": {"pattern": "emote_faceAngry", "fps": 4, "duration": 1.0},
        "alert": {"pattern": "emote_alert", "fps": 12, "duration": 0.4},
        "music": {"pattern": "emote_music", "fps": 6, "duration": 1.2},
        "star": {"pattern": "emote_star", "fps": 8, "duration": 0.8},
        "dots": {"pattern": "emote_dots1", "fps": 4, "duration": 1.0},
        "sweat": {"pattern": "emote_drop", "fps": 6, "duration": 0.8},
        "swirl": {"pattern": "emote_swirl", "fps": 8, "duration": 1.0},
        "cash": {"pattern": "emote_cash", "fps": 8, "duration": 0.8},
    }
    
    def __init__(self, style: str = "style1"):
        self.style = style
        self.entity_states: dict[str, EmoteState] = {}  # entity_id -> EmoteState
        self._animation_cache: dict[str, EmoteAnimation] = {}
        self._build_animations()
    
    def _build_animations(self) -> None:
        """Build emote animations from available sprites."""
        for emote_name, defn in self.EMOTE_DEFINITIONS.items():
            pattern = defn["pattern"]
            # Try to find matching sprites in the style directory
            frames = self._find_emote_frames(pattern)
            if frames:
                self._animation_cache[emote_name] = EmoteAnimation(
                    name=emote_name,
                    frames=frames,
                    fps=defn.get("fps", 8),
                    loop=defn.get("loop", False),
                    duration=defn.get("duration", 1.0)
                )
                logger.debug(f"Loaded emote '{emote_name}': {len(frames)} frame(s) from {frames[0]}")
            else:
                logger.warning(f"Emote '{emote_name}' (pattern: {pattern}) not found in style '{self.style}'")
    
    def _find_emote_frames(self, pattern: str) -> list[str]:
        """Find all frames matching a pattern in the current style."""
        frames = []
        # First try exact match in pixel style
        base_path = f"assets/emote/pixel/{self.style}"
        import os
        if os.path.exists(base_path):
            # Check for animated variants (emote_name_00, emote_name_01, etc.)
            for i in range(10):
                fname = f"{pattern}_{i:02d}.png"
                fpath = os.path.join(base_path, fname)
                if os.path.exists(fpath):
                    frames.append(fpath)
            
            # Check for single frame
            if not frames:
                fname = f"{pattern}.png"
                fpath = os.path.join(base_path, fname)
                if os.path.exists(fpath):
                    frames.append(fpath)
        
        # Also check tilesheets for animated sequences
        if not frames:
            tilesheet_path = f"assets/emote/tilesheets/pixel_{self.style}.png"
            if os.path.exists(tilesheet_path):
                frames.append(tilesheet_path)
        
        return frames
    
    def play_emote(self, entity_id: str, emote_name: str) -> bool:
        """
        Play an emote for an entity.
        Returns True if emote started successfully.
        """
        if emote_name not in self._animation_cache:
            logger.warning(f"Attempted to play unknown emote: '{emote_name}'")
            return False
        
        if entity_id not in self.entity_states:
            self.entity_states[entity_id] = EmoteState()
        
        state = self.entity_states[entity_id]
        animation = self._animation_cache[emote_name]
        
        state.current_emote = emote_name
        state.start_time = time.time()
        state.frame_index = 0
        state.animation = animation
        logger.debug(f"Entity '{entity_id}' started emote '{emote_name}'")
        return True
    
    def stop_emote(self, entity_id: str) -> None:
        """Stop the current emote for an entity."""
        if entity_id in self.entity_states:
            self.entity_states[entity_id].stop()
    
    def update(self, dt: float) -> None:
        """Update all entity emote states."""
        for state in self.entity_states.values():
            state.update(dt)
    
    def get_current_frame(self, entity_id: str) -> str | None:
        """Get the current emote frame path for an entity."""
        if entity_id in self.entity_states:
            return self.entity_states[entity_id].get_current_frame()
        return None
    
    def is_playing(self, entity_id: str) -> bool:
        """Check if an entity is currently playing an emote."""
        if entity_id in self.entity_states:
            return self.entity_states[entity_id].is_playing()
        return False
    
    def get_available_emotes(self) -> list[str]:
        """Get list of available emote names."""
        return list(self._animation_cache.keys())


# Global emote system instance
EMOTE_SYSTEM = EmoteSystem()


def play_emote(entity_id: str, emote_name: str, style: str = "style1") -> bool:
    """Convenience function to play an emote on the global system."""
    global EMOTE_SYSTEM
    if EMOTE_SYSTEM.style != style:
        EMOTE_SYSTEM = EmoteSystem(style)
    return EMOTE_SYSTEM.play_emote(entity_id, emote_name)


def stop_emote(entity_id: str) -> None:
    """Convenience function to stop an emote on the global system."""
    EMOTE_SYSTEM.stop_emote(entity_id)


def update_emotes(dt: float) -> None:
    """Update all emotes on the global system."""
    EMOTE_SYSTEM.update(dt)


def get_emote_frame(entity_id: str) -> str | None:
    """Get current emote frame for an entity."""
    return EMOTE_SYSTEM.get_current_frame(entity_id)