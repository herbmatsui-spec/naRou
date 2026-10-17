# 詳細実装計画: テスト修正・カバレッジ80%達成・3エージェント並行実行・自動再起動監視

## 📋 概要

この計画書は、naRouプロジェクトにおける以下の課題を解決するための詳細な実装計画です：
1. **壊れたテストの修正** - 現在20件の失敗テストを修正
2. **テストカバレッジ80%以上達成** - 現在約11%から80%へ引き上げ
3. **3エージェント並行実装** - 常時3つのサブエージェントで並行作業
4. **エージェント自動監視・再起動** - エージェント停止時の自動検知と再起動

---

## 🔍 現状分析

### 失敗テスト一覧 (20件)

| # | テストファイル | 失敗テスト名 | エラー内容 | 優先度 |
|---|----------------|--------------|------------|--------|
| 1 | test_ui_fx_systems.py | test_screen_shake_lifecycle | `update()` が `True` を返さない | 高 |
| 2 | test_ui_fx_systems.py | test_cinematic_log_rendering | 文字列のスペース不一致 `' 歩いた'` vs `' 歩いた'` | 高 |
| 3 | test_ui_fx_systems.py | test_dynamic_lighting_distance_and_blend | 色値不一致 `(255,255,220)` vs `(255,255,255)` | 高 |
| 4 | test_ui_fx_systems.py | test_check_prerequisites_not_called_for_learned_tiers | リスト不一致 `[]` vs `['a']` | 高 |
| 5 | test_ui_fx_systems.py | test_render_archaeology_summary | `any()` が `False` を返す | 高 |
| 6-15 | test_ui_fx_systems.py | その他10件のUI/FXテスト | 類似のアサーション失敗 | 高 |
| 16 | test_stability.py | test_balance_simulator_execution | `0.12 == 1.0` 失敗 | 中 |
| 17 | test_stability.py | test_save_checksum_and_backup | pickle MagicMock エラー | **最高** |
| 18 | test_skill_eater_meta_intervention_integration.py | test_full_intervention_loop | `KeyError: 'expel'` | 高 |
| 19 | test_reincarnation_72_steps.py | test_all_72_steps_reincarnation_system | save 失敗 (MagicMock pickle) | **最高** |
| 20 | test_skill_eater_audio_integration.py | test_meta_override_and_reincarnation_audio | 音声ファイル `bookFlip3.ogg` 不在 | 中 |
| 21 | test_latency.py | test_latency_consistency | フレーキーなタイミングテスト | 低 |

### カバレッジ現状
- **全体カバレッジ**: 約11% (目標80%)
- **カバレッジ対象**: 85,259行中 74,187行がカバー済み、26,278行が未カバー
- **主要未カバーモジュール**: engine/, audio/, web関連, visual_fx, upgrade, validate等多数

### ログエラー
- `engine/__init__.py:47` - シャットダウンフックで `ValueError: I/O operation on closed file` が繰り返し発生

---

## 🎯 実装フェーズ

### Phase 1: 緊急修正 (Week 1) - 失敗テスト修正
### Phase 2: カバレッジ基盤構築 (Week 2) - 不足テスト追加・モック整備
### Phase 3: カバレッジ拡充 (Week 3-4) - 核心モジュールのテスト網羅
### Phase 4: 並行実行インフラ (Week 1-4 並行) - 3エージェント監視システム

---

## 📦 Phase 1: 緊急修正 - 失敗テスト修正 (優先度順)

### 1.1 save_system.py MagicMock pickle エラー修正 (最高優先度)
**影響**: test_stability.py, test_reincarnation_72_steps.py の2テスト失敗

**原因**: `save_system.py:96` で `pickle.dumps(engine)` 実行時に、エンジン内のモックオブジェクトがピクル化できない

**修正案**:
```python
# save_system.py - __getstate__/__setstate__ 実装またはモック除外
def __getstate__(self):
    state = self.__dict__.copy()
    # ピクル化できない属性を除外
    excluded = ['_mock_kernel', '_mock_web_server', '_logger']
    for key in excluded:
        state.pop(key, None)
    return state
```

