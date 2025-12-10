@echo off
chcp 65001 > nul
cls
echo ============================================================
echo TPO + VWAP + OrderFlow 交易信号系统
echo Trading Signal System
echo ============================================================
echo.
echo 启动中... Starting...
echo.

cd /d "%~dp0"
.venv\Scripts\python.exe main.py

echo.
echo 系统已停止 System stopped
pause
