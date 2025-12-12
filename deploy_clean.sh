#!/bin/bash
# 服务器完整部署脚本

echo "=========================================="
echo "TPO Monitor 完整部署"
echo "=========================================="

# 1. 停止所有Python进程
echo "[1/6] 停止现有进程..."
pkill -f python3
sleep 2

# 2. 备份旧代码
echo "[2/6] 备份旧代码..."
if [ -d "/root/monitor_tpo_backup" ]; then
    rm -rf /root/monitor_tpo_backup
fi
if [ -d "/root/monitor_tpo" ]; then
    mv /root/monitor_tpo /root/monitor_tpo_backup
fi

# 3. 创建新目录
echo "[3/6] 创建新目录..."
mkdir -p /root/monitor_tpo
mkdir -p /root/monitor_tpo/logs

# 4. 等待文件上传
echo "[4/6] 等待文件上传..."
echo "请在本地执行scp上传命令..."

# 5. 配置Telegram
echo "[5/6] 配置Telegram..."
cd /root/monitor_tpo
sed -i 's/YOUR_BOT_TOKEN_HERE/8583262895:AAH-VHocOxBkbMTozRDajmFW_Tlv0B39IKo/g' config.yaml
sed -i 's/YOUR_CHAT_ID_HERE/-5087018570/g' config.yaml

# 6. 安装依赖并启动
echo "[6/6] 安装依赖..."
pip3 install -r requirements-server.txt

echo ""
echo "✅ 部署准备完成！"
echo ""
echo "启动系统:"
echo "  cd /root/monitor_tpo"
echo "  nohup python3 main.py > logs/monitor.log 2>&1 &"
echo ""
echo "查看日志:"
echo "  tail -f /root/monitor_tpo/logs/monitor.log"
echo ""
echo "=========================================="