**テスト修正**: テスト側で `autospec=True` または実際のオブジェクトを使用

### 1.2 test_ui_fx_systems.py 15件修正 (高優先度)
**カテゴリ別修正**:
- **ScreenShake**: `update()` が完了フラグを正しく返すよう修正
- **CinematicLog**: 日本語文字列のスペース正規化
- **DynamicLighting**: 距離減衰計算の境界値修正
- **SkillTree**: 前提条件チェックのロジック修正
- **JournalUI**: 考古学サマリーのレンダリング条件修正

### 1.3 test_skill_eater_meta_intervention_integration.py KeyError修正
**原因**: `devoured_template_counts` 辞書に 'expel' キーが存在しない
**修正**: テンプレート読み込み時に 'expel' を含める、またはテスト期待値を修正

### 1.4 test_skill_eater_audio_integration.py 音声ファイル不在
**修正**: `bookFlip3.ogg` をアセットに追加、またはテスト期待値を既存ファイルに変更

### 1.5 test_stability.py balance_simulator 修正
**修正**: シミュレーションパラメータ調整、または期待値を現実的な値に更新

### 1.6 エンジンシャットダウンログエラー修正
**原因**: ログハンドラがクローズ後に呼び出される
**修正**: `atexit` 登録順序調整、またはハンドラ存在チェック追加

---

## 📦 Phase 2: カバレッジ基盤構築

### 2.1 現在のカバレッジギャップ分析
```bash
# 詳細カバレッジレポート生成
pytest --cov --cov-report=html --cov-report=xml
# 未カバー行の特定
```

### 2.2 モック・フィクスチャ整備 (conftest.py拡充)
```python
# tests/conftest.py に追加
@pytest.fixture
def mock_engine():
    """ピクル化可能なモックエンジン"""
    
@pytest.fixture  
def real_kernel():
    """実際のカーネルインスタンス"""
    
@pytest.fixture
def isolated_save_system():
    """独立したセーブシステム"""
```

### 2.3 カバレッジ除外設定見直し
- `.coveragerc` / `pyproject.toml` の `omit` 設定確認
- 除外すべきでないファイルが除外されていないか確認

### 2.4 パラメータ化テスト導入
- 類似テストを `@pytest.mark.parametrize` で統合
- テスト数削減とカバレッジ向上の両立

---

## 📦 Phase 3: カバレッジ拡充 - モジュール別戦略

### 3.1 高優先度モジュール (カバレッジ0-10% → 80%+)

| モジュール | 現在 | 目標 | 戦略 |
|------------|------|------|------|
| `engine/` | 8-15% | 85% | Engine, GameLoop, Kernel アクセサーの網羅テスト |
| `audio/` | 0-8% | 75% | バックエンド抽象化テスト、モック音声ドライバ |
| `engine/systems/` | 0-37% | 80% | 各システム個別テスト + 統合テスト |
| `web_server.py` | 8% | 70% | HTTPエンドポイントテスト、WebSocketテスト |
| `visual_fx_system.py` | 0% | 75% | エフェクト種別ごとのパラメータ化テスト |

### 3.2 中優先度モジュール

| モジュール | 現在 | 目標 | 戦略 |
|------------|------|------|------|
| `skill_eater/` | 10-30% | 80% | フェーズ別統合テスト拡充 |
| `data/` repositories | 20-40% | 85% | CRUD操作の網羅テスト |
| `ecs/` components | 60-80% | 90% | エッジケース・シリアライズテスト追加 |

### 3.3 テスト追加の具体的アプローチ

#### A. Engine核心テスト (tests/engine/ 追加)
```python
# test_engine_core.py
class TestEngineCore:
    def test_initialization_complete_state(self)
    def test_kernel_registration_all_systems(self)
    def test_state_transitions_all_valid_paths(self)
    def test_player_entity_lifecycle(self)
    def test_dungeon_level_progression(self)
    def test_turn_advance_integration(self)
    def test_shutdown_cleanup_all_resources(self)
```

