"""
5-Gate System - Filter Pipeline for Trade Signals
Only ~10-15% of signals pass all gates
"""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from ..features.feature_engine import AllFeatures
from ..features.regime import RegimeResult, RegimeType

logger = logging.getLogger(__name__)


class GateStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class GateResult:
    """Result of a single gate check"""
    gate_name: str
    status: GateStatus
    score: float  # 0-1
    reason: str
    details: dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class GateSystemResult:
    """Result of all gates"""
    passed: bool
    gate_results: List[GateResult]
    overall_score: float
    blocking_gate: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'passed': self.passed,
            'overall_score': self.overall_score,
            'blocking_gate': self.blocking_gate,
            'gates': {g.gate_name: {'status': g.status.value, 'score': g.score, 'reason': g.reason} 
                     for g in self.gate_results}
        }


@dataclass
class DailyState:
    """Daily trading state"""
    date: str
    pnl: float = 0.0
    trade_count: int = 0
    wins: int = 0
    losses: int = 0
    consecutive_losses: int = 0
    has_position: bool = False
    status: str = "ACTIVE"
    last_trade_time: Optional[datetime] = None
    
    @property
    def should_stop(self) -> bool:
        return self.status != "ACTIVE"


class FiveGateSystem:
    """
    5-Gate Filter System for trade signals.
    
    Gate 1: Context (Session, Funding, Events)
    Gate 2: Regime (Market condition)
    Gate 3: Signal Quality (Setup score)
    Gate 4: AI Confirmation
    Gate 5: Daily Limits (MOST IMPORTANT)
    """
    
    def __init__(
        self,
        context_min_score: float = 0.5,
        regime_confidence_min: float = 0.65,
        exhaustion_risk_max: float = 0.5,
        structure_quality_min: float = 0.6,
        setup_quality_min: int = 70,
        mtf_confluence_min: int = 2,
        ai_confidence_min: float = 0.65,
        max_risk_factors: int = 1,
        daily_target: float = 10.0,
        daily_stop: float = -15.0,
        max_trades: int = 3,
        max_consecutive_losses: int = 2,
        cooldown_minutes: int = 60
    ):
        # Gate 1 thresholds
        self.context_min_score = context_min_score
        
        # Gate 2 thresholds
        self.regime_confidence_min = regime_confidence_min
        self.exhaustion_risk_max = exhaustion_risk_max
        self.structure_quality_min = structure_quality_min
        
        # Gate 3 thresholds
        self.setup_quality_min = setup_quality_min
        self.mtf_confluence_min = mtf_confluence_min
        
        # Gate 4 thresholds
        self.ai_confidence_min = ai_confidence_min
        self.max_risk_factors = max_risk_factors
        
        # Gate 5 thresholds
        self.daily_target = daily_target
        self.daily_stop = daily_stop
        self.max_trades = max_trades
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_minutes = cooldown_minutes
    
    def evaluate(
        self,
        features: AllFeatures,
        regime: RegimeResult,
        signal: dict,
        daily_state: DailyState,
        ai_result: dict = None
    ) -> GateSystemResult:
        """
        Evaluate all 5 gates.
        
        Args:
            features: AllFeatures object
            regime: RegimeResult from detector
            signal: Potential signal dict
            daily_state: Current daily state
            ai_result: Optional AI prediction result
        
        Returns:
            GateSystemResult with pass/fail and details
        """
        gate_results = []
        
        # Gate 1: Context
        gate1 = self._check_gate1_context(features)
        gate_results.append(gate1)
        if gate1.status == GateStatus.FAILED:
            return GateSystemResult(
                passed=False,
                gate_results=gate_results,
                overall_score=gate1.score,
                blocking_gate="Gate 1: Context"
            )
        
        # Gate 2: Regime
        gate2 = self._check_gate2_regime(regime)
        gate_results.append(gate2)
        if gate2.status == GateStatus.FAILED:
            return GateSystemResult(
                passed=False,
                gate_results=gate_results,
                overall_score=(gate1.score + gate2.score) / 2,
                blocking_gate="Gate 2: Regime"
            )
        
        # Gate 3: Signal Quality
        gate3 = self._check_gate3_signal_quality(features, signal)
        gate_results.append(gate3)
        if gate3.status == GateStatus.FAILED:
            return GateSystemResult(
                passed=False,
                gate_results=gate_results,
                overall_score=(gate1.score + gate2.score + gate3.score) / 3,
                blocking_gate="Gate 3: Signal Quality"
            )
        
        # Gate 4: AI Confirmation
        gate4 = self._check_gate4_ai(ai_result)
        gate_results.append(gate4)
        if gate4.status == GateStatus.FAILED:
            return GateSystemResult(
                passed=False,
                gate_results=gate_results,
                overall_score=(gate1.score + gate2.score + gate3.score + gate4.score) / 4,
                blocking_gate="Gate 4: AI Confirmation"
            )
        
        # Gate 5: Daily Limits (MOST IMPORTANT)
        gate5 = self._check_gate5_daily_limits(daily_state)
        gate_results.append(gate5)
        if gate5.status == GateStatus.FAILED:
            return GateSystemResult(
                passed=False,
                gate_results=gate_results,
                overall_score=0.0,  # Gate 5 failure = 0 overall
                blocking_gate="Gate 5: Daily Limits"
            )
        
        # All gates passed!
        overall_score = sum(g.score for g in gate_results) / len(gate_results)
        return GateSystemResult(
            passed=True,
            gate_results=gate_results,
            overall_score=overall_score
        )
    
    def _check_gate1_context(self, features: AllFeatures) -> GateResult:
        """
        Gate 1: Context Check
        - Session quality
        - Funding buffer
        - No Dead Zone
        """
        now = datetime.utcnow()
        score = 0.0
        reasons = []
        
        # Session quality based on UTC hour
        hour = now.hour
        
        if 13 <= hour < 16:  # London + NY overlap
            session_score = 1.0
            session_name = "Overlap (London+NY)"
        elif 16 <= hour < 21:  # New York
            session_score = 0.9
            session_name = "New York"
        elif 8 <= hour < 13:  # London
            session_score = 0.8
            session_name = "London"
        elif 0 <= hour < 8:  # Asia
            session_score = 0.5
            session_name = "Asia"
        else:  # 21:00-00:00 = Dead Zone
            return GateResult(
                gate_name="Gate 1: Context",
                status=GateStatus.FAILED,
                score=0.0,
                reason=f"Dead Zone (21:00-00:00 UTC) - NO TRADE",
                details={'session': 'Dead Zone', 'hour': hour}
            )
        
        score = session_score
        reasons.append(f"Session: {session_name} ({session_score})")
        
        # Funding buffer check (±20 minutes from funding)
        if features.funding:
            time_to_funding = features.funding.time_to_funding
            if time_to_funding <= 20:
                score *= 0.5
                reasons.append(f"Near funding ({time_to_funding}m)")
        
        # Check if score meets minimum
        if score >= self.context_min_score:
            return GateResult(
                gate_name="Gate 1: Context",
                status=GateStatus.PASSED,
                score=score,
                reason="; ".join(reasons),
                details={'session': session_name, 'hour': hour}
            )
        else:
            return GateResult(
                gate_name="Gate 1: Context",
                status=GateStatus.FAILED,
                score=score,
                reason=f"Context score {score:.2f} < {self.context_min_score}",
                details={'session': session_name, 'hour': hour}
            )
    
    def _check_gate2_regime(self, regime: RegimeResult) -> GateResult:
        """
        Gate 2: Regime Check
        - Not CHOPPY
        - Exhaustion risk < 0.5
        - Structure quality >= 0.6
        - Confidence >= 65%
        """
        if regime.regime_type == RegimeType.CHOPPY:
            return GateResult(
                gate_name="Gate 2: Regime",
                status=GateStatus.FAILED,
                score=0.0,
                reason="CHOPPY regime - NO TRADE",
                details={'regime': regime.regime_type.value}
            )
        
        if regime.exhaustion_risk >= self.exhaustion_risk_max:
            return GateResult(
                gate_name="Gate 2: Regime",
                status=GateStatus.FAILED,
                score=regime.confidence,
                reason=f"High exhaustion risk: {regime.exhaustion_risk:.2f}",
                details={'regime': regime.regime_type.value, 'exhaustion': regime.exhaustion_risk}
            )
        
        if regime.structure_quality < self.structure_quality_min:
            return GateResult(
                gate_name="Gate 2: Regime",
                status=GateStatus.FAILED,
                score=regime.confidence,
                reason=f"Low structure quality: {regime.structure_quality:.2f}",
                details={'regime': regime.regime_type.value, 'structure': regime.structure_quality}
            )
        
        if regime.confidence < self.regime_confidence_min:
            return GateResult(
                gate_name="Gate 2: Regime",
                status=GateStatus.FAILED,
                score=regime.confidence,
                reason=f"Low regime confidence: {regime.confidence:.2%}",
                details={'regime': regime.regime_type.value, 'confidence': regime.confidence}
            )
        
        return GateResult(
            gate_name="Gate 2: Regime",
            status=GateStatus.PASSED,
            score=regime.confidence,
            reason=f"{regime.regime_type.value} with {regime.confidence:.0%} confidence",
            details={'regime': regime.regime_type.value, 'confidence': regime.confidence}
        )
    
    def _check_gate3_signal_quality(self, features: AllFeatures, signal: dict) -> GateResult:
        """
        Gate 3: Signal + Setup Quality
        - Setup quality >= 70
        - MTF confluence >= 2/3
        - Volume confirmation
        - Historical win rate >= 50%
        """
        setup_quality = signal.get('setup_quality', 0)
        
        if setup_quality < self.setup_quality_min:
            return GateResult(
                gate_name="Gate 3: Signal Quality",
                status=GateStatus.FAILED,
                score=setup_quality / 100,
                reason=f"Setup quality {setup_quality} < {self.setup_quality_min}",
                details={'setup_quality': setup_quality}
            )
        
        # MTF confluence
        mtf_alignment = features.mtf.mtf_alignment if features.mtf else 0
        if mtf_alignment < self.mtf_confluence_min:
            return GateResult(
                gate_name="Gate 3: Signal Quality",
                status=GateStatus.FAILED,
                score=setup_quality / 100,
                reason=f"MTF confluence {mtf_alignment} < {self.mtf_confluence_min}",
                details={'setup_quality': setup_quality, 'mtf_alignment': mtf_alignment}
            )
        
        # Check for deal breakers
        tech = features.technical
        direction = signal.get('direction', 'LONG')
        
        # RSI extreme
        if direction == 'LONG' and tech.rsi_14 > 80:
            return GateResult(
                gate_name="Gate 3: Signal Quality",
                status=GateStatus.FAILED,
                score=0.0,
                reason=f"RSI {tech.rsi_14:.1f} too high for LONG",
                details={'rsi': tech.rsi_14}
            )
        if direction == 'SHORT' and tech.rsi_14 < 20:
            return GateResult(
                gate_name="Gate 3: Signal Quality",
                status=GateStatus.FAILED,
                score=0.0,
                reason=f"RSI {tech.rsi_14:.1f} too low for SHORT",
                details={'rsi': tech.rsi_14}
            )
        
        return GateResult(
            gate_name="Gate 3: Signal Quality",
            status=GateStatus.PASSED,
            score=setup_quality / 100,
            reason=f"Setup quality {setup_quality}/100, MTF alignment {mtf_alignment}",
            details={'setup_quality': setup_quality, 'mtf_alignment': mtf_alignment}
        )
    
    def _check_gate4_ai(self, ai_result: dict = None) -> GateResult:
        """
        Gate 4: AI Confirmation
        - Confidence >= 65%
        - Risk factors <= 1
        """
        if ai_result is None:
            # If no AI result, skip this gate
            return GateResult(
                gate_name="Gate 4: AI Confirmation",
                status=GateStatus.SKIPPED,
                score=0.65,  # Default score
                reason="AI model not available, skipped",
                details={}
            )
        
        confidence = ai_result.get('confidence', 0)
        risk_factors = len(ai_result.get('risk_factors', []))
        
        if confidence < self.ai_confidence_min:
            return GateResult(
                gate_name="Gate 4: AI Confirmation",
                status=GateStatus.FAILED,
                score=confidence,
                reason=f"AI confidence {confidence:.0%} < {self.ai_confidence_min:.0%}",
                details={'confidence': confidence}
            )
        
        if risk_factors > self.max_risk_factors:
            return GateResult(
                gate_name="Gate 4: AI Confirmation",
                status=GateStatus.FAILED,
                score=confidence,
                reason=f"Too many risk factors: {risk_factors}",
                details={'confidence': confidence, 'risk_factors': risk_factors}
            )
        
        return GateResult(
            gate_name="Gate 4: AI Confirmation",
            status=GateStatus.PASSED,
            score=confidence,
            reason=f"AI confidence {confidence:.0%}",
            details={'confidence': confidence, 'risk_factors': risk_factors}
        )
    
    def _check_gate5_daily_limits(self, daily_state: DailyState) -> GateResult:
        """
        Gate 5: Daily Limits (MOST IMPORTANT)
        - PnL not at target (+$10) or stop (-$15)
        - Trade count < 3
        - Not 2 consecutive losses (or waited 1h)
        - No open position
        """
        # Check daily target
        if daily_state.pnl >= self.daily_target:
            return GateResult(
                gate_name="Gate 5: Daily Limits",
                status=GateStatus.FAILED,
                score=0.0,
                reason=f"Daily target reached: +${daily_state.pnl:.2f}",
                details={'pnl': daily_state.pnl, 'status': 'TARGET_HIT'}
            )
        
        # Check daily stop
        if daily_state.pnl <= self.daily_stop:
            return GateResult(
                gate_name="Gate 5: Daily Limits",
                status=GateStatus.FAILED,
                score=0.0,
                reason=f"Daily stop hit: ${daily_state.pnl:.2f}",
                details={'pnl': daily_state.pnl, 'status': 'STOP_HIT'}
            )
        
        # Check max trades
        if daily_state.trade_count >= self.max_trades:
            return GateResult(
                gate_name="Gate 5: Daily Limits",
                status=GateStatus.FAILED,
                score=0.0,
                reason=f"Max trades reached: {daily_state.trade_count}/{self.max_trades}",
                details={'trade_count': daily_state.trade_count, 'status': 'MAX_TRADES'}
            )
        
        # Check daily status
        if daily_state.status != "ACTIVE":
            return GateResult(
                gate_name="Gate 5: Daily Limits",
                status=GateStatus.FAILED,
                score=0.0,
                reason=f"Daily status: {daily_state.status}",
                details={'status': daily_state.status}
            )
        
        # Check consecutive losses and cooldown
        if daily_state.consecutive_losses >= self.max_consecutive_losses:
            if daily_state.last_trade_time:
                minutes_since = (datetime.utcnow() - daily_state.last_trade_time).total_seconds() / 60
                if minutes_since < self.cooldown_minutes:
                    return GateResult(
                        gate_name="Gate 5: Daily Limits",
                        status=GateStatus.FAILED,
                        score=0.0,
                        reason=f"Cooling down after {daily_state.consecutive_losses} losses ({int(self.cooldown_minutes - minutes_since)}m left)",
                        details={'consecutive_losses': daily_state.consecutive_losses}
                    )
        
        # Check open position
        if daily_state.has_position:
            return GateResult(
                gate_name="Gate 5: Daily Limits",
                status=GateStatus.FAILED,
                score=0.0,
                reason="Position already open",
                details={'has_position': True}
            )
        
        return GateResult(
            gate_name="Gate 5: Daily Limits",
            status=GateStatus.PASSED,
            score=1.0,
            reason=f"All daily checks passed (trades: {daily_state.trade_count}/{self.max_trades}, PnL: ${daily_state.pnl:.2f})",
            details={
                'trade_count': daily_state.trade_count,
                'pnl': daily_state.pnl,
                'consecutive_losses': daily_state.consecutive_losses
            }
        )

