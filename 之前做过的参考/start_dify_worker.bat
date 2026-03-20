@echo off
chcp 65001 > nul
title Dify工作流后端API服务

echo ================================
echo   Dify工作流后端API服务
echo ================================
echo.

echo 正在启动API服务...
echo 服务地址: http://localhost:5000
echo 健康检查: http://localhost:5000/health
echo.

echo 请确保已安装Flask:
echo pip install flask
echo.

echo 按任意键启动服务...
pause > nul

python dify_worker.py

echo.
echo 服务已停止
pause 