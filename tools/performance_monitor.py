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
    
    def start_monitoring(self) -> None:
        """Alias for start()."""
        self.start()

    def stop_monitoring(self) -> None:
        """Alias for stop()."""
        self.stop()

    def measure_cpu(self) -> float:
        """Measure current CPU usage percentage."""
        return float(self._process.cpu_percent(interval=0.01))

    def measure_memory(self) -> Dict[str, Any]:
        """Measure current system and process memory."""
        vmem = psutil.virtual_memory()
        mem_info = self._process.memory_info()
        return {
            "total": vmem.total,
            "available": vmem.available,
            "used": vmem.used,
            "percent": vmem.percent,
            "rss": mem_info.rss,
            "vms": mem_info.vms,
            "process_mb": mem_info.rss / (1024 * 1024),
        }

    def measure_disk_io(self) -> Dict[str, Any]:
        """Measure disk I/O metrics."""
        disk_io = psutil.disk_io_counters()
        if not disk_io:
            return {}
        return {
            "read_bytes": disk_io.read_bytes,
            "write_bytes": disk_io.write_bytes,
            "read_count": disk_io.read_count,
            "write_count": disk_io.write_count,
        }

    def measure_network(self) -> Dict[str, Any]:
        """Measure network I/O metrics."""
        net = psutil.net_io_counters()
        if not net:
            return {}
        return {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
        }

    def measure_footprint(self) -> Dict[str, Any]:
        """Measure memory footprint."""
        mem_info = self._process.memory_info()
        mem_percent = self._process.memory_percent()
        return {
            "rss": mem_info.rss,
            "vms": mem_info.vms,
            "percent": mem_percent,
            "rss_mb": mem_info.rss / (1024 * 1024),
        }

    def get_footprint(self) -> Dict[str, Any]:
        """Get footprint dictionary."""
        return self.measure_footprint()

    def measure_energy(self) -> Dict[str, Any]:
        """Estimate energy consumption."""
        cpu = self.measure_cpu()
        # Typical 65W TDP estimation
        estimated_watts = (cpu / 100.0) * 65.0
        return {
            "cpu_percent": cpu,
            "estimated_watts": max(1.0, estimated_watts),
        }

    def get_energy_consumption(self) -> Dict[str, Any]:
        """Get energy consumption dictionary."""
        return self.measure_energy()

    def collect_baseline(self, duration: int = 3) -> Dict[str, Any]:
        """Collect baseline metrics over duration."""
        measurements = []
        cpu_vals = []
        mem_vals = []
        for _ in range(max(1, duration)):
            cpu = self.measure_cpu()
            mem = self.measure_memory()
            fp = self.measure_footprint()
            net = self.measure_network()
            energy = self.measure_energy()
            cpu_vals.append(cpu)
            mem_vals.append(mem["percent"])
            measurements.append({
                "cpu": cpu,
                "memory": mem,
                "footprint": fp,
                "network": net,
                "energy": energy,
            })
            time.sleep(0.1)

        return {
            "duration": duration,
            "measurements": measurements,
            "statistics": {
                "cpu_avg": sum(cpu_vals) / len(cpu_vals),
                "cpu_max": max(cpu_vals),
                "cpu_min": min(cpu_vals),
                "memory_avg": sum(mem_vals) / len(mem_vals),
                "memory_max": max(mem_vals),
                "memory_min": min(mem_vals),
            }
        }

    def measure_response_time(self, operation: Any = None):
        """Measure response time for a callable task or context manager."""
        if callable(operation):
            start = time.perf_counter()
            operation()
            return time.perf_counter() - start

        @contextmanager
        def _cm():
            start = time.perf_counter()
            try:
                yield
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                self.logger.debug(f"{operation or 'operation'} took {elapsed_ms:.2f}ms")

        return _cm()
    
    def measure_latency(self, func: Callable, *args, **kwargs) -> Any:
        """
        Measure latency of a function call.
        
        Returns:
            If single arg / test expects float: duration in seconds
        """
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        return duration

    
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