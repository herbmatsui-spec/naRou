#!/usr/bin/env python3
"""Runtime integrity checker (Step 63-65).

Provides:
  * Anti-debug detection (Step 64)
  * Memory integrity verification (Step 65)
  * Critical value anomaly detection (Step 69)
  * Violation logging & reporting (Step 70)
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Critical game state keys that should be monitored for tampering
CRITICAL_KEYS = {
    "player": [
        "gold",
        "level",
        "exp",
        "karma_law_chaos",
        "karma_good_evil",
        "hp",
        "mp",
    ],
    "survival": ["hunger", "thirst", "sleepiness"],
}


class IntegrityChecker:
    """Runtime integrity & anti-tamper monitor."""

    def __init__(self, engine: Any | None = None):
        self.engine = engine
        self._baselines: dict[str, Any] = {}
        self._violation_count = 0
        self._last_check = 0.0
        self._check_interval = 30.0  # seconds

    # ---- Step 64: Anti-debug detection ----
    def is_debugger_attached(self) -> bool:
        """Detect common debuggers (Windows/Linux/macOS)."""
        # Windows: IsDebuggerPresent
        if sys.platform == "win32":
            try:
                import ctypes

                return bool(ctypes.windll.kernel32.IsDebuggerPresent())
            except Exception:
                pass
        # Linux: /proc/self/status TracerPid
        if sys.platform == "linux":
            try:
                with open("/proc/self/status") as f:
                    for line in f:
                        if line.startswith("TracerPid:"):
                            return int(line.split(":")[1].strip()) != 0
            except Exception:
                pass
        # macOS: ptrace attach check
        if sys.platform == "darwin":
            try:
                import ctypes

                libc = ctypes.CDLL("libc.dylib")
                if libc.ptrace(31, 0, 0, 0) == -1:  # PT_DENY_ATTACH
                    return True
            except Exception:
                pass
        # Generic: sys.gettrace() set
        return sys.gettrace() is not None

    # ---- Step 65: Memory integrity check ----
    def snapshot_critical_values(self, engine: Any) -> dict[str, Any]:
        """Record baseline values for critical game state."""
        snap = {}
        if not engine:
            return snap
        player = getattr(engine, "player", None)
        if player:
            for attr in CRITICAL_KEYS.get("player", []):
                val = getattr(player, attr, None)
                if val is not None:
                    snap[f"player.{attr}"] = val
        survival = getattr(engine, "survival", None)
        if survival:
            for attr in CRITICAL_KEYS.get("survival", []):
                val = getattr(survival, attr, None)
                if val is not None:
                    snap[f"survival.{attr}"] = val
        self._baselines = snap
        return snap

    def check_memory_integrity(self, engine: Any) -> bool:
        """Compare current critical values against baseline."""
        if not self._baselines:
            self.snapshot_critical_values(engine)
            return True
        current = self.snapshot_critical_values(engine)
        for key, baseline in self._baselines.items():
            current_val = current.get(key)
            if current_val is not None and current_val != baseline:
                # Allow small deltas for stats that change naturally (hp, mp, hunger)
                if key.endswith((".hp", ".mp", ".hunger", ".thirst", ".sleepiness")):
                    if isinstance(current_val, (int, float)) and isinstance(
                        baseline, (int, float)
                    ):
                        if abs(current_val - baseline) <= max(5, baseline * 0.1):
                            continue
                self._log_violation(
                    "memory_tamper",
                    f"Critical value changed: {key} baseline={baseline} current={current_val}",
                )
                return False
        return True

    # ---- Step 69: Anomaly detection (balance anomalies) ----
    def detect_anomaly(self, result: dict[str, Any]) -> bool:
        """Detect statistical anomalies in combat results (one-shot kills, etc.)."""
        # Example: damage > 3x max expected, or 100% crit rate over 50 attacks
        damage = result.get("damage", 0)
        max_expected = result.get("max_expected_damage", 0)
        if max_expected and damage > max_expected * 3:
            self._log_violation(
                "damage_anomaly", f"Damage {damage} exceeds 3x expected {max_expected}"
            )
            return True
        crit_rate = result.get("crit_rate", 0)
        attacks = result.get("attacks", 0)
        if attacks > 50 and crit_rate == 1.0:
            self._log_violation(
                "crit_anomaly", f"100% crit rate over {attacks} attacks"
            )
            return True
        return False

    # ---- Step 70: Violation logging ----
    def _log_violation(self, vtype: str, details: str) -> None:
        self._violation_count += 1
        entry = {
            "type": vtype,
            "details": details,
            "timestamp": time.time(),
            "count": self._violation_count,
        }
        logger.warning("Integrity violation [%s]: %s", vtype, details)
        # Also write to violation log file
        try:
            log_path = Path("integrity_violations.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{vtype}] {details}\n")
        except Exception:
            pass

    def get_violation_count(self) -> int:
        return self._violation_count

    # ---- Periodic check ----
    def periodic_check(self, engine: Any) -> bool:
        """Run all integrity checks; meant to be called every N seconds."""
        if time.time() - self._last_check < self._check_interval:
            return True
        self._last_check = time.time()
        ok = True
        if self.is_debugger_attached():
            self._log_violation("debugger", "Debugger attached detected")
            ok = False
        if not self.check_memory_integrity(engine):
            ok = False
        return ok


def get_integrity_checker(engine: Any | None = None) -> IntegrityChecker:
    """Factory returning an IntegrityChecker bound to engine."""
    return IntegrityChecker(engine)


if __name__ == "__main__":
    # Quick self-test
    checker = IntegrityChecker()
    print("Anti-debug:", checker.is_debugger_attached())
    print("IntegrityChecker initialized OK")
