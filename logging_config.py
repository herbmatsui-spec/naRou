from __future__ import annotations

# Basic logging configuration for naRou
import logging


def configure_logging(level: str = "INFO"):
    """Configure root logger.
    Args:
        level: Logging level name (e.g., "DEBUG", "INFO").
    """
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
