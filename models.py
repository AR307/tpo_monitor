"""
Data Models for TPO + VWAP + Order Flow Trading System

Defines all core data structures used throughout the system.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


# ========================================
# Enums for Type Safety
# ========================================

class SignalType(Enum):
    """Types of trading signals"""
    LONG_ENTRY = "LONG_ENTRY"
    SHORT_ENTRY = "SHORT_ENTRY"
    LONG_FAILURE = "LONG_FAILURE"  # Short trap → Long
    SHORT_FAILURE = "SHORT_FAILURE"  # Long trap → Short


class TPOStructureEvent(Enum):
    """TPO structure interaction events"""
    VAL_BOUNCE = "VAL_BOUNCE"
    VAL_BREAK = "VAL_BREAK"
    VAH_REJECTION = "VAH_REJECTION"
    VAH_BREAKOUT = "VAH_BREAKOUT"
    POC_RECLAIM = "POC_RECLAIM"
    POC_BREAKDOWN = "POC_BREAKDOWN"
    INSIDE_VALUE_AREA = "INSIDE_VALUE_AREA"
    OUTSIDE_VALUE_AREA = "OUTSIDE_VALUE_AREA"


class OrderFlowDirection(Enum):
    """Order flow direction"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


# ========================================
# Market Data Models
# ========================================

@dataclass
class Candle:
    """OHLCV candle data"""
    timestamp: int  # Unix timestamp in milliseconds
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000)
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low


@dataclass
class Trade:
    """Individual trade from exchange"""
    timestamp: int
    price: float
    quantity: float
    is_buyer_maker: bool  # True = sell, False = buy
    
    @property
    def is_buy(self) -> bool:
        return not self.is_buyer_maker
    
    @property
    def is_sell(self) -> bool:
        return self.is_buyer_maker


@dataclass
class OrderBookLevel:
    """Single price level in order book"""
    price: float
    quantity: float
    
    @property
    def notional(self) -> float:
        return self.price * self.quantity


@dataclass
class OrderBookSnapshot:
    """Order book snapshot"""
    timestamp: int
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    
    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0
    
    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 0.0
    
    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid
    
    @property
    def mid_price(self) -> float:
        return (self.best_bid + self.best_ask) / 2


# ========================================
# TPO Models
# ========================================

@dataclass
class TPOProfile:
    """Market Profile (TPO) data structure"""
    session_start: int  # Unix timestamp
    session_end: int
    
    # Key levels
    poc: float  # Point of Control
    vah: float  # Value Area High
    val: float  # Value Area Low
    
    # Distribution data
    price_levels: Dict[float, int] = field(default_factory=dict)  # price -> volume
    tpo_letters: Dict[float, str] = field(default_factory=dict)   # price -> letters
    
    # Metadata
    total_volume: float = 0.0
    value_area_volume: float = 0.0
    
    @property
    def value_area_range(self) -> float:
        return self.vah - self.val
    
    @property
    def poc_position(self) -> float:
        """POC position within value area (0-1, 0.5 = centered)"""
        if self.value_area_range == 0:
            return 0.5
        return (self.poc - self.val) / self.value_area_range
    
    def is_inside_value_area(self, price: float) -> bool:
        return self.val <= price <= self.vah
    
    def distance_to_poc(self, price: float) -> float:
        return abs(price - self.poc)
    
    def distance_to_vah(self, price: float) -> float:
        return price - self.vah
    
    def distance_to_val(self, price: float) -> float:
        return self.val - price


# ========================================
# VWAP Models
# ========================================

@dataclass
class VWAPData:
    """VWAP with standard deviation bands"""
    timestamp: int
    vwap: float
    
    # Standard deviation bands
    upper_1std: float
    lower_1std: float
    upper_2std: float
    lower_2std: float
    
    # Calculation components
    cumulative_vp: float = 0.0  # Σ(price × volume)
    cumulative_volume: float = 0.0  # Σ(volume)
    
    # Trend indicators
    slope: float = 0.0  # VWAP slope
    
    @property
    def std_dev(self) -> float:
        return (self.upper_1std - self.vwap)
    
    def get_band_position(self, price: float) -> float:
        """
        Returns price position relative to VWAP bands
        0 = at VWAP, +1 = at +1std, -1 = at -1std, etc.
        """
        if price >= self.vwap:
            if self.std_dev == 0:
                return 0
            return (price - self.vwap) / self.std_dev
        else:
            if self.std_dev == 0:
                return 0
            return (price - self.vwap) / self.std_dev
    
    def is_pullback_zone(self, price: float, tolerance: float = 0.001) -> bool:
        """Check if price is touching VWAP (within tolerance)"""
        return abs(price - self.vwap) / self.vwap < tolerance


