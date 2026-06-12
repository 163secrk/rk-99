@echo off
chcp 65001 >nul
echo ========================================
echo   数据库查询审计系统 - 启动前端服务
echo   服务地址: http://localhost:3099
echo ========================================
echo.

cd /d "%~dp0frontend"

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到Node.js，请先安装Node.js 16+
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo [信息] 安装前端依赖...
    call npm install
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [信息] 启动Vue开发服务器 (端口: 3099)...
call npm run dev
pause
