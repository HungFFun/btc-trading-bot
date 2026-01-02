"""
BTC Direction Predictor Module
★ INDEPENDENT MODULE - Does NOT affect core trading logic ★

Purpose:
- Analyze current market data
- Predict BTC direction (LONG/SHORT/NEUTRAL)
- Send suggestions via Telegram
- Does NOT auto-execute trades

Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class SignalStrength(str, Enum):
    VERY_STRONG = "VERY_STRONG"
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


@dataclass
class IndicatorResult:
    """Result from a single indicator"""
    name: str
    value: float
    signal: Direction
    weight: float
    description: str


@dataclass
class AnalysisComponent:
    """Result from an analyzer (technical, sentiment, etc.)"""
    name: str
    direction: Direction
    score: float  # -100 to +100
    confidence: float  # 0-100
    indicators: List[IndicatorResult]
    reasoning: List[str]


@dataclass
class ConfidenceBreakdown:
    """Confidence calculation breakdown"""
    overall_confidence: float  # 0-100
    win_probability: float  # 0-100
    signal_strength: float
    indicator_agreement: float
    risk_factors: List[str]
    risk_penalty: float


@dataclass
class PredictionSignal:
    """Complete prediction signal"""
    # Identification
    prediction_id: str
    timestamp: datetime
    model_version: str = "1.0.0"
    
    # Direction
    direction: Direction = Direction.NEUTRAL
    strength: SignalStrength = SignalStrength.WEAK
    
    # Confidence
    confidence: float = 0.0  # 0-100%
    win_probability: float = 0.0  # 0-100%
    
    # Prices
    current_price: float = 0.0
    suggested_entry: float = 0.0
    suggested_tp: float = 0.0
    suggested_sl: float = 0.0
    tp_percent: float = 0.0
    sl_percent: float = 0.0
    
    # Position
    suggested_leverage: int = 20
    position_size_usd: float = 150.0
    
    # Risk/Reward
    risk_reward_ratio: float = 2.0
    potential_profit: float = 0.0
    potential_loss: float = 0.0
    
    # Analysis
    overall_score: float = 0.0
    indicators_summary: Dict[str, float] = field(default_factory=dict)
    reasoning: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'prediction_id': self.prediction_id,
            'timestamp': self.timestamp.isoformat(),
            'direction': self.direction.value,
            'strength': self.strength.value,
            'confidence': self.confidence,
            'win_probability': self.win_probability,
            'current_price': self.current_price,
            'suggested_entry': self.suggested_entry,
            'suggested_tp': self.suggested_tp,
            'suggested_sl': self.suggested_sl,
            'tp_percent': self.tp_percent,
            'sl_percent': self.sl_percent,
            'suggested_leverage': self.suggested_leverage,
            'position_size_usd': self.position_size_usd,
            'risk_reward_ratio': self.risk_reward_ratio,
            'potential_profit': self.potential_profit,
            'potential_loss': self.potential_loss,
            'overall_score': self.overall_score,
            'indicators_summary': self.indicators_summary,
            'reasoning': self.reasoning,
            'warnings': self.warnings
        }


# Export main classes
from .btc_direction_predictor import BTCDirectionPredictor
from .prediction_engine import PredictionEngine
from .confidence_calculator import ConfidenceCalculator
from .signal_formatter import SignalFormatter

__all__ = [
    'Direction',
    'SignalStrength',
    'IndicatorResult',
    'AnalysisComponent',
    'ConfidenceBreakdown',
    'PredictionSignal',
    'BTCDirectionPredictor',
    'PredictionEngine',
    'ConfidenceCalculator',
    'SignalFormatter'
]

