"""Engine package – re-exports the Engine class for backward compatibility."""

import atexit
import logging

from .engine import Engine


def _shutdown_hook():
    try:
        logging.getLogger(__name__).info("Engine shutdown hook executed")
        logging.shutdown()
    except Exception:  # noqa: BLE001
        pass


atexit.register(_shutdown_hook)

__all__ = ["Engine"]
