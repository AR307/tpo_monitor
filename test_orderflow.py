"""
本地测试订单流数据计算
"""
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

print("启动订单流数据测试...")

from data_feed import BinanceDataFeed

# 计数器
trade_count = [0]
delta_values = []
cvd_values = []

def on_trade_received(trade, delta, cvd):
    trade_count[0] += 1
    delta_values.append(delta)
    cvd_values.append(cvd)
    
    if trade_count[0] % 50 == 0:
        print(f"\n[{trade_count[0]}笔交易]")
        print(f"  价格: ${trade.price:.2f}")
        print(f"  方向: {'🟢买' if trade.is_buy else '🔴卖'}")
        print(f"  数量: {trade.quantity:.4f}")
        print(f"  Delta: {delta:.4f}")
        print(f"  CVD: {cvd:.4f}")

# 创建data feed
feed = BinanceDataFeed('BTCUSDT', {})
feed.on_trade(on_trade_received)

print("启动WebSocket...")
feed.start()

# 运行30秒
print("收集30秒数据...\n")
time.sleep(30)

feed.stop()

print("\n" + "="*60)
print("测试结果")
print("="*60)
print(f"总交易数: {trade_count[0]}")
print(f"最终Delta: {feed.get_delta():.4f}")
print(f"最终CVD: {feed.get_cvd():.4f}")

if trade_count[0] > 0:
    print(f"\nDelta变化: {min(delta_values):.4f} 到 {max(delta_values):.4f}")
    print(f"CVD变化: {min(cvd_values):.4f} 到 {max(cvd_values):.4f}")
    
    if abs(feed.get_delta()) < 0.01 and abs(feed.get_cvd()) < 0.01:
        print("\n❌ 问题: Delta和CVD都接近0!")
        print("可能原因:")
        print("  1. 回调函数没有被调用")
        print("  2. Trade.is_buy判断有误")
        print("  3. 每笔交易的买卖抵消了")
    else:
        print("\n✅ 订单流数据正常!")
else:
    print("\n❌ 没有收到任何交易数据!")

print("="*60)
