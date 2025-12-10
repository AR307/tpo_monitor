# 🚀 系统启动指南

## 快速启动

### 方法1: 使用批处理脚本 (推荐)
```batch
# 双击运行
start.bat
```

### 方法2: 命令行
```bash
cd d:\files\crypto\monitor_tpo
.venv\Scripts\python.exe main.py
```

### 方法3: PowerShell
```powershell
cd d:\files\crypto\monitor_tpo
.\.venv\Scripts\python.exe main.py
```

---

## 🎯 启动后应该看到

### 1. 初始化阶段 (5-10秒)
```
INFO:trading_system:交易系统已初始化,监控 2 个币种
INFO:data_feed:DataFeed initialized for BTCUSDT
INFO:data_feed:DataFeed initialized for ETHUSDT
```

### 2. WebSocket连接 (1-2秒)
```
INFO:data_feed:连接到: wss://fstream.binance.com/stream?...
INFO:data_feed:✅ WebSocket已连接 BTCUSDT
INFO:data_feed:✅ WebSocket已连接 ETHUSDT
```

### 3. 预热阶段 (3-5秒)
```
INFO:data_feed:获取到 100 根历史K线
INFO:trading_system:BTCUSDT 已预热 100 根K线
INFO:trading_system:✓ 预热完成
```

### 4. 系统上线
```
INFO:trading_system:✓ 交易系统现已上线 LIVE
[SYSTEM] 系统现已上线 LIVE
INFO:trading_system:系统运行中... (按 Ctrl+C 停止)
```

### 5. 实时数据流
```
DEBUG:orderflow_analyzer:Bar finalized. Delta: 12.5, CVD: 150.3, Trend: BULLISH
# 每分钟更新一次
```

---

## 📊 运行时看到的信息

### 正常运行状态
- 每分钟看到一次 "Bar finalized" 信息
- 偶尔看到ticker错误是正常的(不影响运行)
- 没有持续的ERROR信息

### 交易信号检测到时
```
================================================================================
🚀  LONG_ENTRY SIGNAL DETECTED  🚀
================================================================================
Symbol:     BTCUSDT
Time:       2025-12-10 23:22:45
Price:      $91,950.00
Confidence: 87%

Conditions:
  TPO Event:        PRICE_ABOVE_VAH
  VWAP Aligned:     True
  Delta Confirmed:  True
  CVD Confirmed:    True
  OI Confirmed:     True

Context:
  VAH: $91,900.00 | POC: $91,750.00 | VAL: $91,600.00
  VWAP: $91,820.00
  Delta: 1,250 | CVD: 5,430
================================================================================
```

---

## 🛑 停止系统

### 方法1: 键盘快捷键
```
按 Ctrl+C
```

### 方法2: 关闭窗口
直接关闭PowerShell/CMD窗口

系统会自动:
- 关闭WebSocket连接
- 保存日志
- 优雅退出

---

## 📱 Telegram通知

### 启动时应该收到
1. "交易系统启动 - 监控币种: BTCUSDT, ETHUSDT"
2. "系统现已上线 LIVE"

### 信号检测时会收到
```
🚨 LONG_ENTRY - BTCUSDT

Signal: LONG_ENTRY
Symbol: BTCUSDT
Price: $91,950.00
...
```

### 如果没收到Telegram消息
检查:
1. `config.yaml` 中 `telegram: true`
2. `.env` 文件中Bot Token和Chat ID正确
3. 网络能访问 api.telegram.org

测试Telegram:
```bash
python test_alert.py
```

---

## 🔍 查看日志

### 主日志
```bash
Get-Content logs\main.log -Tail 50 -Wait
```

### 信号日志
```bash
Get-Content logs\signals.log -Tail 20
```

### 错误日志
```bash
Get-Content logs\errors.log
```

---

## ⚙️ 配置选项

### 修改监控币种
编辑 `config.yaml`:
```yaml
exchange:
  symbols:
    - BTCUSDT
    - ETHUSDT
    - BNBUSDT  # 添加更多
```

### 调整信号参数
编辑 `config.yaml`:
```yaml
signals:
  min_confidence: 0.7  # 最低置信度
  cooldown_seconds: 300  # 信号冷却时间
```

---

## 🚨 常见问题

### Q: 系统启动后立即退出
A: 检查是否有Python错误,运行 `python main.py` 查看完整错误

### Q: WebSocket连接失败
A: 检查网络连接,确认能访问 fstream.binance.com

### Q: 一直没有信号
A: 这是正常的,系统只在高置信度条件满足时才发出信号

### Q: ticker错误很多
A: 少量ticker错误是正常的(某些ticker字段可能缺失),不影响核心功能

---

## ✅ 系统健康检查

运行中应该看到:
- ✅ WebSocket已连接提示
- ✅ 每分钟的Bar finalized信息
- ✅ Telegram启动消息
- ✅ 无持续性ERROR

如果持续出现ERROR,检查:
1. 网络连接
2. 币安API可访问性
3. Python依赖完整性

---

**系统已准备就绪，祝交易顺利！** 🎉
