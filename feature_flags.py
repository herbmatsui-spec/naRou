"""Simple feature flag system.
Stores flags in memory; can be extended to load from config or env.
"""

_feature_flags: dict[str, bool] = {
    "ENABLE_TINY_ROGUE_GFX": True,
    "ENABLE_AUDIO_PACK": False,  # Enable real OGG audio playback
}

def set_flag(name: str, enabled: bool) -> None:
    """Set a feature flag."""
    _feature_flags[name] = enabled

def is_enabled(name: str) -> bool:
    """Return True if flag is enabled, False otherwise."""
    return _feature_flags.get(name, False)