#### B. System統合テスト (tests/systems/ 新規作成)
```python
# test_combat_system.py
class TestCombatSystem:
    def test_damage_calculation_all_types(self)
    def test_status_effect_application(self)
    def test_death_handling(self)
    def test_combat_log_generation(self)

# test_render_system.py
class TestRenderSystem:
    def test_tile_rendering_all_types(self)
    def test_fov_calculation_accuracy(self)
    def test_lighting_blend_modes(self)
    def test_particle_system_integration(self)
```

#### C. Audioテスト (tests/audio/ 新規作成)
```python
# test_audio_backend.py
class TestAudioBackend:
    @pytest.mark.parametrize("backend", ["simpleaudio", "pygame", "mock"])
    def test_play_sound(self, backend)
    def test_volume_control(self)
    def test_concurrent_sounds(self)
    def test_cleanup_on_stop(self)
```

#### D. Web/APIテスト (tests/web/ 新規作成)
```python
# test_web_api.py
class TestWebAPI:
    def test_canvas_state_serialization(self)
    def test_action_endpoint_validation(self)
    def test_websocket_message_flow(self)
    def test_static_asset_serving(self)
```

---

## 📦 Phase 4: 3エージェント並行実行インフラ

### 4.1 アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator (Main)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Agent A    │  │  Agent B    │  │  Agent C    │          │
│  │ (Test Fixes)│  │ (Coverage)  │  │ (Infra/Mon) │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          ▼                                   │
│              ┌─────────────────────┐                          │
│              │  Supervisor Daemon  │  ← 常駐監視プロセス       │
│              │  - Health Check     │                          │
│              │  - Auto Restart     │                          │
│              │  - Progress Tracker │                          │
│              │  - Log Aggregation  │                          │
│              └─────────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Supervisor Daemon 設計 (`supervisor.py`)

