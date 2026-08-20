from __future__ import annotations

import numpy as np
import tcod

from core.compositor import PseudoHDR
from core.hdr import AutoExposure


class TCODHDRFallback:
    """Pseudo-HDR implementation for tcod backend."""

    def __init__(self, console_width: int, console_height: int):
        self.console_width = console_width
        self.console_height = console_height

        # Internal HDR framebuffer (float32)
        self.hdr_buffer = np.zeros((console_height, console_width, 3), dtype=np.float32)

        # Pseudo-HDR processor
        self.pseudo_hdr = PseudoHDR()
        self.auto_exposure = AutoExposure()

        # Settings
        self.enabled = True
        self.exposure = 1.0
        self.gamma = 2.2
        self.bloom_enabled = True
        self.bloom_intensity = 0.5

    def begin_frame(self) -> None:
        self.hdr_buffer.fill(0.0)

    def end_frame(self, console: tcod.console.Console) -> None:
        if not self.enabled:
            return

        # Auto exposure
        self.exposure = self.auto_exposure.update(self.hdr_buffer)
        self.pseudo_hdr.exposure = self.exposure

        # Apply pseudo-HDR (tonemap + bloom) to console
        self.pseudo_hdr.gamma = self.gamma
        self.pseudo_hdr.bloom_enabled = self.bloom_enabled
        self.pseudo_hdr.apply(console, self.hdr_buffer)

    def add_hdr_color(
        self, x: int, y: int, color: tuple, intensity: float = 1.0
    ) -> None:
        """Add HDR color to framebuffer at position."""
        if 0 <= x < self.console_width and 0 <= y < self.console_height:
            r, g, b = [c / 255.0 for c in color[:3]]
            self.hdr_buffer[y, x] += np.array([r, g, b], dtype=np.float32) * intensity

    def add_hdr_rect(
        self, x: int, y: int, w: int, h: int, color: tuple, intensity: float = 1.0
    ) -> None:
        """Add HDR color to rectangle."""
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.console_width, x + w)
        y1 = min(self.console_height, y + h)

        if x0 < x1 and y0 < y1:
            r, g, b = [c / 255.0 for c in color[:3]]
            self.hdr_buffer[y0:y1, x0:x1] += (
                np.array([r, g, b], dtype=np.float32) * intensity
            )

    def set_exposure(self, exposure: float) -> None:
        self.exposure = exposure
        self.auto_exposure.current_exposure = exposure

    def set_gamma(self, gamma: float) -> None:
        self.gamma = gamma

    def enable_bloom(self, enabled: bool) -> None:
        self.bloom_enabled = enabled

    def resize(self, width: int, height: int) -> None:
        self.console_width = width
        self.console_height = height
        self.hdr_buffer = np.zeros((height, width, 3), dtype=np.float32)
        self.pseudo_hdr = PseudoHDR()
        self.auto_exposure = AutoExposure()


def apply_pseudo_hdr_tcod(
    console: tcod.console.Console,
    hdr_buffer: np.ndarray,
    exposure: float = 1.0,
    gamma: float = 2.2,
    bloom: bool = True,
) -> None:
    """Apply pseudo-HDR to tcod console from HDR buffer."""
    pseudo_hdr = PseudoHDR()
    pseudo_hdr.exposure = exposure
    pseudo_hdr.gamma = gamma
    pseudo_hdr.bloom_enabled = bloom
    pseudo_hdr.apply(console, hdr_buffer)
