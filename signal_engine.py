"""
Signal Engine

Combines TPO, VWAP, and Order Flow analysis to generate trading signals:
- Long Entry signals
- Short Entry signals  
- Failure Pattern signals (fake breakouts)
"""

import logging
from typing import Optional, Dict
from datetime import datetime

from models import (
    SignalEvent, SignalType, SignalConditions,
    TPOProfile, VWAPData, OrderFlowMetrics,
    TPOStructureEvent
)
import utils


class SignalEngine:
    """
    Trading Signal Engine
    
    Combines multiple indicators to generate high-confidence signals
    """
    
    def __init__(self, symbol: str, config: dict):
        """
        Initialize signal engine
        
        Args:
            symbol: Trading symbol
            config: Signal configuration
        """
        self.logger = utils.get_logger('signal_engine')
        self.symbol = symbol
        self.config = config
        
        # Signal configuration
        self.long_config = config['long']
        self.short_config = config['short']
        self.failure_config = config['failure']
        self.cooldown_seconds = config['cooldown_seconds']
        
        # Last signal tracking (for cooldown)
        self.last_long_signal_time: Optional[int] = None
        self.last_short_signal_time: Optional[int] = None
        self.last_failure_signal_time: Optional[int] = None
        
        # Recent price tracking for failure patterns
        self.recent_high: Optional[float] = None
        self.recent_low: Optional[float] = None
        
        self.logger.info(f"SignalEngine initialized for {symbol}")
    
    def check_signals(
        self,
        current_time: int,
        current_price: float,
        tpo_data: Optional[TPOProfile],
        tpo_event: Optional[TPOStructureEvent],
        vwap_data: Optional[VWAPData],
        orderflow_data: Optional[OrderFlowMetrics]
    ) -> Optional[SignalEvent]:
        """
        Check for trading signals
        
        Args:
            current_time: Current timestamp
            current_price: Current price
            tpo_data: TPO profile data
            tpo_event: Recent TPO structure event
            vwap_data: VWAP data
            orderflow_data: Order flow metrics
            
        Returns:
            SignalEvent if signal detected, None otherwise
        """
        # Update price tracking
        self._update_price_tracking(current_price)
        
        # Check for failure patterns first (highest priority)
        failure_signal = self._check_failure_patterns(
            current_time, current_price, tpo_data, vwap_data, orderflow_data
        )
        if failure_signal:
            return failure_signal
        
        # Check for long entry
        long_signal = self._check_long_entry(
            current_time, current_price, tpo_data, tpo_event, vwap_data, orderflow_data
        )
        if long_signal:
            return long_signal
        
        # Check for short entry
        short_signal = self._check_short_entry(
            current_time, current_price, tpo_data, tpo_event, vwap_data, orderflow_data
        )
        if short_signal:
            return short_signal
        
        return None
    
    def _check_long_entry(
        self,
        current_time: int,
        current_price: float,
        tpo_data: Optional[TPOProfile],
        tpo_event: Optional[TPOStructureEvent],
        vwap_data: Optional[VWAPData],
        orderflow_data: Optional[OrderFlowMetrics]
    ) -> Optional[SignalEvent]:
        """
        Check for LONG ENTRY signal
        
        Conditions:
        1. TPO: VAL bounce, POC reclaim, or VAH breakout
        2. VWAP: Price near/above VWAP with pullback
        3. OrderFlow: Delta+, CVD↑, OI↑, consecutive buying
        """
        # Check cooldown
        if self._is_in_cooldown(self.last_long_signal_time, current_time):
            return None
        
        # Validate data
        if not all([tpo_data, vwap_data, orderflow_data]):
            return None
        
        conditions = SignalConditions()
        confidence = 0.0
        
        # ===== TPO CONDITIONS =====
        tpo_valid = False
        
        if tpo_event in [
            TPOStructureEvent.VAL_BOUNCE,
            TPOStructureEvent.POC_RECLAIM,
            TPOStructureEvent.VAH_BREAKOUT
        ]:
            tpo_valid = True
            conditions.tpo_event = tpo_event
            conditions.tpo_proximity = tpo_data.distance_to_poc(current_price)
            confidence += 0.25
            self.logger.debug(f"Long TPO condition met: {tpo_event.value}")
        
        if not tpo_valid:
            return None  # TPO condition is required
        
        # ===== VWAP CONDITIONS =====
        vwap_valid = False
        
        # Check if price is above or pulling back to VWAP
        if current_price >= vwap_data.vwap:
            conditions.vwap_aligned = True
            vwap_valid = True
            confidence += 0.15
            self.logger.debug("Long VWAP condition met: price above VWAP")
        
        # Bonus for pullback to VWAP
        if vwap_data.is_pullback_zone(current_price, self.long_config['vwap_pullback_tolerance']):
            conditions.vwap_aligned = True
            vwap_valid = True
            confidence += 0.25  # Higher weight for pullback
            self.logger.debug("Long VWAP pullback detected")
        
        # VWAP slope (uptrend)
        if vwap_data.slope > 0:
            conditions.vwap_slope = vwap_data.slope
            confidence += 0.10
        
        conditions.vwap_distance = abs(current_price - vwap_data.vwap) / vwap_data.vwap * 100
        
        if not vwap_valid:
            return None  # VWAP alignment required
        
        # ===== ORDER FLOW CONDITIONS =====
        require_all_of = self.long_config['require_all_orderflow']
        of_score = 0
        of_conditions_met = 0
        of_conditions_total = 4
        
        # Delta positive
        if orderflow_data.delta > 0:
            conditions.delta_confirmed = True
            of_conditions_met += 1
            of_score += 0.10
        
        # CVD rising
        if orderflow_data.delta_trend.value == "BULLISH":
            conditions.cvd_confirmed = True
            of_conditions_met += 1
            of_score += 0.10
        
        # OI increasing (new longs opening)
        if orderflow_data.oi_change_percent > 0:
            conditions.oi_confirmed = True
            of_conditions_met += 1
            of_score += 0.05
        
        # Consecutive buying
        if orderflow_data.consecutive_buy_bars >= 2:
            conditions.aggressive_flow = True
            of_conditions_met += 1
            of_score += 0.10
        
        if require_all_of:
            if of_conditions_met < of_conditions_total:
                self.logger.debug(
                    f"Long OF failed: {of_conditions_met}/{of_conditions_total} conditions met "
                    f"(Delta:{conditions.delta_confirmed}, CVD:{conditions.cvd_confirmed}, "
                    f"OI:{conditions.oi_confirmed}, Flow:{conditions.aggressive_flow})"
                )
                return None  # All OF conditions required
            confidence += of_score
        else:
            # At least 3 out of 4
            if of_conditions_met < 3:
                self.logger.debug(
                    f"Long OF failed: {of_conditions_met}/4 conditions met (need 3+) "
                    f"(Delta:{conditions.delta_confirmed}, CVD:{conditions.cvd_confirmed}, "
                    f"OI:{conditions.oi_confirmed}, Flow:{conditions.aggressive_flow})"
                )
                return None
            confidence += of_score
        
        # Check minimum confidence
        if confidence < self.long_config['min_confidence']:
            self.logger.debug(
                f"Long signal检测到但置信度不足: {confidence:.2f} < {self.long_config['min_confidence']} "
                f"(TPO:{tpo_valid}, VWAP:{vwap_valid}, OF:{of_conditions_met}/4)"
            )
            return None
        
        # ===== GENERATE SIGNAL =====
        self.last_long_signal_time = current_time
        
        signal = SignalEvent(
            timestamp=current_time,
            symbol=self.symbol,
            signal_type=SignalType.LONG_ENTRY,
            price=current_price,
            conditions=conditions,
            confidence=min(confidence, 1.0),
            tpo_data=tpo_data,
            vwap_data=vwap_data,
            orderflow_data=orderflow_data
        )
        
        self.logger.info(
            f"🚀 LONG ENTRY SIGNAL: {current_price:.2f} (confidence: {confidence:.0%})"
        )
        
        return signal
    
    def _check_short_entry(
        self,
        current_time: int,
        current_price: float,
        tpo_data: Optional[TPOProfile],
        tpo_event: Optional[TPOStructureEvent],
        vwap_data: Optional[VWAPData],
        orderflow_data: Optional[OrderFlowMetrics]
    ) -> Optional[SignalEvent]:
        """
        Check for SHORT ENTRY signal
        
        Conditions:
        1. TPO: VAH rejection, POC breakdown, or VAL break
        2. VWAP: Price below VWAP or rejected at VWAP
        3. OrderFlow: Delta-, CVD↓, OI↑, consecutive selling
        """
        # Check cooldown
        if self._is_in_cooldown(self.last_short_signal_time, current_time):
            return None
        
        # Validate data
        if not all([tpo_data, vwap_data, orderflow_data]):
            return None
        
        conditions = SignalConditions()
        confidence = 0.0
        
        # ===== TPO CONDITIONS =====
        tpo_valid = False
        
        if tpo_event in [
            TPOStructureEvent.VAH_REJECTION,
            TPOStructureEvent.POC_BREAKDOWN,
            TPOStructureEvent.VAL_BREAK
        ]:
            tpo_valid = True
            conditions.tpo_event = tpo_event
            conditions.tpo_proximity = tpo_data.distance_to_poc(current_price)
            confidence += 0.25
            self.logger.debug(f"Short TPO condition met: {tpo_event.value}")
        
        if not tpo_valid:
            return None
        
        # ===== VWAP CONDITIONS =====
        vwap_valid = False
        
        # Check if price is below VWAP or rejected
        if current_price <= vwap_data.vwap:
            conditions.vwap_aligned = True
            vwap_valid = True
            confidence += 0.15
            self.logger.debug("Short VWAP condition met: price below VWAP")
        
        # Check for rejection at VWAP
        if vwap_data.is_pullback_zone(current_price, self.short_config['vwap_rejection_tolerance']):
            # Additional check: orderflow should be bearish
            if orderflow_data.delta < 0:
                conditions.vwap_aligned = True
                vwap_valid = True
                confidence += 0.25
                self.logger.debug("Short VWAP rejection detected")
        
        # VWAP slope (downtrend)
        if vwap_data.slope < 0:
            conditions.vwap_slope = vwap_data.slope
            confidence += 0.10
        
        conditions.vwap_distance = abs(current_price - vwap_data.vwap) / vwap_data.vwap * 100
        
        if not vwap_valid:
            return None
        
        # ===== ORDER FLOW CONDITIONS =====
        require_all_of = self.short_config['require_all_orderflow']
        of_score = 0
        of_conditions_met = 0
        of_conditions_total = 4
        
        # Delta negative
        if orderflow_data.delta < 0:
            conditions.delta_confirmed = True
            of_conditions_met += 1
            of_score += 0.10
        
        # CVD falling
        if orderflow_data.delta_trend.value == "BEARISH":
            conditions.cvd_confirmed = True
            of_conditions_met += 1
            of_score += 0.10
        
        # OI increasing (new shorts opening)
        if orderflow_data.oi_change_percent > 0:
            conditions.oi_confirmed = True
            of_conditions_met += 1
            of_score += 0.05
        
        # Consecutive selling
        if orderflow_data.consecutive_sell_bars >= 2:
            conditions.aggressive_flow = True
            of_conditions_met += 1
            of_score += 0.10
        
        if require_all_of:
            if of_conditions_met < of_conditions_total:
                return None
            confidence += of_score
        else:
            if of_conditions_met < 3:
                return None
            confidence += of_score
        
        # Check minimum confidence
        if confidence < self.short_config['min_confidence']:
            self.logger.debug(f"Short signal below confidence threshold: {confidence:.2f}")
            return None
        
        # ===== GENERATE SIGNAL =====
        self.last_short_signal_time = current_time
        
        signal = SignalEvent(
            timestamp=current_time,
            symbol=self.symbol,
            signal_type=SignalType.SHORT_ENTRY,
            price=current_price,
            conditions=conditions,
            confidence=min(confidence, 1.0),
            tpo_data=tpo_data,
            vwap_data=vwap_data,
            orderflow_data=orderflow_data
        )
        
        self.logger.info(
            f"🔻 SHORT ENTRY SIGNAL: {current_price:.2f} (confidence: {confidence:.0%})"
        )
        
        return signal
    
    def _check_failure_patterns(
        self,
        current_time: int,
        current_price: float,
        tpo_data: Optional[TPOProfile],
        vwap_data: Optional[VWAPData],
        orderflow_data: Optional[OrderFlowMetrics]
    ) -> Optional[SignalEvent]:
        """
        Check for FAILURE PATTERNS (fake breakouts)
        
        Long Trap → Short:
        - Price breaks above key level
        - Delta flips negative
        - CVD divergence
        - Absorption at highs
        
        Short Trap → Long:
        - Price breaks below key level
        - Delta flips positive
        - CVD divergence
        - Absorption at lows
        """
        # Check cooldown
        if self._is_in_cooldown(self.last_failure_signal_time, current_time):
            return None
        
        # Validate data
        if not all([tpo_data, vwap_data, orderflow_data]):
            return None
        
        conditions = SignalConditions()
        
        # Check for upside failure (long trap → short)
        upside_failure = self._check_upside_failure(
            current_price, tpo_data, vwap_data, orderflow_data, conditions
        )
        
        if upside_failure:
            confidence = upside_failure  # Returns confidence score
            
            signal = SignalEvent(
                timestamp=current_time,
                symbol=self.symbol,
                signal_type=SignalType.SHORT_FAILURE,
                price=current_price,
                conditions=conditions,
                confidence=min(confidence, 1.0),
                tpo_data=tpo_data,
                vwap_data=vwap_data,
                orderflow_data=orderflow_data
            )
            
            self.last_failure_signal_time = current_time
            self.logger.info(
                f"⚠️  UPSIDE FAILURE PATTERN (Short): {current_price:.2f} (confidence: {confidence:.0%})"
            )
            return signal
        
        # Check for downside failure (short trap → long)
        downside_failure = self._check_downside_failure(
            current_price, tpo_data, vwap_data, orderflow_data, conditions
        )
        
        if downside_failure:
            confidence = downside_failure
            
            signal = SignalEvent(
                timestamp=current_time,
                symbol=self.symbol,
                signal_type=SignalType.LONG_FAILURE,
                price=current_price,
                conditions=conditions,
                confidence=min(confidence, 1.0),
                tpo_data=tpo_data,
                vwap_data=vwap_data,
                orderflow_data=orderflow_data
            )
            
            self.last_failure_signal_time = current_time
            self.logger.info(
                f"⚠️  DOWNSIDE FAILURE PATTERN (Long): {current_price:.2f} (confidence: {confidence:.0%})"
            )
            return signal
        
        return None
    
    def _check_upside_failure(
        self,
        price: float,
        tpo_data: TPOProfile,
        vwap_data: VWAPData,
        orderflow_data: OrderFlowMetrics,
        conditions: SignalConditions
    ) -> float:
        """
        Check for upside failure (long trap)
        
        Returns:
            Confidence score if pattern detected, 0 otherwise
        """
        confidence = 0.0
        
        # Must be near a key high level
        near_key_level = (
            utils.is_near(price, tpo_data.vah, 0.2) or
            utils.is_near(price, vwap_data.upper_1std, 0.2)
        )
        
        if not near_key_level:
            return 0.0
        
        # Check if we recently made new high
        if self.recent_high and price >= self.recent_high * 0.998:
            confidence += 0.2
            conditions.tpo_event = TPOStructureEvent.VAH_REJECTION
        else:
            return 0.0  # Must be at/near recent high
        
        # Delta flip (positive → negative)
        if orderflow_data.delta < 0:
            conditions.delta_flip = True
            confidence += 0.3
        
        # CVD divergence (price up but CVD not confirming)
        if orderflow_data.delta_trend.value != "BULLISH":
            conditions.cvd_divergence = True
            confidence += 0.2
        
        # Absorption at highs
        if orderflow_data.absorption_detected:
            conditions.absorption = True
            confidence += 0.3
        
        # Minimum confidence check
        if confidence < self.failure_config['min_confidence']:
            return 0.0
        
        return confidence
    
    def _check_downside_failure(
        self,
        price: float,
        tpo_data: TPOProfile,
        vwap_data: VWAPData,
        orderflow_data: OrderFlowMetrics,
        conditions: SignalConditions
    ) -> float:
        """
        Check for downside failure (short trap)
        
        Returns:
            Confidence score if pattern detected, 0 otherwise
        """
        confidence = 0.0
        
        # Must be near a key low level
        near_key_level = (
            utils.is_near(price, tpo_data.val, 0.2) or
            utils.is_near(price, vwap_data.lower_1std, 0.2)
        )
        
        if not near_key_level:
            return 0.0
        
        # Check if we recently made new low
        if self.recent_low and price <= self.recent_low * 1.002:
            confidence += 0.2
            conditions.tpo_event = TPOStructureEvent.VAL_BOUNCE
        else:
            return 0.0
        
        # Delta flip (negative → positive)
        if orderflow_data.delta > 0:
            conditions.delta_flip = True
            confidence += 0.3
        
        # CVD divergence (price down but CVD not confirming)
        if orderflow_data.delta_trend.value != "BEARISH":
            conditions.cvd_divergence = True
            confidence += 0.2
        
        # Absorption at lows
        if orderflow_data.absorption_detected:
            conditions.absorption = True
            confidence += 0.3
        
        # Minimum confidence check
        if confidence < self.failure_config['min_confidence']:
            return 0.0
        
        return confidence
    
    def _update_price_tracking(self, price: float):
        """Update recent high/low tracking"""
        if self.recent_high is None or price > self.recent_high:
            self.recent_high = price
        
        if self.recent_low is None or price < self.recent_low:
            self.recent_low = price
    
    def _is_in_cooldown(self, last_signal_time: Optional[int], current_time: int) -> bool:
        """Check if signal is in cooldown period"""
        if last_signal_time is None:
            return False
        
        time_diff_seconds = (current_time - last_signal_time) / 1000
        return time_diff_seconds < self.cooldown_seconds
