"""
Price Action Analysis Module
Features 21-35: Price Action Features
"""
import numpy as np
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class PriceActionFeatures:
    """Price action features (21-35)"""
    body_percent: float = 0.0
    upper_wick_ratio: float = 0.0
    lower_wick_ratio: float = 0.0
    range_expansion: float = 0.0
    breakout_strength: float = 0.0
    swing_high_dist: float = 0.0
    swing_low_dist: float = 0.0
    hh_count: int = 0
    ll_count: int = 0
    hl_count: int = 0
    lh_count: int = 0
    trend_structure: int = 0  # 1 = uptrend, -1 = downtrend, 0 = neutral
    consolidation_bars: int = 0
    volatility_contraction: bool = False
    key_level_distance: float = 0.0


def find_swing_points(highs: List[float], lows: List[float], lookback: int = 5) -> tuple:
    """Find swing highs and lows"""
    swing_highs = []
    swing_lows = []
    
    for i in range(lookback, len(highs) - lookback):
        # Swing high: higher than lookback bars on both sides
        if highs[i] == max(highs[i-lookback:i+lookback+1]):
            swing_highs.append((i, highs[i]))
        
        # Swing low: lower than lookback bars on both sides
        if lows[i] == min(lows[i-lookback:i+lookback+1]):
            swing_lows.append((i, lows[i]))
    
    return swing_highs, swing_lows


def analyze_market_structure(swing_highs: List[tuple], swing_lows: List[tuple]) -> tuple:
    """Analyze HH/HL/LH/LL patterns"""
    hh_count = 0
    ll_count = 0
    hl_count = 0
    lh_count = 0
    
    # Count higher highs and lower highs
    if len(swing_highs) >= 2:
        for i in range(1, min(10, len(swing_highs))):
            if swing_highs[-i][1] > swing_highs[-i-1][1]:
                hh_count += 1
            else:
                lh_count += 1
    
    # Count higher lows and lower lows
    if len(swing_lows) >= 2:
        for i in range(1, min(10, len(swing_lows))):
            if swing_lows[-i][1] > swing_lows[-i-1][1]:
                hl_count += 1
            else:
                ll_count += 1
    
    return hh_count, ll_count, hl_count, lh_count


def calculate_support_resistance(candles: List, lookback: int = 50) -> tuple:
    """Calculate key support and resistance levels"""
    if len(candles) < lookback:
        return [], []
    
    recent = candles[-lookback:]
    highs = [c.high for c in recent]
    lows = [c.low for c in recent]
    
    # Simple approach: use swing points as S/R
    swing_highs, swing_lows = find_swing_points(highs, lows, 3)
    
    resistance_levels = [sh[1] for sh in swing_highs[-5:]] if swing_highs else []
    support_levels = [sl[1] for sl in swing_lows[-5:]] if swing_lows else []
    
    return support_levels, resistance_levels


def calculate_volatility_contraction(ranges: List[float], period: int = 10) -> bool:
    """Detect volatility contraction (narrowing ranges)"""
    if len(ranges) < period:
        return False
    
    recent = ranges[-period:]
    earlier = ranges[-period*2:-period] if len(ranges) >= period * 2 else ranges[:period]
    
    if not earlier:
        return False
    
    avg_recent = np.mean(recent)
    avg_earlier = np.mean(earlier)
    
    # Contraction if recent range is < 70% of earlier
    return avg_recent < avg_earlier * 0.7


class PriceActionAnalyzer:
    """Calculate all price action features"""
    
    def __init__(self):
        self.support_levels: List[float] = []
        self.resistance_levels: List[float] = []
    
    def calculate(self, candles: List) -> PriceActionFeatures:
        """Calculate all price action features"""
        if not candles or len(candles) < 2:
            return PriceActionFeatures()
        
        features = PriceActionFeatures()
        current = candles[-1]
        
        # Current candle analysis
        if current.range > 0:
            features.body_percent = current.body / current.range
            features.upper_wick_ratio = current.upper_wick / current.range
            features.lower_wick_ratio = current.lower_wick / current.range
        
        # Range expansion
        avg_range = np.mean([c.range for c in candles[-20:]]) if len(candles) >= 20 else current.range
        features.range_expansion = current.range / avg_range if avg_range > 0 else 1.0
        
        # Extract price series
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        
        # Swing points
        swing_highs, swing_lows = find_swing_points(highs, lows, 5)
        
        # Distance to swing points
        current_price = current.close
        if swing_highs:
            features.swing_high_dist = (swing_highs[-1][1] - current_price) / current_price
        if swing_lows:
            features.swing_low_dist = (current_price - swing_lows[-1][1]) / current_price
        
        # Market structure analysis
        hh, ll, hl, lh = analyze_market_structure(swing_highs, swing_lows)
        features.hh_count = hh
        features.ll_count = ll
        features.hl_count = hl
        features.lh_count = lh
        
        # Trend structure
        if hh > lh and hl > ll:
            features.trend_structure = 1  # Uptrend
        elif lh > hh and ll > hl:
            features.trend_structure = -1  # Downtrend
        else:
            features.trend_structure = 0  # Neutral
        
        # Breakout strength (how far above/below recent range)
        if len(candles) >= 20:
            recent_high = max(highs[-20:-1])
            recent_low = min(lows[-20:-1])
            recent_range = recent_high - recent_low
            
            if recent_range > 0:
                if current.close > recent_high:
                    features.breakout_strength = (current.close - recent_high) / recent_range
                elif current.close < recent_low:
                    features.breakout_strength = (recent_low - current.close) / recent_range
        
        # Consolidation bars (bars within a tight range)
        if len(candles) >= 10:
            ranges = [c.range for c in candles[-10:]]
            avg_range = np.mean(ranges)
            consolidation = sum(1 for r in ranges if r < avg_range * 0.5)
            features.consolidation_bars = consolidation
        
        # Volatility contraction
        ranges = [c.range for c in candles]
        features.volatility_contraction = calculate_volatility_contraction(ranges)
        
        # Key level distance
        self.support_levels, self.resistance_levels = calculate_support_resistance(candles)
        
        nearest_support = min(self.support_levels, key=lambda x: abs(x - current_price), default=current_price)
        nearest_resistance = min(self.resistance_levels, key=lambda x: abs(x - current_price), default=current_price)
        
        dist_support = abs(current_price - nearest_support) / current_price
        dist_resistance = abs(nearest_resistance - current_price) / current_price
        features.key_level_distance = min(dist_support, dist_resistance)
        
        return features

