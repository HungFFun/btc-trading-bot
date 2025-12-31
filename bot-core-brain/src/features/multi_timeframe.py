"""
Multi-Timeframe Analysis Module
Features 36-50: Multi-Timeframe Features
"""
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass

from .technical import calculate_ema, calculate_rsi


@dataclass
class MTFFeatures:
    """Multi-timeframe features (36-50)"""
    # 15m timeframe
    tf_15m_trend: int = 0  # -1, 0, 1
    tf_15m_strength: float = 0.0
    tf_15m_rsi: float = 50.0
    
    # 5m timeframe
    tf_5m_trend: int = 0
    tf_5m_strength: float = 0.0
    tf_5m_rsi: float = 50.0
    
    # 3m & 1m momentum
    tf_3m_momentum: float = 0.0
    tf_1m_momentum: float = 0.0
    
    # MTF alignment
    mtf_alignment: int = 0  # Number of aligned timeframes
    mtf_confluence_score: float = 0.0  # 0-100
    
    # Higher timeframe levels
    htf_support_dist: float = 0.0
    htf_resistance_dist: float = 0.0
    
    # Divergence and momentum
    tf_divergence: bool = False
    momentum_acceleration: float = 0.0
    trend_age_bars: int = 0


def calculate_trend_direction(candles: List, ema_short: int = 9, ema_long: int = 21) -> tuple:
    """Calculate trend direction and strength"""
    if len(candles) < ema_long:
        return 0, 0.0
    
    closes = [c.close for c in candles]
    
    ema_s = calculate_ema(closes, ema_short)
    ema_l = calculate_ema(closes, ema_long)
    
    current_price = closes[-1]
    
    # Direction
    if ema_s > ema_l and current_price > ema_s:
        direction = 1  # Uptrend
    elif ema_s < ema_l and current_price < ema_s:
        direction = -1  # Downtrend
    else:
        direction = 0  # Neutral
    
    # Strength: how far apart EMAs are as percentage of price
    ema_diff = abs(ema_s - ema_l) / current_price
    strength = min(1.0, ema_diff * 100)  # Normalize to 0-1
    
    return direction, strength


def calculate_momentum(candles: List, period: int = 10) -> float:
    """Calculate price momentum"""
    if len(candles) < period:
        return 0.0
    
    closes = [c.close for c in candles]
    current = closes[-1]
    previous = closes[-period]
    
    if previous == 0:
        return 0.0
    
    momentum = ((current - previous) / previous) * 100
    return momentum


def calculate_momentum_acceleration(candles: List, period: int = 5) -> float:
    """Calculate rate of change of momentum"""
    if len(candles) < period * 2:
        return 0.0
    
    closes = [c.close for c in candles]
    
    # Recent momentum
    recent_momentum = ((closes[-1] - closes[-period]) / closes[-period]) * 100 if closes[-period] != 0 else 0
    
    # Previous momentum
    prev_momentum = ((closes[-period] - closes[-period*2]) / closes[-period*2]) * 100 if closes[-period*2] != 0 else 0
    
    # Acceleration is the change in momentum
    return recent_momentum - prev_momentum


def detect_tf_divergence(tf1_direction: int, tf2_direction: int, tf3_direction: int) -> bool:
    """Detect if timeframes are diverging"""
    directions = [tf1_direction, tf2_direction, tf3_direction]
    non_neutral = [d for d in directions if d != 0]
    
    if len(non_neutral) < 2:
        return False
    
    # Divergence if different directions
    return len(set(non_neutral)) > 1


def calculate_trend_age(candles: List, current_direction: int) -> int:
    """Calculate how many bars the current trend has been active"""
    if len(candles) < 10 or current_direction == 0:
        return 0
    
    closes = [c.close for c in candles]
    age = 0
    
    # Simple: count bars where price movement aligns with direction
    for i in range(len(closes) - 1, 0, -1):
        if current_direction == 1 and closes[i] > closes[i-1]:
            age += 1
        elif current_direction == -1 and closes[i] < closes[i-1]:
            age += 1
        else:
            break
    
    return age


def find_htf_levels(candles: List, lookback: int = 100) -> tuple:
    """Find higher timeframe support and resistance"""
    if len(candles) < lookback:
        lookback = len(candles)
    
    if lookback < 10:
        return 0, float('inf')
    
    recent = candles[-lookback:]
    highs = [c.high for c in recent]
    lows = [c.low for c in recent]
    
    # Simple: use highest high and lowest low
    resistance = max(highs)
    support = min(lows)
    
    return support, resistance


class MTFAnalyzer:
    """Calculate multi-timeframe features"""
    
    def __init__(self):
        self.prev_momentum_1m = 0.0
        self.prev_momentum_3m = 0.0
    
    def calculate(self, candles_dict: Dict[str, List]) -> MTFFeatures:
        """Calculate MTF features from candles of different timeframes"""
        features = MTFFeatures()
        
        candles_15m = candles_dict.get('15m', [])
        candles_5m = candles_dict.get('5m', [])
        candles_3m = candles_dict.get('3m', [])
        candles_1m = candles_dict.get('1m', [])
        
        # 15m analysis
        if candles_15m:
            features.tf_15m_trend, features.tf_15m_strength = calculate_trend_direction(candles_15m)
            closes_15m = [c.close for c in candles_15m]
            features.tf_15m_rsi = calculate_rsi(closes_15m, 14)
        
        # 5m analysis
        if candles_5m:
            features.tf_5m_trend, features.tf_5m_strength = calculate_trend_direction(candles_5m)
            closes_5m = [c.close for c in candles_5m]
            features.tf_5m_rsi = calculate_rsi(closes_5m, 14)
        
        # 3m momentum
        if candles_3m:
            features.tf_3m_momentum = calculate_momentum(candles_3m, 10)
        
        # 1m momentum
        if candles_1m:
            features.tf_1m_momentum = calculate_momentum(candles_1m, 10)
        
        # MTF alignment (count how many timeframes agree)
        directions = [features.tf_15m_trend, features.tf_5m_trend]
        if candles_3m:
            directions.append(1 if features.tf_3m_momentum > 0 else (-1 if features.tf_3m_momentum < 0 else 0))
        
        bullish = sum(1 for d in directions if d == 1)
        bearish = sum(1 for d in directions if d == -1)
        
        features.mtf_alignment = max(bullish, bearish)
        
        # Confluence score (0-100)
        total_directions = len([d for d in directions if d != 0])
        if total_directions > 0:
            features.mtf_confluence_score = (max(bullish, bearish) / len(directions)) * 100
        
        # TF Divergence
        features.tf_divergence = detect_tf_divergence(
            features.tf_15m_trend,
            features.tf_5m_trend,
            1 if features.tf_3m_momentum > 0.1 else (-1 if features.tf_3m_momentum < -0.1 else 0)
        )
        
        # Momentum acceleration
        if candles_1m:
            features.momentum_acceleration = calculate_momentum_acceleration(candles_1m, 5)
        
        # Trend age (using 15m as reference)
        if candles_15m:
            features.trend_age_bars = calculate_trend_age(candles_15m, features.tf_15m_trend)
        
        # HTF levels (using 15m)
        if candles_15m:
            support, resistance = find_htf_levels(candles_15m)
            current_price = candles_15m[-1].close
            
            features.htf_support_dist = (current_price - support) / current_price if support > 0 else 0
            features.htf_resistance_dist = (resistance - current_price) / current_price if resistance > 0 else 0
        
        return features

