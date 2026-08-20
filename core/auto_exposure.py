from __future__ import annotations

import numpy as np


class AutoExposure:
    """Automatic exposure control using luminance histogram."""

    def __init__(
        self,
        min_exposure: float = 0.1,
        max_exposure: float = 10.0,
        target_luminance: float = 0.5,
        adaptation_speed: float = 0.5,
    ):
        self.min_exposure = min_exposure
        self.max_exposure = max_exposure
        self.target_luminance = target_luminance
        self.adaptation_speed = adaptation_speed
        self.current_exposure = 1.0

    def update(self, hdr: np.ndarray) -> float:
        """Update exposure based on scene luminance."""
        if hdr.size == 0:
            return self.current_exposure

        # Calculate luminance from RGB
        if hdr.ndim == 3 and hdr.shape[2] >= 3:
            # Standard luminance weights
            luminance = (
                0.2126 * hdr[:, :, 0] + 0.7152 * hdr[:, :, 1] + 0.0722 * hdr[:, :, 2]
            )
        elif hdr.ndim == 3 and hdr.shape[2] == 2:
            # RG16F approximate
            luminance = hdr[:, :, 0] + hdr[:, :, 1]
        else:
            luminance = hdr

        # Avoid zero luminance
        luminance = np.maximum(luminance, 1e-6)

        # Log average luminance (avoids bright outliers dominating)
        log_lum = np.log(luminance)
        avg_log_lum = np.mean(log_lum)
        avg_luminance = np.exp(avg_log_lum)

        # Target exposure
        if avg_luminance > 1e-6:
            target_exposure = self.target_luminance / avg_luminance
        else:
            target_exposure = 1.0

        # Clamp to range
        target_exposure = np.clip(target_exposure, self.min_exposure, self.max_exposure)

        # Smooth adaptation (exponential moving average)
        self.current_exposure += (
            target_exposure - self.current_exposure
        ) * self.adaptation_speed

        return self.current_exposure

    def set_target_luminance(self, target: float) -> None:
        self.target_luminance = target

    def set_adaptation_speed(self, speed: float) -> None:
        self.adaptation_speed = np.clip(speed, 0.0, 1.0)

    def set_exposure_range(self, min_exp: float, max_exp: float) -> None:
        self.min_exposure = min_exp
        self.max_exposure = max_exp
        self.current_exposure = np.clip(self.current_exposure, min_exp, max_exp)

    def get_exposure(self) -> float:
        return self.current_exposure

    def reset(self) -> None:
        self.current_exposure = 1.0


class HistogramAutoExposure(AutoExposure):
    """Advanced auto-exposure using luminance histogram."""

    def __init__(
        self,
        bins: int = 256,
        min_exposure: float = 0.1,
        max_exposure: float = 10.0,
        target_percentile: float = 0.95,
        adaptation_speed: float = 0.5,
    ):
        super().__init__(min_exposure, max_exposure, 0.5, adaptation_speed)
        self.bins = bins
        self.target_percentile = target_percentile
        self.histogram_range = (0.0, 10.0)

    def update(self, hdr: np.ndarray) -> float:
        if hdr.size == 0:
            return self.current_exposure

        # Calculate luminance
        if hdr.ndim == 3 and hdr.shape[2] >= 3:
            luminance = (
                0.2126 * hdr[:, :, 0] + 0.7152 * hdr[:, :, 1] + 0.0722 * hdr[:, :, 2]
            )
        else:
            luminance = hdr.flatten()

        # Build histogram
        hist, bin_edges = np.histogram(
            luminance, bins=self.bins, range=self.histogram_range
        )

        # Find target percentile
        cumsum = np.cumsum(hist)
        total = cumsum[-1]
        if total == 0:
            return self.current_exposure

        target_count = total * self.target_percentile
        idx = np.searchsorted(cumsum, target_count)

        if idx >= len(bin_edges) - 1:
            target_luminance = bin_edges[-1]
        else:
            target_luminance = bin_edges[idx]

        # Calculate exposure
        if target_luminance > 1e-6:
            target_exposure = 1.0 / target_luminance
        else:
            target_exposure = 1.0

        target_exposure = np.clip(target_exposure, self.min_exposure, self.max_exposure)

        # Smooth adaptation
        self.current_exposure += (
            target_exposure - self.current_exposure
        ) * self.adaptation_speed

        return self.current_exposure
