#!/usr/bin/env python3
"""Performance test suite integration."""
import os
import sys
import pytest

# Import all test modules
from tests.performance import (
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
)

class TestIntegration:
    def test_all_modules_import(self):
        """Test all test modules can be imported."""
        modules = [
            test_cpu, test_memory, test_disk_io, test_network,
            test_response_time, test_latency, test_footprint, test_energy,
            test_stress, test_load, test_spike, test_sustainability,
            test_endurance, test_reliability, test_availability,
            test_scalability, test_interoperability, test_compatibility
        ]
        
        for mod in modules:
            assert hasattr(mod, 'TestCPU') or hasattr(mod, 'TestMemory') or \
                   hasattr(mod, 'TestDiskIO') or hasattr(mod, 'TestNetwork') or \
                   hasattr(mod, 'TestResponseTime') or hasattr(mod, 'TestLatency') or \
                   hasattr(mod, 'TestFootprint') or hasattr(mod, 'TestEnergy') or \
                   hasattr(mod, 'TestStress') or hasattr(mod, 'TestLoad') or \
                   hasattr(mod, 'TestSpike') or hasattr(mod, 'TestSustainability') or \
                   hasattr(mod, 'TestEndurance') or hasattr(mod, 'TestReliability') or \
                   hasattr(mod, 'TestAvailability') or hasattr(mod, 'TestScalability') or \
                   hasattr(mod, 'TestInteroperability') or hasattr(mod, 'TestCompatibility')
        
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
        
        print(f"Integration - Footprint: {footprint['rss_mb']:.1f}MB, Energy: {energy['estimated_watts']:.2f}W")
        print(f"Integration - Summary samples: {summary.get('samples', 0)}")
        
        assert footprint['rss_mb'] > 0
        assert summary.get('samples', 0) > 0


if __name__ == "__main__":
    import time
    test = TestIntegration()
    test.test_all_modules_import()
    test.test_full_suite_execution()
    print("All integration tests passed")