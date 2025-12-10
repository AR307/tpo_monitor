# TPO + VWAP + OrderFlow 交易信号系统

基于 **TPO (Time Price Opportunity)**、**VWAP** 和 **订单流分析** 的加密货币交易信号系统。

## 📊 功能特性

- **实时数据分析**: 接收币安Futures WebSocket数据流
- **TPO分析**: 市场轮廓分析 (POC, VAH, VAL)
- **VWAP计算**: 成交量加权平均价
- **订单流分析**: Delta、CVD、订单簿失衡检测
- **信号检测**: 多重条件确认的交易信号
- **多渠道报警**: Console、文件日志、Telegram推送

## 🚀 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

复制 `.env.example` 为 `.env` 并配置:

```env
# Telegram (可选)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

编辑 `config.yaml` 设置监控币种和参数。

### 3. 运行

```bash
# 方式1: 直接运行
python main.py

# 方式2: 使用启动脚本 (Windows)
start.bat
```

## 📱 Telegram 配置

1. 与 [@BotFather](https://t.me/botfather) 创建Bot获取Token
2. 与 [@userinfobot](https://t.me/userinfobot) 获取Chat ID
3. 在 `.env` 中配置Token和Chat ID
4. 在 `config.yaml` 中启用: `telegram: true`

## 📈 信号类型

### LONG_ENTRY (做多入场)
- 价格突破VAH
- VWAP方向一致
- Delta/CVD确认
- OI增加

### SHORT_ENTRY (做空入场)
- 价格跌破VAL
- VWAP方向一致
- Delta/CVD确认
- OI增加

### FAILURE模式
- POC反弹失败
- 吸收失败

## 🛠️ 技术架构

```
├── main.py                 # 主程序入口
├── data_feed.py           # WebSocket数据源
├── tpo_analyzer.py        # TPO分析器
├── vwap_calculator.py     # VWAP计算器
├── orderflow_analyzer.py  # 订单流分析器
├── signal_engine.py       # 信号引擎
├── alert_manager.py       # 报警管理器
├── models.py              # 数据模型
└── utils.py               # 工具函数
```

## ⚙️ 配置说明

### 监控币种

编辑 `config.yaml`:

```yaml
exchange:
  symbols:
    - BTCUSDT
    - ETHUSDT
    # 添加更多币种...
```

### 信号参数

```yaml
signals:
  min_confidence: 0.7      # 最低置信度 (0-1)
  cooldown_seconds: 300    # 信号冷却时间(秒)
```

### TPO参数

```yaml
tpo:
  session_duration_minutes: 60  # TPO会话时长
  vah_percent: 70              # VAH百分比
  val_percent: 70              # VAL百分比
```

## 📊 输出示例

### Console输出

```
🚀  LONG_ENTRY SIGNAL DETECTED  🚀
Symbol:     BTCUSDT
Price:      $91,950.00
Confidence: 87%

Conditions:
  - TPO: PRICE_ABOVE_VAH ✓
  - VWAP: Aligned ✓
  - Delta: Confirmed ✓
  - CVD: Confirmed ✓
  - OI: Increasing ✓
```

### Telegram消息

```
🚨 LONG_ENTRY - BTCUSDT

Signal: LONG_ENTRY
Symbol: BTCUSDT
Price: $91,950.00
Confidence: 85%

⏰ 2025-12-10 23:38:45
```

## 📁 日志文件

- `logs/main.log` - 主日志
- `logs/signals.log` - 信号日志
- `logs/errors.log` - 错误日志

## 🔒 安全说明

- ⚠️ 不要提交 `.env` 文件到Git
- ⚠️ API密钥和Token应保密
- ⚠️ 本系统仅供信号参考，不构成投资建议

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## ⚠️ 免责声明

本系统仅用于教育和研究目的。加密货币交易存在风险，使用本系统产生的任何损失，开发者不承担责任。请谨慎决策，风险自负。

---

**开发**: 基于币安Futures API  
**数据源**: WebSocket实时数据流  
**版本**: 1.0.0
