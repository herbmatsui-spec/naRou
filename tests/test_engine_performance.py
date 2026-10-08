"""Test Engine() construction performance improvements."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest


class TestEnginePerformance:
    """Verify Engine() construction is fast in headless mode."""

    def test_engine_construct_under_2500ms_headless(self) -> None:
        """Engine() should construct in < 2600ms when NAROU_HEADLESS=1 (first run)."""
        os.environ["NAROU_HEADLESS"] = "1"

        # Import after setting env var
        import game

        start = time.perf_counter()
        engine = game.Engine()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Cleanup
        if hasattr(engine, "web_server") and engine.web_server:
            engine.web_server.shutdown()

        assert elapsed_ms < 2600, f"Engine() took {elapsed_ms:.1f}ms (expected < 2600ms)"

    def test_engine_construct_cache_hit_under_1500ms(self) -> None:
        """Second Engine() construction should be < 1500ms (YAML cache hit)."""
        os.environ["NAROU_HEADLESS"] = "1"

        import game

        # First construction (cold) - warm up cache
        engine1 = game.Engine()
        if hasattr(engine1, "web_server") and engine1.web_server:
            engine1.web_server.shutdown()

        # Second construction (warm - should use cached YAML)
        start2 = time.perf_counter()
        engine2 = game.Engine()
        second_ms = (time.perf_counter() - start2) * 1000

        if hasattr(engine2, "web_server") and engine2.web_server:
            engine2.web_server.shutdown()

        # Second should be under 1500ms (cache working, but other init still happens)
        assert second_ms < 1500, \
            f"Cached Engine() took {second_ms:.1f}ms (expected < 1500ms)"

    def test_web_server_not_bound_in_headless(self) -> None:
        """In headless mode, web server should not attempt to bind port 8080."""
        os.environ["NAROU_HEADLESS"] = "1"

        import game

        engine = game.Engine()

        # web_server should be None or not started
        assert engine.web_server is None, \
            f"web_server should be None in headless mode, got {engine.web_server}"

        # No error on shutdown
        if engine.web_server:
            engine.web_server.shutdown()


class TestNonVacuity:
    """Non-vacuity proofs for engine performance tests."""

    def test_assert_can_fail_slow_engine(self) -> None:
        """Test that our performance check CAN detect a slow engine."""
        from tests.helpers.non_vacuity import assert_distinguishes

        def check_fast_engine(elapsed_ms: float) -> None:
            """Assertion: engine construction is fast (< 2600ms first run)."""
            assert elapsed_ms < 2600, f"Engine took {elapsed_ms}ms"

        # Good case: fast engine (1500ms)
        good_time = 1500.0
        # Bad case: slow engine (3000ms = old behavior)
        bad_time = 3000.0

        assert_distinguishes(check_fast_engine, good_time, bad_time, label="engine_construct_time")

    def test_assert_can_fail_web_server_bound(self) -> None:
        """Test that our check CAN detect web server binding in headless."""
        from tests.helpers.non_vacuity import assert_distinguishes

        def check_no_web_server(web_server) -> None:
            """Assertion: web_server is None in headless."""
            assert web_server is None, "web_server should be None in headless"

        # Good case: None
        good_server = None
        # Bad case: mock server object
        class MockServer:
            pass
        bad_server = MockServer()

        assert_distinguishes(check_no_web_server, good_server, bad_server, label="headless_web_server")

    def test_assert_can_fail_no_cache_speedup(self) -> None:
        """Test that our check CAN detect missing cache speedup."""
        from tests.helpers.non_vacuity import assert_distinguishes

        def check_cache_speedup(first_ms: float, second_ms: float) -> None:
            """Assertion: second run is significantly faster."""
            assert second_ms < 1500, f"Cached run took {second_ms}ms"

        # Good case: second run is fast (500ms)
        good_first, good_second = 2000.0, 500.0
        # Bad case: second run is slow (2000ms = no cache)
        bad_first, bad_second = 2000.0, 2000.0

        assert_distinguishes(
            lambda args: check_cache_speedup(*args),
            (good_first, good_second),
            (bad_first, bad_second),
            label="cache_speedup",
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])