from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

stubs_dir = os.path.join(ROOT, "stubs")
# Only fall back to stubs for packages that are not actually installed, so a
# real installation (e.g. PIL) always takes precedence over the stub version.
def _need_stub(modname: str) -> bool:
    try:
        __import__(modname)
        return False
    except Exception:
        return True


if _need_stub("PIL") or _need_stub("psutil") or _need_stub("pydantic"):
    if stubs_dir not in sys.path:
        sys.path.insert(0, stubs_dir)
