# 本地部署到服务器完整流程

## ✅ 本地测试结果

**Data Feed**: 200+笔交易成功接收，Delta/CVD正常变化

## 📦 部署步骤

### 1. 在本地PowerShell执行

```powershell
# 压缩所有Python文件
cd d:\files\crypto\monitor_tpo

# 上传核心文件
scp *.py *.yaml *.txt root@47.250.142.117:/root/monitor_tpo/

# 或使用tar打包上传
tar -czf monitor_tpo.tar.gz *.py *.yaml *.txt *.md
scp monitor_tpo.tar.gz root@47.250.142.117:/root/

# 在服务器解压
ssh root@47.250.142.117
cd /root
tar -xzf monitor_tpo.tar.gz -C monitor_tpo/
```

### 2. 在SSH服务器执行

```bash
cd /root/monitor_tpo

# 配置Telegram
sed -i 's/YOUR_BOT_TOKEN_HERE/8583262895:AAH-VHocOxBkbMTozRDajmFW_Tlv0B39IKo/g' config.yaml
sed -i 's/YOUR_CHAT_ID_HERE/-5087018570/g' config.yaml

# 安装依赖（如果需要）
pip3 install -r requirements-server.txt

# 启动
nohup python3 main.py > logs/monitor.log 2>&1 &

# 查看日志
tail -f logs/monitor.log
```

## ⚠️ 关键修复

### 已修复的问题
1. ✅ 移除binance.client依赖
2. ✅ Data Feed使用requests直接调用API  
3. ✅ 信号阈值降低到0.5
4. ✅ Telegram格式修复（换行和时间戳）

### 预期结果
- ✅ 无import错误
- ✅ WebSocket正常连接
- ✅ Delta/CVD有数值变化
- ✅ Telegram推送成功
- ✅ 每天5-10个信号

## 📝 验证清单

启动后30秒内检查:
- [ ] `✅ WebSocket已连接 BTCUSDT`
- [ ] `✅ WebSocket已连接 ETHUSDT`
- [ ] `Bar finalized. CVD: XX.XX` (不是0)
- [ ] Telegram收到"系统现已上线 LIVE"
- [ ] 没有ERROR日志

如果CVD还是0:
```bash
grep "处理交易" logs/monitor.log
```
应该能看到大量"处理交易"日志。
