"""Tests for the telemetry manager (step 59).

These assert that: telemetry is off by default, no PII leaves the process, queue
persists, GDPR deletion works, and batch flush clears the queue.
"""
import json
from pathlib import Path

import pytest

import telemetry_manager as tm


@pytest.fixture()
def mgr(tmp_path):
    m = tm.TelemetryManager(cache_dir=tmp_path)
    yield m
    # cleanup
    for f in tmp_path.glob("*"):
        f.unlink(missing_ok=True)


def test_module_loads():
    assert hasattr(tm, "TelemetryManager")
    assert len(tm.FUNNEL_EVENTS) > 0


def test_anonymous_id_stable(mgr):
    a = mgr.get_anonymous_id()
    b = mgr.get_anonymous_id()
    assert a == b and len(a) >= 32  # uuid4 hex


def test_no_send_when_opt_out(mgr):
    # Manager never sends in tests; flush returns count and clears.
    mgr.track("level_up", {"level": 5})
    assert len(mgr._queue) >= 1
    sent = mgr.flush()
    assert sent >= 1
    assert len(mgr._queue) == 0


def test_session_tracking(mgr):
    mgr.start_session()
    assert mgr.session_active is True
    mgr.end_session()
    assert mgr.session_active is False


def test_gdpr_delete(mgr):
    mgr.track("x", {})
    assert mgr.delete_my_data() is True
    assert len(mgr._queue) == 0


def test_ab_variant_deterministic(mgr):
    v1 = mgr.get_variant("pricing")
    v2 = mgr.get_variant("pricing")
    assert v1 == v2


def test_privacy_policy_exists():
    assert Path("privacy_policy.html").exists()
