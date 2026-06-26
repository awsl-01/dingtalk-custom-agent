@echo off
chcp 65001 >nul
echo ========================================
echo    钉钉机器人 Web 管理后台
echo ========================================
echo.

REM 切换到项目目录
cd /d D:\claude

REM 检查 Python 环境
echo [1/3] 检查 Python 环境...
D:\miniconda\python.exe --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 找不到 Python
    pause
    exit /b 1
)
echo Python 环境正常

REM 安装依赖
echo.
echo [2/3] 检查依赖...
D:\miniconda\python.exe -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo 安装 Web 依赖...
    D:\miniconda\python.exe -m pip install -r web/requirements.txt -q
)
echo 依赖检查完成

REM 启动服务
echo.
echo [3/3] 启动 Web 服务器...
echo.
echo ========================================
echo    服务地址: http://localhost:8913
echo    API 文档: http://localhost:8913/docs
echo ========================================
echo.
echo 按 Ctrl+C 停止服务
echo.

D:\miniconda\python.exe -m uvicorn web.app:app --host 0.0.0.0 --port 8913 --reload
