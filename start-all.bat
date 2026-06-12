@echo off
chcp 65001 >nul
title 数据库查询审计系统

echo ================================================
echo     数据库查询审计系统 - 一键启动
echo ================================================
echo   后端 API:   http://localhost:8099
echo   前端界面:   http://localhost:3099
echo   API文档:    http://localhost:8099/docs
echo ================================================
echo.

cd /d "%~dp0"

echo [启动] 后端服务 (新窗口)...
start "后端-FastAPI-8099" cmd /k call start-backend.bat

echo [启动] 等待3秒后启动前端服务...
timeout /t 3 /nobreak >nul

echo [启动] 前端服务 (新窗口)...
start "前端-Vue-3099" cmd /k call start-frontend.bat

echo.
echo [完成] 两个服务已启动！
echo        浏览器访问: http://localhost:3099
echo.
pause
