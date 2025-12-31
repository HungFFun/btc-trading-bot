"""
Learning Engine - Analyze patterns from trade results
"""
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import logging
import uuid

logger = logging.getLogger(__name__)


@dataclass
class TradeResult:
    """Trade result for analysis"""
    signal_id: str
    direction: str
    strategy: str
    regime: str
    setup_quality: int
    confidence: float
    result: str  # WIN, LOSS, TIMEOUT
    pnl: float
    mfe: float
    mae: float
    duration_minutes: int
    features: Dict[str, Any]


@dataclass
class Lesson:
    """Learning insight"""
    lesson_id: str
    created_at: datetime
    signal_ids: List[str]
    pattern_type: str
    observation: str
    conclusion: str
    action_suggested: str
    sample_size: int
    confidence: float
    validated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'lesson_id': self.lesson_id,
            'created_at': self.created_at.isoformat(),
            'pattern_type': self.pattern_type,
            'observation': self.observation,
            'conclusion': self.conclusion,
            'action_suggested': self.action_suggested,
            'sample_size': self.sample_size,
            'confidence': self.confidence,
            'validated': self.validated
        }


class LearningEngine:
    """
    Analyze trade results to find patterns and generate insights.
    
    Analyzes:
    - Winning patterns
    - Losing patterns
    - Condition correlations
    - On-chain correlations
    """
    
    def __init__(self, min_sample_size: int = 5):
        self.min_sample_size = min_sample_size
        self.trade_history: List[TradeResult] = []
        self.lessons: List[Lesson] = []
        
        # Pattern tracking
        self.pattern_stats: Dict[str, Dict] = defaultdict(lambda: {
            'wins': 0, 'losses': 0, 'total_pnl': 0.0,
            'signals': []
        })
    
    def add_result(self, result: TradeResult):
        """Add a trade result for analysis"""
        self.trade_history.append(result)
        
        # Update pattern stats
        patterns = self._extract_patterns(result)
        for pattern in patterns:
            stats = self.pattern_stats[pattern]
            if result.result == "WIN":
                stats['wins'] += 1
            else:
                stats['losses'] += 1
            stats['total_pnl'] += result.pnl
            stats['signals'].append(result.signal_id)
    
    def analyze(self, results: List[TradeResult]) -> List[Lesson]:
        """
        Analyze new results and generate lessons.
        
        Args:
            results: List of new trade results
        
        Returns:
            List of new lessons discovered
        """
        new_lessons = []
        
        for result in results:
            self.add_result(result)
        
        # Only analyze if we have enough data
        if len(self.trade_history) < self.min_sample_size:
            return new_lessons
        
        # Analyze patterns
        new_lessons.extend(self._analyze_winning_patterns())
        new_lessons.extend(self._analyze_losing_patterns())
        new_lessons.extend(self._analyze_condition_correlations())
        new_lessons.extend(self._analyze_regime_performance())
        
        # Store new lessons
        self.lessons.extend(new_lessons)
        
        return new_lessons
    
    def _extract_patterns(self, result: TradeResult) -> List[str]:
        """Extract pattern identifiers from a trade result"""
        patterns = []
        
        # Strategy + Direction
        patterns.append(f"{result.strategy}_{result.direction}")
        
        # Regime
        patterns.append(f"regime_{result.regime}")
        
        # Setup quality range
        if result.setup_quality >= 90:
            patterns.append("quality_90_plus")
        elif result.setup_quality >= 80:
            patterns.append("quality_80_89")
        elif result.setup_quality >= 70:
            patterns.append("quality_70_79")
        
        # Confidence range
        if result.confidence >= 0.85:
            patterns.append("confidence_high")
        elif result.confidence >= 0.75:
            patterns.append("confidence_medium")
        else:
            patterns.append("confidence_low")
        
        # Feature-based patterns
        features = result.features
        
        # RSI zones
        rsi = features.get('rsi_14', 50)
        if rsi < 30:
            patterns.append("rsi_oversold")
        elif rsi > 70:
            patterns.append("rsi_overbought")
        
        # ADX strength
        adx = features.get('adx', 25)
        if adx > 35:
            patterns.append("adx_strong")
        elif adx < 20:
            patterns.append("adx_weak")
        
        return patterns
    
    def _analyze_winning_patterns(self) -> List[Lesson]:
        """Find patterns that lead to wins"""
        lessons = []
        
        for pattern, stats in self.pattern_stats.items():
            total = stats['wins'] + stats['losses']
            if total < self.min_sample_size:
                continue
            
            win_rate = stats['wins'] / total
            
            # Good patterns (>65% win rate)
            if win_rate >= 0.65:
                lesson = Lesson(
                    lesson_id=self._generate_lesson_id(),
                    created_at=datetime.utcnow(),
                    signal_ids=stats['signals'][-10:],
                    pattern_type="winning_pattern",
                    observation=f"Pattern '{pattern}' has {win_rate:.0%} win rate over {total} trades",
                    conclusion=f"This pattern is highly effective",
                    action_suggested=f"Prioritize signals matching '{pattern}'",
                    sample_size=total,
                    confidence=min(0.95, win_rate)
                )
                lessons.append(lesson)
        
        return lessons
    
    def _analyze_losing_patterns(self) -> List[Lesson]:
        """Find patterns that lead to losses"""
        lessons = []
        
        for pattern, stats in self.pattern_stats.items():
            total = stats['wins'] + stats['losses']
            if total < self.min_sample_size:
                continue
            
            loss_rate = stats['losses'] / total
            
            # Bad patterns (>60% loss rate)
            if loss_rate >= 0.60:
                lesson = Lesson(
                    lesson_id=self._generate_lesson_id(),
                    created_at=datetime.utcnow(),
                    signal_ids=stats['signals'][-10:],
                    pattern_type="losing_pattern",
                    observation=f"Pattern '{pattern}' has {loss_rate:.0%} loss rate over {total} trades",
                    conclusion=f"This pattern is underperforming",
                    action_suggested=f"Avoid or reduce signals matching '{pattern}'",
                    sample_size=total,
                    confidence=min(0.95, loss_rate)
                )
                lessons.append(lesson)
        
        return lessons
    
    def _analyze_condition_correlations(self) -> List[Lesson]:
        """Analyze correlations between conditions and outcomes"""
        lessons = []
        
        if len(self.trade_history) < 20:
            return lessons
        
        # Analyze by time of day (session)
        session_performance = defaultdict(lambda: {'wins': 0, 'losses': 0})
        
        for trade in self.trade_history:
            hour = trade.features.get('hour', 12)
            
            if 13 <= hour < 16:
                session = "overlap"
            elif 16 <= hour < 21:
                session = "ny"
            elif 8 <= hour < 13:
                session = "london"
            else:
                session = "asia"
            
            if trade.result == "WIN":
                session_performance[session]['wins'] += 1
            else:
                session_performance[session]['losses'] += 1
        
        # Find best/worst sessions
        for session, stats in session_performance.items():
            total = stats['wins'] + stats['losses']
            if total < 5:
                continue
            
            win_rate = stats['wins'] / total
            
            if win_rate >= 0.70:
                lessons.append(Lesson(
                    lesson_id=self._generate_lesson_id(),
                    created_at=datetime.utcnow(),
                    signal_ids=[],
                    pattern_type="session_performance",
                    observation=f"{session.upper()} session has {win_rate:.0%} win rate",
                    conclusion=f"Best performance in {session} session",
                    action_suggested=f"Prioritize trading during {session} session",
                    sample_size=total,
                    confidence=win_rate
                ))
            elif win_rate <= 0.35:
                lessons.append(Lesson(
                    lesson_id=self._generate_lesson_id(),
                    created_at=datetime.utcnow(),
                    signal_ids=[],
                    pattern_type="session_performance",
                    observation=f"{session.upper()} session has only {win_rate:.0%} win rate",
                    conclusion=f"Poor performance in {session} session",
                    action_suggested=f"Reduce trading during {session} session",
                    sample_size=total,
                    confidence=1 - win_rate
                ))
        
        return lessons
    
    def _analyze_regime_performance(self) -> List[Lesson]:
        """Analyze performance by market regime"""
        lessons = []
        
        regime_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0})
        
        for trade in self.trade_history:
            regime = trade.regime
            if trade.result == "WIN":
                regime_stats[regime]['wins'] += 1
            else:
                regime_stats[regime]['losses'] += 1
            regime_stats[regime]['pnl'] += trade.pnl
        
        for regime, stats in regime_stats.items():
            total = stats['wins'] + stats['losses']
            if total < 5:
                continue
            
            win_rate = stats['wins'] / total
            avg_pnl = stats['pnl'] / total
            
            lesson = Lesson(
                lesson_id=self._generate_lesson_id(),
                created_at=datetime.utcnow(),
                signal_ids=[],
                pattern_type="regime_analysis",
                observation=f"{regime} regime: {win_rate:.0%} win rate, avg PnL ${avg_pnl:.2f}",
                conclusion="Performance varies by regime" if abs(avg_pnl) > 5 else "Consistent across regimes",
                action_suggested=f"{'Favor' if avg_pnl > 0 else 'Avoid'} trading in {regime}",
                sample_size=total,
                confidence=abs(win_rate - 0.5) + 0.5
            )
            lessons.append(lesson)
        
        return lessons
    
    def _generate_lesson_id(self) -> str:
        """Generate unique lesson ID"""
        return f"LESSON_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6].upper()}"
    
    def get_insights_summary(self) -> Dict[str, Any]:
        """Get summary of all insights"""
        winning = [l for l in self.lessons if l.pattern_type == "winning_pattern"]
        losing = [l for l in self.lessons if l.pattern_type == "losing_pattern"]
        
        return {
            'total_lessons': len(self.lessons),
            'winning_patterns': len(winning),
            'losing_patterns': len(losing),
            'top_winning': [l.pattern_type for l in sorted(winning, key=lambda x: x.confidence, reverse=True)[:3]],
            'top_losing': [l.pattern_type for l in sorted(losing, key=lambda x: x.confidence, reverse=True)[:3]]
        }
    
    def get_action_recommendations(self) -> List[str]:
        """Get actionable recommendations"""
        recommendations = []
        
        # Sort by confidence
        high_confidence = [l for l in self.lessons if l.confidence >= 0.7]
        
        for lesson in sorted(high_confidence, key=lambda x: x.confidence, reverse=True)[:5]:
            recommendations.append(lesson.action_suggested)
        
        return recommendations

