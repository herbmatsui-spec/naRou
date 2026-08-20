from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from core.auto_exposure import AutoExposure
from core.hdr import HDRCompositor
from core.renderer_base import RendererBase


@dataclass
class RenderPass:
    name: str
    enabled: bool = True
    input_texture: str = ""
    output_texture: str = ""


class Compositor:
    """HDR render pipeline: Scene -> Bloom -> Tonemap -> Output."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.hdr_compositor = HDRCompositor(width, height)
        self.auto_exposure = AutoExposure()

        # Passes in order
        self.passes: list[RenderPass] = [
            RenderPass("scene", True, "", "hdr_scene"),
            RenderPass("bright_extract", True, "hdr_scene", "bloom_bright"),
            RenderPass("downsample_1", True, "bloom_bright", "bloom_down_1"),
            RenderPass("downsample_2", True, "bloom_down_1", "bloom_down_2"),
            RenderPass("downsample_3", True, "bloom_down_2", "bloom_down_3"),
            RenderPass("downsample_4", True, "bloom_down_3", "bloom_down_4"),
            RenderPass("downsample_5", True, "bloom_down_4", "bloom_down_5"),
            RenderPass("upsample_5", True, "bloom_down_5", "bloom_up_5"),
            RenderPass("upsample_4", True, "bloom_up_5", "bloom_up_4"),
            RenderPass("upsample_3", True, "bloom_up_4", "bloom_up_3"),
            RenderPass("upsample_2", True, "bloom_up_3", "bloom_up_2"),
            RenderPass("upsample_1", True, "bloom_up_2", "bloom_up_1"),
            RenderPass("bloom_composite", True, "hdr_scene", "hdr_bloomed"),
            RenderPass("tonemap", True, "hdr_bloomed", "ldr_output"),
        ]

        # Debug visualization
        self.debug_pass = -1  # -1 = off, otherwise index of pass to visualize
        self.debug_mode = False

    def begin_frame(self) -> None:
        self.hdr_compositor.begin_frame()

    def render_scene(self, renderer: RendererBase, scene_data: dict[str, Any]) -> None:
        """Render main scene to HDR. Delegate to game-specific renderer."""
        # This is called by the game's render system

    def execute_passes(self, renderer: RendererBase) -> np.ndarray:
        """Execute all render passes and return final LDR frame."""
        # In a real implementation, this would use GPU compute shaders
        # For now, use CPU fallback
        hdr = self.hdr_compositor.hdr_target.get_read_texture()

        if self.hdr_compositor.bloom_enabled:
            self.hdr_compositor.apply_bloom()
            hdr = self.hdr_compositor.hdr_target.get_read_texture()

        # Auto exposure
        exposure = self.auto_exposure.update(hdr)
        self.hdr_compositor.exposure = exposure

        # Tonemap
        ldr = self.hdr_compositor.apply_tonemap(hdr)

        return ldr

    def end_frame(self) -> np.ndarray:
        """Complete frame and return LDR output."""
        return self.execute_passes(None)

    def set_debug_pass(self, pass_index: int) -> None:
        self.debug_pass = pass_index
        self.debug_mode = pass_index >= 0

    def get_pass_names(self) -> list[str]:
        return [p.name for p in self.passes]

    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.hdr_compositor.hdr_target.resize(width, height)

    def set_bloom_params(
        self,
        threshold: float = 1.0,
        intensity: float = 1.0,
        radius: int = 8,
        iterations: int = 5,
    ) -> None:
        self.hdr_compositor.bloom_threshold = threshold
        self.hdr_compositor.bloom_intensity = intensity
        self.hdr_compositor.bloom_radius = radius
        self.hdr_compositor.bloom_iterations = iterations

    def set_tonemap_mode(self, mode: str) -> None:
        if mode in ("aces", "reinhard", "filmic"):
            self.hdr_compositor.tonemap_mode = mode

    def set_exposure(self, exposure: float) -> None:
        self.hdr_compositor.exposure = exposure
        self.auto_exposure.current_exposure = exposure


class PseudoHDR:
    """Pseudo-HDR fallback for tcod using 10-bit LUT."""

    def __init__(self):
        self.lut_size = 1024
        self.lut: np.ndarray | None = None
        self.exposure = 1.0
        self.gamma = 2.2
        self.bloom_enabled = True
        self.bloom_radius = 2
        self._generate_lut()

    def _generate_lut(self) -> None:
        """Generate 10-bit tonemap LUT."""
        self.lut = np.zeros(self.lut_size, dtype=np.uint32)

        for i in range(self.lut_size):
            # Input: 0.0 to 10.0 (HDR range mapped to 10-bit)
            hdr = (i / (self.lut_size - 1)) * 10.0

            # Simple filmic tonemap
            A, B, C, D, E, F = 0.22, 0.30, 0.10, 0.20, 0.01, 0.30
            W = 11.2

            x = max(hdr, 0)
            num = x * (A * x + C * B) + D * E
            den = x * (A * x + B) + D * F
            white_num = W * (A * W + C * B) + D * E
            white_den = W * (A * W + B) + D * F
            white_scale = white_num / white_den - E / F

            tonemapped = (num / (den + 1e-6) - E / F) / white_scale
            tonemapped = max(0, min(1, tonemapped))
            tonemapped = tonemapped ** (1.0 / self.gamma)

            # Pack as RGB24
            val = int(tonemapped * 255)
            self.lut[i] = (val << 16) | (val << 8) | val

    def apply(self, console, framebuffer: np.ndarray) -> None:
        """Apply pseudo-HDR to tcod console framebuffer."""
        h, w = framebuffer.shape[:2]

        # Simple bloom approximation: 3x3 gaussian x2
        if self.bloom_enabled:
            framebuffer = self._gaussian_blur(framebuffer, 3)
            framebuffer = self._gaussian_blur(framebuffer, 3)

        # Apply LUT tonemap
        # framebuffer is RGB float, convert using LUT
        for y in range(h):
            for x in range(w):
                r, g, b = framebuffer[y, x]
                # Approximate luminance
                lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
                idx = int(np.clip(lum * self.lut_size, 0, self.lut_size - 1))
                color = self.lut[idx]

                # Apply to console (simplified)
                console.rgb[y, x]["fg"] = (
                    color >> 16 & 0xFF,
                    color >> 8 & 0xFF,
                    color & 0xFF,
                )

    def _gaussian_blur(self, img: np.ndarray, kernel_size: int) -> np.ndarray:
        """Simple separable Gaussian blur."""
        from scipy.ndimage import gaussian_filter

        result = np.zeros_like(img)
        for c in range(3):
            result[:, :, c] = gaussian_filter(img[:, :, c], sigma=kernel_size / 3)
        return result

    def set_exposure(self, exposure: float) -> None:
        self.exposure = exposure
        self._generate_lut()

    def set_gamma(self, gamma: float) -> None:
        self.gamma = gamma
        self._generate_lut()


def apply_pseudo_hdr(
    console,
    framebuffer: np.ndarray,
    exposure: float = 1.0,
    gamma: float = 2.2,
    bloom: bool = True,
) -> None:
    """Convenience function to apply pseudo-HDR to tcod console."""
    phdr = PseudoHDR()
    phdr.exposure = exposure
    phdr.gamma = gamma
    phdr.bloom_enabled = bloom
    phdr.apply(console, framebuffer)
