#!/bin/bash
# 3エージェント並行起動スクリプト

set -e

PROJECT_DIR="/home/herbmatsui/narou"
cd "$PROJECT_DIR"

# 既存のセッション確認・クリーンアップ
echo "Cleaning up existing sessions..."
pkill -f "supervisor.py" 2>/dev/null || true
pkill -f "mimo.*general" 2>/dev/null || true
pkill -f "mimo.*explore" 2>/dev/null || true

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

echo ""
echo "All agents launched. Monitor with:"
echo "  tail -f supervisor.log"
echo "  cat supervisor_dashboard.json"
echo "  cat supervisor_dashboard.txt"
echo ""
echo "To stop: kill $SUPERVISOR_PID"
echo ""
echo "Initial tasks loaded:"
echo "  Test Fixes: 6 tasks"
echo "  Coverage: 7 tasks" 
echo "  Infra: 3 tasks"
echo ""
echo "Agents will automatically pick up tasks and report progress."