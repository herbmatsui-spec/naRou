"""
Message Log Module
Re-exports MessageLog from core_framework for backward compatibility.
"""

from core_framework import LogMessage, MessageLog

__all__ = ["MessageLog", "LogMessage"]