# ========================================
# Order Flow Models
# ========================================

@dataclass
class OrderFlowMetrics:
    """Comprehensive order flow analysis"""
    timestamp: int
    
    # Delta metrics
    delta: float  # Buy volume - Sell volume
    cumulative_delta: float  # CVD
    delta_trend: OrderFlowDirection = OrderFlowDirection.NEUTRAL
    
    # Volume breakdown
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    total_volume: float = 0.0
    
    # Open Interest
    oi: float = 0.0
    oi_change: float = 0.0
    oi_change_percent: float = 0.0
    
    # Imbalance metrics
    bid_volume: float = 0.0
    ask_volume: float = 0.0
    imbalance_ratio: float = 0.0  # |ask - bid| / total
    
    # Absorption detection
    absorption_detected: bool = False
    absorption_price: Optional[float] = None
    absorption_volume: float = 0.0
    
    # Aggressive trading
    consecutive_buy_bars: int = 0
    consecutive_sell_bars: int = 0
    
    @property
    def is_bullish(self) -> bool:
        return (self.delta > 0 and 
                self.delta_trend == OrderFlowDirection.BULLISH and
                self.oi_change > 0)
    
    @property
    def is_bearish(self) -> bool:
        return (self.delta < 0 and 
                self.delta_trend == OrderFlowDirection.BEARISH and
                self.oi_change > 0)
    
    @property
    def has_significant_imbalance(self, threshold: float = 0.6) -> bool:
        return self.imbalance_ratio > threshold


# ========================================
# Signal Models
# ========================================

@dataclass
class SignalConditions:
    """Conditions that triggered a signal"""
    # TPO conditions
    tpo_event: Optional[TPOStructureEvent] = None
    tpo_proximity: float = 0.0
    
    # VWAP conditions
    vwap_aligned: bool = False
    vwap_distance: float = 0.0
    vwap_slope: float = 0.0
    
    # Order Flow conditions
    delta_confirmed: bool = False
    cvd_confirmed: bool = False
    oi_confirmed: bool = False
    aggressive_flow: bool = False
    absorption: bool = False
    
    # Failure pattern specific
    delta_flip: bool = False
    cvd_divergence: bool = False


@dataclass
class SignalEvent:
    """Trading signal event"""
    timestamp: int
    symbol: str
    signal_type: SignalType
    price: float
    
    # Condition details
    conditions: SignalConditions
    
    # Confidence score (0-1)
    confidence: float
    
    # Context data
    tpo_data: Optional[TPOProfile] = None
    vwap_data: Optional[VWAPData] = None
    orderflow_data: Optional[OrderFlowMetrics] = None
    
    # Alert tracking
    alerted: bool = False
    alert_timestamp: Optional[int] = None
    
    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/alerts"""
        return {
            'timestamp': self.datetime.isoformat(),
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'price': self.price,
            'confidence': round(self.confidence, 2),
            'conditions': {
                'tpo_event': self.conditions.tpo_event.value if self.conditions.tpo_event else None,
                'vwap_aligned': self.conditions.vwap_aligned,
                'delta_confirmed': self.conditions.delta_confirmed,
                'cvd_confirmed': self.conditions.cvd_confirmed,
                'oi_confirmed': self.conditions.oi_confirmed,
                'delta_flip': self.conditions.delta_flip,
                'cvd_divergence': self.conditions.cvd_divergence,
            },
            'context': {
                'poc': self.tpo_data.poc if self.tpo_data else None,
                'vah': self.tpo_data.vah if self.tpo_data else None,
                'val': self.tpo_data.val if self.tpo_data else None,
                'vwap': self.vwap_data.vwap if self.vwap_data else None,
                'delta': self.orderflow_data.delta if self.orderflow_data else None,
                'cvd': self.orderflow_data.cumulative_delta if self.orderflow_data else None,
                'oi_change': f"{self.orderflow_data.oi_change_percent:.2f}%" if self.orderflow_data else None,
            }
        }


# ========================================
# Alert Models
# ========================================

class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """Alert message"""
    timestamp: int
    priority: AlertPriority
    title: str
    message: str
    signal: Optional[SignalEvent] = None
    
    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000)
