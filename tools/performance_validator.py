#!/usr/bin/env python3
"""
Performance Validator Tool
パフォーマンス検証ツール
"""
import json
import os
import time
import statistics
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from performance_monitor import PerformanceMonitor
from performance_optimizer import PerformanceOptimizer


class PerformanceValidator:
    """パフォーマンス検証クラス"""
    
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.optimizer = PerformanceOptimizer()
        self.validation_history = []
        self.benchmarks = {}
        self.targets = {}
    
    def validate_performance(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """パフォーマンスを検証"""
        self.monitor.start()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            raise e
        finally:
            end_time = time.time()
            self.monitor.stop()
        
        validation_result = {
            'timestamp': datetime.now().isoformat(),
            'function_name': getattr(func, '__name__', str(func)),
            'success': success,
            'execution_time': end_time - start_time,
            'result': result,
            'cpu_usage': self.monitor.get_summary().get('cpu', {}).get('avg', 0),
            'memory_usage': self.monitor.get_summary().get('memory', {}).get('avg', 0),
            'footprint': self.monitor.get_footprint()
        }
        
        self.validation_history.append(validation_result)
        return validation_result
    
    def run_benchmark(self, func: Callable, benchmark_name: str, *args, **kwargs) -> Dict[str, Any]:
        """ベンチマークテストを実行"""
        validation_result = self.validate_performance(func, *args, **kwargs)
        
        benchmark_data = {
            'name': benchmark_name,
            'timestamp': validation_result['timestamp'],
            'execution_time': validation_result['execution_time'],
            'cpu_usage': validation_result['cpu_usage'],
            'memory_usage': validation_result['memory_usage'],
            'iterations': 1
        }
        
        self.benchmarks[benchmark_name] = benchmark_data
        return benchmark_data
    
    def run_comparison_test(self, func_a: Callable, func_b: Callable, 
                          test_name: str, *args, **kwargs) -> Dict[str, Any]:
        """比較テストを実行"""
        # Func Aのテスト
        result_a = self.validate_performance(func_a, *args, **kwargs)
        
        # Func Bのテスト
        result_b = self.validate_performance(func_b, *args, **kwargs)
        
        # 比較結果
        time_improvement = ((result_a['execution_time'] - result_b['execution_time']) / 
                           result_a['execution_time'] * 100) if result_a['execution_time'] > 0 else 0
        
        comparison_result = {
            'test_name': test_name,
            'timestamp': datetime.now().isoformat(),
            'function_a': {
                'name': getattr(func_a, '__name__', str(func_a)),
                'execution_time': result_a['execution_time'],
                'cpu_usage': result_a['cpu_usage'],
                'memory_usage': result_a['memory_usage']
            },
            'function_b': {
                'name': getattr(func_b, '__name__', str(func_b)),
                'execution_time': result_b['execution_time'],
                'cpu_usage': result_b['cpu_usage'],
                'memory_usage': result_b['memory_usage']
            },
            'improvement': {
                'execution_time_percent': time_improvement,
                'faster_function': func_b.__name__ if time_improvement > 0 else func_a.__name__
            }
        }
        
        return comparison_result
    
    def run_baseline_test(self, func: Callable, baseline_name: str, *args, **kwargs) -> Dict[str, Any]:
        """基準テストを実行"""
        validation_result = self.validate_performance(func, *args, **kwargs)
        
        baseline_data = {
            'name': baseline_name,
            'timestamp': validation_result['timestamp'],
            'execution_time': validation_result['execution_time'],
            'cpu_usage': validation_result['cpu_usage'],
            'memory_usage': validation_result['memory_usage'],
            'status': 'baseline_recorded'
        }
        
        # ベースラインとして保存
        self.benchmarks[f"{baseline_name}_baseline"] = baseline_data
        
        return baseline_data
    
    def run_target_test(self, func: Callable, target_name: str, 
                       target_criteria: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        """目標テストを実行"""
        validation_result = self.validate_performance(func, *args, **kwargs)
        
        # 目標達成状況をチェック
        target_met = True
        failed_criteria = []
        
        # 実行時間目標チェック
        if 'max_execution_time' in target_criteria:
            if validation_result['execution_time'] > target_criteria['max_execution_time']:
                target_met = False
                failed_criteria.append('max_execution_time')
        
        # CPU使用率目標チェック
        if 'max_cpu_percent' in target_criteria:
            if validation_result['cpu_usage'] > target_criteria['max_cpu_percent']:
                target_met = False
                failed_criteria.append('max_cpu_percent')
        
        # メモリ使用量目標チェック
        if 'max_memory_mb' in target_criteria:
            mem_mb = validation_result['memory_usage'].get('used', 0) / (1024 * 1024)
            if mem_mb > target_criteria['max_memory_mb']:
                target_met = False
                failed_criteria.append('max_memory_mb')
        
        target_result = {
            'target_name': target_name,
            'timestamp': validation_result['timestamp'],
            'function_name': getattr(func, '__name__', str(func)),
            'target_criteria': target_criteria,
            'actual_results': {
                'execution_time': validation_result['execution_time'],
                'cpu_usage': validation_result['cpu_usage'],
                'memory_usage_mb': validation_result['memory_usage'].get('used', 0) / (1024 * 1024)
            },
            'target_met': target_met,
            'failed_criteria': failed_criteria
        }
        
        self.targets[target_name] = target_result
        return target_result
    
    def generate_report(self, report_type: str = "summary") -> str:
        """レポートを生成"""
        if report_type == "summary":
            return self._generate_summary_report()
        elif report_type == "detailed":
            return self._generate_detailed_report()
        elif report_type == "validation":
            return self._generate_validation_report()
        else:
            return self._generate_summary_report()
    
    def _generate_summary_report(self) -> str:
        """サマリーレポートを生成"""
        report = []
        report.append("=" * 60)
        report.append("パフォーマンス検証サマリーレポート")
        report.append("=" * 60)
        report.append(f"生成日時: {datetime.now().isoformat()}")
        report.append("")
        
        # 検証履歴サマリー
        if self.validation_history:
            report.append(f"総検証回数: {len(self.validation_history)}")
            successful_validations = [v for v in self.validation_history if v['success']]
            report.append(f"成功回数: {len(successful_validations)}")
            report.append(f"失敗回数: {len(self.validation_history) - len(successful_validations)}")
            
            if successful_validations:
                avg_time = statistics.mean([v['execution_time'] for v in successful_validations])
                report.append(f"平均実行時間: {avg_time:.4f}秒")
        
        # ベンチマークサマリー
        if self.benchmarks:
            report.append("")
            report.append(f"ベンチマーク数: {len(self.benchmarks)}")
            for name, benchmark in self.benchmarks.items():
                report.append(f"  - {name}: {benchmark['execution_time']:.4f}秒")
        
        # 目標達成サマリー
        if self.targets:
            report.append("")
            report.append(f"目標数: {len(self.targets)}")
            met_targets = [t for t in self.targets.values() if t['target_met']]
            report.append(f"達成目標: {len(met_targets)}")
            report.append(f"未達成目標: {len(self.targets) - len(met_targets)}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def _generate_detailed_report(self) -> str:
        """詳細レポートを生成"""
        summary = self._generate_summary_report()
        report = [summary, ""]
        
        # 詳細な検証履歴
        if self.validation_history:
            report.append("詳細な検証履歴:")
            report.append("-" * 40)
            for i, validation in enumerate(self.validation_history[-10:], 1):  # 最新10件
                report.append(f"{i}. {validation['function_name']}")
                report.append(f"   タイムスタンプ: {validation['timestamp']}")
                report.append(f"   成功: {validation['success']}")
                report.append(f"   実行時間: {validation['execution_time']:.4f}秒")
                report.append(f"   CPU使用率: {validation['cpu_usage']:.1f}%")
                report.append("")
        
        # 詳細なベンチマーク
        if self.benchmarks:
            report.append("ベンチマーク詳細:")
            report.append("-" * 40)
            for name, benchmark in self.benchmarks.items():
                report.append(f"ベンチマーク: {name}")
                report.append(f"  タイムスタンプ: {benchmark['timestamp']}")
                report.append(f"  実行時間: {benchmark['execution_time']:.4f}秒")
                report.append(f"  CPU使用率: {benchmark['cpu_usage']:.1f}%")
                report.append("")
        
        # 詳細な目標
        if self.targets:
            report.append("目標詳細:")
            report.append("-" * 40)
            for name, target in self.targets.items():
                report.append(f"目標: {name}")
                report.append(f"  タイムスタンプ: {target['timestamp']}")
                report.append(f"  達成状況: {'達成' if target['target_met'] else '未達成'}")
                if not target['target_met']:
                    report.append(f"  未達成基準: {', '.join(target['failed_criteria'])}")
                report.append("")
        
        return "\n".join(report)
    
    def _generate_validation_report(self) -> str:
        """検証レポートを生成"""
        return self._generate_detailed_report()
    
    def save_report(self, filepath: str, report_type: str = "summary"):
        """レポートをファイルに保存"""
        report = self.generate_report(report_type)
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
    
    def generate_html_report(self) -> str:
        """HTMLレポートを生成"""
        report = self._generate_detailed_report()
        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>パフォーマンス検証レポート</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #2c3e50; }}
        .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #bdc3c7; border-radius: 5px; }}
        .success {{ color: #27ae60; }}
        .failure {{ color: #e74c3c; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <h1>パフォーマンス検証レポート</h1>
    <p><strong>生成日時:</strong> {datetime.now().isoformat()}</p>
    
    <div class="summary">
        <h2>サマリー</h2>
        <div class="metric">
            <strong>総検証回数:</strong> {len(self.validation_history)}
        </div>
        <div class="metric">
            <strong>成功回数:</strong> {len([v for v in self.validation_history if v['success']])}
        </div>
        <div class="metric">
            <strong>平均実行時間:</strong> {(statistics.mean([v['execution_time'] for v in self.validation_history if v['success']]) if self.validation_history else 0):.4f}秒
        </div>
    </div>
    
    <h2>詳細レポート</h2>
    <pre>{report}</pre>
</body>
</html>
        """
        return html.strip()
    
    def save_html_report(self, filepath: str):
        """HTMLレポートをファイルに保存"""
        html_report = self.generate_html_report()
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_report)
    
    def generate_pdf_report(self) -> bytes:
        """PDFレポートを生成（簡易版：HTMLをベースに）"""
        # 実際のPDF生成にはreportlabなどのライブラリが必要だが、
        # ここではHTMLベースの簡易版を返す
        html_content = self.generate_html_report()
        return html_content.encode('utf-8')
    
    def save_pdf_report(self, filepath: str):
        """PDFレポートをファイルに保存"""
        pdf_data = self.generate_pdf_report()
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(pdf_data)
    
    def generate_excel_report(self) -> str:
        """Excelレポートを生成（CSV形式で簡易版）"""
        # 実際のExcel生成にはopenpyxlなどが必要だが、
        # ここではCSVベースの簡易版を返す
        lines = []
        lines.append("タイムスタンプ,関数名,成功,実行時間(秒),CPU使用率(%),メモリ使用量(MB)")
        
        for validation in self.validation_history:
            mem_mb = validation['memory_usage'].get('used', 0) / (1024 * 1024)
            lines.append(f"{validation['timestamp']},{validation['function_name']},{validation['success']},{validation['execution_time']:.4f},{validation['cpu_usage']:.1f},{mem_mb:.2f}")
        
        return "\n".join(lines)
    
    def save_excel_report(self, filepath: str):
        """Excelレポートをファイルに保存"""
        csv_data = self.generate_excel_report()
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(csv_data)
    
    def generate_csv_report(self) -> str:
        """CSVレポートを生成"""
        return self.generate_excel_report()  # 同じ内容
    
    def save_csv_report(self, filepath: str):
        """CSVレポートをファイルに保存"""
        self.save_excel_report(filepath)
    
    def generate_json_report(self) -> str:
        """JSONレポートを生成"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'validation_history': self.validation_history,
            'benchmarks': self.benchmarks,
            'targets': self.targets,
            'summary': {
                'total_validations': len(self.validation_history),
                'successful_validations': len([v for v in self.validation_history if v['success']]),
                'total_benchmarks': len(self.benchmarks),
                'total_targets': len(self.targets),
                'met_targets': len([t for t in self.targets.values() if t['target_met']])
            }
        }
        return json.dumps(report_data, indent=2, ensure_ascii=False)
    
    def save_json_report(self, filepath: str):
        """JSONレポートをファイルに保存"""
        json_data = self.generate_json_report()
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_data)
    
    def artifactize_report(self, format_type: str = "json") -> Dict[str, Any]:
        """レポートをアーティファクト化"""
        if format_type == "json":
            data = json.loads(self.generate_json_report())
        elif format_type == "csv":
            data = {"csv_data": self.generate_csv_report()}
        elif format_type == "html":
            data = {"html_data": self.generate_html_report()}
        else:
            data = {"report": self.generate_report()}
        
        artifact = {
            'artifact_type': 'performance_report',
            'format': format_type,
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'checksum': hash(str(data))  # 簡易チェックサム
        }
        
        return artifact
    
    def save_artifact(self, filepath: str, format_type: str = "json"):
        """アーティファクトをファイルに保存"""
        artifact = self.artifactize_report(format_type)
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        
        if format_type == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(artifact, f, indent=2, ensure_ascii=False)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(str(artifact))


def main():
    """メイン関数（テスト用）"""
    validator = PerformanceValidator()
    
    # テスト関数
    def sample_function(n):
        total = 0
        for i in range(n):
            total += i * i
        return total
    
    # パフォーマンス検証テスト
    print("Performance validation test...")
    result = validator.validate_performance(sample_function, 1000)
    print(f"Validation result: {result['success']}, Time: {result['execution_time']:.4f}s")
    
    # ベンチマークテスト
    print("\nBenchmark test...")
    benchmark = validator.run_benchmark(sample_function, "test_benchmark", 500)
    print(f"Benchmark: {benchmark['name']}, Time: {benchmark['execution_time']:.4f}s")
    
    # レポート生成
    print("\nGenerating report...")
    report = validator.generate_report()
    print("Report generated successfully")
    
    # アーティファクト化
    print("\nArtifactizing report...")
    artifact = validator.artifactize_report("json")
    print(f"Artifact created: {artifact['artifact_type']}")


if __name__ == '__main__':
    main()