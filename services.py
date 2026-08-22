from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ConfigService:
    """Service wrapper for ConfigManager with simplified API."""

    def __init__(self, config_manager: ConfigManager | None = None):
        self._config_manager = config_manager or ConfigManager()
        logger.debug("ConfigService initialized")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notation key (e.g., 'game.difficulty')."""
        return self._config_manager.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value by dot-notation key."""
        self._config_manager.set(key, value)

    def get_section(self, section: str) -> dict[str, Any]:
        """Get an entire configuration section."""
        return self._config_manager.get_section(section)

    def load(self, config_path: str | Path) -> None:
        """Load configuration from file."""
        self._config_manager.load(config_path)

    def save(self, config_path: str | Path) -> None:
        """Save configuration to file."""
        self._config_manager.save(config_path)

    def reload(self) -> None:
        """Reload configuration from default paths."""
        self._config_manager.reload()

    @property
    def raw(self) -> dict[str, Any]:
        """Get raw configuration dictionary."""
        return self._config_manager.raw


from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SoundService:
    """Service wrapper for SoundManager with simplified API."""

    def __init__(self, sound_manager: Any | None = None):
        if sound_manager is not None:
            self._sound_manager = sound_manager
        else:
            from sound_manager import SoundManager

            self._sound_manager = SoundManager()
        logger.debug("SoundService initialized")

    def play_se(self, name: str, volume: float = 1.0) -> None:
        """Play a sound effect."""
        self._sound_manager.play_se(name, volume)

    def play_bgm(self, name: str, volume: float = 1.0, loop: bool = True) -> None:
        """Play background music."""
        self._sound_manager.play_bgm(name, volume, loop)

    def stop_bgm(self) -> None:
        """Stop background music."""
        self._sound_manager.stop_bgm()

    def set_volume(self, volume: float) -> None:
        """Set master volume (0.0 - 1.0)."""
        self._sound_manager.set_volume(volume)

    def set_se_volume(self, volume: float) -> None:
        """Set SE volume (0.0 - 1.0)."""
        self._sound_manager.set_se_volume(volume)

    def set_bgm_volume(self, volume: float) -> None:
        """Set BGM volume (0.0 - 1.0)."""
        self._sound_manager.set_bgm_volume(volume)

    def preload(self, name: str) -> None:
        """Preload a sound."""
        self._sound_manager.preload(name)