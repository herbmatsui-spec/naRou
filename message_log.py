"""
Message Log Module
Re-exports MessageLog from core_framework for backward compatibility.
"""
from __future__ import annotations

from core_framework import LogMessage, MessageLog

__all__ = ["LogMessage", "MessageLog"]
