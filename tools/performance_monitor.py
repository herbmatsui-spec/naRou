#!/usr/bin/env python3
"""
Performance Monitor for naRou
Handles CPU, memory, disk I/O, network, and response time monitoring.
"""

import os
import time
import psutil
import threading
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from contextlib import contextmanager


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    response_time_ms: float = 0.0
    latency_ms: float = 0.0
    footprint_mb: float = 0.0
    energy_watts: float = 0.0


class PerformanceMonitor:
    """
    Monitors system performance metrics including CPU, memory, disk I/O,
    network, response time, and latency.
    """
    
    def __init__(self, interval: float = 1.0, output_dir: str = "logs/performance"):
        """
        Initialize the PerformanceMonitor.
        
        Args:
            interval: Sampling interval in seconds
            output_dir: Directory for saving metrics logs
        """
        self.interval = interval
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self._monitoring = False
        self._thread: Optional[threading.Thread] = None
        self._metrics_history: List[PerformanceMetrics] = []
        self._lock = threading.Lock()
        
        # Baseline for delta calculations
        self._baseline_disk = psutil.disk_io_counters()
        self._baseline_net = psutil.net_io_counters()
        self._baseline_time = time.time()
        
        # Process reference
        self._process = psutil.Process()
    
    def start(self) -> None:
        """Start monitoring in background thread."""
        if self._monitoring:
            self.logger.warning("Monitoring already running")
            return
        
        self._monitoring = True
        self._metrics_history.clear()
        self._baseline_disk = psutil.disk_io_counters()
        self._baseline_net = psutil.net_io_counters()
        self._baseline_time = time.time()
        
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self.logger.info("Performance monitoring started")
    
    def stop(self) -> None:
        """Stop monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self.logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring:
            metrics = self._collect_metrics()
            with self._lock:
                self._metrics_history.append(metrics)
            time.sleep(self.interval)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics."""
        # CPU
        cpu_percent = self._process.cpu_percent(interval=0.0)
        
        # Memory
        mem_info = self._process.memory_info()
        memory_mb = mem_info.rss / (1024 * 1024)
        memory_percent = self._process.memory_percent()
        
        # Disk I/O (delta from baseline)
        disk_io = psutil.disk_io_counters()
        disk_read_mb = 0.0
        disk_write_mb = 0.0
        if self._baseline_disk and disk_io:
            disk_read_mb = (disk_io.read_bytes - self._baseline_disk.read_bytes) / (1024 * 1024)
            disk_write_mb = (disk_io.write_bytes - self._baseline_disk.write_bytes) / (1024 * 1024)
        
        # Network (delta from baseline)
        net_io = psutil.net_io_counters()
        network_sent_mb = 0.0
        network_recv_mb = 0.0
        if self._baseline_net and net_io:
            network_sent_mb = (net_io.bytes_sent - self._baseline_net.bytes_sent) / (1024 * 1024)
            network_recv_mb = (net_io.bytes_recv - self._baseline_net.bytes_recv) / (1024 * 1024)
        
        # Process footprint
        footprint_mb = memory_mb
        
        return PerformanceMetrics(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_percent=memory_percent,
            disk_read_mb=disk_read_mb,
            disk_write_mb=disk_write_mb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            footprint_mb=footprint_mb,
        )
    
    @contextmanager
    def measure_response_time(self, operation_name: str = "operation"):
        """Context manager to measure response time of an operation."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.logger.debug(f"{operation_name} took {elapsed_ms:.2f}ms")
    
    def measure_latency(self, func: Callable, *args, **kwargs) -> tuple:
        """
        Measure latency of a function call.
        
        Returns:
            Tuple of (result, latency_ms)
        """
        start = time.perf_counter()
        result = func(*args, **kwargs)
        latency_ms = (time.perf_counter() - start) * 1000
        return result, latency_ms
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current metrics snapshot."""
        return self._collect_metrics()
    
    def get_history(self) -> List[PerformanceMetrics]:
        """Get all collected metrics history."""
        with self._lock:
            return list(self._metrics_history)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get statistical summary of collected metrics."""
        with self._lock:
            if not self._metrics_history:
                return {}
            
            history = self._metrics_history
            return {
                "samples": len(history),
                "duration_seconds": history[-1].timestamp - history[0].timestamp if len(history) > 1 else 0,
                "cpu": {
                    "avg": sum(m.cpu_percent for m in history) / len(history),
                    "max": max(m.cpu_percent for m in history),
                    "min": min(m.cpu_percent for m in history),
                },
                "memory_mb": {
                    "avg": sum(m.memory_mb for m in history) / len(history),
                    "max": max(m.memory_mb for m in history),
                    "min": min(m.memory_mb for m in history),
                },
                "disk_read_mb_total": sum(m.disk_read_mb for m in history),
                "disk_write_mb_total": sum(m.disk_write_mb for m in history),
                "network_sent_mb_total": sum(m.network_sent_mb for m in history),
                "network_recv_mb_total": sum(m.network_recv_mb for m in history),
                "footprint_mb": {
                    "avg": sum(m.footprint_mb for m in history) / len(history),
                    "max": max(m.footprint_mb for m in history),
                },
            }
    
    def save_baseline(self, filepath: Optional[str] = None) -> str:
        """Save current metrics as baseline."""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(self.output_dir / f"baseline_{timestamp}.json")
        
        summary = self.get_summary()
        baseline_data = {
            "timestamp": time.time(),
            "summary": summary,
            "raw_history": [asdict(m) for m in self.get_history()],
        }
        
        with open(filepath, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        self.logger.info(f"Baseline saved to {filepath}")
        return filepath
    
    def load_baseline(self, filepath: str) -> Dict[str, Any]:
        """Load baseline from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.logger.info(f"Baseline loaded from {filepath}")
        return data
    
    def compare_with_baseline(self, baseline_file: str) -> Dict[str, Any]:
        """Compare current metrics with a saved baseline."""
        baseline = self.load_baseline(baseline_file)
        current = self.get_summary()
        
        comparison = {}
        for key in ["cpu", "memory_mb", "footprint_mb"]:
            if key in baseline.get("summary", {}) and key in current:
                base_avg = baseline["summary"][key].get("avg", 0)
                curr_avg = current[key].get("avg", 0)
                if base_avg > 0:
                    change_pct = ((curr_avg - base_avg) / base_avg) * 100
                else:
                    change_pct = 0
                comparison[key] = {
                    "baseline_avg": base_avg,
                    "current_avg": curr_avg,
                    "change_percent": change_pct,
                }
        
        return comparison
    
    def run_baseline_test(self, duration: float = 10.0) -> str:
        """Run a baseline test for specified duration."""
        self.logger.info(f"Running baseline test for {duration}s")
        self.start()
        time.sleep(duration)
        self.stop()
        return self.save_baseline()
    
    def generate_report(self, output_path: Optional[str] = None) -> str:
        """Generate performance report."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(self.output_dir / f"performance_report_{timestamp}.json")
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "history": [asdict(m) for m in self.get_history()],
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Report generated: {output_path}")
        return output_path


def get_performance_monitor(interval: float = 1.0, 
                             output_dir: str = "logs/performance") -> PerformanceMonitor:
    """Factory function for PerformanceMonitor."""
    return PerformanceMonitor(interval, output_dir)


def quick_cpu_test(duration: float = 5.0) -> Dict[str, float]:
    """Quick CPU usage test."""
    monitor = PerformanceMonitor(interval=0.5)
    monitor.start()
    time.sleep(duration)
    monitor.stop()
    return monitor.get_summary().get("cpu", {})


def quick_memory_test(duration: float = 5.0) -> Dict[str, float]:
    """Quick memory usage test."""
    monitor = PerformanceMonitor(interval=0.5)
    monitor.start()
    time.sleep(duration)
    monitor.stop()
    return monitor.get_summary().get("memory_mb", {})


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Running quick performance tests...")
        print("CPU test:", quick_cpu_test(3.0))
        print("Memory test:", quick_memory_test(3.0))
    else:
        print("PerformanceMonitor module loaded")
        print("Usage: python performance_monitor.py test")