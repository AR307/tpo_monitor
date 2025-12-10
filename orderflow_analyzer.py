"""
Order Flow Analyzer

Analyzes order flow metrics:
- Delta (aggressive buy vs sell volume)
- CVD (Cumulative Volume Delta)
- Open Interest changes
- Bid/Ask imbalance
- Absorption patterns
"""

import logging
from typing import Optional, List
from collections import deque

from models import OrderFlowMetrics, OrderFlowDirection, Trade, OrderBookSnapshot
import utils


class OrderFlowAnalyzer:
    """
    Order Flow Analyzer
    
    Analyzes:
    - Delta (buy - sell volume)
    - CVD trends
    - OI changes
    - Footprint imbalance
    - Absorption patterns
    """
    
    def __init__(self, symbol: str, config: dict):
        """
        Initialize order flow analyzer
        
        Args:
            symbol: Trading symbol
            config: Order flow configuration
        """
        self.logger = utils.get_logger('orderflow_analyzer')
        self.symbol = symbol
        self.config = config
        
        # Delta configuration
        self.delta_threshold = config['delta']['significant_threshold']
        self.consecutive_bars_required = config['delta']['consecutive_bars']
        
        # CVD configuration
        self.cvd_trend_lookback = config['cvd']['trend_lookback']
        self.cvd_divergence_threshold = config['cvd']['divergence_threshold']
        
        # OI configuration
        self.oi_significant_change = config['oi']['significant_change_percent']
        
        # Imbalance configuration
        self.imbalance_ratio_threshold = config['imbalance']['ratio_threshold']
        self.imbalance_volume_threshold = config['imbalance']['volume_threshold']
        
        # Absorption configuration
        self.absorption_volume_multiplier = config['absorption']['volume_multiplier']
        self.absorption_price_tolerance = config['absorption']['price_move_tolerance']
        self.absorption_lookback = config['absorption']['lookback_bars']
        
        # Current bar metrics
        self.current_delta = 0.0
        self.cumulative_delta = 0.0
        self.buy_volume_current = 0.0
        self.sell_volume_current = 0.0
        
        # Historical data
        self.delta_history: deque = deque(maxlen=100)
        self.cvd_history: deque = deque(maxlen=100)
        self.volume_history: deque = deque(maxlen=self.absorption_lookback)
        self.price_history: deque = deque(maxlen=self.absorption_lookback)
        
        # OI tracking
        self.current_oi = 0.0
        self.previous_oi = 0.0
        
        # Order book imbalance
        self.current_imbalance_ratio = 0.0
        
        # State tracking
        self.consecutive_buy_bars = 0
        self.consecutive_sell_bars = 0
        self.cvd_trend = OrderFlowDirection.NEUTRAL
        
        # Absorption detection
        self.absorption_detected = False
        self.absorption_price: Optional[float] = None
        self.absorption_volume = 0.0
        
        self.logger.info(f"OrderFlowAnalyzer initialized for {symbol}")
    
    def update_from_trades(self, trades: List[Trade]):
        """
        Update delta from trade data
        
        Args:
            trades: List of trades in current period
        """
        buy_vol = 0.0
        sell_vol = 0.0
        
        for trade in trades:
            if trade.is_buy:
                buy_vol += trade.quantity
            else:
                sell_vol += trade.quantity
        
        self.buy_volume_current = buy_vol
        self.sell_volume_current = sell_vol
        self.current_delta = buy_vol - sell_vol
        
        self.logger.debug(f"Delta updated: {self.current_delta:+.2f} (Buy: {buy_vol:.2f}, Sell: {sell_vol:.2f})")
    
    def update_from_orderbook(self, orderbook: OrderBookSnapshot):
        """
        Update imbalance from order book
        
        Args:
            orderbook: Order book snapshot
        """
        if not orderbook or not orderbook.bids or not orderbook.asks:
            return
        
        # Calculate bid/ask volume imbalance
        bid_volume = sum(level.quantity for level in orderbook.bids[:5])  # Top 5 levels
        ask_volume = sum(level.quantity for level in orderbook.asks[:5])
        
        total_volume = bid_volume + ask_volume
        
        if total_volume > 0:
            # Imbalance ratio: |ask - bid| / total
            self.current_imbalance_ratio = abs(ask_volume - bid_volume) / total_volume
        else:
            self.current_imbalance_ratio = 0.0
        
        self.logger.debug(f"Imbalance ratio: {self.current_imbalance_ratio:.3f}")
    
    def update_oi(self, new_oi: float):
        """
        Update Open Interest
        
        Args:
            new_oi: New OI value
        """
        self.previous_oi = self.current_oi
        self.current_oi = new_oi
        
        if self.previous_oi > 0:
            change_pct = ((new_oi - self.previous_oi) / self.previous_oi) * 100
            self.logger.debug(f"OI updated: {new_oi:,.0f} ({change_pct:+.2f}%)")
    
    def finalize_bar(self, price: float):
        """
        Finalize current bar and update metrics
        
        Should be called at the end of each candle period
        
        Args:
            price: Closing price of the bar
        """
        # Update cumulative delta
        self.cumulative_delta += self.current_delta
        
        # Add to history
        self.delta_history.append(self.current_delta)
        self.cvd_history.append(self.cumulative_delta)
        self.volume_history.append(self.buy_volume_current + self.sell_volume_current)
        self.price_history.append(price)
        
        # Update trend detection
        self._update_trend()
        
        # Update consecutive bars
        self._update_consecutive_bars()
        
        # Check for absorption
        self._check_absorption(price)
        
        # Reset current bar metrics
        self.current_delta = 0.0
        self.buy_volume_current = 0.0
        self.sell_volume_current = 0.0
        
        self.logger.debug(f"Bar finalized. CVD: {self.cumulative_delta:,.0f}, Trend: {self.cvd_trend.value}")
    
    def _update_trend(self):
        """Update CVD trend direction"""
        if len(self.cvd_history) < self.cvd_trend_lookback:
            self.cvd_trend = OrderFlowDirection.NEUTRAL
            return
        
        recent_cvd = list(self.cvd_history)[-self.cvd_trend_lookback:]
        
        # Calculate slope
        slope = utils.calculate_slope(recent_cvd)
        
        # Determine trend
        if slope > 0:
            self.cvd_trend = OrderFlowDirection.BULLISH
        elif slope < 0:
            self.cvd_trend = OrderFlowDirection.BEARISH
        else:
            self.cvd_trend = OrderFlowDirection.NEUTRAL
    
    def _update_consecutive_bars(self):
        """Update consecutive buy/sell bar counts"""
        if self.is_delta_bullish():
            self.consecutive_buy_bars += 1
            self.consecutive_sell_bars = 0
        elif self.is_delta_bearish():
            self.consecutive_sell_bars += 1
            self.consecutive_buy_bars = 0
        else:
            self.consecutive_buy_bars = 0
            self.consecutive_sell_bars = 0
    
    def _check_absorption(self, price: float):
        """
        Check for absorption pattern
        
        Absorption = high volume at a price level without price movement
        
        Args:
            price: Current price
        """
        if len(self.volume_history) < self.absorption_lookback:
            self.absorption_detected = False
            return
        
        # Calculate average volume
        avg_volume = sum(self.volume_history) / len(self.volume_history)
        
        # Get recent volume
        recent_volume = self.volume_history[-1]
        
        # Check if current volume is significantly higher
        if recent_volume < avg_volume * self.absorption_volume_multiplier:
            self.absorption_detected = False
            return
        
        # Check if price didn't move much despite high volume
        if len(self.price_history) < 2:
            self.absorption_detected = False
            return
        
        previous_price = self.price_history[-2]
        price_change_pct = abs((price - previous_price) / previous_price) * 100
        
        if price_change_pct <= self.absorption_price_tolerance:
            self.absorption_detected = True
            self.absorption_price = price
            self.absorption_volume = recent_volume
            self.logger.info(f"ABSORPTION detected at {price:.2f} (Volume: {recent_volume:,.0f})")
        else:
            self.absorption_detected = False
    
    def is_delta_bullish(self) -> bool:
        """Check if current delta is bullish"""
        if not self.delta_history:
            return False
        return self.delta_history[-1] > self.delta_threshold
    
    def is_delta_bearish(self) -> bool:
        """Check if current delta is bearish"""
        if not self.delta_history:
            return False
        return self.delta_history[-1] < -self.delta_threshold
    
    def is_cvd_rising(self) -> bool:
        """Check if CVD is rising"""
        return self.cvd_trend == OrderFlowDirection.BULLISH
    
    def is_cvd_falling(self) -> bool:
        """Check if CVD is falling"""
        return self.cvd_trend == OrderFlowDirection.BEARISH
    
    def is_oi_increasing(self) -> bool:
        """Check if OI is increasing significantly"""
        if self.previous_oi == 0:
            return False
        
        change_pct = ((self.current_oi - self.previous_oi) / self.previous_oi) * 100
        return change_pct >= self.oi_significant_change
    
    def is_oi_decreasing(self) -> bool:
        """Check if OI is decreasing significantly"""
        if self.previous_oi == 0:
            return False
        
        change_pct = ((self.current_oi - self.previous_oi) / self.previous_oi) * 100
        return change_pct <= -self.oi_significant_change
    
    def has_imbalance(self) -> bool:
        """Check if there's significant bid/ask imbalance"""
        return self.current_imbalance_ratio > self.imbalance_ratio_threshold
    
    def has_consecutive_buying(self) -> bool:
        """Check if there are consecutive buy bars"""
        return self.consecutive_buy_bars >= self.consecutive_bars_required
    
    def has_consecutive_selling(self) -> bool:
        """Check if there are consecutive sell bars"""
        return self.consecutive_sell_bars >= self.consecutive_bars_required
    
    def has_absorption(self) -> bool:
        """Check if absorption pattern was detected"""
        return self.absorption_detected
    
    def check_delta_flip(self) -> bool:
        """
        Check if delta flipped direction recently
        
        Returns:
            True if delta flipped from positive to negative or vice versa
        """
        if len(self.delta_history) < 2:
            return False
        
        previous_delta = self.delta_history[-2]
        current_delta = self.delta_history[-1]
        
        # Check for flip
        flipped = (previous_delta > 0 and current_delta < 0) or \
                  (previous_delta < 0 and current_delta > 0)
        
        if flipped:
            self.logger.info(f"DELTA FLIP detected: {previous_delta:+.0f} → {current_delta:+.0f}")
        
        return flipped
    
    def check_cvd_divergence(self, price_trend: str) -> bool:
        """
        Check for CVD divergence with price
        
        Args:
            price_trend: "UP" or "DOWN"
            
        Returns:
            True if divergence detected
        """
        if len(self.cvd_history) < self.cvd_trend_lookback:
            return False
        
        # CVD rising but price falling = bullish divergence
        if price_trend == "DOWN" and self.is_cvd_rising():
            self.logger.info("BULLISH CVD divergence detected")
            return True
        
        # CVD falling but price rising = bearish divergence
        if price_trend == "UP" and self.is_cvd_falling():
            self.logger.info("BEARISH CVD divergence detected")
            return True
        
        return False
    
    def get_metrics(self, timestamp: int) -> OrderFlowMetrics:
        """
        Get current order flow metrics
        
        Args:
            timestamp: Current timestamp
            
        Returns:
            OrderFlowMetrics object
        """
        oi_change_pct = 0.0
        if self.previous_oi > 0:
            oi_change_pct = ((self.current_oi - self.previous_oi) / self.previous_oi) * 100
        
        current_delta = self.delta_history[-1] if self.delta_history else 0.0
        
        return OrderFlowMetrics(
            timestamp=timestamp,
            delta=current_delta,
            cumulative_delta=self.cumulative_delta,
            delta_trend=self.cvd_trend,
            buy_volume=self.buy_volume_current,
            sell_volume=self.sell_volume_current,
            total_volume=self.buy_volume_current + self.sell_volume_current,
            oi=self.current_oi,
            oi_change=self.current_oi - self.previous_oi,
            oi_change_percent=oi_change_pct,
            imbalance_ratio=self.current_imbalance_ratio,
            absorption_detected=self.absorption_detected,
            absorption_price=self.absorption_price,
            absorption_volume=self.absorption_volume,
            consecutive_buy_bars=self.consecutive_buy_bars,
            consecutive_sell_bars=self.consecutive_sell_bars,
        )
    
    def reset(self):
        """Reset all metrics (e.g., for new session)"""
        self.logger.info("Resetting OrderFlow metrics")
        self.cumulative_delta = 0.0
        self.cvd_history.clear()
        self.delta_history.clear()
        self.volume_history.clear()
        self.price_history.clear()
        self.consecutive_buy_bars = 0
        self.consecutive_sell_bars = 0
        self.absorption_detected = False
