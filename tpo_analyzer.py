"""
TPO (Market Profile) Analyzer

Calculates and tracks TPO structure:
- Value Area High (VAH)
- Value Area Low (VAL)  
- Point of Control (POC)
- Detects structural events (breakouts, rejections, reclaims)
"""

import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime

from models import TPOProfile, TPOStructureEvent, Candle
import utils


class TPOAnalyzer:
    """
    Market Profile / TPO (Time Price Opportunity) Analyzer
    
    Builds TPO structure and identifies key price levels
    """
    
    def __init__(self, symbol: str, config: dict):
        """
        Initialize TPO analyzer
        
        Args:
            symbol: Trading symbol
            config: TPO configuration
        """
        self.logger = utils.get_logger('tpo_analyzer')
        self.symbol = symbol
        self.config = config
        
        # Session settings
        self.session_start_time = config['session_start']
        self.session_duration_hours = config['session_duration']
        self.time_slice_minutes = config['time_slice_minutes']
        self.value_area_percent = config['value_area_percent']
        
        # Structure detection settings
        self.proximity_ticks = config['structure']['proximity_ticks']
        self.tick_size = 0.1  # BTCUSDT tick size (will auto-detect)
        
        # Current session data
        self.current_session_start: Optional[int] = None
        self.current_profile: Optional[TPOProfile] = None
        self.previous_profile: Optional[TPOProfile] = None
        
        # Price-Volume distribution
        self.price_volume_map: Dict[float, float] = defaultdict(float)
        self.price_time_map: Dict[float, List[str]] = defaultdict(list)
        
        # TPO letters (A, B, C, ...)
        self.current_letter_index = 0
        self.last_slice_time: Optional[int] = None
        
        # Price tracking for structure events
        self.last_price: Optional[float] = None
        
        self.logger.info(f"TPOAnalyzer initialized for {symbol}")
    
    def update(self, candle: Candle) -> Optional[TPOStructureEvent]:
        """
        Update TPO with new candle data
        
        Args:
            candle: New candle data
            
        Returns:
            Structure event if detected, None otherwise
        """
        # Check if new session
        session_start = utils.get_session_start(candle.timestamp, self.session_start_time)
        
        if self.current_session_start is None or session_start != self.current_session_start:
            self._start_new_session(session_start)
        
        # Check if new time slice (new TPO letter)
        if self._is_new_time_slice(candle.timestamp):
            self._advance_tpo_letter()
            self.last_slice_time = candle.timestamp
        
        # Add price-volume data
        self._add_price_volume(candle)
        
        # Recalculate profile
        self._calculate_profile()
        
        # Detect structure events
        event = self._detect_structure_event(candle.close)
        
        # Update last price
        self.last_price = candle.close
        
        return event
    
    def _start_new_session(self, session_start: int):
        """Start a new TPO session"""
        # Save previous session
        if self.current_profile:
            self.previous_profile = self.current_profile
            self.logger.info(
                f"Session ended. VAH: {self.current_profile.vah:.1f}, "
                f"POC: {self.current_profile.poc:.1f}, VAL: {self.current_profile.val:.1f}"
            )
        
        # Reset for new session
        self.current_session_start = session_start
        self.price_volume_map.clear()
        self.price_time_map.clear()
        self.current_letter_index = 0
        self.last_slice_time = None
        
        self.logger.info(f"New TPO session started at {utils.format_timestamp(session_start)}")
    
    def _is_new_time_slice(self, timestamp: int) -> bool:
        """Check if we entered a new time slice"""
        if self.last_slice_time is None:
            return True
        
        time_diff_minutes = (timestamp - self.last_slice_time) / (1000 * 60)
        return time_diff_minutes >= self.time_slice_minutes
    
    def _advance_tpo_letter(self):
        """Move to next TPO letter"""
        self.current_letter_index += 1
        letter = chr(ord('A') + self.current_letter_index % 26)
        self.logger.debug(f"Advanced to TPO letter: {letter}")
    
    def _add_price_volume(self, candle: Candle):
        """
        Add candle data to price-volume distribution
        
        Args:
            candle: Candle to process
        """
        # Round prices to tick size
        prices = [
            utils.round_to_tick(candle.open, self.tick_size),
            utils.round_to_tick(candle.high, self.tick_size),
            utils.round_to_tick(candle.low, self.tick_size),
            utils.round_to_tick(candle.close, self.tick_size)
        ]
        
        # Get current TPO letter
        letter = chr(ord('A') + self.current_letter_index % 26)
        
        # Distribute volume across price range
        price_range = candle.high - candle.low
        if price_range == 0:
            # Single price
            self.price_volume_map[candle.close] += candle.volume
            self.price_time_map[candle.close].append(letter)
        else:
            # Distribute proportionally
            current_price = candle.low
            while current_price <= candle.high:
                price_key = utils.round_to_tick(current_price, self.tick_size)
                
                # Simple equal distribution (could be improved with actual tick data)
                volume_at_price = candle.volume / (price_range / self.tick_size + 1)
                self.price_volume_map[price_key] += volume_at_price
                
                if letter not in self.price_time_map[price_key]:
                    self.price_time_map[price_key].append(letter)
                
                current_price += self.tick_size
    
    def _calculate_profile(self):
        """Calculate TPO profile (VAH, VAL, POC)"""
        if not self.price_volume_map:
            return
        
        # Find POC (Point of Control) - price with highest volume
        poc_price = max(self.price_volume_map.items(), key=lambda x: x[1])[0]
        poc_volume = self.price_volume_map[poc_price]
        
        # Calculate total volume
        total_volume = sum(self.price_volume_map.values())
        
        # Calculate Value Area (70% of volume around POC)
        target_volume = total_volume * (self.value_area_percent / 100)
        
        # Expand from POC until we reach target volume
        value_area_volume = poc_volume
        upper_price = poc_price
        lower_price = poc_price
        
        prices = sorted(self.price_volume_map.keys())
        poc_index = prices.index(poc_price)
        
        upper_index = poc_index
        lower_index = poc_index
        
        while value_area_volume < target_volume:
            # Get volume above and below
            volume_above = 0
            volume_below = 0
            
            if upper_index + 1 < len(prices):
                volume_above = self.price_volume_map[prices[upper_index + 1]]
            
            if lower_index - 1 >= 0:
                volume_below = self.price_volume_map[prices[lower_index - 1]]
            
            # Expand in direction with more volume
            if volume_above >= volume_below and upper_index + 1 < len(prices):
                upper_index += 1
                upper_price = prices[upper_index]
                value_area_volume += volume_above
            elif lower_index - 1 >= 0:
                lower_index -= 1
                lower_price = prices[lower_index]
                value_area_volume += volume_below
            else:
                break  # Can't expand further
        
        vah = upper_price
        val = lower_price
        
        # Create profile
        self.current_profile = TPOProfile(
            session_start=self.current_session_start,
            session_end=self.current_session_start + (self.session_duration_hours * 3600 * 1000),
            poc=poc_price,
            vah=vah,
            val=val,
            price_levels=dict(self.price_volume_map),
            tpo_letters={p: ''.join(letters) for p, letters in self.price_time_map.items()},
            total_volume=total_volume,
            value_area_volume=value_area_volume
        )
        
        self.logger.debug(
            f"Profile updated: VAH={vah:.1f}, POC={poc_price:.1f}, VAL={val:.1f}"
        )
    
    def _detect_structure_event(self, current_price: float) -> Optional[TPOStructureEvent]:
        """
        Detect TPO structure interaction events
        
        Args:
            current_price: Current price
            
        Returns:
            Detected event or None
        """
        if not self.current_profile or self.last_price is None:
            return None
        
        profile = self.current_profile
        proximity = self.proximity_ticks * self.tick_size
        
        # Check VAH events
        if utils.is_near(current_price, profile.vah, proximity):
            if self.last_price < profile.vah and current_price >= profile.vah:
                self.logger.info(f"VAH BREAKOUT detected at {current_price:.1f}")
                return TPOStructureEvent.VAH_BREAKOUT
            elif self.last_price > profile.vah and current_price <= profile.vah:
                self.logger.info(f"VAH REJECTION detected at {current_price:.1f}")
                return TPOStructureEvent.VAH_REJECTION
        
        # Check VAL events
        if utils.is_near(current_price, profile.val, proximity):
            if self.last_price > profile.val and current_price <= profile.val:
                self.logger.info(f"VAL BREAK detected at {current_price:.1f}")
                return TPOStructureEvent.VAL_BREAK
            elif self.last_price < profile.val and current_price >= profile.val:
                self.logger.info(f"VAL BOUNCE detected at {current_price:.1f}")
                return TPOStructureEvent.VAL_BOUNCE
        
        # Check POC events
        if utils.is_near(current_price, profile.poc, proximity):
            if self.last_price < profile.poc and current_price >= profile.poc:
                self.logger.info(f"POC RECLAIM detected at {current_price:.1f}")
                return TPOStructureEvent.POC_RECLAIM
            elif self.last_price > profile.poc and current_price <= profile.poc:
                self.logger.info(f"POC BREAKDOWN detected at {current_price:.1f}")
                return TPOStructureEvent.POC_BREAKDOWN
        
        # Check if inside/outside value area
        was_inside = profile.is_inside_value_area(self.last_price)
        is_inside = profile.is_inside_value_area(current_price)
        
        if not was_inside and is_inside:
            return TPOStructureEvent.INSIDE_VALUE_AREA
        elif was_inside and not is_inside:
            return TPOStructureEvent.OUTSIDE_VALUE_AREA
        
        return None
    
    def get_current_profile(self) -> Optional[TPOProfile]:
        """Get current TPO profile"""
        return self.current_profile
    
    def get_previous_profile(self) -> Optional[TPOProfile]:
        """Get previous session's TPO profile"""
        return self.previous_profile
    
    def is_near_key_level(self, price: float) -> Tuple[bool, Optional[str]]:
        """
        Check if price is near any key TPO level
        
        Args:
            price: Price to check
            
        Returns:
            (is_near, level_name) tuple
        """
        if not self.current_profile:
            return False, None
        
        proximity = self.proximity_ticks * self.tick_size
        
        if utils.is_near(price, self.current_profile.vah, proximity):
            return True, "VAH"
        if utils.is_near(price, self.current_profile.val, proximity):
            return True, "VAL"
        if utils.is_near(price, self.current_profile.poc, proximity):
            return True, "POC"
        
        return False, None
