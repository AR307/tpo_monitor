#!/bin/bash
# 服务器部署脚本

echo "========================================"
echo "TPO Monitor 服务器部署"
echo "========================================"

# 1. 创建.env文件
echo "创建.env配置文件..."
cat > /root/monitor_tpo/.env << 'EOF'
# Telegram配置 (请填写您的真实信息)
TELEGRAM_BOT_TOKEN=8583262895:AAH-VHocOxBkbMTozRDajmFW_Tlv0B39IKo
TELEGRAM_CHAT_ID=-5087018570
EOF

echo "✅ .env文件已创建"

# 2. 更新config.yaml中的Telegram配置
echo "更新config.yaml..."
sed -i 's/YOUR_BOT_TOKEN_HERE/8583262895:AAH-VHocOxBkbMTozRDajmFW_Tlv0B39IKo/g' /root/monitor_tpo/config.yaml
sed -i 's/YOUR_CHAT_ID_HERE/-5087018570/g' /root/monitor_tpo/config.yaml

echo "✅ config.yaml已更新"

# 3. 安装Python依赖
echo "安装Python依赖..."
cd /root/monitor_tpo
pip3 install -r requirements.txt

echo "✅ 依赖安装完成"

# 4. 创建日志目录
mkdir -p /root/monitor_tpo/logs

# 5. 测试运行
echo "启动监控系统..."
nohup python3 /root/monitor_tpo/main.py > /root/monitor_tpo/logs/nohup.log 2>&1 &

echo "✅ 系统已后台启动"
echo ""
echo "查看日志:"
echo "  tail -f /root/monitor_tpo/logs/nohup.log"
echo ""
echo "停止系统:"  
echo "  pkill -f main.py"
echo ""
echo "========================================"
echo "部署完成！"
echo "========================================"
