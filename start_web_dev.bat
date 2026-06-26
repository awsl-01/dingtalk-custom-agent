@echo off
chcp 65001 >nul
echo ========================================
echo    钉钉机器人 Web 管理后台 - 开发模式
echo ========================================
echo.
echo 此脚本同时启动后端和前端开发服务器
echo.

REM 检查 Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 找不到 Node.js，请先安装 Node.js
    pause
    exit /b 1
)

REM 启动后端（后台运行）
echo [1/2] 启动后端服务器 (端口 8913)...
start "Web Backend" cmd /c "cd /d D:\claude && D:\miniconda\python.exe -m uvicorn web.app:app --host 0.0.0.0 --port 8913 --reload"

REM 安装前端依赖
echo [2/2] 启动前端开发服务器 (端口 3000)...
cd /d D:\claude\web-frontend

REM 检查是否需要安装依赖
if not exist "node_modules" (
    echo 安装前端依赖...
    npm install
)

echo.
echo ========================================
echo    后端: http://localhost:8913
echo    前端: http://localhost:3000
echo    API 文档: http://localhost:8913/docs
echo ========================================
echo.
echo 按 Ctrl+C 停止服务
echo.

npm run dev
