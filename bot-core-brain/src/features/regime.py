"""
Market Regime Detection Module
Detects market conditions: TRENDING_UP, TRENDING_DOWN, RANGING, HIGH_VOLATILITY, CHOPPY
"""
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass
import logging

from .feature_engine import AllFeatures

logger = logging.getLogger(__name__)


class RegimeType(str, Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    CHOPPY = "CHOPPY"


@dataclass
class RegimeResult:
    """Result of regime detection"""
    regime_type: RegimeType
    confidence: float  # 0-1
    exhaustion_risk: float  # 0-1
    structure_quality: float  # 0-1
    reasoning: str = ""
    
    @property
    def is_tradeable(self) -> bool:
        """Check if regime is tradeable"""
        return self.regime_type != RegimeType.CHOPPY


@dataclass 
class ExhaustionIndicators:
    """Indicators of trend exhaustion"""
    rsi_divergence: float = 0.0
    volume_declining: float = 0.0
    body_shrinking: float = 0.0
    extreme_rsi: float = 0.0
    onchain_divergence: float = 0.0
    
    def calculate_risk(self) -> float:
        """Calculate exhaustion risk (0-1)"""
        weighted = (
            self.rsi_divergence * 0.30 +
            self.volume_declining * 0.20 +
            self.body_shrinking * 0.15 +
            self.extreme_rsi * 0.15 +
            self.onchain_divergence * 0.20
        )
        return min(1.0, max(0.0, weighted))


class RegimeDetector:
    """
    Detect market regime from features.
    
    Regimes:
    - TRENDING_UP: ADX > 25, EMA aligned upward
    - TRENDING_DOWN: ADX > 25, EMA aligned downward  
    - RANGING: Choppiness < 50, clear S/R
    - HIGH_VOLATILITY: ATR percentile > 80
    - CHOPPY: No clear direction (NO TRADE)
    """
    
    def __init__(self):
        self.last_regime: Optional[RegimeResult] = None
        self.regime_history: List[RegimeType] = []
    
    def detect(self, features: AllFeatures) -> RegimeResult:
        """Detect current market regime"""
        tech = features.technical
        pa = features.price_action
        mtf = features.mtf
        onchain = features.onchain
        
        # Calculate exhaustion risk first
        exhaustion = self._calculate_exhaustion(features)
        exhaustion_risk = exhaustion.calculate_risk()
        
        # Calculate structure quality
        structure_quality = self._calculate_structure_quality(features)
        
        # Step 1: Check HIGH_VOLATILITY
        if tech.atr_percentile > 80:
            result = RegimeResult(
                regime_type=RegimeType.HIGH_VOLATILITY,
                confidence=min(0.95, tech.atr_percentile / 100),
                exhaustion_risk=exhaustion_risk,
                structure_quality=structure_quality,
                reasoning=f"High volatility: ATR percentile {tech.atr_percentile:.1f}%"
            )
            self._update_history(result)
            return result
        
        # Step 2: Check CHOPPY (no clear direction)
        choppiness = self._calculate_choppiness(features)
        if choppiness > 50 and tech.adx < 25:
            result = RegimeResult(
                regime_type=RegimeType.CHOPPY,
                confidence=0.7,
                exhaustion_risk=exhaustion_risk,
                structure_quality=structure_quality,
                reasoning=f"Choppy market: ADX {tech.adx:.1f}, no clear direction"
            )
            self._update_history(result)
            return result
        
        # Step 3: Check TRENDING
        if tech.adx >= 25:
            # Check EMA alignment
            ema_up = tech.ema_9 > tech.ema_21 > tech.ema_50
            ema_down = tech.ema_9 < tech.ema_21 < tech.ema_50
            
            if ema_up:
                confidence = self._calculate_trend_confidence(features, "up")
                result = RegimeResult(
                    regime_type=RegimeType.TRENDING_UP,
                    confidence=confidence,
                    exhaustion_risk=exhaustion_risk,
                    structure_quality=structure_quality,
                    reasoning=f"Uptrend: ADX {tech.adx:.1f}, EMA aligned up"
                )
                self._update_history(result)
                return result
            
            if ema_down:
                confidence = self._calculate_trend_confidence(features, "down")
                result = RegimeResult(
                    regime_type=RegimeType.TRENDING_DOWN,
                    confidence=confidence,
                    exhaustion_risk=exhaustion_risk,
                    structure_quality=structure_quality,
                    reasoning=f"Downtrend: ADX {tech.adx:.1f}, EMA aligned down"
                )
                self._update_history(result)
                return result
        
        # Step 4: Check RANGING
        if choppiness < 50:
            result = RegimeResult(
                regime_type=RegimeType.RANGING,
                confidence=0.75,
                exhaustion_risk=exhaustion_risk,
                structure_quality=structure_quality,
                reasoning=f"Ranging: Choppiness {choppiness:.1f}, clear S/R levels"
            )
            self._update_history(result)
            return result
        
        # Default: CHOPPY
        result = RegimeResult(
            regime_type=RegimeType.CHOPPY,
            confidence=0.5,
            exhaustion_risk=exhaustion_risk,
            structure_quality=structure_quality,
            reasoning="Unclear market conditions"
        )
        self._update_history(result)
        return result
    
    def _calculate_choppiness(self, features: AllFeatures) -> float:
        """Calculate choppiness index (simplified)"""
        tech = features.technical
        pa = features.price_action
        
        # Factors that increase choppiness:
        choppiness = 50.0  # Base
        
        # ADX < 20 = more choppy
        if tech.adx < 20:
            choppiness += 20
        elif tech.adx < 25:
            choppiness += 10
        else:
            choppiness -= 10
        
        # Many upper/lower wicks = indecision
        if pa.upper_wick_ratio > 0.3 and pa.lower_wick_ratio > 0.3:
            choppiness += 15
        
        # Small body = indecision
        if pa.body_percent < 0.3:
            choppiness += 10
        
        # MTF divergence = choppy
        if features.mtf.tf_divergence:
            choppiness += 15
        
        return min(100, max(0, choppiness))
    
    def _calculate_exhaustion(self, features: AllFeatures) -> ExhaustionIndicators:
        """Calculate exhaustion indicators"""
        tech = features.technical
        pa = features.price_action
        onchain = features.onchain
        
        indicators = ExhaustionIndicators()
        
        # RSI divergence (price up but RSI down, or vice versa)
        if tech.rsi_14 > 70 or tech.rsi_14 < 30:
            indicators.extreme_rsi = 1.0
        elif tech.rsi_14 > 60 or tech.rsi_14 < 40:
            indicators.extreme_rsi = 0.5
        
        # Volume declining (approximated from features)
        # Would need volume history for proper calculation
        indicators.volume_declining = 0.0
        
        # Body shrinking
        if pa.body_percent < 0.3:
            indicators.body_shrinking = 1.0 - (pa.body_percent / 0.3)
        
        # On-chain divergence
        # If price up but exchange inflow high (selling pressure)
        if onchain.exchange_netflow > 0:
            indicators.onchain_divergence = min(1.0, onchain.exchange_netflow / 10000)
        
        return indicators
    
    def _calculate_structure_quality(self, features: AllFeatures) -> float:
        """Calculate market structure quality"""
        pa = features.price_action
        
        quality = 0.5  # Base
        
        # Clear trend structure
        if pa.trend_structure == 1:  # HH + HL = uptrend
            quality += 0.3
        elif pa.trend_structure == -1:  # LH + LL = downtrend
            quality += 0.3
        
        # Good swing count
        if pa.hh_count >= 2 or pa.ll_count >= 2:
            quality += 0.1
        
        # Not too much consolidation
        if pa.consolidation_bars < 5:
            quality += 0.1
        
        return min(1.0, max(0.0, quality))
    
    def _calculate_trend_confidence(self, features: AllFeatures, direction: str) -> float:
        """Calculate confidence in trend direction"""
        tech = features.technical
        mtf = features.mtf
        pa = features.price_action
        
        confidence = 0.65  # Base
        
        # ADX strength
        if tech.adx > 30:
            confidence += 0.1
        if tech.adx > 40:
            confidence += 0.1
        
        # MTF alignment
        if direction == "up" and mtf.tf_15m_trend == 1 and mtf.tf_5m_trend == 1:
            confidence += 0.1
        elif direction == "down" and mtf.tf_15m_trend == -1 and mtf.tf_5m_trend == -1:
            confidence += 0.1
        
        # Trend structure
        if direction == "up" and pa.trend_structure == 1:
            confidence += 0.05
        elif direction == "down" and pa.trend_structure == -1:
            confidence += 0.05
        
        return min(0.95, confidence)
    
    def _update_history(self, result: RegimeResult):
        """Update regime history"""
        self.last_regime = result
        self.regime_history.append(result.regime_type)
        
        # Keep last 100 regimes
        if len(self.regime_history) > 100:
            self.regime_history = self.regime_history[-100:]
    
    def get_regime_stability(self, lookback: int = 10) -> float:
        """Check how stable the regime has been"""
        if len(self.regime_history) < lookback:
            return 0.5
        
        recent = self.regime_history[-lookback:]
        most_common = max(set(recent), key=recent.count)
        stability = recent.count(most_common) / lookback
        
        return stability

