"""
Technical Analyzer - RSI, MACD, EMA, Bollinger, ADX
★ INDEPENDENT - Self-contained calculations ★
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional

from .. import Direction, IndicatorResult, AnalysisComponent

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """
    Technical indicators analysis:
    - RSI (14): Overbought/Oversold
    - MACD: Trend & Momentum
    - EMA (9/21/50): Trend direction
    - Bollinger Bands: Mean reversion
    - ADX: Trend strength
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def analyze(self, market_data: Dict[str, Any]) -> Optional[AnalysisComponent]:
        """Analyze market data with technical indicators"""
        try:
            # Get candles - prefer 5m or whatever is available
            candles = market_data.get('candles', {})
            
            # Try to get timeframe data
            if '5m' in candles:
                candle_data = candles['5m']
            elif '15m' in candles:
                candle_data = candles['15m']
            elif '1h' in candles:
                candle_data = candles['1h']
            elif isinstance(candles, list):
                candle_data = candles
            else:
                logger.warning("No suitable candle data found")
                return None
            
            if not candle_data or len(candle_data) < 50:
                logger.warning("Insufficient candle data for analysis")
                return None
            
            # Extract price data
            closes = self._extract_closes(candle_data)
            highs = self._extract_highs(candle_data)
            lows = self._extract_lows(candle_data)
            
            if len(closes) < 50:
                return None
            
            indicators: List[IndicatorResult] = []
            reasoning: List[str] = []
            
            # 1. RSI (20% weight)
            rsi_result = self._analyze_rsi(closes)
            if rsi_result:
                indicators.append(rsi_result)
                reasoning.append(rsi_result.description)
            
            # 2. MACD (20% weight)
            macd_result = self._analyze_macd(closes)
            if macd_result:
                indicators.append(macd_result)
                reasoning.append(macd_result.description)
            
            # 3. EMA alignment (25% weight)
            ema_result = self._analyze_ema(closes)
            if ema_result:
                indicators.append(ema_result)
                reasoning.append(ema_result.description)
            
            # 4. Bollinger Bands (20% weight)
            bb_result = self._analyze_bollinger(closes)
            if bb_result:
                indicators.append(bb_result)
                reasoning.append(bb_result.description)
            
            # 5. ADX (15% weight)
            adx_result = self._analyze_adx(highs, lows, closes)
            if adx_result:
                indicators.append(adx_result)
                reasoning.append(adx_result.description)
            
            # Calculate overall score
            score = self._calculate_score(indicators)
            direction = self._determine_direction(indicators)
            confidence = self._calculate_confidence(indicators)
            
            return AnalysisComponent(
                name='Technical',
                direction=direction,
                score=score,
                confidence=confidence,
                indicators=indicators,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Technical analysis failed: {e}")
            return None
    
    def _extract_closes(self, candles: List) -> np.ndarray:
        """Extract close prices from candles"""
        if isinstance(candles[0], dict):
            return np.array([c.get('close', c.get('c', 0)) for c in candles])
        return np.array(candles)
    
    def _extract_highs(self, candles: List) -> np.ndarray:
        """Extract high prices from candles"""
        if isinstance(candles[0], dict):
            return np.array([c.get('high', c.get('h', 0)) for c in candles])
        return np.array(candles)
    
    def _extract_lows(self, candles: List) -> np.ndarray:
        """Extract low prices from candles"""
        if isinstance(candles[0], dict):
            return np.array([c.get('low', c.get('l', 0)) for c in candles])
        return np.array(candles)
    
    # =====================================================
    # RSI Analysis
    # =====================================================
    
    def _analyze_rsi(self, closes: np.ndarray) -> Optional[IndicatorResult]:
        """Calculate and analyze RSI"""
        try:
            rsi = self._calc_rsi(closes, 14)
            
            if rsi < 30:
                signal = Direction.LONG
                desc = f"RSI Oversold ({rsi:.1f}) - Potential bounce"
            elif rsi > 70:
                signal = Direction.SHORT
                desc = f"RSI Overbought ({rsi:.1f}) - Potential pullback"
            elif rsi < 40:
                signal = Direction.LONG
                desc = f"RSI approaching oversold ({rsi:.1f})"
            elif rsi > 60:
                signal = Direction.SHORT
                desc = f"RSI approaching overbought ({rsi:.1f})"
            else:
                signal = Direction.NEUTRAL
                desc = f"RSI neutral ({rsi:.1f})"
            
            return IndicatorResult(
                name='RSI',
                value=rsi,
                signal=signal,
                weight=0.20,
                description=desc
            )
        except:
            return None
    
    def _calc_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """Calculate RSI"""
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    # =====================================================
    # MACD Analysis
    # =====================================================
    
    def _analyze_macd(self, closes: np.ndarray) -> Optional[IndicatorResult]:
        """Calculate and analyze MACD"""
        try:
            macd_line, signal_line, histogram = self._calc_macd(closes)
            
            current_hist = histogram[-1]
            prev_hist = histogram[-2]
            
            if current_hist > prev_hist and macd_line[-1] > signal_line[-1]:
                signal = Direction.LONG
                desc = "MACD bullish crossover"
            elif current_hist < prev_hist and macd_line[-1] < signal_line[-1]:
                signal = Direction.SHORT
                desc = "MACD bearish crossover"
            elif current_hist > 0:
                signal = Direction.LONG
                desc = "MACD histogram positive"
            elif current_hist < 0:
                signal = Direction.SHORT
                desc = "MACD histogram negative"
            else:
                signal = Direction.NEUTRAL
                desc = "MACD no clear signal"
            
            return IndicatorResult(
                name='MACD',
                value=current_hist,
                signal=signal,
                weight=0.20,
                description=desc
            )
        except:
            return None
    
    def _calc_macd(self, closes: np.ndarray):
        """Calculate MACD"""
        ema12 = self._calc_ema_array(closes, 12)
        ema26 = self._calc_ema_array(closes, 26)
        macd_line = ema12 - ema26
        signal_line = self._calc_ema_array(macd_line, 9)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    # =====================================================
    # EMA Analysis
    # =====================================================
    
    def _analyze_ema(self, closes: np.ndarray) -> Optional[IndicatorResult]:
        """Analyze EMA alignment"""
        try:
            ema9 = self._calc_ema(closes, 9)
            ema21 = self._calc_ema(closes, 21)
            ema50 = self._calc_ema(closes, 50)
            
            current_price = closes[-1]
            
            if ema9 > ema21 > ema50 and current_price > ema9:
                signal = Direction.LONG
                desc = "EMA perfect bullish alignment"
            elif ema9 > ema21 > ema50:
                signal = Direction.LONG
                desc = "EMA bullish alignment"
            elif ema9 < ema21 < ema50 and current_price < ema9:
                signal = Direction.SHORT
                desc = "EMA perfect bearish alignment"
            elif ema9 < ema21 < ema50:
                signal = Direction.SHORT
                desc = "EMA bearish alignment"
            else:
                signal = Direction.NEUTRAL
                desc = "EMA mixed signals"
            
            return IndicatorResult(
                name='EMA',
                value=ema9,
                signal=signal,
                weight=0.25,
                description=desc
            )
        except:
            return None
    
    def _calc_ema(self, closes: np.ndarray, period: int) -> float:
        """Calculate single EMA value"""
        return self._calc_ema_array(closes, period)[-1]
    
    def _calc_ema_array(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA array"""
        multiplier = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = (data[i] * multiplier) + (ema[i-1] * (1 - multiplier))
        
        return ema
    
    # =====================================================
    # Bollinger Bands Analysis
    # =====================================================
    
    def _analyze_bollinger(self, closes: np.ndarray) -> Optional[IndicatorResult]:
        """Analyze Bollinger Bands position"""
        try:
            upper, middle, lower = self._calc_bollinger(closes)
            current_price = closes[-1]
            
            bb_position = (current_price - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
            
            if bb_position < 0.1:
                signal = Direction.LONG
                desc = f"Price near lower BB ({bb_position*100:.0f}%)"
            elif bb_position < 0.3:
                signal = Direction.LONG
                desc = f"Price in lower BB zone ({bb_position*100:.0f}%)"
            elif bb_position > 0.9:
                signal = Direction.SHORT
                desc = f"Price near upper BB ({bb_position*100:.0f}%)"
            elif bb_position > 0.7:
                signal = Direction.SHORT
                desc = f"Price in upper BB zone ({bb_position*100:.0f}%)"
            else:
                signal = Direction.NEUTRAL
                desc = f"Price in middle BB zone ({bb_position*100:.0f}%)"
            
            return IndicatorResult(
                name='BB',
                value=bb_position * 100,
                signal=signal,
                weight=0.20,
                description=desc
            )
        except:
            return None
    
    def _calc_bollinger(self, closes: np.ndarray, period: int = 20, std_dev: float = 2.0):
        """Calculate Bollinger Bands"""
        middle = np.mean(closes[-period:])
        std = np.std(closes[-period:])
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    # =====================================================
    # ADX Analysis
    # =====================================================
    
    def _analyze_adx(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> Optional[IndicatorResult]:
        """Analyze ADX trend strength"""
        try:
            adx = self._calc_adx(highs, lows, closes)
            
            if adx > 40:
                # Strong trend - follow the direction
                ema9 = self._calc_ema(closes, 9)
                ema21 = self._calc_ema(closes, 21)
                
                if ema9 > ema21:
                    signal = Direction.LONG
                    desc = f"ADX strong trend ({adx:.1f}) - Bullish"
                else:
                    signal = Direction.SHORT
                    desc = f"ADX strong trend ({adx:.1f}) - Bearish"
            elif adx > 25:
                signal = Direction.NEUTRAL
                desc = f"ADX moderate trend ({adx:.1f})"
            else:
                signal = Direction.NEUTRAL
                desc = f"ADX weak/no trend ({adx:.1f})"
            
            return IndicatorResult(
                name='ADX',
                value=adx,
                signal=signal,
                weight=0.15,
                description=desc
            )
        except:
            return None
    
    def _calc_adx(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Calculate ADX"""
        try:
            # True Range
            high_low = highs - lows
            high_close = np.abs(highs - np.roll(closes, 1))
            low_close = np.abs(lows - np.roll(closes, 1))
            
            tr = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = np.mean(tr[-period:])
            
            # Directional Movement
            up_move = highs - np.roll(highs, 1)
            down_move = np.roll(lows, 1) - lows
            
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            
            plus_di = 100 * np.mean(plus_dm[-period:]) / atr if atr > 0 else 0
            minus_di = 100 * np.mean(minus_dm[-period:]) / atr if atr > 0 else 0
            
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
            
            return dx
        except:
            return 25  # Default moderate
    
    # =====================================================
    # Scoring
    # =====================================================
    
    def _calculate_score(self, indicators: List[IndicatorResult]) -> float:
        """Calculate weighted score from indicators"""
        if not indicators:
            return 0
        
        total_weight = sum(i.weight for i in indicators)
        weighted_score = 0
        
        for ind in indicators:
            if ind.signal == Direction.LONG:
                score = 50
            elif ind.signal == Direction.SHORT:
                score = -50
            else:
                score = 0
            
            weighted_score += score * ind.weight
        
        return (weighted_score / total_weight) if total_weight > 0 else 0
    
    def _determine_direction(self, indicators: List[IndicatorResult]) -> Direction:
        """Determine overall direction from indicators"""
        long_weight = sum(i.weight for i in indicators if i.signal == Direction.LONG)
        short_weight = sum(i.weight for i in indicators if i.signal == Direction.SHORT)
        
        if long_weight > short_weight * 1.5:
            return Direction.LONG
        elif short_weight > long_weight * 1.5:
            return Direction.SHORT
        return Direction.NEUTRAL
    
    def _calculate_confidence(self, indicators: List[IndicatorResult]) -> float:
        """Calculate confidence based on indicator agreement"""
        if not indicators:
            return 0
        
        # Count agreement
        directions = [i.signal for i in indicators]
        long_count = directions.count(Direction.LONG)
        short_count = directions.count(Direction.SHORT)
        
        max_count = max(long_count, short_count)
        agreement = (max_count / len(indicators)) * 100
        
        return agreement

