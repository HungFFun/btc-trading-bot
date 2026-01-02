"""
Confidence Calculator - Calculate prediction confidence and win probability
★ INDEPENDENT - Does not import from core trading logic ★
"""

import logging
from typing import Dict, Any, List, Tuple

from . import Direction, ConfidenceBreakdown, AnalysisComponent

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """
    Calculate confidence metrics for predictions
    
    Base win rates (realistic):
    - VERY_STRONG: 65%
    - STRONG: 58%
    - MODERATE: 52%
    - WEAK: 45%
    """
    
    BASE_WIN_RATES = {
        'VERY_STRONG': 0.65,
        'STRONG': 0.58,
        'MODERATE': 0.52,
        'WEAK': 0.45
    }
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def calculate(self, analysis: Dict[str, Any]) -> ConfidenceBreakdown:
        """
        Calculate confidence breakdown from analysis
        
        Args:
            analysis: Dictionary containing:
                - score: float (-100 to +100)
                - direction: Direction
                - components: List[AnalysisComponent]
                - indicators_summary: Dict[str, float]
        
        Returns:
            ConfidenceBreakdown with all metrics
        """
        try:
            score = analysis.get('score', 0)
            direction = analysis.get('direction', Direction.NEUTRAL)
            components = analysis.get('components', [])
            indicators = analysis.get('indicators_summary', {})
            
            # 1. Signal strength (0-100)
            signal_strength = min(abs(score), 100)
            
            # 2. Indicator agreement
            agreement = self._calculate_agreement(components, direction)
            
            # 3. Risk factors and penalty
            risks, penalty = self._identify_risks(indicators, score)
            
            # 4. Overall confidence
            # Weighted: 40% signal strength + 60% agreement - penalty
            base_confidence = (signal_strength * 0.4 + agreement * 0.6)
            overall_confidence = max(0, min(100, base_confidence - penalty))
            
            # 5. Win probability (keep realistic: 40-70%)
            win_probability = self._calculate_win_probability(signal_strength, agreement)
            
            return ConfidenceBreakdown(
                overall_confidence=overall_confidence,
                win_probability=win_probability,
                signal_strength=signal_strength,
                indicator_agreement=agreement,
                risk_factors=risks,
                risk_penalty=penalty
            )
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return ConfidenceBreakdown(
                overall_confidence=50,
                win_probability=50,
                signal_strength=0,
                indicator_agreement=0,
                risk_factors=["Calculation error"],
                risk_penalty=0
            )
    
    def _calculate_agreement(
        self, 
        components: List[AnalysisComponent], 
        direction: Direction
    ) -> float:
        """Calculate how many components agree with the direction"""
        if not components:
            return 50
        
        agreeing = sum(1 for c in components if c.direction == direction)
        agreement = (agreeing / len(components)) * 100
        
        return agreement
    
    def _identify_risks(
        self, 
        indicators: Dict[str, float], 
        score: float
    ) -> Tuple[List[str], float]:
        """
        Identify risk factors and calculate penalty
        
        Returns:
            Tuple of (risk_list, total_penalty)
        """
        risks = []
        penalty = 0
        
        # 1. Extreme RSI
        rsi = indicators.get('RSI', 50)
        if rsi > 80:
            risks.append(f"⚠️ Extreme RSI overbought ({rsi:.1f})")
            penalty += 10
        elif rsi < 20:
            risks.append(f"⚠️ Extreme RSI oversold ({rsi:.1f})")
            penalty += 10
        elif rsi > 75 or rsi < 25:
            risks.append(f"⚠️ RSI in extreme zone ({rsi:.1f})")
            penalty += 5
        
        # 2. Low volume
        volume = indicators.get('Volume', 1.0)
        if volume < 0.5:
            risks.append(f"⚠️ Very low volume ({volume:.1f}x)")
            penalty += 10
        elif volume < 0.7:
            risks.append(f"⚠️ Below average volume ({volume:.1f}x)")
            penalty += 5
        
        # 3. Weak ADX (no trend)
        adx = indicators.get('ADX', 25)
        if adx < 15:
            risks.append(f"⚠️ No clear trend (ADX: {adx:.1f})")
            penalty += 10
        elif adx < 20:
            risks.append(f"⚠️ Weak trend (ADX: {adx:.1f})")
            penalty += 5
        
        # 4. Conflicting signals
        if abs(score) < 25:
            risks.append("⚠️ Weak overall signal strength")
            penalty += 5
        
        # 5. Extreme funding (contrarian warning)
        funding = indicators.get('Funding', 0)
        if abs(funding) > 0.1:
            risks.append(f"⚠️ Extreme funding rate ({funding:.3f}%)")
            penalty += 5
        
        # 6. BB at extremes
        bb_pos = indicators.get('BB', 50)
        if bb_pos < 5 or bb_pos > 95:
            risks.append(f"⚠️ Price at BB extreme ({bb_pos:.0f}%)")
            penalty += 5
        
        # Cap penalty at 30
        penalty = min(penalty, 30)
        
        return risks, penalty
    
    def _calculate_win_probability(
        self, 
        signal_strength: float, 
        agreement: float
    ) -> float:
        """
        Calculate realistic win probability
        
        Keep in range 40-70% to be realistic
        """
        # Determine base rate from signal strength
        if signal_strength >= 70:
            base_rate = self.BASE_WIN_RATES['VERY_STRONG']
        elif signal_strength >= 50:
            base_rate = self.BASE_WIN_RATES['STRONG']
        elif signal_strength >= 30:
            base_rate = self.BASE_WIN_RATES['MODERATE']
        else:
            base_rate = self.BASE_WIN_RATES['WEAK']
        
        # Adjust based on agreement
        agreement_bonus = (agreement - 50) / 100 * 0.05  # +/- 5% max
        
        # Calculate final probability
        win_prob = (base_rate + agreement_bonus) * 100
        
        # Clamp to realistic range: 40-70%
        return max(40, min(70, win_prob))

