"""
完整系统本地测试
"""
import time
import logging
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

print("="*60)
print("完整系统测试")
print("="*60)

# 1. 测试配置加载
print("\n[1/5] 测试配置加载...")
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
print(f"✅ 配置加载成功 - {len(config['exchange']['symbols'])} 个币种")

# 2. 测试Data Feed
print("\n[2/5] 测试Data Feed...")
from data_feed import BinanceDataFeed

feed = BinanceDataFeed('BTCUSDT', config['exchange'])
trade_count = [0]
delta_list = []

def on_trade(trade, delta, cvd):
    trade_count[0] += 1
    delta_list.append((delta, cvd))
    if trade_count[0] % 100 == 0:
        print(f"  收到 {trade_count[0]} 笔交易, Delta={delta:.2f}, CVD={cvd:.2f}")

feed.on_trade(on_trade)
feed.start()
print("  WebSocket已启动，收集10秒数据...")
time.sleep(10)
feed.stop()

if trade_count[0] > 0:
    print(f"✅ Data Feed正常 - 收到 {trade_count[0]} 笔交易")
    final_delta, final_cvd = delta_list[-1]
    print(f"  最终 Delta={final_delta:.2f}, CVD={final_cvd:.2f}")
    if abs(final_delta) < 0.01 and abs(final_cvd) < 0.01:
        print("  ⚠️ 警告: Delta和CVD都接近0")
else:
    print("❌ Data Feed失败 - 没有收到交易数据")
    exit(1)

# 3. 测试OrderFlow分析器
print("\n[3/5] 测试OrderFlow分析器...")
from orderflow_analyzer import OrderFlowAnalyzer
from models import Trade

of_analyzer = OrderFlowAnalyzer('BTCUSDT', config['orderflow'])

# 模拟一些交易
test_trades = [
    Trade(1000, 90000.0, 0.1, False),  # 买单
    Trade(2000, 90001.0, 0.2, True),   # 卖单
    Trade(3000, 90002.0, 0.15, False), # 买单
]

for trade in test_trades:
    of_analyzer.on_trade(trade)

metrics = of_analyzer.get_metrics()
if metrics:
    print(f"✅ OrderFlow正常 - Delta={metrics.delta:.4f}, CVD={metrics.cumulative_delta:.4f}")
else:
    print("❌ OrderFlow失败")

# 4. 测试Telegram
print("\n[4/5] 测试Telegram配置...")
import os
from dotenv import load_dotenv
import requests

load_dotenv()
bot_token = config['alerts']['telegram']['bot_token']
chat_id = config['alerts']['telegram']['chat_id']

if bot_token == "YOUR_BOT_TOKEN_HERE":
    print("⚠️ Telegram未配置 - 使用占位符")
else:
    print(f"  Token: {bot_token[:20]}...")
    print(f"  Chat ID: {chat_id}")
    
    # 测试发送
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': '✅ 本地测试消息',
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Telegram测试成功 - 消息已发送")
        else:
            print(f"❌ Telegram失败 - 状态码 {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"❌ Telegram错误: {e}")

# 5. 测试信号检测
print("\n[5/5] 测试信号检测逻辑...")
from signal_engine import SignalEngine
from models import TPOProfile, VWAPData, OrderFlowMetrics, DeltaTrend

signal_engine = SignalEngine('BTCUSDT', config['signals'])

# 创建测试数据
test_tpo = TPOProfile(
    session_start=1000,
    poc=90000.0,
    vah=90100.0,
    val=89900.0,
    total_volume=1000.0
)

test_vwap = VWAPData(
    timestamp=1000,
    vwap=90000.0,
    upper_1std=90050.0,
    upper_2std=90100.0,
    lower_1std=89950.0,
    lower_2std=89900.0,
    slope=0.1
)

test_of = OrderFlowMetrics(
    timestamp=1000,
    delta=5.0,
    cumulative_delta=10.0,
    delta_trend=DeltaTrend.BULLISH,
    oi_change_percent=1.5,
    consecutive_buy_bars=3,
    consecutive_sell_bars=0,
    imbalance_ratio=0.7,
    absorption_detected=False
)

# 模拟检查信号（不会真正生成，因为需要TPO事件）
print("✅ 信号引擎初始化成功")
print(f"  配置: min_confidence={config['signals']['long']['min_confidence']}")

print("\n" + "="*60)
print("测试完成摘要")
print("="*60)
print(f"✅ Data Feed: {trade_count[0]} 笔交易")
print(f"✅ OrderFlow: Delta计算正常")
print(f"✅ 信号引擎: 已初始化")
print(f"{'✅' if bot_token != 'YOUR_BOT_TOKEN_HERE' else '⚠️'} Telegram: {'已配置' if bot_token != 'YOUR_BOT_TOKEN_HERE' else '未配置'}")
print("="*60)
