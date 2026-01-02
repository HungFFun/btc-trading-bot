"""
Sentiment Analyzer - Funding Rate, Long/Short Ratio, Open Interest
★ INDEPENDENT - Self-contained calculations ★
"""

import logging
from typing import Dict, Any, List, Optional

from .. import Direction, IndicatorResult, AnalysisComponent

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Sentiment indicators analysis:
    - Funding Rate (contrarian signal)
    - Long/Short Ratio
    - Open Interest changes
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def analyze(self, market_data: Dict[str, Any]) -> Optional[AnalysisComponent]:
        """Analyze market sentiment"""
        try:
            indicators: List[IndicatorResult] = []
            reasoning: List[str] = []
            
            # 1. Funding Rate (50% weight)
            funding_result = self._analyze_funding(market_data)
            if funding_result:
                indicators.append(funding_result)
                reasoning.append(funding_result.description)
            
            # 2. Long/Short Ratio (30% weight)
            ls_result = self._analyze_long_short_ratio(market_data)
            if ls_result:
                indicators.append(ls_result)
                reasoning.append(ls_result.description)
            
            # 3. Open Interest (20% weight)
            oi_result = self._analyze_open_interest(market_data)
            if oi_result:
                indicators.append(oi_result)
                reasoning.append(oi_result.description)
            
            if not indicators:
                # Return neutral if no sentiment data
                return AnalysisComponent(
                    name='Sentiment',
                    direction=Direction.NEUTRAL,
                    score=0,
                    confidence=50,
                    indicators=[],
                    reasoning=["No sentiment data available"]
                )
            
            # Calculate overall score
            score = self._calculate_score(indicators)
            direction = self._determine_direction(indicators)
            confidence = self._calculate_confidence(indicators)
            
            return AnalysisComponent(
                name='Sentiment',
                direction=direction,
                score=score,
                confidence=confidence,
                indicators=indicators,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return None
    
    # =====================================================
    # Funding Rate Analysis (Contrarian)
    # =====================================================
    
    def _analyze_funding(self, market_data: Dict[str, Any]) -> Optional[IndicatorResult]:
        """
        Analyze funding rate as contrarian signal
        
        - High positive funding = Too many longs = SHORT signal
        - High negative funding = Too many shorts = LONG signal
        """
        funding = market_data.get('funding_rate')
        
        if funding is None:
            return None
        
        try:
            funding_pct = funding * 100  # Convert to percentage
            
            if funding > 0.001:  # > 0.1%
                signal = Direction.SHORT
                desc = f"Funding extreme positive ({funding_pct:.3f}%) - Contrarian SHORT"
            elif funding > 0.0005:  # > 0.05%
                signal = Direction.SHORT
                desc = f"Funding high positive ({funding_pct:.3f}%) - Slight bearish bias"
            elif funding < -0.001:  # < -0.1%
                signal = Direction.LONG
                desc = f"Funding extreme negative ({funding_pct:.3f}%) - Contrarian LONG"
            elif funding < -0.0005:  # < -0.05%
                signal = Direction.LONG
                desc = f"Funding negative ({funding_pct:.3f}%) - Slight bullish bias"
            else:
                signal = Direction.NEUTRAL
                desc = f"Funding neutral ({funding_pct:.3f}%)"
            
            return IndicatorResult(
                name='Funding',
                value=funding_pct,
                signal=signal,
                weight=0.50,
                description=desc
            )
        except:
            return None
    
    # =====================================================
    # Long/Short Ratio Analysis
    # =====================================================
    
    def _analyze_long_short_ratio(self, market_data: Dict[str, Any]) -> Optional[IndicatorResult]:
        """
        Analyze Long/Short ratio
        
        - High ratio (> 1.5) = Too many longs = SHORT signal (contrarian)
        - Low ratio (< 0.67) = Too many shorts = LONG signal (contrarian)
        """
        ls_ratio = market_data.get('long_short_ratio')
        
        if ls_ratio is None:
            return None
        
        try:
            if ls_ratio > 2.0:
                signal = Direction.SHORT
                desc = f"L/S ratio extreme ({ls_ratio:.2f}) - Contrarian SHORT"
            elif ls_ratio > 1.5:
                signal = Direction.SHORT
                desc = f"L/S ratio high ({ls_ratio:.2f}) - Bearish bias"
            elif ls_ratio < 0.5:
                signal = Direction.LONG
                desc = f"L/S ratio extreme low ({ls_ratio:.2f}) - Contrarian LONG"
            elif ls_ratio < 0.67:
                signal = Direction.LONG
                desc = f"L/S ratio low ({ls_ratio:.2f}) - Bullish bias"
            else:
                signal = Direction.NEUTRAL
                desc = f"L/S ratio balanced ({ls_ratio:.2f})"
            
            return IndicatorResult(
                name='LS_Ratio',
                value=ls_ratio,
                signal=signal,
                weight=0.30,
                description=desc
            )
        except:
            return None
    
    # =====================================================
    # Open Interest Analysis
    # =====================================================
    
    def _analyze_open_interest(self, market_data: Dict[str, Any]) -> Optional[IndicatorResult]:
        """
        Analyze Open Interest changes
        
        - Rising OI + Rising price = LONG continuation
        - Rising OI + Falling price = SHORT continuation
        - Falling OI = Trend exhaustion
        """
        oi_change = market_data.get('oi_change_pct')
        price_change = market_data.get('price_change_pct')
        
        if oi_change is None:
            return None
        
        try:
            # Default price change to 0 if not available
            if price_change is None:
                price_change = 0
            
            if oi_change > 5:  # OI increasing > 5%
                if price_change > 0:
                    signal = Direction.LONG
                    desc = f"OI rising (+{oi_change:.1f}%) with price up - LONG continuation"
                elif price_change < 0:
                    signal = Direction.SHORT
                    desc = f"OI rising (+{oi_change:.1f}%) with price down - SHORT continuation"
                else:
                    signal = Direction.NEUTRAL
                    desc = f"OI rising (+{oi_change:.1f}%) - Building positions"
            elif oi_change < -5:  # OI decreasing > 5%
                signal = Direction.NEUTRAL
                desc = f"OI falling ({oi_change:.1f}%) - Positions closing"
            else:
                signal = Direction.NEUTRAL
                desc = f"OI stable ({oi_change:+.1f}%)"
            
            return IndicatorResult(
                name='OI_Change',
                value=oi_change,
                signal=signal,
                weight=0.20,
                description=desc
            )
        except:
            return None
    
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
        
        if long_weight > short_weight * 1.3:
            return Direction.LONG
        elif short_weight > long_weight * 1.3:
            return Direction.SHORT
        return Direction.NEUTRAL
    
    def _calculate_confidence(self, indicators: List[IndicatorResult]) -> float:
        """Calculate confidence based on indicator agreement"""
        if not indicators:
            return 50
        
        directions = [i.signal for i in indicators]
        long_count = directions.count(Direction.LONG)
        short_count = directions.count(Direction.SHORT)
        
        max_count = max(long_count, short_count)
        agreement = (max_count / len(indicators)) * 100
        
        return agreement