```python
#!/usr/bin/env python3
"""
3エージェント並行実行の監視・自動再起動デーモン
"""
import asyncio
import subprocess
import json
import time
import signal
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
import logging

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
    completed_tasks: list = field(default_factory=list)
    error_log: list = field(default_factory=list)

class SupervisorDaemon:
    def __init__(self, config_file: str = "supervisor_config.json"):
        self.agents: Dict[str, AgentState] = {}
        self.config_file = Path(config_file)
        self.running = False
        self.logger = self._setup_logging()
        
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
                    "prompt_template": "Fix failing tests in {target_file}. Run pytest to verify.",
                    "working_dir": "/home/herbmatsui/narou",
                    "max_restarts": 10
                },
                {
                    "name": "agent-coverage-builder",
                    "task_type": "coverage",
                    "prompt_template": "Add tests for {target_module} to achieve 80% coverage. Focus on {focus_areas}.",
                    "working_dir": "/home/herbmatsui/narou",
                    "max_restarts": 5
                },
                {
                    "name": "agent-infra-monitor",
                    "task_type": "infra",
                    "prompt_template": "Monitor test execution, collect metrics, update progress dashboard.",
                    "working_dir": "/home/herbmatsui/narou",
                    "max_restarts": 3
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
    
    async def start_agent(self, name: str) -> bool:
        """エージェント起動"""
        state = self.agents[name]
        if state.process and state.process.poll() is None:
            self.logger.warning(f"{name} already running (PID: {state.pid})")
            return True
        
        state.status = "starting"
        state.start_time = time.time()
        
        # タスクキューから次のタスクを取得
        task = self.get_next_task(state.config.task_type)
        if not task:
            self.logger.info(f"No tasks for {name}")
            state.status = "idle"
            return False
        
        state.current_task = task
        
        # サブエージェント起動コマンド構築
        # ここでは mimo コマンドまたは python スクリプトでエージェントを起動
        cmd = [
            "mimo", "run",
            "--agent", name,
            "--task", task,
            "--prompt", state.config.prompt_template.format(target=task)
        ]
        
        try:
            state.process = subprocess.Popen(
                cmd,
                cwd=state.config.working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # プロセスグループ作成
            )
            state.pid = state.process.pid
            state.status = "running"
            self.logger.info(f"Started {name} (PID: {state.pid}) on task: {task}")
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
        if state.process.poll() is not None:
            # プロセス終了
            exit_code = state.process.returncode
            stdout, stderr = state.process.communicate()
            state.error_log.append({
                "time": datetime.now().isoformat(),
                "exit_code": exit_code,
                "stdout": stdout.decode()[-1000:] if stdout else "",
                "stderr": stderr.decode()[-1000:] if stderr else ""
            })
            return False
        
        # タイムアウト確認
        if state.start_time and (time.time() - state.start_time) > state.config.timeout:
            self.logger.warning(f"{name} timeout, terminating")
            state.process.terminate()
            try:
                state.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                state.process.kill()
            return False
        
        # ハートビートファイル確認（オプション）
        heartbeat_file = Path(f"/tmp/agent_{name}_heartbeat")
        if heartbeat_file.exists():
            mtime = heartbeat_file.stat().st_mtime
            if time.time() - mtime > state.config.health_check_interval * 2:
                self.logger.warning(f"{name} heartbeat stale")
                return False
        
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
    
    def get_next_task(self, task_type: str) -> Optional[str]:
        """タスクキューから次のタスク取得"""
        # 実装: タスクキューから該当タイプのタスクを取得
        # ここでは簡易的にタスクファイルから読む
        task_file = Path(f"tasks_{task_type}.json")
        if task_file.exists():
            with open(task_file) as f:
                tasks = json.load(f)
            for task in tasks:
                if task["status"] == "pending":
                    task["status"] = "in_progress"
                    task["assigned_to"] = name
                    task["started_at"] = datetime.now().isoformat()
                    with open(task_file, 'w') as f:
                        json.dump(tasks, f, indent=2)
                    return task["id"]
        return None
    
    def mark_task_complete(self, name: str, task_id: str, success: bool):
        """タスク完了記録"""
        task_file = Path(f"tasks_{self.agents[name].config.task_type}.json")
        if task_file.exists():
            with open(task_file) as f:
                tasks = json.load(f)
            for task in tasks:
                if task["id"] == task_id:
                    task["status"] = "done" if success else "failed"
                    task["completed_at"] = datetime.now().isoformat()
                    break
            with open(task_file, 'w') as f:
                json.dump(tasks, f, indent=2)
        
        state = self.agents[name]
        state.completed_tasks.append({
            "task_id": task_id,
            "success": success,
            "time": datetime.now().isoformat()
        })
        state.current_task = None
    
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
            "agents": {}
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
        
        with open("supervisor_dashboard.json", "w") as f:
            json.dump(dashboard, f, indent=2)
    
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
        supervisor.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### 4.3 タスクキュー設計

#### tasks_test_fix.json
```json
{
  "tasks": [
    {"id": "fix_save_pickle", "type": "test_fix", "target": "save_system.py", "tests": ["test_stability.py", "test_reincarnation_72_steps.py"], "priority": 1, "status": "pending"},
    {"id": "fix_ui_fx_15", "type": "test_fix", "target": "ui_fx_systems.py", "tests": ["test_ui_fx_systems.py"], "priority": 2, "status": "pending"},
    {"id": "fix_skill_eater_expel", "type": "test_fix", "target": "meta_intervention", "tests": ["test_skill_eater_meta_intervention_integration.py"], "priority": 3, "status": "pending"},
    {"id": "fix_audio_bookflip", "type": "test_fix", "target": "audio assets", "tests": ["test_skill_eater_audio_integration.py"], "priority": 4, "status": "pending"},
    {"id": "fix_balance_sim", "type": "test_fix", "target": "balance_simulator", "tests": ["test_stability.py"], "priority": 5, "status": "pending"},
    {"id": "fix_shutdown_log", "type": "test_fix", "target": "engine/__init__.py", "tests": ["all"], "priority": 6, "status": "pending"}
  ]
}
```

#### tasks_coverage.json
```json
{
  "tasks": [
    {"id": "cov_engine_core", "type": "coverage", "target": "engine/", "focus_areas": ["Engine", "GameLoop", "Kernel", "StateProperties"], "priority": 1, "status": "pending"},
    {"id": "cov_engine_systems", "type": "coverage", "target": "engine/systems/", "focus_areas": ["CombatSystem", "RenderSystem", "WorldSystem", "EntitySystem"], "priority": 2, "status": "pending"},
    {"id": "cov_audio", "type": "coverage", "target": "audio/", "focus_areas": ["Backend", "BGMPlayer", "WorldClockAudio", "DynamicAudio"], "priority": 3, "status": "pending"},
    {"id": "cov_web", "type": "coverage", "target": "web_server.py", "focus_areas": ["CanvasState", "WebSocket", "ActionEndpoints"], "priority": 4, "status": "pending"},
    {"id": "cov_visual_fx", "type": "coverage", "target": "visual_fx_system.py", "focus_areas": ["ScreenShake", "ParticleSystem", "Lighting"], "priority": 5, "status": "pending"},
    {"id": "cov_skill_eater", "type": "coverage", "target": "skill_eater/", "focus_areas": ["Phases", "Economy", "MetaIntervention"], "priority": 6, "status": "pending"},
    {"id": "cov_data_repos", "type": "coverage", "target": "data/repositories/", "focus_areas": ["CRUD", "SchemaValidation", "Migration"], "priority": 7, "status": "pending"}
  ]
}
```

### 4.4 エージェント起動スクリプト (`launch_agents.sh`)

```bash
#!/bin/bash
# 3エージェント並行起動スクリプト

