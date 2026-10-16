#!/usr/bin/env python3
"""
3エージェント並行実行の監視・自動再起動デーモン
"""
import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class AgentConfig:
    name: str
    task_type: str  # "test_fix", "coverage", "infra"
    prompt_template: str
    working_dir: str
    max_restarts: int = 5
    restart_delay: float = 10.0
    health_check_interval: float = 30.0
    timeout: float = 3600.0  # 1時間でタイムアウト

@dataclass
class AgentState:
    config: AgentConfig
    process: Optional[subprocess.Popen] = None
    pid: Optional[int] = None
    start_time: Optional[float] = None
    restart_count: int = 0
    last_health_check: Optional[float] = None
    status: str = "stopped"  # stopped, starting, running, unhealthy, restarting
    current_task: Optional[str] = None
    completed_tasks: List[dict] = field(default_factory=list)
    error_log: List[dict] = field(default_factory=list)

class SupervisorDaemon:
    def __init__(self, config_file: str = "supervisor_config.json"):
        self.agents: Dict[str, AgentState] = {}
        self.config_file = Path(config_file)
        self.running = False
        self.logger = self._setup_logging()
        self.task_queues: Dict[str, List[dict]] = {}

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('supervisor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger(__name__)

    def load_config(self):
        """エージェント設定読み込み"""
        default_config = {
            "agents": [
                {
                    "name": "agent-test-fixer",
                    "task_type": "test_fix",
                    "prompt_template": "Fix failing tests in {target}. Run pytest to verify the fix.",
                    "working_dir": "/home/herbmatsui/narou",
                    "max_restarts": 10,
                    "health_check_interval": 300.0  # 5 minutes
                },
                {
                    "name": "agent-coverage-builder",
                    "task_type": "coverage",
                    "prompt_template": "Add tests for {target} to improve coverage. Focus on {focus_areas}.",
                    "working_dir": "/home/herbmatsui/narou",
                    "max_restarts": 5,
                    "health_check_interval": 300.0  # 5 minutes
                },
                {
                    "name": "agent-infra-monitor",
                    "task_type": "infra",
                    "prompt_template": "Monitor test execution and update progress dashboard for {target}.",
                    "working_dir": "/home/herbmatsui/narou",
                    "max_restarts": 3,
                    "health_check_interval": 300.0  # 5 minutes
                }
            ]
        }

        if self.config_file.exists():
            with open(self.config_file) as f:
                config = json.load(f)
        else:
            config = default_config
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

        for agent_cfg in config["agents"]:
            self.agents[agent_cfg["name"]] = AgentState(
                config=AgentConfig(**agent_cfg)
            )

        # Initialize task queues
        self.initialize_task_queues()

    def initialize_task_queues(self):
        """タスクキュー初期化"""
        # Test fix tasks
        self.task_queues["test_fix"] = [
            {"id": "fix_save_pickle", "target": "save_system.py", "focus_areas": ["MagicMock pickle error"], "status": "pending"},
            {"id": "fix_ui_fx_15", "target": "ui_fx_systems.py", "focus_areas": ["ScreenShake lifecycle", "CinematicLog spacing", "DynamicLighting color", "SkillTree prerequisites", "JournalUI archaeology"], "status": "pending"},
            {"id": "fix_skill_eater_expel", "target": "skill_eater_meta_intervention", "focus_areas": ["expel template missing"], "status": "pending"},
            {"id": "fix_audio_bookflip", "target": "skill_eater_audio_integration", "focus_areas": ["bookFlip3.ogg missing"], "status": "pending"},
            {"id": "fix_balance_sim", "target": "stability.py::test_balance_simulator_execution", "focus_areas": ["balance simulation parameters"], "status": "pending"},
            {"id": "fix_shutdown_log", "target": "engine/__init__.py", "focus_areas": ["shutdown hook logging error"], "status": "pending"}
        ]

        # Coverage tasks
        self.task_queues["coverage"] = [
            {"id": "cov_engine_core", "target": "engine/", "focus_areas": ["Engine", "GameLoop", "Kernel", "StateProperties"], "status": "pending"},
            {"id": "cov_engine_systems", "target": "engine/systems/", "focus_areas": ["CombatSystem", "RenderSystem", "WorldSystem", "EntitySystem"], "status": "pending"},
            {"id": "cov_audio", "target": "audio/", "focus_areas": ["Backend", "BGMPlayer", "WorldClockAudio", "DynamicAudio"], "status": "pending"},
            {"id": "cov_web", "target": "web_server.py", "focus_areas": ["CanvasState", "WebSocket", "ActionEndpoints"], "status": "pending"},
            {"id": "cov_visual_fx", "target": "visual_fx_system.py", "focus_areas": ["ScreenShake", "ParticleSystem", "Lighting"], "status": "pending"},
            {"id": "cov_skill_eater", "target": "skill_eater/", "focus_areas": ["Phases", "Economy", "MetaIntervention"], "status": "pending"},
            {"id": "cov_data_repos", "target": "data/repositories/", "focus_areas": ["CRUD", "SchemaValidation", "Migration"], "status": "pending"}
        ]

        # Infra tasks
        self.task_queues["infra"] = [
            {"id": "infra_dashboard", "target": "progress_dashboard", "focus_areas": ["update dashboard with metrics"], "status": "pending"},
            {"id": "infra_metrics", "target": "coverage_metrics", "focus_areas": ["collect and track coverage metrics"], "status": "pending"},
            {"id": "infra_health", "target": "system_health", "focus_areas": ["monitor system health and logs"], "status": "pending"}
        ]

    async def start_agent(self, name: str) -> bool:
        """エージェント起動"""
        state = self.agents[name]
        if state.process and state.process.poll() is None:
            self.logger.warning(f"{name} already running (PID: {state.pid})")
            return True

        state.status = "starting"
        state.start_time = time.time()

        # タスクキューから次のタスクを取得
        task = self.get_next_task(state.config.task_type, name)
        if not task:
            self.logger.info(f"No tasks for {name}")
            state.status = "idle"
            return False

        state.current_task = task["id"]

        # サブエージェント起動コマンド構築
        # mimoコマンドを使用してサブエージェントを起動
        # 標準入力からプロンプトを提供する
        prompt_text = state.config.prompt_template.format(
            target=task["target"],
            focus_areas=", ".join(task["focus_areas"]) if isinstance(task["focus_areas"], list) else task["focus_areas"]
        ) + f"\n\nTASK ID: {task['id']}\nTASK TARGET: {task['target']}\nFOCUS AREAS: {task['focus_areas']}"

        cmd = [
            "mimo", "run",
            "--subagent-type", "general"
        ]

        try:
            state.process = subprocess.Popen(
                cmd,
                cwd=state.config.working_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # プロセスグループ作成
            )
            # プロンプトを標準入力に送信
            if state.process.stdin:
                state.process.stdin.write(prompt_text.encode('utf-8'))
                state.process.stdin.close()
            state.pid = state.process.pid
            state.status = "running"
            self.logger.info(f"Started {name} (PID: {state.pid}) on task: {task['id']} - {task['target']}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start {name}: {e}")
            state.status = "failed"
            return False

    async def health_check(self, name: str) -> bool:
        """エージェント健全性チェック"""
        state = self.agents[name]

        if not state.process:
            return False

        # プロセス存在確認
        poll_result = state.process.poll()
        if poll_result is not None:
            # プロセス終了
            exit_code = poll_result
            try:
                # Try to communicate, but handle case where stdin might be closed
                stdout, stderr = state.process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                stdout, stderr = b"", b"Process terminated during communicate"
                try:
                    state.process.kill()
                except:
                    pass
            except ValueError:
                # Handle case where stdin is already closed
                # Try to get output without communicating
                try:
                    stdout, stderr = state.process.communicate(timeout=5)
                except:
                    stdout, stderr = b"", b""

            state.error_log.append({
                "time": datetime.now().isoformat(),
                "exit_code": exit_code,
                "stdout": stdout.decode('utf-8', errors='replace')[-1000:] if stdout else "",
                "stderr": stderr.decode('utf-8', errors='replace')[-1000:] if stderr else ""
            })

            # タスクを完了としてマーク
            if state.current_task:
                success = exit_code == 0
                self.mark_task_complete(name, state.current_task, success)
                state.current_task = None

            return False

        # タイムアウト確認
        if state.start_time and (time.time() - state.start_time) > state.config.timeout:
            self.logger.warning(f"{name} timeout, terminating")
            try:
                state.process.terminate()
                state.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    state.process.kill()
                except:
                    pass
            return False

        # ハートビートファイル確認（オプション）
        heartbeat_file = Path(f"/tmp/agent_{name}_heartbeat")
        if heartbeat_file.exists():
            mtime = heartbeat_file.stat().st_mtime
            if time.time() - mtime > state.config.health_check_interval * 2:
                self.logger.warning(f"{name} heartbeat stale")
                # Still return True to allow graceful completion

        state.last_health_check = time.time()
        return True

    async def restart_agent(self, name: str):
        """エージェント再起動"""
        state = self.agents[name]

        if state.restart_count >= state.config.max_restarts:
            self.logger.error(f"{name} exceeded max restarts ({state.config.max_restarts})")
            state.status = "dead"
            return

        state.status = "restarting"
        state.restart_count += 1

        # 古いプロセス確実に終了
        if state.process:
            state.process.terminate()
            try:
                state.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                state.process.kill()

        await asyncio.sleep(state.config.restart_delay)
        await self.start_agent(name)

    def get_next_task(self, task_type: str, agent_name: str) -> Optional[dict]:
        """タスクキューから次のタスク取得"""
        if task_type not in self.task_queues:
            return None

        queue = self.task_queues[task_type]
        for task in queue:
            if task["status"] == "pending":
                task["status"] = "in_progress"
                task["assigned_to"] = agent_name
                task["started_at"] = datetime.now().isoformat()
                return task
        return None

    def mark_task_complete(self, name: str, task_id: str, success: bool):
        """タスク完了記録"""
        # Update task queues
        for task_type, queue in self.task_queues.items():
            for task in queue:
                if task["id"] == task_id:
                    task["status"] = "done" if success else "failed"
                    task["completed_at"] = datetime.now().isoformat()
                    task["result"] = "success" if success else "failure"
                    break

        state = self.agents[name]
        state.completed_tasks.append({
            "task_id": task_id,
            "success": success,
            "time": datetime.now().isoformat()
        })
        state.current_task = None

        self.logger.info(f"Task {task_id} marked as {'success' if success else 'failure'} for {name}")

    async def monitor_loop(self):
        """メイン監視ループ"""
        self.logger.info("Supervisor daemon started")
        self.running = True

        # 初期起動
        for name in self.agents:
            await self.start_agent(name)

        while self.running:
            for name in list(self.agents.keys()):
                state = self.agents[name]

                if state.status in ("running", "starting"):
                    healthy = await self.health_check(name)
                    if not healthy:
                        self.logger.warning(f"{name} unhealthy, restarting...")
                        await self.restart_agent(name)

                elif state.status == "idle":
                    # 新しいタスクがあれば起動
                    await self.start_agent(name)

                elif state.status == "dead":
                    self.logger.error(f"{name} is dead, manual intervention required")

            # 進捗ダッシュボード更新
            self.update_dashboard()

            await asyncio.sleep(10)  # 10秒間隔でチェック

    def update_dashboard(self):
        """進捗ダッシュボード更新"""
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "task_queues": {},
            "summary": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "in_progress_tasks": 0,
                "pending_tasks": 0
            }
        }

        for name, state in self.agents.items():
            dashboard["agents"][name] = {
                "status": state.status,
                "pid": state.pid,
                "uptime": time.time() - state.start_time if state.start_time else 0,
                "restart_count": state.restart_count,
                "current_task": state.current_task,
                "completed_count": len(state.completed_tasks),
                "last_health_check": state.last_health_check
            }

        # Task queue status
        for task_type, queue in self.task_queues.items():
            dashboard["task_queues"][task_type] = []
            for task in queue:
                dashboard["task_queues"][task_type].append({
                    "id": task["id"],
                    "target": task["target"],
                    "status": task["status"],
                    "assigned_to": task.get("assigned_to"),
                    "started_at": task.get("started_at"),
                    "completed_at": task.get("completed_at")
                })

                # Update summary counts
                dashboard["summary"]["total_tasks"] += 1
                if task["status"] == "done":
                    dashboard["summary"]["completed_tasks"] += 1
                elif task["status"] == "failed":
                    dashboard["summary"]["failed_tasks"] += 1
                elif task["status"] == "in_progress":
                    dashboard["summary"]["in_progress_tasks"] += 1
                elif task["status"] == "pending":
                    dashboard["summary"]["pending_tasks"] += 1

        with open("supervisor_dashboard.json", "w") as f:
            json.dump(dashboard, f, indent=2)

        # Also create a simple text summary for quick viewing
        self.update_text_dashboard(dashboard)

    def update_text_dashboard(self, dashboard: dict):
        """テキスト版ダッシュボード更新"""
        lines = [
            "=== naRogue Test Agents Dashboard ===",
            f"Last updated: {dashboard['timestamp']}",
            "",
            "Agent Status:",
        ]

        for name, info in dashboard["agents"].items():
            status_emoji = {
                "running": "🟢",
                "starting": "🟡",
                "idle": "⚪",
                "stopped": "⚫",
                "unhealthy": "🔴",
                "restarting": "🟠",
                "failed": "❌",
                "dead": "☠️"
            }.get(info["status"], "⚪")

            lines.append(
                f"  {status_emoji} {name}: {info['status']} "
                f"(PID: {info['pid'] or 'N/A'}, "
                f"Uptime: {info['uptime']:.0f}s, "
                f"Restarts: {info['restart_count']})"
            )

            if info['current_task']:
                lines.append(f"    Current task: {info['current_task']}")

        lines.extend([
            "",
            "Task Summary:",
            f"  Total: {dashboard['summary']['total_tasks']}",
            f"  Completed: {dashboard['summary']['completed_tasks']} ✅",
            f"  Failed: {dashboard['summary']['failed_tasks']} ❌",
            f"  In Progress: {dashboard['summary']['in_progress_tasks']} 🔄",
            f"  Pending: {dashboard['summary']['pending_tasks']} ⏳",
            "",
            "Recent Activity:"
        ])

        # Add recent completions
        recent_completions = []
        for name, info in dashboard["agents"].items():
            for task in info.get("completed_tasks", [])[-3:]:  # Last 3 per agent
                recent_completions.append({
                    "agent": name,
                    "task": task["task_id"],
                    "success": task["success"],
                    "time": task["time"]
                })

        # Sort by time descending
        recent_completions.sort(key=lambda x: x["time"], reverse=True)

        for item in recent_completions[:5]:  # Show top 5
            status = "✅" if item["success"] else "❌"
            lines.append(f"  {status} {item['agent']}: {item['task']} ({item['time'][:19]})")

        with open("supervisor_dashboard.txt", "w") as f:
            f.write("\n".join(lines))

    def shutdown(self):
        """全エージェント停止"""
        self.logger.info("Shutting down supervisor...")
        self.running = False
        for name, state in self.agents.items():
            if state.process and state.process.poll() is None:
                state.process.terminate()
                try:
                    state.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    state.process.kill()
                    self.logger.warning(f"Killed {name} (PID: {state.pid})")
        self.logger.info("All agents stopped")

async def main():
    supervisor = SupervisorDaemon()
    supervisor.load_config()

    # シグナルハンドラ
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, supervisor.shutdown)

    try:
        await supervisor.monitor_loop()
    except KeyboardInterrupt:
        supervisor.logger.info("Received keyboard interrupt")
        supervisor.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
