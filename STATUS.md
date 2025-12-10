# TPO+VWAP+OrderFlow 交易信号系统

## ✅ 系统状态: 运行中 (LIVE)

**最后更新**: 2025-12-10 23:10

---

## 🎯 快速启动

```bash
# 1. 进入项目目录
cd d:\files\crypto\monitor_tpo

# 2. 激活虚拟环境 (如果需要)
.venv\Scripts\activate

# 3. 启动系统
python main.py
```

**停止**: 按 `Ctrl+C`

---

## 📊 系统功能

### 实时数据监控
- ✅ 聚合交易流 (Delta/CVD计算)
- ✅ 1分钟K线 (VWAP/TPO)
- ✅ 24小时Ticker (价格更新)
- ✅ 持仓量 (Open Interest)

### 信号检测
- 🟢 **多头入场信号** (LONG_ENTRY)
- 🔴 **空头入场信号** (SHORT_ENTRY)
- ⚠️ **反转失败信号** (FAILURE PATTERNS)

### 报警渠道
- 💻 **Console** - 控制台输出
- 📝 **File** - 日志文件 (logs/signals.log)
- 📱 **Telegram** - 即时推送

---

## ⚙️ 配置

### 编辑监控币种
文件: `config.yaml`
```yaml
exchange:
  symbols:
    - BTCUSDT
    - ETHUSDT
    # 添加更多...
```

### 启用Telegram推送
文件: `config.yaml`
```yaml
alerts:
  channels:
    telegram: true  # 改为true
```

文件: `.env`
```env
TELEGRAM_BOT_TOKEN=你的Bot Token
TELEGRAM_CHAT_ID=你的Chat ID
```

---

## 📖 文档

- **README.md** - 完整功能说明
- **QUICKSTART.md** - 快速入门指南
- **WEBSOCKET_REWRITE_SUCCESS.md** - 技术实现详情
- **FIX_REPORT.md** - 修复记录

---

## 🔧 故障排除

### 系统无法启动
```bash
# 重新安装依赖
pip install -r requirements.txt
```

### WebSocket断连
系统会自动重连,无需手动处理

### 查看日志
```bash
# Windows PowerShell
Get-Content logs\main.log -Tail 50 -Wait

# Linux/Mac
tail -f logs/main.log
```

---

## 📝 信号示例

```
🚀 LONG_ENTRY SIGNAL DETECTED
Symbol:     BTCUSDT
Price:      $95,234.50
Confidence: 87%

Conditions:
  - TPO: PRICE_ABOVE_VAH
  - VWAP: Aligned
  - Delta: Confirmed (+1250.5)
  - CVD: Confirmed
  - OI: Increasing

Context:
  VAH: $95,180.00 | POC: $94,890.00 | VAL: $94,650.00
  VWAP: $94,920.00
  Delta: 1,250 | CVD: 5,430
```

---

## ✨ 核心特性

- **三重确认**: TPO + VWAP + OrderFlow
- **实时分析**: 毫秒级数据延迟
- **自动重连**: WebSocket断线自动恢复
- **智能过滤**: 信号置信度评分
- **灵活配置**: 所有参数可调

---

**系统版本**: 1.0.0  
**Python版本**: 3.8+  
**数据源**: 币安Futures (免费API)

---

🎉 **系统已就绪，祝交易顺利！**