set -e

PROJECT_DIR="/home/herbmatsui/narou"
cd "$PROJECT_DIR"

# 既存のセッション確認・クリーンアップ
echo "Cleaning up existing sessions..."
pkill -f "supervisor.py" 2>/dev/null || true
pkill -f "mimo.*agent" 2>/dev/null || true

# 仮想環境アクティベート（必要な場合）
# source venv/bin/activate

# Supervisorデーモン起動
echo "Starting supervisor daemon..."
nohup python3 supervisor.py > supervisor.log 2>&1 &
SUPERVISOR_PID=$!
echo $SUPERVISOR_PID > supervisor.pid
echo "Supervisor started (PID: $SUPERVISOR_PID)"

# 起動確認
sleep 3
if kill -0 $SUPERVISOR_PID 2>/dev/null; then
    echo "✓ Supervisor running"
else
    echo "✗ Supervisor failed to start"
    cat supervisor.log
    exit 1
fi

echo "All agents launched. Monitor with:"
echo "  tail -f supervisor.log"
echo "  cat supervisor_dashboard.json"
echo ""
echo "To stop: kill $SUPERVISOR_PID"
```

### 4.5 Systemd サービス化 (本番運用用)

```ini
# /etc/systemd/system/narou-test-agents.service
[Unit]
Description=naRou Test Agents Supervisor
After=network.target

[Service]
Type=simple
User=herbmatsui
WorkingDirectory=/home/herbmatsui/narou
ExecStart=/usr/bin/python3 /home/herbmatsui/narou/supervisor.py
Restart=always
RestartSec=10
StandardOutput=append:/home/herbmatsui/narou/supervisor.log
StandardError=append:/home/herbmatsui/narou/supervisor.log

# リソース制限
MemoryMax=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

---

## 🔧 実装手順詳細

### Step 1: 環境準備 (Day 1)
```bash
# 1. 依存関係確認
cd /home/herbmatsui/narou
pip install -e ".[dev]"

# 2. 現在のテスト実行ベースライン取得
pytest tests/ --tb=no -q --co 2>&1 | tail -5
pytest tests/ -x --tb=line 2>&1 | grep -E "(FAILED|PASSED|ERROR)" | head -30

# 3. カバレッジベースライン
pytest tests/ecs/ tests/engine/ --cov --cov-report=term 2>&1 | grep TOTAL
```

### Step 2: 失敗テスト修正 (Day 1-3)
各失敗テストに対して：
1. 失敗テストを単独実行して再現
2. 原因特定（コードリーディング、デバッグ）
3. 最小限の修正実施
4. 回帰テスト実行（関連テスト全件）

