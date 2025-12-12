"""
Test signal display bug fixes
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime
from models import SignalEvent, SignalType, SignalConditions, TPOProfile, VWAPData, OrderFlowMetrics
from models import TPOStructureEvent, OrderFlowDirection
from alert_manager import AlertManager

print("="*60)
print("Testing Signal Display Fixes")
print("="*60)

# Create test signal
print("\n1. Creating SHORT_FAILURE test signal...")

conditions = SignalConditions(
    tpo_event=TPOStructureEvent.VAH_REJECTION,
    delta_flip=True,
    cvd_divergence=True
)

tpo_data = TPOProfile(
    session_start=1000,
    session_end=2000,
    poc=3182.60,
    vah=3194.50,
    val=3164.10,
    total_volume=1000.0
)

vwap_data = VWAPData(
    timestamp=1000,
    vwap=3176.19,
    upper_1std=3200.0,
    lower_1std=3150.0,
    upper_2std=3220.0,
    lower_2std=3130.0
)

orderflow_data = OrderFlowMetrics(
    timestamp=1000,
    delta=0.0,
    cumulative_delta=4.0,
    delta_trend=OrderFlowDirection.NEUTRAL,
    oi_change_percent=0.00
)

# UTC time: 2025-12-12 02:30:00 -> Local: 2025-12-12 10:30:00 (UTC+8)
timestamp_utc = int(datetime(2025, 12, 12, 2, 30, 0).timestamp() * 1000)

signal = SignalEvent(
    timestamp=timestamp_utc,
    symbol="ETHUSDT",
    signal_type=SignalType.SHORT_FAILURE,
    price=3197.45,
    conditions=conditions,
    confidence=0.70,
    tpo_data=tpo_data,
    vwap_data=vwap_data,
    orderflow_data=orderflow_data
)

print("[OK] Signal created")

# Test to_dict
print("\n2. Testing to_dict() time conversion...")
signal_dict = signal.to_dict()
print(f"   Original UTC: 2025-12-12 02:30:00")
print(f"   Converted:    {signal_dict['timestamp']}")
if signal_dict['timestamp'].startswith("2025-12-12T10:30"):
    print("   [OK] Time converted correctly (UTC+8)")
else:
    print(f"   [FAIL] Expected 2025-12-12T10:30, got {signal_dict['timestamp']}")

# Test Alert formatting
print("\n3. Testing AlertManager formatting...")

config = {
    'channels': {
        'console': True,
        'file': True,
        'telegram': False
    },
    'throttle': {
        'enabled': False
    }
}

alert_mgr = AlertManager(config)
message = alert_mgr._format_alert_message(signal)

print("\n--- Formatted Message ---")
print(message)
print("--- End Message ---\n")

# Verify fixes
print("\n4. Verifying 3 bug fixes:")

# Bug 1: Signal name
if "SHORT FAILURE" in message:
    print("   [OK] Bug 1: Signal name has space (SHORT FAILURE)")
elif "SHORTFAILURE" in message or "SHORT_FAILURE" in message:
    print("   [FAIL] Bug 1: Signal name still no space")
else:
    print("   [WARN] Bug 1: Cannot find signal name")

# Bug 2: Time format
if "2025-12-12 10:30" in message:
    print("   [OK] Bug 2: Time shows local (UTC+8), no T separator")
elif "2025-12-12T" in message:
    print("   [FAIL] Bug 2: Time still has T separator")
elif "2025-12-12 02:30" in message:
    print("   [FAIL] Bug 2: Time still UTC, not converted")
else:
    print("   [WARN] Bug 2: Cannot find time")

# Bug 3: OI Change display
if "OI Change: 0.00%" in message:
    print("   [FAIL] Bug 3: OI Change 0.00% still showing")
elif "OI Change:" not in message:
    print("   [OK] Bug 3: OI Change 0.00% hidden")
else:
    print("   [WARN] Bug 3: Check unclear")

print("\n" + "="*60)
print("Test Complete")
print("="*60)
