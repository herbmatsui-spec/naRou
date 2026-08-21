from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class HDRTarget:
    """HDR render target with ping-pong buffers for bloom."""

    width: int
    height: int
    color_format: str = "RG16F"  # 16-bit float per channel
    depth_format: str = "DEPTH24_STENCIL8"

    # Ping-pong buffers for bloom
    color_a: np.ndarray | None = None
    color_b: np.ndarray | None = None
    depth: np.ndarray | None = None

    # Current read/write buffer
    read_buffer: int = 0  # 0 = A, 1 = B

    def __post_init__(self) -> None:
        self.resize(self.width, self.height)

    def resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

        # RG16F = 2 channels, 16-bit float
        self.color_a = np.zeros((height, width, 2), dtype=np.float16)
        self.color_b = np.zeros((height, width, 2), dtype=np.float16)
        self.depth = np.full((height, width), 1.0, dtype=np.float32)
        self.read_buffer = 0

    def get_read_texture(self) -> np.ndarray:
        tex = self.color_a if self.read_buffer == 0 else self.color_b
        assert tex is not None
        return tex

    def get_write_texture(self) -> np.ndarray:
        tex = self.color_b if self.read_buffer == 0 else self.color_a
        assert tex is not None
        return tex

    def swap_buffers(self) -> None:
        self.read_buffer = 1 - self.read_buffer

    def clear(
        self, color: tuple[float, float] = (0.0, 0.0), depth: float = 1.0
    ) -> None:
        write_tex = self.get_write_texture()
        write_tex[:, :] = color
        depth_tex = self.get_depth_texture()
        depth_tex[:, :] = depth

    def get_depth_texture(self) -> np.ndarray:
        assert self.depth is not None
        return self.depth


