"""Dynamic Audio Enhancement Module (Steps 1-24).

Implements realistic audio features:
- Footstep randomization with pitch variation (Steps 1-8)
- Diegetic UI sounds (Steps 9-16)
- Positional/Spatial 3D audio (Steps 17-24)
"""

from __future__ import annotations

import logging
import math
import os
import random
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ==========================================
# Step 1: Define footstep sound file paths
# ==========================================
FOOTSTEP_SOUND_PATHS: list[str] = [
    os.path.join("audio", "Audio", f"footstep{i:02d}.ogg") for i in range(10)
]

# ==========================================
# Step 2: Cache for loaded footstep audio objects
# ==========================================
_FOOTSTEP_AUDIO_CACHE: list[Any] = []
_AUDIO_LOADED: bool = False


def load_footstep_cache(loader_func: Callable[[str], Any] | None = None) -> list[Any]:
    """Step 2: Loop through FOOTSTEP_SOUND_PATHS and cache audio objects in memory."""
    global _FOOTSTEP_AUDIO_CACHE, _AUDIO_LOADED
    _FOOTSTEP_AUDIO_CACHE.clear()
    for path in FOOTSTEP_SOUND_PATHS:
        if loader_func:
            try:
                sound_obj = loader_func(path)
                _FOOTSTEP_AUDIO_CACHE.append(sound_obj)
            except Exception as e:
                logger.warning("Failed to load footstep sound %s: %s", path, e)
                _FOOTSTEP_AUDIO_CACHE.append(path)
        else:
            # Store validated path or resource identifier
            _FOOTSTEP_AUDIO_CACHE.append(path)
    _AUDIO_LOADED = True
    return _FOOTSTEP_AUDIO_CACHE


# ==========================================
# Step 3 - Step 7: Footstep sound playback
# ==========================================
def play_footstep_sound(
    volume: float = 0.6,
    backend_play_func: Callable[[Any, float, float], None] | None = None,
) -> dict[str, Any]:
    """Steps 3-7: Play footstep with randomized selection and pitch modulation."""
    global _FOOTSTEP_AUDIO_CACHE
    if not _FOOTSTEP_AUDIO_CACHE:
        load_footstep_cache()

    # Step 4: Random selection from 0 to 9
    idx = random.randint(0, len(_FOOTSTEP_AUDIO_CACHE) - 1)
    selected_sound = _FOOTSTEP_AUDIO_CACHE[idx]

    # Step 5: Random pitch modulation between 0.95 and 1.05
    pitch = random.uniform(0.95, 1.05)

    # Step 6 & 7: Apply pitch and play sound
    if backend_play_func:
        try:
            backend_play_func(selected_sound, volume, pitch)
        except Exception as e:
            logger.debug("Playback backend error: %s", e)

    return {
        "index": idx,
        "sound": selected_sound,
        "pitch": pitch,
        "volume": volume,
    }


# ==========================================
# Step 9 - Step 16: Diegetic UI Sounds
# ==========================================
UI_SOUND_PATHS: dict[str, str] = {
    "bookOpen": os.path.join("audio", "Audio", "bookOpen.ogg"),
    "bookFlip": os.path.join("audio", "Audio", "bookFlip1.ogg"),
    "bookClose": os.path.join("audio", "Audio", "bookClose.ogg"),
    "cloth1": os.path.join("audio", "Audio", "cloth1.ogg"),
    "clothBelt": os.path.join("audio", "Audio", "clothBelt.ogg"),
    "handleCoins": os.path.join("audio", "Audio", "handleCoins.ogg"),
    "metalClick": os.path.join("audio", "Audio", "metalClick.ogg"),
    "metalLatch": os.path.join("audio", "Audio", "metalLatch.ogg"),
    "knifeSlice": os.path.join("audio", "Audio", "knifeSlice.ogg"),
}

_UI_AUDIO_CACHE: dict[str, Any] = {}


