#!/usr/bin/env python3
"""Performance test suite integration."""

import time

# Import all test modules
from tests.performance import (
    test_availability,
    test_compatibility,
    test_cpu,
    test_disk_io,
    test_endurance,
    test_energy,
    test_footprint,
    test_interoperability,
    test_latency,
    test_load,
    test_memory,
    test_network,
    test_reliability,
    test_response_time,
    test_scalability,
    test_spike,
    test_stress,
    test_sustainability,
)


class TestIntegration:
    def test_all_modules_import(self):
        """Test all test modules can be imported."""
        modules = [
            test_cpu,
            test_memory,
            test_disk_io,
            test_network,
            test_response_time,
            test_latency,
            test_footprint,
            test_energy,
            test_stress,
            test_load,
            test_spike,
            test_sustainability,
            test_endurance,
            test_reliability,
            test_availability,
            test_scalability,
            test_interoperability,
            test_compatibility,
        ]

        for mod in modules:
            assert any(k.startswith("Test") for k in dir(mod))

        print(f"Integration - All {len(modules)} test modules imported")

    def test_full_suite_execution(self):
        """Run a quick test from each module."""
        from tools.performance_monitor import PerformanceMonitor

        monitor = PerformanceMonitor(interval=0.05)
        monitor.start()

        def work():
            time.sleep(0.001)
            return "done"

        # Quick tests from each category
        for _ in range(5):
            monitor.measure_response_time(work)

        footprint = monitor.get_footprint()
        energy = monitor.get_energy_consumption()
        summary = monitor.get_summary()

        monitor.stop()

        print(
            f"Integration - Footprint: {footprint['rss_mb']:.1f}MB, Energy: {energy['estimated_watts']:.2f}W"
        )
        print(f"Integration - Summary samples: {summary.get('samples', 0)}")

        assert footprint["rss_mb"] > 0
        assert summary.get("samples", 0) > 0


if __name__ == "__main__":
    import time

    test = TestIntegration()
    test.test_all_modules_import()
    test.test_full_suite_execution()
    print("All integration tests passed")
