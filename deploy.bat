@echo off
chcp 65001 >nul
echo ================================
echo TPO Monitor 部署脚本
echo ================================
echo.

set SERVER=root@47.250.142.117
set REMOTE_PATH=/root/monitor_tpo

echo [1/3] 准备上传文件到服务器...
echo 服务器: %SERVER%
echo 远程路径: %REMOTE_PATH%
echo.

REM 使用 SCP 上传文件（排除不必要的文件）
echo [2/3] 上传 Python 代码文件...
scp *.py %SERVER%:%REMOTE_PATH%/

echo.
echo [2/3] 上传配置文件...
scp config.yaml %SERVER%:%REMOTE_PATH%/
scp requirements.txt %SERVER%:%REMOTE_PATH%/
scp .env.example %SERVER%:%REMOTE_PATH%/

echo.
echo [3/3] 上传文档文件...
scp *.md %SERVER%:%REMOTE_PATH%/

echo.
echo ================================
echo ✅ 上传完成！
echo ================================
echo.
echo 下一步操作：
echo 1. SSH 登录服务器: ssh %SERVER%
echo 2. 进入目录: cd %REMOTE_PATH%
echo 3. 安装依赖: pip3 install -r requirements.txt
echo 4. 配置环境: cp .env.example .env ^&^& nano .env
echo 5. 运行程序: python3 main.py
echo.
pause
