@echo off
chcp 65001  nul
title 一键启动Dify后端服务

echo ==================================================
echo.
echo      🚀 正在启动 Dify 后端服务...
echo.
echo ==================================================

echo.
echo [12] 正在后台启动 Python API 服务器 (dify_worker.py)...
REM 使用 start 命令在新的、最小化的窗口中运行Python服务器
start Python Worker min python dify_worker.py

echo.
echo [22] 正在启动 ngrok 隧道...
echo.
echo      一个新的 ngrok 窗口将会弹出。
echo      请从该窗口中复制以 'https' 开头的地址，
echo      并将其粘贴到 Dify 工作流的 HTTP 请求节点中。
echo.

timeout t 5  nul

REM 在一个新窗口中启动 ngrok，这个窗口会保持打开状态供您复制地址
start Ngrok Tunnel ngrok http 5000

echo.
echo ==================================================
echo.
echo      ✅ 所有服务已启动！
echo.
echo      请确保 Python Worker 和 Ngrok Tunnel
echo      这两个窗口在您使用期间保持运行。
echo.
echo      您可以关闭当前这个窗口。
echo.
echo ==================================================

pause
