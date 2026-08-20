"""CanvasManager – singleton wrapper for a 2D canvas context.
Provides a single `ctx` attribute to avoid multiple `getContext('2d')` calls.
Used by any part of the engine that needs direct draw calls.
"""

from __future__ import annotations


class CanvasManager:
    _instance: CanvasManager = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.canvas = (
            None  # Placeholder for actual canvas object (e.g., via web integration)
        )
        self.ctx = None
        self._initialized = True

    def set_canvas(self, canvas) -> None:
        """Assign a canvas object and obtain its 2D context."""
        self.canvas = canvas
        # In a real environment, this would be `canvas.getContext('2d')`
        # Here we just store a placeholder.
        self.ctx = getattr(canvas, "getContext", lambda _: None)("2d")

    def get_context(self):
        """Return the stored 2D context, creating it lazily if needed."""
        if self.ctx is None and self.canvas is not None:
            self.set_canvas(self.canvas)
        return self.ctx
