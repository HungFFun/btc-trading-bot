"""
Bot IQ Calculator - Score trade quality
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class IQScore:
    """IQ score breakdown"""
    total: int  # 0-100
    decision_quality: float
    execution_quality: float
    risk_adherence: float
    details: Dict[str, float]


@dataclass
class IQTrend:
    """IQ trend analysis"""
    avg_10: float
    avg_20: float
    trend: str  # improving, declining, stable
    warning: bool
    critical: bool


class BotIQCalculator:
    """
    Calculate Bot IQ scores for trades.
    
    Components:
    - Decision Quality (45%)
    - Execution Quality (30%)
    - Risk Adherence (25%)
    """
    
    def __init__(
        self,
        decision_weight: float = 0.45,
        execution_weight: float = 0.30,
        risk_weight: float = 0.25,
        warning_threshold: int = 60,
        critical_threshold: int = 50
    ):
        self.decision_weight = decision_weight
        self.execution_weight = execution_weight
        self.risk_weight = risk_weight
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        
        self.iq_history: List[int] = []
    
    def calculate(self, signal, result) -> IQScore:
        """
        Calculate IQ score for a trade.
        
        Args:
            signal: Signal object with prediction details
            result: TrackingResult with outcome
        
        Returns:
            IQScore with breakdown
        """
        details = {}
        
        # Decision Quality (45%)
        decision = self._calculate_decision_quality(signal, result)
        details['confidence_vs_outcome'] = decision['confidence_vs_outcome']
        details['setup_quality_vs_outcome'] = decision['setup_quality_vs_outcome']
        details['timing_precision'] = decision['timing']
        decision_score = decision['total']
        
        # Execution Quality (30%)
        execution = self._calculate_execution_quality(signal, result)
        details['slippage_control'] = execution['slippage']
        details['entry_precision'] = execution['entry']
        details['exit_efficiency'] = execution['exit']
        execution_score = execution['total']
        
        # Risk Adherence (25%)
        risk = self._calculate_risk_adherence(signal, result)
        details['position_accuracy'] = risk['position']
        details['sl_discipline'] = risk['sl']
        details['rr_achieved'] = risk['rr']
        risk_score = risk['total']
        
        # Calculate total IQ
        total = int(
            self.decision_weight * decision_score +
            self.execution_weight * execution_score +
            self.risk_weight * risk_score
        )
        total = max(0, min(100, total))
        
        # Track history
        self.iq_history.append(total)
        if len(self.iq_history) > 100:
            self.iq_history = self.iq_history[-100:]
        
        return IQScore(
            total=total,
            decision_quality=decision_score,
            execution_quality=execution_score,
            risk_adherence=risk_score,
            details=details
        )
    
    def _calculate_decision_quality(self, signal, result) -> Dict[str, float]:
        """Calculate decision quality score"""
        is_win = result.status == "WIN"
        
        # Confidence vs Outcome (40%)
        # High confidence + win = good, high confidence + loss = bad
        confidence = signal.confidence
        if is_win:
            conf_score = confidence * 100
        else:
            # Penalize for high confidence losses
            conf_score = (1 - confidence) * 100
        
        # Setup Quality vs Outcome (30%)
        setup_quality = signal.setup_quality
        if is_win:
            setup_score = setup_quality
        else:
            # Lower score for high quality setups that lost
            setup_score = 100 - setup_quality * 0.5
        
        # Timing Precision (30%)
        # Based on MFE - if trade went in our direction quickly
        mfe = result.mfe
        mae = result.mae
        
        if mfe > mae:
            timing_score = min(100, (mfe / (mfe + mae)) * 100 if (mfe + mae) > 0 else 50)
        else:
            timing_score = max(0, 50 - mae * 10)
        
        total = (
            conf_score * 0.4 +
            setup_score * 0.3 +
            timing_score * 0.3
        )
        
        return {
            'confidence_vs_outcome': conf_score,
            'setup_quality_vs_outcome': setup_score,
            'timing': timing_score,
            'total': total
        }
    
    def _calculate_execution_quality(self, signal, result) -> Dict[str, float]:
        """Calculate execution quality score"""
        # Slippage Control (50%)
        # Assuming minimal slippage for now
        slippage_score = 90  # Good execution
        
        # Entry Precision (30%)
        # Based on how close to optimal entry
        entry_score = 80  # Default good
        
        # Exit Efficiency (20%)
        # Based on whether we captured MFE
        mfe = result.mfe
        if result.status == "WIN":
            # Hit TP, so we captured the move
            exit_score = 100
        elif result.status == "TIMEOUT":
            # Timed out, might have left profit on table
            exit_score = 50
        else:
            # Hit SL
            exit_score = 40
        
        total = (
            slippage_score * 0.5 +
            entry_score * 0.3 +
            exit_score * 0.2
        )
        
        return {
            'slippage': slippage_score,
            'entry': entry_score,
            'exit': exit_score,
            'total': total
        }
    
    def _calculate_risk_adherence(self, signal, result) -> Dict[str, float]:
        """Calculate risk adherence score"""
        # Position Accuracy (50%)
        # Check if position was at planned size
        planned_margin = 150
        actual_margin = signal.position_margin
        
        if abs(actual_margin - planned_margin) < 1:
            position_score = 100
        else:
            deviation = abs(actual_margin - planned_margin) / planned_margin
            position_score = max(0, 100 - deviation * 100)
        
        # SL Discipline (30%)
        # Check if SL was honored
        if result.status == "LOSS":
            # SL was hit, discipline maintained
            sl_score = 100
        elif result.status == "WIN":
            sl_score = 100
        else:
            # Timeout - might have avoided SL
            sl_score = 80
        
        # R:R Achieved (20%)
        planned_rr = 2.0
        if result.status == "WIN":
            # Achieved planned R:R
            rr_score = 100
        elif result.status == "LOSS":
            # Lost planned amount
            rr_score = 80  # Still followed plan
        else:
            # Timeout - variable R:R
            if result.result_pnl > 0:
                rr_score = 70
            else:
                rr_score = 50
        
        total = (
            position_score * 0.5 +
            sl_score * 0.3 +
            rr_score * 0.2
        )
        
        return {
            'position': position_score,
            'sl': sl_score,
            'rr': rr_score,
            'total': total
        }
    
    def get_trend(self) -> IQTrend:
        """Get IQ trend analysis"""
        if len(self.iq_history) < 10:
            return IQTrend(
                avg_10=np.mean(self.iq_history) if self.iq_history else 0,
                avg_20=np.mean(self.iq_history) if self.iq_history else 0,
                trend="stable",
                warning=False,
                critical=False
            )
        
        avg_10 = np.mean(self.iq_history[-10:])
        avg_20 = np.mean(self.iq_history[-20:]) if len(self.iq_history) >= 20 else avg_10
        
        # Determine trend
        if avg_10 > avg_20 + 5:
            trend = "improving"
        elif avg_10 < avg_20 - 5:
            trend = "declining"
        else:
            trend = "stable"
        
        # Check thresholds
        warning = avg_10 < self.warning_threshold
        critical = avg_10 < self.critical_threshold
        
        return IQTrend(
            avg_10=avg_10,
            avg_20=avg_20,
            trend=trend,
            warning=warning,
            critical=critical
        )
    
    def check_degradation(self) -> Optional[Dict[str, Any]]:
        """Check for IQ degradation that needs alert"""
        trend = self.get_trend()
        
        if trend.critical:
            return {
                'level': 'CRITICAL',
                'message': f'IQ critically low: {trend.avg_10:.0f}/100 (last 10 trades)',
                'action': 'PAUSE trading and review'
            }
        
        if trend.warning:
            return {
                'level': 'WARNING',
                'message': f'IQ declining: {trend.avg_10:.0f}/100 (last 10 trades)',
                'action': 'Review recent trades'
            }
        
        if trend.trend == "declining" and trend.avg_10 < 70:
            return {
                'level': 'INFO',
                'message': f'IQ trend declining: {trend.avg_10:.0f}/100',
                'action': 'Monitor closely'
            }
        
        return None

