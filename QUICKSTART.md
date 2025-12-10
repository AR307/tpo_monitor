# 快速启动指南 | Quick Start Guide

## 🚀 5分钟启动系统

### 第一步:安装依赖

```bash
pip install -r requirements.txt
```

### 第二步:测试系统

```bash
python test_system.py
```

预期输出:
```
✓ Configuration loaded
✓ Data models working
✓ Analyzers initialized
Total: 5/5 tests passed
🎉 All tests passed!
```

### 第三步:配置交易对

编辑 `config.yaml`:

```yaml
exchange:
  symbols:
    - "BTCUSDT"    # 比特币
    - "ETHUSDT"    # 以太坊
```

### 第四步:启动系统

```bash
python main.py
```

系统将:
1. 加载配置
2. 连接币安 WebSocket
3. 预热历史数据(100根K线)
4. 开始实时监控

### 预期输出

```
============================================================
            TPO + VWAP + Order Flow Trading System
============================================================
Status: Initializing...
Time: 2025-12-10 21:48:28 UTC
============================================================

[INFO] DataFeed initialized for BTCUSDT
[INFO] TPOAnalyzer initialized for BTCUSDT
[INFO] VWAPCalculator initialized for BTCUSDT
[INFO] OrderFlowAnalyzer initialized for BTCUSDT
[INFO] SignalEngine initialized for BTCUSDT
[INFO] Warming up with historical data...
[INFO] Warmed up BTCUSDT with 100 bars
[INFO] ✓ Trading System is now LIVE

... waiting for signals ...
```

---

## 📊 信号示例

当检测到交易机会时,将看到:

```
============================================================
🚀  LONG_ENTRY SIGNAL DETECTED  🚀
============================================================
Symbol:     BTCUSDT
Time:       2025-12-10 14:23:15
Price:      $42,350.00
Confidence: 85%

Conditions:
  TPO Event:        VAL_BOUNCE
  VWAP Aligned:     True
  Delta Confirmed:  True
  CVD Confirmed:    True
  OI Confirmed:     True

Context:
  VAH: $42,800  |  POC: $42,200  |  VAL: $41,600
  VWAP: $42,300
  Delta: 1,250  |  CVD: 15,800
  OI Change: +2.5%
============================================================
```

---

## ⚙️ 常用配置调整

### 提高信号质量(减少假信号)

```yaml
signals:
  long:
    min_confidence: 0.85  # 默认 0.7
  short:
    min_confidence: 0.85
```

### 调整信号频率

```yaml
signals:
  cooldown_seconds: 600  # 10分钟冷却(默认5分钟)
```

### 启用 Telegram 报警

```yaml
alerts:
  telegram:
    bot_token: "YOUR_BOT_TOKEN"      # 从 @BotFather 获取
    chat_id: "YOUR_CHAT_ID"          # 从消息记录获取
  channels:
    telegram: true
```

获取 `chat_id`:
1. 向机器人发送一条消息
2. 访问: `https://api.telegram.org/bot8583262895:AAH-VHocOxBkbMTozRDajmFW_Tlv0B39IKo/getUpdates`
3. 找到 `"chat":{"id":123456789}` 中的数字

---

## 🔧 常见问题

### Q: 系统启动报错?

**A**: 检查依赖安装
```bash
pip install --upgrade -r requirements.txt
```

### Q: 没有收到信号?

**A**: 可能市场条件不满足,调低置信度阈值:
```yaml
signals:
  long:
    min_confidence: 0.5  # 更宽松的条件
```

### Q: 如何查看详细日志?

**A**: 启用 DEBUG 级别:
```yaml
logging:
  level: "DEBUG"
```

然后查看日志:
```bash
tail -f logs/system.log
```

### Q: WebSocket 连接失败?

**A**: 检查:
1. 网络连接
2. 币安 API 状态: https://www.binance.com/en/support/announcement
3. 防火墙设置

---

## 📱 添加报警渠道

### Telegram

1. 创建机器人:
   - 找 @BotFather
   - 发送 `/newbot`
   - 获取 token

2. 获取 chat_id:
   - 向机器人发消息
   - 访问: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - 复制 chat.id

3. 更新配置:
   ```yaml
   alerts:
     telegram:
       bot_token: "YOUR_TOKEN"
       chat_id: "YOUR_CHAT_ID"
     channels:
       telegram: true
   ```

### Discord

1. 创建 Webhook:
   - 服务器设置 → 整合 → Webhook
   - 复制 Webhook URL

2. 更新配置:
   ```yaml
   alerts:
     discord:
       webhook_url: "YOUR_WEBHOOK_URL"
     channels:
       discord: true
   ```

### 自定义 Webhook

```yaml
alerts:
  webhook:
    url: "https://your-server.com/webhook"
    timeout_seconds: 5
  channels:
    webhook: true
```

接收的 JSON 格式:
```json
{
  "timestamp": "2025-12-10T14:23:15",
  "signal_type": "LONG_ENTRY",
  "symbol": "BTCUSDT",
  "price": 42350.0,
  "confidence": 0.85,
  "conditions": {...},
  "context": {...}
}
```

---

## 🎯 信号解读

### 多头信号 (LONG_ENTRY)
- **何时入场**: 所有确认条件满足时
- **止损建议**: VAL 下方 0.5-1%
- **目标位**: VAH 或更高

### 空头信号 (SHORT_ENTRY)
- **何时入场**: 所有确认条件满足时
- **止损建议**: VAH 上方 0.5-1%
- **目标位**: VAL 或更低

### 反转失败信号 (FAILURE_PATTERN)
- **优先级**: 最高(胜率通常较高)
- **特征**: 假突破被快速反转
- **风险**: 较低(明确的反转确认)

---

## 📈 性能优化建议

### 减少内存占用

```yaml
data:
  warmup_bars: 50  # 默认 100
  retention:
    orderflow_minutes: 30  # 默认 60
```

### 提高响应速度

```yaml
performance:
  update_interval_ms: 50  # 默认 100
```

### 多线程处理

```yaml
performance:
  use_threading: true
  worker_threads: 4
```

---

## 🛑 停止系统

**方法1**: Ctrl+C (推荐)

**方法2**: 发送停止信号
```bash
kill -SIGTERM <PID>
```

系统将:
1. 停止 WebSocket 连接
2. 保存日志
3. 发送关闭通知
4. 优雅退出

---

## 📚 进一步学习

- **完整文档**: 查看 `README.md`
- **实现细节**: 查看 `walkthrough.md`
- **配置参考**: 查看 `config.yaml` 中的注释

---

## ⚠️ 免责声明

本系统仅供学习和研究使用,不构成投资建议。

- ✅ 请在模拟环境充分测试
- ✅ 理解每个信号的逻辑
- ✅ 设置合理的风险管理
- ❌ 不要盲目跟随信号
- ❌ 不要使用超过承受能力的资金

---

## 🎉 开始使用!

```bash
python main.py
```

祝交易顺利! 📈
