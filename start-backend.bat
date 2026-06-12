@echo off
chcp 65001 >nul
echo ========================================
echo   数据库查询审计系统 - 启动后端服务
echo   服务地址: http://localhost:8099
echo ========================================
echo.

cd /d "%~dp0backend"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

if not exist "venv" (
    echo [信息] 创建虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
)

echo [信息] 激活虚拟环境...
call venv\Scripts\activate.bat

if not exist "venv\Lib\site-packages\fastapi" (
    echo [信息] 安装后端依赖...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [信息] 启动FastAPI服务 (端口: 8099)...
python main.py
pause
