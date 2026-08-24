"""
Shim module for UI FX systems.
Provides lazy re‑export of the actual implementation in ``naRou.ui.ui_fx_systems``
to break the circular import caused by the original ``import *`` pattern.
"""

import importlib

_real_module = None


def __getattr__(name):
    global _real_module
    if _real_module is None:
        _real_module = importlib.import_module('naRou.ui.ui_fx_systems')
    return getattr(_real_module, name)


def __dir__():
    if _real_module is None:
        _real_module = importlib.import_module('naRou.ui.ui_fx_systems')
    return dir(_real_module)