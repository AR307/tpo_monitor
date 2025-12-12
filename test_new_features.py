"""
测试新功能：中文化信号和OI获取
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime
from models import SignalEvent, SignalType, SignalConditions, TPOProfile, VWAPData, OrderFlowMetrics
from models import TPOStructureEvent, OrderFlowDirection
from alert_manager import AlertManager

print("="*60)
print("测试1: 中文化信号消息")
print("="*60)

# 测试所有4种信号类型
signal_types_tests = [
    (SignalType.SHORT_FAILURE, "多头陷阱反转", "📉 看跌"),
    (SignalType.LONG_FAILURE, "空头陷阱反转", "📈 看涨"),
    (SignalType.SHORT_ENTRY, "做空入场", "📉 看跌"),
    (SignalType.LONG_ENTRY, "做多入场", "📈 看涨"),
]

config = {
    'channels': {'console': True, 'file': True, 'telegram': False},
    'throttle': {'enabled': False}
}
alert_mgr = AlertManager(config)

for signal_type, expected_cn, expected_direction in signal_types_tests:
    print(f"\n测试 {signal_type.value}:")
    
    signal = SignalEvent(
        timestamp=int(datetime.now().timestamp() * 1000),
        symbol="BTCUSDT",
        signal_type=signal_type,
        price=90000.0,
        conditions=SignalConditions(tpo_event=TPOStructureEvent.VAH_REJECTION),
        confidence=0.75,
        tpo_data=TPOProfile(1000, 2000, 90000, 91000, 89000, total_volume=1000),
        vwap_data=VWAPData(1000, 90000, 90500, 89500, 91000, 89000),
        orderflow_data=OrderFlowMetrics(1000, 10.0, 20.0, OrderFlowDirection.BULLISH)
    )
    
    message = alert_mgr._format_alert_message(signal)
    first_line = message.split('\n')[0]
    print(f"  消息首行: {first_line}")
    
    if expected_cn in first_line and expected_direction in first_line:
        print(f"  ✓ 包含中文 '{expected_cn}' 和方向 '{expected_direction}'")
    else:
        print(f"  ✗ 缺少中文或方向")

print("\n" + "="*60)
print("测试2: OI获取功能")
print("="*60)

print("\n测试OI API调用...")
from data_feed import BinanceDataFeed
import time

feed = BinanceDataFeed('BTCUSDT', {})

# 测试_fetch_open_interest方法
print("调用 _fetch_open_interest()...")
oi = feed._fetch_open_interest()

if oi is not None and oi > 0:
    print(f"✓ OI获取成功: {oi:,.2f}")
    print(f"  当前OI: {feed.current_oi:,.2f}")
    
    # 模拟第二次获取
    time.sleep(1)
    feed.previous_oi = feed.current_oi
    feed.current_oi = feed._fetch_open_interest()
    
    oi_change = feed.get_oi_change()
    print(f"  OI变化: {oi_change:.4f}%")
    
    if abs(oi_change) < 10:  # 正常范围
        print("  ✓ OI变化计算正常")
else:
    print("✗ OI获取失败")

print("\n" + "="*60)
print("测试3: 完整信号消息（带OI）")
print("="*60)

# 创建带真实OI数据的信号
if oi:
    orderflow_with_oi = OrderFlowMetrics(
        timestamp=1000,
        delta=150.0,
        cumulative_delta=300.0,
        delta_trend=OrderFlowDirection.BULLISH,
        oi_change_percent=0.25  # 0.25%变化
    )
    
    signal_with_oi = SignalEvent(
        timestamp=int(datetime.now().timestamp() * 1000),
        symbol="BTCUSDT",
        signal_type=SignalType.LONG_ENTRY,
        price=90000.0,
        conditions=SignalConditions(
            tpo_event=TPOStructureEvent.VAL_BOUNCE,
            delta_confirmed=True,
            oi_confirmed=True
        ),
        confidence=0.85,
        tpo_data=TPOProfile(1000, 2000, 90000, 91000, 89000, total_volume=1000),
        vwap_data=VWAPData(1000, 90000, 90500, 89500, 91000, 89000),
        orderflow_data=orderflow_with_oi
    )
    
    message_with_oi = alert_mgr._format_alert_message(signal_with_oi)
    print(message_with_oi)
    
    if "0.25%" in message_with_oi:
        print("\n✓ OI Change正确显示")
    else:
        print("\n✗ OI Change未显示")

print("\n" + "="*60)
print("所有测试完成")
print("="*60)