def load_ui_sound_cache(loader_func: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """Step 10: Load and cache UI sound files into memory."""
    global _UI_AUDIO_CACHE
    _UI_AUDIO_CACHE.clear()
    for key, path in UI_SOUND_PATHS.items():
        if loader_func:
            try:
                _UI_AUDIO_CACHE[key] = loader_func(path)
            except Exception as e:
                logger.warning("Failed to load UI sound %s: %s", key, e)
                _UI_AUDIO_CACHE[key] = path
        else:
            _UI_AUDIO_CACHE[key] = path
    return _UI_AUDIO_CACHE


def play_ui_sound(
    sound_key: str,
    volume: float = 0.7,
    backend_play_func: Callable[[Any, float], None] | None = None,
) -> dict[str, Any]:
    """Step 11: Play UI sound (e.g. bookOpen for menus, cloth1 for equip, handleCoins for shop)."""
    global _UI_AUDIO_CACHE
    if not _UI_AUDIO_CACHE:
        load_ui_sound_cache()

    sound_obj = _UI_AUDIO_CACHE.get(sound_key, UI_SOUND_PATHS.get(sound_key))
    if backend_play_func and sound_obj:
        try:
            backend_play_func(sound_obj, volume)
        except Exception as e:
            logger.debug("UI sound play error: %s", e)

    return {"key": sound_key, "sound": sound_obj, "volume": volume}


# ==========================================
# Step 17 - Step 24: Spatial / 3D Audio
# ==========================================
ENVIRONMENT_SOUND_PATHS: dict[str, str] = {
    "doorOpen": os.path.join("audio", "Audio", "doorOpen_1.ogg"),
    "doorClose": os.path.join("audio", "Audio", "doorClose_1.ogg"),
    "creak": os.path.join("audio", "Audio", "creak1.ogg"),
    "metalPot": os.path.join("audio", "Audio", "metalPot1.ogg"),
    "chop": os.path.join("audio", "Audio", "chop.ogg"),
}

_ENV_AUDIO_CACHE: dict[str, Any] = {}


def load_env_sound_cache(loader_func: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """Step 17: Load and cache environmental sounds."""
    global _ENV_AUDIO_CACHE
    _ENV_AUDIO_CACHE.clear()
    for key, path in ENVIRONMENT_SOUND_PATHS.items():
        if loader_func:
            try:
                _ENV_AUDIO_CACHE[key] = loader_func(path)
            except Exception as e:
                logger.warning("Failed to load env sound %s: %s", key, e)
                _ENV_AUDIO_CACHE[key] = path
        else:
            _ENV_AUDIO_CACHE[key] = path
    return _ENV_AUDIO_CACHE


def play_positional_sound(
    sound_name: str,
    source_x: float,
    source_y: float,
    listener_x: float = 0.0,
    listener_y: float = 0.0,
    max_distance: float = 15.0,
    base_volume: float = 1.0,
    backend_spatial_func: Callable[[Any, float, float], None] | None = None,
) -> dict[str, Any]:
    """Steps 18-22: Calculate distance, volume attenuation, stereo pan, and play sound."""
    global _ENV_AUDIO_CACHE
    if not _ENV_AUDIO_CACHE:
        load_env_sound_cache()

    sound_obj = _ENV_AUDIO_CACHE.get(sound_name, ENVIRONMENT_SOUND_PATHS.get(sound_name))

    # Step 19: Euclidean distance
    dx = source_x - listener_x
    dy = source_y - listener_y
    distance = math.hypot(dx, dy)

    # Step 20: Attenuation calculation
    if distance >= max_distance:
        volume = 0.0
    else:
        volume = max(0.0, base_volume * (1.0 - (distance / max_distance)))

    # Step 21: Stereo pan calculation (-1.0 left to +1.0 right)
    pan = 0.0
    if distance > 0:
        pan = max(-1.0, min(1.0, dx / max(1.0, max_distance * 0.5)))

    # Step 22: Apply volume & pan to playback
    if backend_spatial_func and sound_obj and volume > 0:
        try:
            backend_spatial_func(sound_obj, volume, pan)
        except Exception as e:
            logger.debug("Positional playback error: %s", e)

    return {
        "sound": sound_name,
        "distance": distance,
        "volume": volume,
        "pan": pan,
    }
