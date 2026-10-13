from __future__ import annotations

"""Simple feature flag system.
Stores flags in memory; can be extended to load from config or env.
"""

_feature_flags: dict[str, bool] = {
    "ENABLE_TINY_ROGUE_GFX": True,
    "ENABLE_AUDIO_PACK": False,  # Enable real OGG audio playback
    "ENABLE_TEXT_MODE": False,  # GPU/SDL なしでも遊べるテキストモード
    "ENABLE_HUSK_PUPPET_HACKING": False,  # 傀儡ハッキングシステム（Husk使役）
}


def set_flag(name: str, enabled: bool) -> None:
    """Set a feature flag."""
    _feature_flags[name] = enabled


def is_enabled(name: str) -> bool:
    """Return True if flag is enabled, False otherwise."""
    return _feature_flags.get(name, False)


def get_text_mode_enabled() -> bool:
    """Step 11: テキストモードが有効かをフラグまたは config から判定。"""
    if _feature_flags.get("ENABLE_TEXT_MODE", False):
        return True
    try:
        from config import get_config

        if get_config("accessibility.text_mode") is True:
            return True
    except (ImportError, KeyError):
        pass
    return False


def get_husk_enabled() -> bool:
    """Step 3: 傀儡ハッキングが有効かをフラグまたは config から判定。"""
    if _feature_flags.get("ENABLE_HUSK_PUPPET_HACKING", False):
        return True
    try:
        from narou.config import get_config

        if get_config("husk.enabled") is True:
            return True
    except (ImportError, KeyError):
        pass
    return False


def set_text_mode_enabled(enabled: bool) -> None:
    """Step 11: テキストモードを有効/無効にする。"""
    _feature_flags["ENABLE_TEXT_MODE"] = bool(enabled)
