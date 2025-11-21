#!/bin/bash

echo "=========================================="
echo "智能电网规划系统 - 启动脚本"
echo "=========================================="

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3"
    exit 1
fi

echo "✓ Python3 已安装"

# 检查是否在正确的目录
if [ ! -d "backend" ]; then
    echo "错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 安装依赖
echo ""
echo "检查并安装依赖..."
cd backend

if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

echo "激活虚拟环境..."
source venv/bin/activate

echo "安装Python依赖..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "启动后端服务..."
echo "=========================================="

python app.py &
BACKEND_PID=$!

echo "后端服务进程ID: $BACKEND_PID"

# 等待后端启动
sleep 3

echo ""
echo "=========================================="
echo "系统启动完成!"
echo "=========================================="
echo ""
echo "后端服务: http://localhost:5001"
echo "前端界面: 请在浏览器中打开 frontend/index.html"
echo ""
echo "或使用以下命令启动前端服务器:"
echo "  cd frontend"
echo "  python3 -m http.server 8080"
echo "  然后访问 http://localhost:8080"
echo ""
echo "按 Ctrl+C 停止后端服务"
echo ""

# 等待中断信号
trap "echo ''; echo '停止服务...'; kill $BACKEND_PID; exit" INT

wait $BACKEND_PID
