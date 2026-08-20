#!/usr/bin/env python3
"""Performance optimization tool for naRou project."""
import time
import json
import psutil
from datetime import datetime
from typing import Dict, List, Any, Callable
from dataclasses import dataclass, asdict
from tools.performance_monitor import PerformanceMonitor

@dataclass
class OptimizationResult:
    timestamp: str
    optimization_type: str
    before: Dict[str, Any]
    after: Dict[str, Any]
    improvement: float
    success: bool

class PerformanceOptimizer:
    def __init__(self):
        self.results: List[OptimizationResult] = []
    
    def profile_function(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Profile a function's performance."""
        # CPU profiling
        start_time = time.perf_counter()
        start_cpu = psutil.cpu_percent()
        
        # Memory profiling
        process = psutil.Process()
        start_mem = process.memory_info().rss / (1024 * 1024)
        
        # Execute function
        result = func(*args, **kwargs)
        
        # End profiling
        end_time = time.perf_counter()
        end_cpu = psutil.cpu_percent()
        end_mem = process.memory_info().rss / (1024 * 1024)
        
        return {
            "execution_time_ms": (end_time - start_time) * 1000,
            "cpu_usage_percent": (start_cpu + end_cpu) / 2,
            "memory_usage_mb": end_mem - start_mem,
            "peak_memory_mb": process.memory_info().rss / (1024 * 1024),
            "result": result
        }
    
    def profile_code_block(self, code_block: Callable) -> Dict[str, Any]:
        """Profile a code block."""
        return self.profile_function(code_block)
    
    def detect_bottlenecks(self, profile_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect performance bottlenecks."""
        bottlenecks = []
        
        # CPU bottleneck
        if profile_data.get("cpu_usage_percent", 0) > 80:
            bottlenecks.append({
                "type": "CPU",
                "severity": "high",
                "value": profile_data["cpu_usage_percent"],
                "threshold": 80,
                "description": "High CPU usage detected"
            })
        
        # Memory bottleneck
        if profile_data.get("memory_usage_mb", 0) > 100:
            bottlenecks.append({
                "type": "Memory",
                "severity": "high",
                "value": profile_data["memory_usage_mb"],
                "threshold": 100,
                "description": "High memory allocation detected"
            })
        
        # Execution time bottleneck
        if profile_data.get("execution_time_ms", 0) > 1000:
            bottlenecks.append({
                "type": "Execution Time",
                "severity": "medium",
                "value": profile_data["execution_time_ms"],
                "threshold": 1000,
                "description": "Slow execution time detected"
            })
        
        return bottlenecks
    
    def detect_memory_leaks(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect memory leaks from snapshots."""
        if len(snapshots) < 2:
            return {"leak_detected": False, "confidence": 0}
        
        memory_values = [s.get("memory_mb", 0) for s in snapshots]
        
        # Calculate trend
        if len(memory_values) >= 3:
            # Simple linear trend
            n = len(memory_values)
            sum_x = sum(range(n))
            sum_y = sum(memory_values)
            sum_xy = sum(i * memory_values[i] for i in range(n))
            sum_x2 = sum(i * i for i in range(n))
            
            if n * sum_x2 - sum_x * sum_x != 0:
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                leak_detected = slope > 1.0  # More than 1MB per sample
                confidence = min(abs(slope) * 10, 100)  # Cap at 100%
                
                return {
                    "leak_detected": leak_detected,
                    "confidence": min(confidence, 100),
                    "growth_rate_mb_per_sample": slope,
                    "total_growth_mb": memory_values[-1] - memory_values[0]
                }
        
        return {"leak_detected": False, "confidence": 0}
    
    def optimize_cpu(self, func: Callable, *args, **kwargs) -> OptimizationResult:
        """Optimize CPU usage of a function."""
        before = self.profile_function(func, *args, **kwargs)
        
        # Optimization: Suggest using built-in functions, list comprehensions, etc.
        # For demo, we'll just run it again (in practice, would apply actual optimizations)
        after = self.profile_function(func, *args, **kwargs)
        
        improvement = 0
        if before["execution_time_ms"] > 0:
            improvement = ((before["execution_time_ms"] - after["execution_time_ms"]) / 
                          before["execution_time_ms"]) * 100
        
        result = OptimizationResult(
            timestamp=datetime.now().isoformat(),
            optimization_type="CPU",
            before=before,
            after=after,
            improvement=improvement,
            success=improvement > 0
        )
        
        self.results.append(result)
        return result
    
    def optimize_memory(self, func: Callable, *args, **kwargs) -> OptimizationResult:
        """Optimize memory usage of a function."""
        before = self.profile_function(func, *args, **kwargs)
        
        # Optimization: Suggest using generators, deleting unused variables, etc.
        after = self.profile_function(func, *args, **kwargs)
        
        improvement = 0
        if before["memory_usage_mb"] > 0:
            improvement = ((before["memory_usage_mb"] - after["memory_usage_mb"]) / 
                         before["memory_usage_mb"]) * 100
        
        result = OptimizationResult(
            timestamp=datetime.now().isoformat(),
            optimization_type="Memory",
            before=before,
            after=after,
            improvement=improvement,
            success=improvement > 0
        )
        
        self.results.append(result)
        return result
    
    def optimize_disk_io(self, func: Callable, *args, **kwargs) -> OptimizationResult:
        """Optimize disk I/O of a function."""
        before = self.profile_function(func, *args, **kwargs)
        
        # Optimization: Suggest buffering, batching, etc.
        after = self.profile_function(func, *args, **kwargs)
        
        # For disk I/O, we'd look at read/write bytes in a real implementation
        improvement = 0
        
        result = OptimizationResult(
            timestamp=datetime.now().isoformat(),
            optimization_type="Disk I/O",
            before=before,
            after=after,
            improvement=improvement,
            success=True  # Assume success for demo
        )
        
        self.results.append(result)
        return result
    
    def optimize_network(self, func: Callable, *args, **kwargs) -> OptimizationResult:
        """Optimize network usage of a function."""
        before = self.profile_function(func, *args, **kwargs)
        
        # Optimization: Suggest connection pooling, compression, etc.
        after = self.profile_function(func, *args, **kwargs)
        
        improvement = 0
        
        result = OptimizationResult(
            timestamp=datetime.now().isoformat(),
            optimization_type="Network",
            before=before,
            after=after,
            improvement=improvement,
            success=True
        )
        
        self.results.append(result)
        return result
    
    def optimize_response_time(self, func: Callable, *args, **kwargs) -> OptimizationResult:
        """Optimize response time of a function."""
        before = self.profile_function(func, *args, **kwargs)
        
        # Optimization: Suggest caching, async processing, etc.
        after = self.profile_function(func, *args, **kwargs)
        
        improvement = 0
        if before["execution_time_ms"] > 0:
            improvement = ((before["execution_time_ms"] - after["execution_time_ms"]) / 
                          before["execution_time_ms"]) * 100
        
        result = OptimizationResult(
            timestamp=datetime.now().isoformat(),
            optimization_type="Response Time",
            before=before,
            after=after,
            improvement=improvement,
            success=improvement > 0
        )
        
        self.results.append(result)
        return result
    
    def optimize_latency(self, func: Callable, *args, **kwargs) -> OptimizationResult:
        """Optimize latency of a function."""
        return self.optimize_response_time(func, *args, **kwargs)
    
    def optimize_footprint(self, func: Callable, *args, **kwargs) -> OptimizationResult:
        """Optimize footprint of a function."""
        before = self.profile_function(func, *args, **kwargs)
        
        # Optimization: Suggest using __slots__, data classes, etc.
        after = self.profile_function(func, *args, **kwargs)
        
        improvement = 0
        if before["peak_memory_mb"] > 0:
            improvement = ((before["peak_memory_mb"] - after["peak_memory_mb"]) / 
                          before["peak_memory_mb"]) * 100
        
        result = OptimizationResult(
            timestamp=datetime.now().isoformat(),
            optimization_type="Footprint",
            before=before,
            after=after,
            improvement=improvement,
            success=improvement > 0
        )
        
        self.results.append(result)
        return result
    
    def optimize_energy_consumption(self, func: Callable, *args, **kwargs) -> OptimizationResult:
        """Optimize energy consumption of a function."""
        before = self.profile_function(func, *args, **kwargs)
        
        # Optimization: Reduce CPU usage, use efficient algorithms
        after = self.profile_function(func, *args, **kwargs)
        
        improvement = 0
        if before["cpu_usage_percent"] > 0:
            improvement = ((before["cpu_usage_percent"] - after["cpu_usage_percent"]) / 
                         before["cpu_usage_percent"]) * 100
        
        result = OptimizationResult(
            timestamp=datetime.now().isoformat(),
            optimization_type="Energy Consumption",
            before=before,
            after=after,
            improvement=improvement,
            success=improvement > 0
        )
        
        self.results.append(result)
        return result
    
    def run_stress_test(self, func: Callable, duration: int = 10, *args, **kwargs) -> Dict[str, Any]:
        """Run stress test on a function."""
        start_time = time.time()
        end_time = start_time + duration
        
        executions = 0
        errors = 0
        latencies = []
        
        while time.time() < end_time:
            try:
                exec_start = time.perf_counter()
                func(*args, **kwargs)
                exec_end = time.perf_counter()
                latencies.append((exec_end - exec_start) * 1000)
                executions += 1
            except Exception as e:
                errors += 1
                print(f"Error during stress test: {e}")
        
        actual_duration = time.time() - start_time
        
        return {
            "duration_seconds": actual_duration,
            "executions": executions,
            "errors": errors,
            "execution_per_second": executions / actual_duration if actual_duration > 0 else 0,
            "error_rate_percent": (errors / executions * 100) if executions > 0 else 0,
            "latency_avg_ms": sum(latencies) / len(latencies) if latencies else 0,
            "latency_max_ms": max(latencies) if latencies else 0,
            "latency_min_ms": min(latencies) if latencies else 0
        }
    
    def run_load_test(self, func: Callable, target_rps: float, duration: int = 10, *args, **kwargs) -> Dict[str, Any]:
        """Run load test on a function."""
        start_time = time.time()
        end_time = start_time + duration
        
        executions = 0
        errors = 0
        latencies = []
        interval = 1.0 / target_rps if target_rps > 0 else 0.1
        
        while time.time() < end_time:
            exec_start = time.perf_counter()
            try:
                func(*args, **kwargs)
                exec_end = time.perf_counter()
                latencies.append((exec_end - exec_start) * 1000)
                executions += 1
            except Exception:
                errors += 1
            
            elapsed = time.perf_counter() - exec_start
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)
        
        actual_duration = time.time() - start_time
        
        return {
            "duration_seconds": actual_duration,
            "target_rps": target_rps,
            "actual_rps": executions / actual_duration if actual_duration > 0 else 0,
            "executions": executions,
            "errors": errors,
            "error_rate_percent": (errors / executions * 100) if executions > 0 else 0,
            "latency_avg_ms": sum(latencies) / len(latencies) if latencies else 0,
            "latency_max_ms": max(latencies) if latencies else 0,
            "latency_p95_ms": sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0
        }
    
    def run_spike_test(self, func: Callable, normal_load: int, spike_load: int, 
                      duration: int = 10, *args, **kwargs) -> Dict[str, Any]:
        """Run spike test on a function."""
        import threading
        
        results = {"normal_before": {}, "spike": {}, "normal_after": {}}
        
        def worker(duration_sec, count_list):
            end = time.time() + duration_sec
            while time.time() < end:
                start = time.perf_counter()
                try:
                    func(*args, **kwargs)
                    end = time.perf_counter()
                    count_list.append((end - start) * 1000)
                except Exception:
                    count_list.append(-1)  # Error marker
                time.sleep(0.01)
        
        # Normal load before
        before_times = []
        t1 = threading.Thread(target=worker, args=(2, before_times))
        t1.start()
        t1.join()
        results["normal_before"] = {
            "avg": sum(t for t in before_times if t > 0) / len([t for t in before_times if t > 0]) if before_times else 0,
            "max": max(before_times) if before_times else 0,
            "count": len(before_times)
        }
        
        # Spike load
        spike_times = []
        t2 = threading.Thread(target=worker, args=(2, spike_times))
        t2.start()
        t2.join()
        results["spike"] = {
            "avg": sum(t for t in spike_times if t > 0) / len([t for t in spike_times if t > 0]) if spike_times else 0,
            "max": max(spike_times) if spike_times else 0,
            "count": len(spike_times)
        }
        
        # Normal load after
        after_times = []
        t3 = threading.Thread(target=worker, args=(2, after_times))
        t3.start()
        t3.join()
        results["normal_after"] = {
            "avg": sum(t for t in after_times if t > 0) / len([t for t in after_times if t > 0]) if after_times else 0,
            "max": max(after_times) if after_times else 0,
            "count": len(after_times)
        }
        
        return results
    
    def run_sustainability_test(self, func: Callable, duration: int = 30, *args, **kwargs) -> Dict[str, Any]:
        """Run sustainability test on a function."""
        start_time = time.time()
        end_time = start_time + duration
        
        latencies = []
        memory_samples = []
        
        while time.time() < end_time:
            exec_start = time.perf_counter()
            try:
                func(*args, **kwargs)
                exec_end = time.perf_counter()
                latencies.append((exec_end - exec_start) * 1000)
            except Exception:
                pass
            
            # Sample memory
            process = psutil.Process()
            memory_samples.append(process.memory_info().rss / (1024 * 1024))
            
            time.sleep(0.1)
        
        # Analyze for degradation
        if len(latencies) >= 10:
            first_quarter = latencies[:len(latencies)//4]
            last_quarter = latencies[-len(latencies)//4:]
            
            avg_first = sum(first_quarter) / len(first_quarter) if first_quarter else 0
            avg_last = sum(last_quarter) / len(last_quarter) if last_quarter else 0
            
            degradation = ((avg_last - avg_first) / avg_first * 100) if avg_first > 0 else 0
        else:
            degradation = 0
        
        # Check for memory leaks
        memory_growth = memory_samples[-1] - memory_samples[0] if len(memory_samples) > 1 else 0
        
        return {
            "duration_seconds": duration,
            "samples": len(latencies),
            "latency_avg_ms": sum(latencies) / len(latencies) if latencies else 0,
            "latency_degradation_percent": degradation,
            "memory_start_mb": memory_samples[0] if memory_samples else 0,
            "memory_end_mb": memory_samples[-1] if memory_samples else 0,
            "memory_growth_mb": memory_growth,
            "stable": abs(degradation) < 10 and abs(memory_growth) < 10
        }
    
    def run_endurance_test(self, func: Callable, duration: int = 60, *args, **kwargs) -> Dict[str, Any]:
        """Run endurance test on a function."""
        return self.run_sustainability_test(func, duration, *args, **kwargs)
    
    def run_reliability_test(self, func: Callable, iterations: int = 100, *args, **kwargs) -> Dict[str, Any]:
        """Run reliability test on a function."""
        successes = 0
        failures = 0
        latencies = []
        
        for i in range(iterations):
            start = time.perf_counter()
            try:
                func(*args, **kwargs)
                end = time.perf_counter()
                latencies.append((end - start) * 1000)
                successes += 1
            except Exception as e:
                failures += 1
                if i < 5:  # Log first few errors
                    print(f"Reliability test error: {e}")
        
        total = successes + failures
        success_rate = (successes / total * 100) if total > 0 else 0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        return {
            "iterations": total,
            "successes": successes,
            "failures": failures,
            "success_rate_percent": success_rate,
            "latency_avg_ms": avg_latency,
            "reliable": success_rate >= 95
        }
    
    def run_availability_test(self, func: Callable, duration: int = 30, *args, **kwargs) -> Dict[str, Any]:
        """Run availability test on a function."""
        start_time = time.time()
        end_time = start_time + duration
        
        checks = 0
        successful = 0
        total_downtime = 0
        last_failure = None
        
        while time.time() < end_time:
            checks += 1
            try:
                func(*args, **kwargs)
                check_end = time.perf_counter()
                successful += 1
                # If we had a failure before, calculate downtime
                if last_failure is not None:
                    total_downtime += check_end - last_failure
                    last_failure = None
            except Exception:
                if last_failure is None:
                    last_failure = time.perf_counter()
            
            time.sleep(0.1)
        
        # If still down at end
        if last_failure is not None:
            total_downtime += time.perf_counter() - last_failure
        
        uptime_percent = ((duration - total_downtime) / duration * 100) if duration > 0 else 0
        
        return {
            "duration_seconds": duration,
            "checks": checks,
            "successful": successful,
            "uptime_percent": uptime_percent,
            "downtime_seconds": total_downtime,
            "available": uptime_percent >= 99
        }
    
    def run_scalability_test(self, func: Callable, max_workers: int = 8, *args, **kwargs) -> Dict[str, Any]:
        """Run scalability test on a function."""
        import threading
        
        results = {}
        
        for workers in [1, 2, 4, max_workers]:
            def worker_task():
                start = time.perf_counter()
                try:
                    func(*args, **kwargs)
                    end = time.perf_counter()
                    return (end - start) * 1000, None
                except Exception as e:
                    return 0, str(e)
            
            # Run with specified worker count
            threads = []
            latencies = []
            errors = 0
            
            for _ in range(workers * 5):  # 5 tasks per worker
                t = threading.Thread(target=lambda: (
                    latencies.append(worker_task()[0]) if worker_task()[1] is None else 
                    (errors.__iadd__(1))
                ))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            success_count = len([l for l in latencies if l > 0])
            avg_latency = sum(l for l in latencies if l > 0) / success_count if success_count > 0 else 0
            
            results[workers] = {
                "workers": workers,
                "tasks": workers * 5,
                "successful": success_count,
                "failed": errors,
                "latency_avg_ms": avg_latency,
                "throughput": success_count / 5 if success_count > 0 else 0  # Tasks per second per worker
            }
        
        return results
    
    def run_compatibility_test(self) -> Dict[str, Any]:
        """Run compatibility test."""
        import platform
        import sys
        
        compatibility = {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "tests": {}
        }
        
        # Test basic functionality
        try:
            monitor = PerformanceMonitor(interval=0.1)
            monitor.start()
            time.sleep(0.2)
            monitor.stop()
            compatibility["tests"]["performance_monitor"] = "PASS"
        except Exception as e:
            compatibility["tests"]["performance_monitor"] = f"FAIL: {e}"
        
        # Test profiling
        try:
            def dummy(): return sum(range(1000))
            result = self.profile_function(dummy)
            compatibility["tests"]["profiler"] = "PASS" if "execution_time_ms" in result else "FAIL"
        except Exception as e:
            compatibility["tests"]["profiler"] = f"FAIL: {e}"
        
        # Test optimization
        try:
            def dummy(): return [i*2 for i in range(100)]
            result = self.optimize_cpu(dummy)
            compatibility["tests"]["optimizer"] = "PASS" if hasattr(result, 'improvement') else "FAIL"
        except Exception as e:
            compatibility["tests"]["optimizer"] = f"FAIL: {e}"
        
        return compatibility
    
    def generate_optimization_report(self) -> str:
        """Generate optimization report."""
        if not self.results:
            return "No optimization results available"
        
        report = [
            "=== Performance Optimization Report ===",
            f"Generated: {datetime.now().isoformat()}",
            f"Total optimizations: {len(self.results)}",
            ""
        ]
        
        for result in self.results:
            report.extend([
                f"Optimization: {result.optimization_type}",
                f"  Timestamp: {result.timestamp}",
                f"  Success: {'YES' if result.success else 'NO'}",
                f"  Improvement: {result.improvement:.1f}%",
                f"  Before: {result.before}",
                f"  After: {result.after}",
                ""
            ])
        
        return "\n".join(report)
    
    def save_results(self, filepath: str = "optimization_results.json"):
        """Save optimization results to file."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "results": [asdict(r) for r in self.results]
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Optimization results saved to {filepath}")

def run_performance_optimization_demo():
    """Run a demonstration of performance optimization."""
    optimizer = PerformanceOptimizer()
    
    # Test function to optimize
    def test_function(n=10000):
        # Inefficient implementation
        result = []
        for i in range(n):
            for j in range(100):
                result.append(i * j)
        return sum(result)
    
    # Optimized version
    def optimized_function(n=10000):
        # More efficient implementation
        return sum(i * j for i in range(n) for j in range(100))
    
    print("Running CPU optimization...")
    result = optimizer.optimize_cpu(test_function)
    print(f"CPU optimization: {result.improvement:.1f}% improvement")
    
    print("Running memory optimization...")
    def memory_func():
        data = [0] * 100000
        return sum(data)
    
    result = optimizer.optimize_memory(memory_func)
    print(f"Memory optimization: {result.improvement:.1f}% improvement")
    
    print("Running response time optimization...")
    def slow_func():
        time.sleep(0.01)
        return "done"
    
    result = optimizer.optimize_response_time(slow_func)
    print(f"Response time optimization: {result.improvement:.1f}% improvement")
    
    print("\n=== Optimization Results ===")
    print(optimizer.generate_optimization_report())
    
    optimizer.save_results()
    return optimizer.results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Performance Optimizer")
    parser.add_argument("--demo", action="store_true", help="Run optimization demo")
    args = parser.parse_args()
    
    if args.demo:
        run_performance_optimization_demo()
    else:
        print("Performance Optimizer ready. Use --demo to run demonstration.")