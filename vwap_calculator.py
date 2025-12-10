"""
VWAP Calculator

Calculates Volume-Weighted Average Price with standard deviation bands.
Tracks VWAP trend and detects pullback/rejection patterns.
"""

import logging
from typing import Optional, List
from collections import deque

from models import VWAPData, Candle
import utils


class VWAPCalculator:
    """
    VWAP (Volume-Weighted Average Price) Calculator
    
    Calculates:
    - Session VWAP
    -±1σ and ±2σ standard deviation bands
    - VWAP slope (trend direction)
    - Pullback/rejection detection
    """
    
    def __init__(self, symbol: str, config: dict):
        """
        Initialize VWAP calculator
        
        Args:
            symbol: Trading symbol
            config: VWAP configuration
        """
        self.logger = utils.get_logger('vwap_calculator')
        self.symbol = symbol
        self.config = config
        
        # Session settings
        self.session_reset_time = config['session_reset']
        self.std_dev_bands = config['std_dev_bands']
        
        # Slope calculation
        self.slope_lookback = config['slope_lookback_bars']
        self.slope_threshold = config['slope_threshold']
        
        # Pullback detection
        self.pullback_tolerance = config['pullback']['tolerance_percent']
        self.pullback_confirmation_bars = config['pullback']['confirmation_bars']
        
        # Session tracking
        self.current_session_start: Optional[int] = None
        
        # VWAP calculation components
        self.cumulative_pv = 0.0  # Σ(Price × Volume)
        self.cumulative_volume = 0.0  # Σ(Volume)
        self.cumulative_pv2 = 0.0  # Σ(Price² × Volume) for variance
        
        # Current VWAP data
        self.current_vwap: Optional[VWAPData] = None
        
        # VWAP history for slope calculation
        self.vwap_history: deque = deque(maxlen=self.slope_lookback)
        
        # Pullback tracking
        self.consecutive_pullback_bars = 0
        self.consecutive_rejection_bars = 0
        
        self.logger.info(f"VWAPCalculator initialized for {symbol}")
    
    def update(self, candle: Candle) -> VWAPData:
        """
        Update VWAP with new candle
        
        Args:
            candle: New candle data
            
        Returns:
            Updated VWAP data
        """
        # Check if new session
        session_start = utils.get_session_start(candle.timestamp, self.session_reset_time)
        
        if self.current_session_start is None or session_start != self.current_session_start:
            self._reset_session(session_start)
        
        # Calculate typical price (HLC/3)
        typical_price = (candle.high + candle.low + candle.close) / 3
        
        # Update cumulative values
        pv = typical_price * candle.volume
        self.cumulative_pv += pv
        self.cumulative_volume += candle.volume
        self.cumulative_pv2 += (typical_price ** 2) * candle.volume
        
        # Calculate VWAP
        if self.cumulative_volume == 0:
            vwap = typical_price
        else:
            vwap = self.cumulative_pv / self.cumulative_volume
        
        # Calculate variance and standard deviation
        if self.cumulative_volume == 0:
            variance = 0
        else:
            variance = (self.cumulative_pv2 / self.cumulative_volume) - (vwap ** 2)
        
        std_dev = max(0, variance) ** 0.5
        
        # Calculate bands
        upper_1std = vwap + std_dev
        lower_1std = vwap - std_dev
        upper_2std = vwap + (2 * std_dev)
        lower_2std = vwap - (2 * std_dev)
        
        # Create VWAP data
        self.current_vwap = VWAPData(
            timestamp=candle.timestamp,
            vwap=vwap,
            upper_1std=upper_1std,
            lower_1std=lower_1std,
            upper_2std=upper_2std,
            lower_2std=lower_2std,
            cumulative_vp=self.cumulative_pv,
            cumulative_volume=self.cumulative_volume,
            slope=self._calculate_slope()
        )
        
        # Add to history
        self.vwap_history.append(vwap)
        
        # Update pullback/rejection tracking
        self._update_pullback_tracking(candle.close)
        
        self.logger.debug(f"VWAP updated: {vwap:.2f} (slope: {self.current_vwap.slope:.6f})")
        
        return self.current_vwap
    
    def _reset_session(self, session_start: int):
        """Reset for new session"""
        self.logger.info(f"Resetting VWAP for new session at {utils.format_timestamp(session_start)}")
        
        self.current_session_start = session_start
        self.cumulative_pv = 0.0
        self.cumulative_volume = 0.0
        self.cumulative_pv2 = 0.0
        self.vwap_history.clear()
        self.consecutive_pullback_bars = 0
        self.consecutive_rejection_bars = 0
    
    def _calculate_slope(self) -> float:
        """
        Calculate VWAP slope using linear regression
        
        Returns:
            Slope value (positive = uptrend, negative = downtrend)
        """
        if len(self.vwap_history) < 2:
            return 0.0
        
        values = list(self.vwap_history)
        slope = utils.calculate_slope(values)
        
        return slope
    
    def _update_pullback_tracking(self, price: float):
        """Track consecutive pullback/rejection bars"""
        if not self.current_vwap:
            return
        
        # Check if price is pulling back to VWAP
        if self.is_pullback(price):
            self.consecutive_pullback_bars += 1
            self.consecutive_rejection_bars = 0
        # Check if price is being rejected by VWAP
        elif self.is_rejection(price):
            self.consecutive_rejection_bars += 1
            self.consecutive_pullback_bars = 0
        else:
            self.consecutive_pullback_bars = 0
            self.consecutive_rejection_bars = 0
    
    def is_pullback(self, price: float, tolerance: Optional[float] = None) -> bool:
        """
        Check if price is pulling back to VWAP
        
        Args:
            price: Current price
            tolerance: Tolerance percentage (default from config)
            
        Returns:
            True if price is touching VWAP from above/below
        """
        if not self.current_vwap:
            return False
        
        if tolerance is None:
            tolerance = self.pullback_tolerance
        
        # Price is within tolerance of VWAP
        return abs(price - self.current_vwap.vwap) / self.current_vwap.vwap * 100 <= tolerance
    
    def is_rejection(self, price: float) -> bool:
        """
        Check if price is being rejected by VWAP
        
        Similar to pullback but requires price to be moving away after touching
        (This is a simplified version - could be enhanced with more sophisticated logic)
        
        Args:
            price: Current price
            
        Returns:
            True if rejection detected
        """
        if not self.current_vwap or len(self.vwap_history) < 2:
            return False
        
        # Price was near VWAP but is now moving away
        previous_vwap = self.vwap_history[-2] if len(self.vwap_history) >= 2 else self.current_vwap.vwap
        
        was_near = abs(price - previous_vwap) / previous_vwap * 100 <= self.pullback_tolerance
        is_moving_away = abs(price - self.current_vwap.vwap) / self.current_vwap.vwap * 100 > self.pullback_tolerance
        
        return was_near and is_moving_away
    
    def is_pullback_confirmed(self) -> bool:
        """
        Check if pullback is confirmed (multiple bars touching VWAP)
        
        Returns:
            True if pullback confirmed
        """
        return self.consecutive_pullback_bars >= self.pullback_confirmation_bars
    
    def is_rejection_confirmed(self) -> bool:
        """
        Check if rejection is confirmed
        
        Returns:
            True if rejection confirmed
        """
        return self.consecutive_rejection_bars >= self.pullback_confirmation_bars
    
    def is_trending_up(self) -> bool:
        """
        Check if VWAP is trending upward
        
        Returns:
            True if uptrend
        """
        if not self.current_vwap:
            return False
        
        return self.current_vwap.slope > self.slope_threshold
    
    def is_trending_down(self) -> bool:
        """
        Check if VWAP is trending downward
        
        Returns:
            True if downtrend
        """
        if not self.current_vwap:
            return False
        
        return self.current_vwap.slope < -self.slope_threshold
    
    def get_vwap_data(self) -> Optional[VWAPData]:
        """Get current VWAP data"""
        return self.current_vwap
    
    def get_price_position(self, price: float) -> str:
        """
        Get price position relative to VWAP
        
        Args:
            price: Current price
            
        Returns:
            Position string: "ABOVE", "BELOW", or "AT"
        """
        if not self.current_vwap:
            return "UNKNOWN"
        
        if self.is_pullback(price):
            return "AT"
        elif price > self.current_vwap.vwap:
            return "ABOVE"
        else:
            return "BELOW"
    
    def get_band_level(self, price: float) -> str:
        """
        Get which VWAP band price is at
        
        Args:
            price: Current price
            
        Returns:
            Band level: "VWAP", "+1SD", "+2SD", "-1SD", "-2SD", or "NEUTRAL"
        """
        if not self.current_vwap:
            return "UNKNOWN"
        
        tolerance_pct = 0.1  # 0.1% tolerance
        
        if utils.is_near(price, self.current_vwap.vwap, tolerance_pct):
            return "VWAP"
        elif utils.is_near(price, self.current_vwap.upper_1std, tolerance_pct):
            return "+1SD"
        elif utils.is_near(price, self.current_vwap.upper_2std, tolerance_pct):
            return "+2SD"
        elif utils.is_near(price, self.current_vwap.lower_1std, tolerance_pct):
            return "-1SD"
        elif utils.is_near(price, self.current_vwap.lower_2std, tolerance_pct):
            return "-2SD"
        else:
            return "NEUTRAL"
