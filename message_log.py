"""
Message Log Module
Re-exports MessageLog from core_framework for backward compatibility.
"""
from core_framework import MessageLog, LogMessage

__all__ = ['MessageLog', 'LogMessage']