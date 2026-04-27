#!/bin/bash
# DrugMind 部署脚本
set -e

PORT=${1:-8096}
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "🧠 DrugMind v1.0 部署"
echo "========================"

# 安装依赖
echo "📦 安装依赖..."
pip3 install -q fastapi uvicorn rdkit-pypi 2>/dev/null || true

# 杀旧进程
pkill -f "uvicorn.*drugmind" 2>/dev/null || true
sleep 1

# 启动
echo "🚀 启动 DrugMind API (端口: $PORT)..."
cd "$DIR"
export MIMO_BASE_URL="https://api.xiaomimimo.com/v1"
export MIMO_API_KEY="${MIMO_API_KEY:-}"
export MIMO_MODEL="mimo-v2-pro"

nohup python3 -m uvicorn api.api:app --host 0.0.0.0 --port "$PORT" --log-level info > drugmind.log 2>&1 &
echo $! > drugmind.pid

sleep 2

# 验证
if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
    echo "✅ DrugMind 启动成功!"
    echo "   🌐 界面: http://0.0.0.0:$PORT"
    echo "   📚 API文档: http://0.0.0.0:$PORT/docs"
    echo "   📋 PID: $(cat drugmind.pid)"
else
    echo "❌ 启动失败，请查看 drugmind.log"
    tail -5 drugmind.log
    exit 1
fi
