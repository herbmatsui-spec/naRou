from __future__ import annotations

"""Pytest configuration: ensure project root is importable for test suites."""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