class HDRCompositor:
    """HDR composition pipeline: Scene → Bloom → Tonemap → Output."""

    def __init__(self, width: int, height: int):
        self.hdr_target = HDRTarget(width, height)
        self.bloom_enabled = True
        self.bloom_threshold = 1.0
        self.bloom_intensity = 1.0
        self.exposure = 1.0
        self.gamma = 2.2

        # Bloom parameters
        self.bloom_radius = 8
        self.bloom_iterations = 5

        # Tonemap parameters
        self.tonemap_mode = "aces"  # "aces", "reinhard", "filmic"
        self.color_space = "srgb"  # "srgb", "p3", "rec2020"

    def begin_frame(self) -> None:
        self.hdr_target.clear()

    def render_scene_to_hdr(self, scene_renderer: Any) -> None:
        """Render scene to HDR target. Implement in renderer-specific code."""

    def apply_bloom(self) -> None:
        """Apply Kawase dual-filter bloom."""
        if not self.bloom_enabled:
            return

        # Extract bright pixels
        bright = self._extract_bright_pixels()

        # Downsample pyramid
        pyramid = self._downsample_pyramid(bright)

        # Upsample with blur (Kawase)
        bloom = self._upsample_kawase(pyramid)

        # Composite bloom back to HDR
        self._composite_bloom(bloom)

    def _extract_bright_pixels(self) -> np.ndarray:
        """Extract pixels above threshold."""
        hdr = self.hdr_target.get_read_texture()
        # Luminance = 0.2126*R + 0.7152*G + 0.0722*B (approximate from RG)
        # For RG16F, we approximate luminance from R+G
        luminance = hdr[:, :, 0] + hdr[:, :, 1]
        mask = luminance > self.bloom_threshold
        bright = np.zeros_like(hdr)
        bright[mask] = hdr[mask] * self.bloom_intensity
        return bright  # type: ignore[no-any-return]

    def _downsample_pyramid(self, bright: np.ndarray) -> list[np.ndarray]:
        """Create mip pyramid for bloom."""
        pyramid = [bright]
        current = bright

        for i in range(self.bloom_iterations):
            h, w = current.shape[:2]
            if h <= 4 or w <= 4:
                break

            # Simple box downsample
            down_h, down_w = max(h // 2, 1), max(w // 2, 1)
            downsampled = np.zeros((down_h, down_w, 2), dtype=np.float16)

            for y in range(down_h):
                for x in range(down_w):
                    y0, y1 = y * 2, min(y * 2 + 2, h)
                    x0, x1 = x * 2, min(x * 2 + 2, w)
                    downsampled[y, x] = np.mean(current[y0:y1, x0:x1], axis=(0, 1))

            pyramid.append(downsampled)
            current = downsampled

        return pyramid

    def _upsample_kawase(self, pyramid: list[np.ndarray]) -> np.ndarray:
        """Kawase blur upsample."""
        current = pyramid[-1]

        for i in range(len(pyramid) - 2, -1, -1):
            target = pyramid[i]
            h, w = target.shape[:2]

            # Upsample current to target size
            upsampled = self._upsample_bilinear(current, h, w)

            # Kawase blur: weighted average with offset samples
            blurred = self._kawase_blur(upsampled, radius=self.bloom_radius)

            # Add to pyramid level
            current = blurred + target

        return current

    def _upsample_bilinear(
        self, src: np.ndarray, target_h: int, target_w: int
    ) -> np.ndarray:
        """Bilinear upsample."""
        src_h, src_w = src.shape[:2]
        result: np.ndarray = np.zeros((target_h, target_w, 2), dtype=np.float16)

        for y in range(target_h):
            for x in range(target_w):
                src_x = (x + 0.5) * src_w / target_w - 0.5
                src_y = (y + 0.5) * src_h / target_h - 0.5

                x0, y0 = int(src_x), int(src_y)
                x1, y1 = min(x0 + 1, src_w - 1), min(y0 + 1, src_h - 1)

                fx, fy = src_x - x0, src_y - y0

                c00 = src[y0, x0]
                c10 = src[y0, x1]
                c01 = src[y1, x0]
                c11 = src[y1, x1]

                result[y, x] = (
                    c00 * (1 - fx) * (1 - fy)
                    + c10 * fx * (1 - fy)
                    + c01 * (1 - fx) * fy
                    + c11 * fx * fy
                )

        return result

    def _kawase_blur(self, src: np.ndarray, radius: int) -> np.ndarray:
        """Kawase blur filter."""
        h, w = src.shape[:2]
        result = np.zeros_like(src)

        # Kawase weights and offsets
        weights = [0.227027, 0.194595, 0.121622, 0.054054, 0.016216]
        offsets = [0.0, 1.384615, 3.230769, 5.076923, 7.0]

        for y in range(h):
            for x in range(w):
                acc: np.ndarray = np.zeros(2, dtype=np.float16)
                total_w = 0.0

                for w_i, offset in zip(weights, offsets):
                    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                        sx = int(x + dx * offset)
                        sy = int(y + dy * offset)
                        if 0 <= sx < w and 0 <= sy < h:
                            acc += src[sy, sx] * w_i
                            total_w += w_i

                if total_w > 0:
                    result[y, x] = acc / total_w
                else:
                    result[y, x] = src[y, x]

        return result  # type: ignore[no-any-return]

    def _composite_bloom(self, bloom: np.ndarray) -> None:
        """Add bloom to HDR buffer."""
        hdr = self.hdr_target.get_write_texture()
        hdr += bloom

    def apply_tonemap(self, hdr: np.ndarray) -> np.ndarray:
        """Apply tonemapping to HDR buffer."""
        if self.tonemap_mode == "aces":
            return self._aces_tonemap(hdr)
        elif self.tonemap_mode == "reinhard":
            return self._reinhard_tonemap(hdr)
        elif self.tonemap_mode == "filmic":
            return self._filmic_tonemap(hdr)
        return hdr

    def _aces_tonemap(self, hdr: np.ndarray) -> np.ndarray:
        """ACES RRT + ODT (sRGB)."""
        # ACES input transform (approximate)
        a = 2.51
        b = 0.03
        c = 2.43
        d = 0.59
        e = 0.14

        # Exposure
        hdr = hdr * self.exposure

        # RRT
        num = hdr * (a * hdr + b)
        den = hdr * (c * hdr + d) + e
        tonemapped = num / (den + 1e-6)

        # ODT (sRGB gamma)
        tonemapped = np.clip(tonemapped, 0, 1)
        tonemapped = np.power(tonemapped, 1.0 / self.gamma)

        return tonemapped  # type: ignore[no-any-return]

    def _reinhard_tonemap(self, hdr: np.ndarray) -> np.ndarray:
        """Reinhard tonemapping."""
        hdr = hdr * self.exposure
        tonemapped = hdr / (1.0 + hdr)
        tonemapped = np.power(tonemapped, 1.0 / self.gamma)
        return tonemapped  # type: ignore[no-any-return]

    def _filmic_tonemap(self, hdr: np.ndarray) -> np.ndarray:
        """Filmic tonemapping (Unreal-style)."""
        hdr = hdr * self.exposure

        # Filmic curve parameters
        A = 0.22
        B = 0.30
        C = 0.10
        D = 0.20
        E = 0.01
        F = 0.30
        W = 11.2

        x = np.maximum(hdr, 0)
        num = x * (A * x + C * B) + D * E
        den = x * (A * x + B) + D * F
        tonemapped = num / (den + 1e-6) - E / F

        # White point normalization
        white = W * (A * W + C * B) + D * E
        white_den = W * (A * W + B) + D * F
        white_scale = white / (white_den + 1e-6) - E / F
        tonemapped = tonemapped / white_scale

        tonemapped = np.clip(tonemapped, 0, 1)
        tonemapped = np.power(tonemapped, 1.0 / self.gamma)

        return tonemapped  # type: ignore[no-any-return]

    def end_frame(self) -> np.ndarray:
        """Complete frame and return LDR output."""
        hdr = self.hdr_target.get_read_texture()

        if self.bloom_enabled:
            self.apply_bloom()
            hdr = self.hdr_target.get_read_texture()

        ldr = self.apply_tonemap(hdr)
        return ldr
