@echo off
echo ==========================================
echo 智能电网规划系统 - 启动脚本
echo ==========================================

REM 检查Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 未找到Python
    pause
    exit /b 1
)

echo √ Python 已安装

REM 检查目录
if not exist "backend" (
    echo 错误: 请在项目根目录运行此脚本
    pause
    exit /b 1
)

REM 安装依赖
echo.
echo 检查并安装依赖...
cd backend

if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

echo 激活虚拟环境...
call venv\Scripts\activate.bat

echo 安装Python依赖...
pip install -r requirements.txt

echo.
echo ==========================================
echo 启动后端服务...
echo ==========================================

start "Grid Planning Backend" python app.py

timeout /t 3 /nobreak >nul

echo.
echo ==========================================
echo 系统启动完成!
echo ==========================================
echo.
echo 后端服务: http://localhost:5000
echo 前端界面: 请在浏览器中打开 frontend\index.html
echo.
echo 或使用以下命令启动前端服务器:
echo   cd frontend
echo   python -m http.server 8080
echo   然后访问 http://localhost:8080
echo.
echo 按任意键退出...
pause >nul
