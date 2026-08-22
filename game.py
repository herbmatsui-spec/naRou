"""Backward‑compatibility wrapper for the Engine class.

The real implementation now lives in `naRou.engine.engine.Engine`.
All existing imports (`from naRou.game import Engine`) continue to
work without modification."""
from naRou.engine import Engine  # re-export
