"""
Technical Indicators Module
Features 1-20: Technical Indicators
"""
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class TechnicalFeatures:
    """Technical indicator features (1-20)"""
    # RSI
    rsi_7: float = 0.0
    rsi_14: float = 0.0
    
    # EMA
    ema_9: float = 0.0
    ema_21: float = 0.0
    ema_50: float = 0.0
    ema_200: float = 0.0
    
    # MACD
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    
    # Bollinger Bands
    bb_upper: float = 0.0
    bb_lower: float = 0.0
    bb_position: float = 0.0  # 0-1 position within bands
    
    # ATR
    atr_14: float = 0.0
    atr_percentile: float = 0.0  # vs 30 days
    
    # ADX & DI
    adx: float = 0.0
    plus_di: float = 0.0
    minus_di: float = 0.0
    
    # Stochastic
    stoch_k: float = 0.0
    stoch_d: float = 0.0
    
    # VWAP
    vwap: float = 0.0


def calculate_ema(prices: List[float], period: int) -> float:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return prices[-1] if prices else 0.0
    
    multiplier = 2 / (period + 1)
    ema = prices[0]
    
    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema


def calculate_rsi(prices: List[float], period: int) -> float:
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """Calculate MACD, Signal, and Histogram"""
    if len(prices) < slow:
        return 0.0, 0.0, 0.0
    
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    macd_line = ema_fast - ema_slow
    
    # For signal line, we need MACD history
    macd_history = []
    for i in range(max(slow, len(prices) - 50), len(prices)):
        ema_f = calculate_ema(prices[:i+1], fast)
        ema_s = calculate_ema(prices[:i+1], slow)
        macd_history.append(ema_f - ema_s)
    
    if len(macd_history) >= signal:
        macd_signal = calculate_ema(macd_history, signal)
    else:
        macd_signal = macd_line
    
    macd_histogram = macd_line - macd_signal
    
    return macd_line, macd_signal, macd_histogram


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> tuple:
    """Calculate Bollinger Bands"""
    if len(prices) < period:
        return prices[-1] if prices else 0, prices[-1] if prices else 0, 0.5
    
    recent_prices = prices[-period:]
    sma = np.mean(recent_prices)
    std = np.std(recent_prices)
    
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    
    current_price = prices[-1]
    if upper - lower == 0:
        position = 0.5
    else:
        position = (current_price - lower) / (upper - lower)
    
    return upper, lower, max(0, min(1, position))


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Calculate Average True Range"""
    if len(highs) < period + 1:
        return 0.0
    
    true_ranges = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        true_ranges.append(tr)
    
    return np.mean(true_ranges[-period:])


def calculate_adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> tuple:
    """Calculate ADX, +DI, -DI"""
    if len(highs) < period + 1:
        return 0.0, 0.0, 0.0
    
    plus_dm = []
    minus_dm = []
    tr_list = []
    
    for i in range(1, len(highs)):
        # True Range
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        tr_list.append(tr)
        
        # Directional Movement
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]
        
        if up_move > down_move and up_move > 0:
            plus_dm.append(up_move)
        else:
            plus_dm.append(0)
        
        if down_move > up_move and down_move > 0:
            minus_dm.append(down_move)
        else:
            minus_dm.append(0)
    
    if len(tr_list) < period:
        return 0.0, 0.0, 0.0
    
    # Calculate smoothed averages
    atr = np.mean(tr_list[-period:])
    smoothed_plus_dm = np.mean(plus_dm[-period:])
    smoothed_minus_dm = np.mean(minus_dm[-period:])
    
    if atr == 0:
        return 0.0, 0.0, 0.0
    
    plus_di = 100 * smoothed_plus_dm / atr
    minus_di = 100 * smoothed_minus_dm / atr
    
    # Calculate DX and ADX
    di_sum = plus_di + minus_di
    if di_sum == 0:
        return 0.0, plus_di, minus_di
    
    dx = 100 * abs(plus_di - minus_di) / di_sum
    adx = dx  # Simplified - normally would use smoothed DX
    
    return adx, plus_di, minus_di


def calculate_stochastic(highs: List[float], lows: List[float], closes: List[float], 
                         k_period: int = 14, d_period: int = 3) -> tuple:
    """Calculate Stochastic %K and %D"""
    if len(closes) < k_period:
        return 50.0, 50.0
    
    recent_highs = highs[-k_period:]
    recent_lows = lows[-k_period:]
    
    highest_high = max(recent_highs)
    lowest_low = min(recent_lows)
    current_close = closes[-1]
    
    if highest_high - lowest_low == 0:
        k = 50.0
    else:
        k = 100 * (current_close - lowest_low) / (highest_high - lowest_low)
    
    # Calculate %D as SMA of %K
    k_values = []
    for i in range(max(0, len(closes) - d_period), len(closes)):
        h = highs[max(0, i-k_period+1):i+1]
        l = lows[max(0, i-k_period+1):i+1]
        hh = max(h) if h else 0
        ll = min(l) if l else 0
        if hh - ll == 0:
            k_values.append(50.0)
        else:
            k_values.append(100 * (closes[i] - ll) / (hh - ll))
    
    d = np.mean(k_values) if k_values else k
    
    return k, d


def calculate_vwap(prices: List[float], volumes: List[float]) -> float:
    """Calculate Volume Weighted Average Price"""
    if not prices or not volumes or len(prices) != len(volumes):
        return prices[-1] if prices else 0.0
    
    total_volume = sum(volumes)
    if total_volume == 0:
        return prices[-1]
    
    vwap = sum(p * v for p, v in zip(prices, volumes)) / total_volume
    return vwap


def calculate_atr_percentile(current_atr: float, atr_history: List[float]) -> float:
    """Calculate ATR percentile vs history"""
    if not atr_history:
        return 50.0
    
    count_below = sum(1 for atr in atr_history if atr < current_atr)
    percentile = (count_below / len(atr_history)) * 100
    return percentile


class TechnicalAnalyzer:
    """Calculate all technical features"""
    
    def __init__(self):
        self.atr_history: List[float] = []
    
    def calculate(self, candles: List) -> TechnicalFeatures:
        """Calculate all technical features from candles"""
        if not candles or len(candles) < 2:
            return TechnicalFeatures()
        
        # Extract price series
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        volumes = [c.volume for c in candles]
        
        features = TechnicalFeatures()
        
        # RSI
        features.rsi_7 = calculate_rsi(closes, 7)
        features.rsi_14 = calculate_rsi(closes, 14)
        
        # EMA
        features.ema_9 = calculate_ema(closes, 9)
        features.ema_21 = calculate_ema(closes, 21)
        features.ema_50 = calculate_ema(closes, 50)
        features.ema_200 = calculate_ema(closes, 200)
        
        # MACD
        features.macd_line, features.macd_signal, features.macd_histogram = calculate_macd(closes)
        
        # Bollinger Bands
        features.bb_upper, features.bb_lower, features.bb_position = calculate_bollinger_bands(closes)
        
        # ATR
        features.atr_14 = calculate_atr(highs, lows, closes, 14)
        self.atr_history.append(features.atr_14)
        if len(self.atr_history) > 30 * 24:  # Keep ~30 days of hourly ATR
            self.atr_history = self.atr_history[-30*24:]
        features.atr_percentile = calculate_atr_percentile(features.atr_14, self.atr_history)
        
        # ADX
        features.adx, features.plus_di, features.minus_di = calculate_adx(highs, lows, closes)
        
        # Stochastic
        features.stoch_k, features.stoch_d = calculate_stochastic(highs, lows, closes)
        
        # VWAP
        features.vwap = calculate_vwap(closes, volumes)
        
        return features

