"""
Structure Analyzer - Support/Resistance, Price Patterns, Volume
★ INDEPENDENT - Self-contained calculations ★
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional

from .. import Direction, IndicatorResult, AnalysisComponent

logger = logging.getLogger(__name__)


class StructureAnalyzer:
    """
    Market structure analysis:
    - Support/Resistance levels
    - Price patterns (higher highs, lower lows)
    - Volume confirmation
    - Key levels
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def analyze(self, market_data: Dict[str, Any]) -> Optional[AnalysisComponent]:
        """Analyze market structure"""
        try:
            # Get candles
            candles = market_data.get('candles', {})
            
            if '5m' in candles:
                candle_data = candles['5m']
            elif '15m' in candles:
                candle_data = candles['15m']
            elif '1h' in candles:
                candle_data = candles['1h']
            elif isinstance(candles, list):
                candle_data = candles
            else:
                return None
            
            if not candle_data or len(candle_data) < 20:
                return None
            
            indicators: List[IndicatorResult] = []
            reasoning: List[str] = []
            
            # 1. Price structure (40% weight)
            structure_result = self._analyze_price_structure(candle_data)
            if structure_result:
                indicators.append(structure_result)
                reasoning.append(structure_result.description)
            
            # 2. Support/Resistance proximity (35% weight)
            sr_result = self._analyze_sr_levels(candle_data, market_data.get('current_price'))
            if sr_result:
                indicators.append(sr_result)
                reasoning.append(sr_result.description)
            
            # 3. Volume structure (25% weight)
            vol_result = self._analyze_volume(candle_data)
            if vol_result:
                indicators.append(vol_result)
                reasoning.append(vol_result.description)
            
            if not indicators:
                return None
            
            # Calculate overall score
            score = self._calculate_score(indicators)
            direction = self._determine_direction(indicators)
            confidence = self._calculate_confidence(indicators)
            
            return AnalysisComponent(
                name='Structure',
                direction=direction,
                score=score,
                confidence=confidence,
                indicators=indicators,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            return None
    
    # =====================================================
    # Price Structure Analysis
    # =====================================================
    
    def _analyze_price_structure(self, candles: List) -> Optional[IndicatorResult]:
        """
        Analyze price structure:
        - Higher highs + Higher lows = Uptrend
        - Lower highs + Lower lows = Downtrend
        """
        try:
            highs = self._extract_highs(candles)
            lows = self._extract_lows(candles)
            
            if len(highs) < 20:
                return None
            
            # Find swing points (last 20 candles)
            recent_highs = highs[-20:]
            recent_lows = lows[-20:]
            
            # Compare last 5 vs previous 5
            last_high = np.max(recent_highs[-5:])
            prev_high = np.max(recent_highs[-10:-5])
            last_low = np.min(recent_lows[-5:])
            prev_low = np.min(recent_lows[-10:-5])
            
            higher_high = last_high > prev_high
            higher_low = last_low > prev_low
            lower_high = last_high < prev_high
            lower_low = last_low < prev_low
            
            if higher_high and higher_low:
                signal = Direction.LONG
                desc = "Price making HH/HL - Uptrend structure"
                score = 70
            elif lower_high and lower_low:
                signal = Direction.SHORT
                desc = "Price making LH/LL - Downtrend structure"
                score = 70
            elif higher_high and not higher_low:
                signal = Direction.LONG
                desc = "Price making HH - Potential bullish breakout"
                score = 50
            elif lower_low and not lower_high:
                signal = Direction.SHORT
                desc = "Price making LL - Potential bearish breakdown"
                score = 50
            else:
                signal = Direction.NEUTRAL
                desc = "Price consolidating - Mixed structure"
                score = 30
            
            return IndicatorResult(
                name='Structure',
                value=score,
                signal=signal,
                weight=0.40,
                description=desc
            )
        except:
            return None
    
    # =====================================================
    # Support/Resistance Analysis
    # =====================================================
    
    def _analyze_sr_levels(self, candles: List, current_price: Optional[float]) -> Optional[IndicatorResult]:
        """
        Analyze proximity to support/resistance levels
        """
        try:
            if current_price is None:
                closes = self._extract_closes(candles)
                current_price = closes[-1]
            
            highs = self._extract_highs(candles)
            lows = self._extract_lows(candles)
            
            # Find key levels
            resistance = np.max(highs[-20:])
            support = np.min(lows[-20:])
            
            price_range = resistance - support
            if price_range == 0:
                return None
            
            # Calculate position in range
            position = (current_price - support) / price_range
            
            # Distance to levels
            dist_to_resistance = (resistance - current_price) / current_price * 100
            dist_to_support = (current_price - support) / current_price * 100
            
            if position < 0.2:  # Near support
                signal = Direction.LONG
                desc = f"Price near support (${support:,.0f}) - {dist_to_support:.1f}% above"
            elif position > 0.8:  # Near resistance
                signal = Direction.SHORT
                desc = f"Price near resistance (${resistance:,.0f}) - {dist_to_resistance:.1f}% below"
            elif position < 0.4:
                signal = Direction.LONG
                desc = f"Price in lower half of range"
            elif position > 0.6:
                signal = Direction.SHORT
                desc = f"Price in upper half of range"
            else:
                signal = Direction.NEUTRAL
                desc = f"Price in middle of range ({position*100:.0f}%)"
            
            return IndicatorResult(
                name='SR_Level',
                value=position * 100,
                signal=signal,
                weight=0.35,
                description=desc
            )
        except:
            return None
    
    # =====================================================
    # Volume Analysis
    # =====================================================
    
    def _analyze_volume(self, candles: List) -> Optional[IndicatorResult]:
        """
        Analyze volume patterns
        """
        try:
            volumes = self._extract_volumes(candles)
            closes = self._extract_closes(candles)
            
            if len(volumes) < 20:
                return None
            
            # Average volume
            avg_volume = np.mean(volumes[-20:])
            recent_volume = np.mean(volumes[-5:])
            
            # Volume ratio
            vol_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # Price direction
            price_change = (closes[-1] - closes[-5]) / closes[-5] * 100 if closes[-5] > 0 else 0
            
            if vol_ratio > 1.5:  # High volume
                if price_change > 0:
                    signal = Direction.LONG
                    desc = f"High volume ({vol_ratio:.1f}x) with price up - Bullish"
                elif price_change < 0:
                    signal = Direction.SHORT
                    desc = f"High volume ({vol_ratio:.1f}x) with price down - Bearish"
                else:
                    signal = Direction.NEUTRAL
                    desc = f"High volume ({vol_ratio:.1f}x) - Distribution"
            elif vol_ratio < 0.5:  # Low volume
                signal = Direction.NEUTRAL
                desc = f"Low volume ({vol_ratio:.1f}x) - Weak conviction"
            else:
                signal = Direction.NEUTRAL
                desc = f"Normal volume ({vol_ratio:.1f}x)"
            
            return IndicatorResult(
                name='Volume',
                value=vol_ratio,
                signal=signal,
                weight=0.25,
                description=desc
            )
        except:
            return None
    
    # =====================================================
    # Helper methods
    # =====================================================
    
    def _extract_closes(self, candles: List) -> np.ndarray:
        if isinstance(candles[0], dict):
            return np.array([c.get('close', c.get('c', 0)) for c in candles])
        return np.array(candles)
    
    def _extract_highs(self, candles: List) -> np.ndarray:
        if isinstance(candles[0], dict):
            return np.array([c.get('high', c.get('h', 0)) for c in candles])
        return np.array(candles)
    
    def _extract_lows(self, candles: List) -> np.ndarray:
        if isinstance(candles[0], dict):
            return np.array([c.get('low', c.get('l', 0)) for c in candles])
        return np.array(candles)
    
    def _extract_volumes(self, candles: List) -> np.ndarray:
        if isinstance(candles[0], dict):
            return np.array([c.get('volume', c.get('v', 0)) for c in candles])
        return np.array([1] * len(candles))  # Default if no volume
    
    # =====================================================
    # Scoring
    # =====================================================
    
    def _calculate_score(self, indicators: List[IndicatorResult]) -> float:
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
        long_weight = sum(i.weight for i in indicators if i.signal == Direction.LONG)
        short_weight = sum(i.weight for i in indicators if i.signal == Direction.SHORT)
        
        if long_weight > short_weight * 1.3:
            return Direction.LONG
        elif short_weight > long_weight * 1.3:
            return Direction.SHORT
        return Direction.NEUTRAL
    
    def _calculate_confidence(self, indicators: List[IndicatorResult]) -> float:
        if not indicators:
            return 50
        
        directions = [i.signal for i in indicators]
        long_count = directions.count(Direction.LONG)
        short_count = directions.count(Direction.SHORT)
        
        max_count = max(long_count, short_count)
        return (max_count / len(indicators)) * 100