### Step 3: カバレッジ基盤 (Day 3-5)
1. `conftest.py` に共通フィクスチャ追加
2. モック戦略統一（`autospec=True` 徹底）
3. パラメータ化テスト導入
4. カバレッジ除外設定見直し

### Step 4: カバレッジ拡充 (Day 5-20)
モジュールごとに並行してテスト追加：
- Agent A: Engine核心 + Systems
- Agent B: Audio + Web + VisualFX
- Agent C: SkillEater + Data Repositories

### Step 5: 監視インフラ構築 (Day 1-2 並行)
1. `supervisor.py` 作成・テスト
2. タスクキューJSON作成
3. 起動スクリプト作成
4. ダッシュボード確認

---

## 📊 進捗管理・成功基準

### マイルストーン

| マイルストーン | 期限 | 成功基準 |
|----------------|------|----------|
| M1: 全テスト通過 | Day 3 | `pytest tests/ -x` が 0 failures |
| M2: カバレッジ40% | Day 10 | `pytest --cov` で 40%+ |
| M3: カバレッジ60% | Day 15 | `pytest --cov` で 60%+ |
| M4: カバレッジ80% | Day 20 | `pytest --cov --cov-fail-under=80` 通過 |
| M5: 監視安定稼働 | Day 5 | 3エージェントが24時間無人稼働 |

### 日次チェックリスト
- [ ] Supervisorダッシュボード確認 (`cat supervisor_dashboard.json`)
- [ ] エージェント再起動回数確認 (5回以上なら要調査)
- [ ] カバレッジ推移記録
- [ ] 失敗テスト数推移記録
- [ ] 新規バグ・リグレッションなし確認

### 週次レビュー項目
1. カバレッジ増加率（目標: 週15%+）
2. エージェント稼働率（目標: 95%+）
3. タスク完了率（目標: 80%+）
4. 技術的負債の蓄積チェック

---

## ⚠️ リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| MagicMockピクル化問題が根深い | 高 | 高 | 実オブジェクト使用へのリファクタ、または `__reduce_ex__` 実装 |
| カバレッジ80%到達に時間超過 | 高 | 中 | 除外設定見直し、生成コード除外、重要パス優先 |
| エージェント間競合（ファイルロック等） | 中 | 中 | 作業ディレクトリ分離、git worktree活用 |
| フレーキーテスト増加 | 中 | 高 | タイムアウト設定、リトライ機構、決定論的テスト設計 |
| リソース枯渇（メモリ/CPU） | 中 | 低 | cgroups制限、プロセス数監視、定期再起動 |

---

## 🚀 即座に実行すべきアクション

### 今すぐ実行（このセッション内）
1. ✅ 現状分析完了
2. 🔴 `save_system.py` のピクル化問題修正着手
3. 🔴 `test_ui_fx_systems.py` の1件目をデバッグ着手

### 次回セッション開始時
1. Supervisorデーモン実装・起動
2. タスクキュー投入
3. 3エージェント並行稼働開始

---

## 📁 成果物

1. **修正済みテストファイル** - 全20件の失敗テスト修正版
2. **新規テストファイル** - カバレッジ向上用（推定50-100ファイル追加）
3. **supervisor.py** - 監視・自動再起動デーモン
4. **supervisor_config.json** - エージェント設定
5. **tasks_*.json** - タスクキュー
6. **launch_agents.sh** - 起動スクリプト
7. **supervisor_dashboard.json** - リアルタイム進捗
8. **coverage_report.html** - 最終カバレッジレポート

---

## 📝 備考

- **並行性制御**: git worktree を使用して各エージェントを独立ブランチで作業させ、PRベースでマージ
- **コードレビュー**: 各エージェントの成果は `compose:review` スキルで品質確認
- **ロールバック**: 失敗時は `git stash` + タスク再キューイングで即座に復旧可能
- **通知**: Slack/Discord Webhook 連携で完了・異常を通知（オプション）

---

**作成日**: 2025-01-22
**作成者**: MiMoCode Compose Agent
**バージョン**: 1.0