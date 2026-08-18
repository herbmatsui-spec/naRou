#!/usr/bin/env python3
"""Performance monitoring tool for naRou project."""
import os
import sys
import time
import json
import psutil
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class PerformanceMetrics:
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_read_mb: float
    disk_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    response_time_ms: float
    latency_ms: float

class PerformanceMonitor:
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.metrics: List[PerformanceMetrics] = []
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.start_time: Optional[float] = None
        self.disk_io_start = psutil.disk_io_counters()
        self.network_io_start = psutil.net_io_counters()
    
    def start(self):
        """Start monitoring in background thread."""
        self.running = True
        self.start_time = time.time()
        self.disk_io_start = psutil.disk_io_counters()
        self.network_io_start = psutil.net_io_counters()
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        print("Performance monitoring started")
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.running:
            self._collect_metrics()
            time.sleep(self.interval)
    
    def _collect_metrics(self):
        """Collect current performance metrics."""
        cpu = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        
        disk_io = psutil.disk_io_counters()
        disk_read = (disk_io.read_bytes - self.disk_io_start.read_bytes) / (1024 * 1024)
        disk_write = (disk_io.write_bytes - self.disk_io_start.write_bytes) / (1024 * 1024)
        
        net_io = psutil.net_io_counters()
        net_sent = (net_io.bytes_sent - self.network_io_start.bytes_sent) / (1024 * 1024)
        net_recv = (net_io.bytes_recv - self.network_io_start.bytes_recv) / (1024 * 1024)
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu,
            memory_percent=memory.percent,
            memory_mb=memory.used / (1024 * 1024),
            disk_read_mb=disk_read,
            disk_write_mb=disk_write,
            network_sent_mb=net_sent,
            network_recv_mb=net_recv,
            response_time_ms=0.0,
            latency_ms=0.0
        )
        self.metrics.append(metrics)
    
    def measure_response_time(self, func, *args, **kwargs):
        """Measure response time of a function."""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        if self.metrics:
            self.metrics[-1].response_time_ms = elapsed
        return result, elapsed
    
    def measure_latency(self, func, *args, **kwargs):
        """Measure latency of a function."""
        return self.measure_response_time(func, *args, **kwargs)
    
    def get_footprint(self) -> Dict[str, float]:
        """Get memory footprint."""
        process = psutil.Process()
        mem_info = process.memory_info()
        return {
            "rss_mb": mem_info.rss / (1024 * 1024),
            "vms_mb": mem_info.vms / (1024 * 1024),
            "percent": process.memory_percent()
        }
    
    def get_energy_consumption(self) -> Dict[str, float]:
        """Estimate energy consumption (simplified)."""
        cpu = psutil.cpu_percent()
        return {
            "estimated_watts": cpu * 0.1,
            "cpu_percent": cpu
        }
    
    def save_baseline(self, filepath: str = "baseline.json"):
        """Save baseline data to file."""
        data = {
            "start_time": self.start_time,
            "end_time": time.time(),
            "duration": time.time() - self.start_time if self.start_time else 0,
            "metrics": [asdict(m) for m in self.metrics],
            "summary": self.get_summary()
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Baseline saved to {filepath}")
        return data
    
    def load_baseline(self, filepath: str = "baseline.json") -> Dict:
        """Load baseline data from file."""
        with open(filepath) as f:
            return json.load(f)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self.metrics:
            return {}
        
        cpu_vals = [m.cpu_percent for m in self.metrics]
        mem_vals = [m.memory_percent for m in self.metrics]
        resp_vals = [m.response_time_ms for m in self.metrics if m.response_time_ms > 0]
        lat_vals = [m.latency_ms for m in self.metrics if m.latency_ms > 0]
        
        return {
            "cpu": {"avg": sum(cpu_vals)/len(cpu_vals), "max": max(cpu_vals), "min": min(cpu_vals)},
            "memory": {"avg": sum(mem_vals)/len(mem_vals), "max": max(mem_vals), "min": min(mem_vals)},
            "response_time": {"avg": sum(resp_vals)/len(resp_vals) if resp_vals else 0, "max": max(resp_vals) if resp_vals else 0},
            "latency": {"avg": sum(lat_vals)/len(lat_vals) if lat_vals else 0, "max": max(lat_vals) if lat_vals else 0},
            "samples": len(self.metrics)
        }
    
    def analyze_baseline(self) -> Dict[str, Any]:
        """Analyze baseline data."""
        summary = self.get_summary()
        return {
            "cpu_analysis": "normal" if summary.get("cpu", {}).get("avg", 0) < 50 else "high",
            "memory_analysis": "normal" if summary.get("memory", {}).get("avg", 0) < 70 else "high",
            "performance_rating": self._calculate_rating(summary)
        }
    
    def _calculate_rating(self, summary: Dict) -> str:
        """Calculate performance rating."""
        cpu_avg = summary.get("cpu", {}).get("avg", 100)
        mem_avg = summary.get("memory", {}).get("avg", 100)
        score = 100 - (cpu_avg * 0.5 + mem_avg * 0.5)
        if score >= 80: return "Excellent"
        elif score >= 60: return "Good"
        elif score >= 40: return "Fair"
        return "Poor"
    
    def validate_baseline(self, thresholds: Dict = None) -> Dict[str, bool]:
        """Validate baseline against thresholds."""
        if thresholds is None:
            thresholds = {"cpu_max": 80, "memory_max": 85, "response_time_max": 1000}
        
        summary = self.get_summary()
        return {
            "cpu_ok": summary.get("cpu", {}).get("max", 0) < thresholds.get("cpu_max", 80),
            "memory_ok": summary.get("memory", {}).get("max", 0) < thresholds.get("memory_max", 85),
            "response_time_ok": summary.get("response_time", {}).get("max", 0) < thresholds.get("response_time_max", 1000),
        }
    
    def generate_report(self) -> str:
        """Generate text report."""
        summary = self.get_summary()
        analysis = self.analyze_baseline()
        validation = self.validate_baseline()
        
        report = [
            "=== Performance Baseline Report ===",
            f"Generated: {datetime.now().isoformat()}",
            f"Duration: {time.time() - self.start_time:.1f}s" if self.start_time else "",
            f"Samples: {summary.get('samples', 0)}",
            "",
            "CPU:",
            f"  Average: {summary.get('cpu', {}).get('avg', 0):.1f}%",
            f"  Max: {summary.get('cpu', {}).get('max', 0):.1f}%",
            "",
            "Memory:",
            f"  Average: {summary.get('memory', {}).get('avg', 0):.1f}%",
            f"  Max: {summary.get('memory', {}).get('max', 0):.1f}%",
            "",
            "Response Time:",
            f"  Average: {summary.get('response_time', {}).get('avg', 0):.1f}ms",
            f"  Max: {summary.get('response_time', {}).get('max', 0):.1f}ms",
            "",
            "Analysis:",
            f"  CPU: {analysis.get('cpu_analysis', 'unknown')}",
            f"  Memory: {analysis.get('memory_analysis', 'unknown')}",
            f"  Rating: {analysis.get('performance_rating', 'unknown')}",
            "",
            "Validation:",
            f"  CPU: {'PASS' if validation.get('cpu_ok', False) else 'FAIL'}",
            f"  Memory: {'PASS' if validation.get('memory_ok', False) else 'FAIL'}",
            f"  Response Time: {'PASS' if validation.get('response_time_ok', False) else 'FAIL'}",
        ]
        return "\n".join(report)
    
    def generate_html_report(self, filepath: str = "report.html"):
        """Generate HTML report."""
        summary = self.get_summary()
        html = f"""
<!DOCTYPE html>
<html>
<head><title>Performance Report</title>
<style>body{{font-family:sans-serif;margin:20px;}} table{{border-collapse:collapse;width:100%;}} th,td{{border:1px solid #ddd;padding:8px;}} th{{background:#f2f2f2;}}</style></head>
<body>
<h1>Performance Baseline Report</h1>
<p>Generated: {datetime.now().isoformat()}</p>
<p>Samples: {summary.get('samples', 0)}</p>
<table><tr><th>Metric</th><th>Average</th><th>Max</th><th>Min</th></tr>
<tr><td>CPU %</td><td>{summary.get('cpu', {}).get('avg', 0):.1f}%</td><td>{summary.get('cpu', {}).get('max', 0):.1f}%</td><td>{summary.get('cpu', {}).get('min', 0):.1f}%</td></tr>
<tr><td>Memory %</td><td>{summary.get('memory', {}).get('avg', 0):.1f}%</td><td>{summary.get('memory', {}).get('max', 0):.1f}%</td><td>{summary.get('memory', {}).get('min', 0):.1f}%</td></tr>
<tr><td>Response Time (ms)</td><td>{summary.get('response_time', {}).get('avg', 0):.1f}</td><td>{summary.get('response_time', {}).get('max', 0):.1f}</td><td>{summary.get('response_time', {}).get('min', 0):.1f}</td></tr>
</table>
</body></html>
"""
        with open(filepath, "w") as f:
            f.write(html)
        print(f"HTML report saved to {filepath}")
    
    def backup_baseline(self, backup_dir: str = "backups"):
        """Backup baseline data."""
        Path(backup_dir).mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_baseline(f"{backup_dir}/baseline_{timestamp}.json")
    
    def restore_baseline(self, filepath: str):
        """Restore baseline from backup."""
        return self.load_baseline(filepath)


def run_baseline_test(duration: int = 10) -> Dict:
    """Run a baseline test."""
    monitor = PerformanceMonitor(interval=0.5)
    monitor.start()
    
    # Simulate some work
    def dummy_work():
        total = 0
        for i in range(100000):
            total += i * i
        return total
    
    end_time = time.time() + duration
    while time.time() < end_time:
        monitor.measure_response_time(dummy_work)
        time.sleep(0.1)
    
    monitor.stop()
    monitor.save_baseline()
    monitor.generate_html_report()
    print(monitor.generate_report())
    return monitor.get_summary()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Performance Monitor")
    parser.add_argument("--duration", type=int, default=10, help="Test duration in seconds")
    parser.add_argument("--interval", type=float, default=1.0, help="Sampling interval")
    args = parser.parse_args()
    
    run_baseline_test(args.duration)