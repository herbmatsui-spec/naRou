from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime
from typing import Any


class NaRouError(Exception):
    """Base exception class for all naRou errors."""

    def __init__(self, message: str = "", context: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()

    def log_to_file(self, log_dir: str = "logs") -> str:
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = os.path.join(log_dir, f"error_log_{ts}.txt")
        with open(fn, "w", encoding="utf-8") as f:
            f.write(f"=== Error: {self.__class__.__name__} ===\n{self.message}\n")
            exc = sys.exc_info()[1]
            if exc:
                traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
            else:
                traceback.print_stack(file=f)
        return fn


class GameLogicError(NaRouError):
    """Game logic related errors."""


class SaveSystemError(NaRouError):
    """Save/load system errors."""


class SaveDataCorruptedError(SaveSystemError):
    """Save data is corrupted."""


class ConfigError(NaRouError):
    """Configuration errors."""


class NetworkError(NaRouError):
    """Network related errors."""


class ResourceLoadError(NaRouError):
    """Resource loading errors."""


class DataParseError(NaRouError):
    """Data parsing errors."""


class AIBehaviorError(NaRouError):
    """AI behavior errors."""


class RenderingError(NaRouError):
    """Rendering errors."""


class SystemInitError(NaRouError):
    """System initialization errors."""


class AudioError(NaRouError):
    """Audio system errors."""


class UIError(NaRouError):
    """UI system errors."""


class QuestError(NaRouError):
    """Quest system errors."""


class CombatError(NaRouError):
    """Combat system errors."""


class ValidationError(NaRouError):
    """Data validation errors."""


# Backwards compatibility aliases
ElonaError = NaRouError
GameLogicError = GameLogicError
SaveSystemError = SaveSystemError
SaveDataCorruptedError = SaveDataCorruptedError
ConfigError = ConfigError
NetworkError = NetworkError
ResourceLoadError = ResourceLoadError
DataParseError = DataParseError
AIBehaviorError = AIBehaviorError
RenderingError = RenderingError
SystemInitError = SystemInitError


def is_narou_error(exc: BaseException) -> bool:
    """Check if an exception is a NaRouError."""
    return isinstance(exc, NaRouError)
