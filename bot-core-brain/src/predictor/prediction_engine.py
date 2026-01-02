"""
Prediction Engine - Combines multiple analyzers
★ INDEPENDENT - Does not import from core trading logic ★
"""

import logging
from typing import Dict, Any, List, Optional

from . import Direction, AnalysisComponent, IndicatorResult
from .indicators.technical import TechnicalAnalyzer
from .indicators.sentiment import SentimentAnalyzer
from .indicators.structure import StructureAnalyzer

logger = logging.getLogger(__name__)


class PredictionEngine:
    """
    Analysis engine - combines multiple indicator types
    
    Weights:
    - Technical: 40%
    - Structure: 20%
    - Sentiment: 25%
    - On-chain: 15% (optional)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Default weights
        weights_config = config.get('weights', {})
        self.weights = {
            'technical': weights_config.get('technical', 0.40),
            'structure': weights_config.get('structure', 0.20),
            'sentiment': weights_config.get('sentiment', 0.25),
            'onchain': weights_config.get('onchain', 0.15)
        }
        
        # Initialize analyzers
        self.technical = TechnicalAnalyzer(config)
        self.structure = StructureAnalyzer(config)
        self.sentiment = SentimentAnalyzer(config)
        
        logger.info(f"PredictionEngine initialized with weights: {self.weights}")
    
    def analyze(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Run all analyzers and combine results
        
        Args:
            market_data: Dictionary containing:
                - current_price: float
                - candles: Dict[timeframe, List[candle]]
                - funding_rate: float (optional)
                - volume_24h: float (optional)
        
        Returns:
            {
                'direction': Direction,
                'score': float (-100 to +100),
                'components': List[AnalysisComponent],
                'indicators_summary': Dict[str, float],
                'reasoning': List[str]
            }
        """
        try:
            components: List[AnalysisComponent] = []
            
            # 1. Technical Analysis (40%)
            tech = self.technical.analyze(market_data)
            if tech:
                components.append(tech)
                logger.debug(f"Technical: {tech.direction.value} (score: {tech.score:.1f})")
            
            # 2. Structure Analysis (20%)
            struct = self.structure.analyze(market_data)
            if struct:
                components.append(struct)
                logger.debug(f"Structure: {struct.direction.value} (score: {struct.score:.1f})")
            
            # 3. Sentiment Analysis (25%)
            sent = self.sentiment.analyze(market_data)
            if sent:
                components.append(sent)
                logger.debug(f"Sentiment: {sent.direction.value} (score: {sent.score:.1f})")
            
            if not components:
                logger.warning("No analysis components generated")
                return None
            
            # Calculate weighted score
            score = self._calculate_score(components)
            direction = self._determine_direction(score)
            
            # Extract indicators summary
            indicators_summary = self._extract_indicators(components)
            
            # Generate reasoning
            reasoning = self._generate_reasoning(components, direction)
            
            return {
                'direction': direction,
                'score': score,
                'components': components,
                'indicators_summary': indicators_summary,
                'reasoning': reasoning
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return None
    
    def _calculate_score(self, components: List[AnalysisComponent]) -> float:
        """Calculate weighted score from all components"""
        total_weight = 0
        weighted_score = 0
        
        for comp in components:
            weight = self.weights.get(comp.name.lower(), 0.25)
            weighted_score += comp.score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0
        
        return weighted_score / total_weight * (len(components) / 3)  # Normalize
    
    def _determine_direction(self, score: float) -> Direction:
        """Determine direction from score - Always LONG or SHORT"""
        # No neutral zone - positive = LONG, negative/zero = SHORT
        if score >= 0:
            return Direction.LONG
        else:
            return Direction.SHORT
    
    def _extract_indicators(self, components: List[AnalysisComponent]) -> Dict[str, float]:
        """Extract all indicator values for summary"""
        summary = {}
        
        for comp in components:
            for ind in comp.indicators:
                summary[ind.name] = ind.value
        
        return summary
    
    def _generate_reasoning(
        self, 
        components: List[AnalysisComponent], 
        direction: Direction
    ) -> List[str]:
        """Generate human-readable reasoning"""
        reasons = []
        
        # Count agreeing components
        agreeing = [c for c in components if c.direction == direction]
        
        if direction == Direction.LONG:
            reasons.append(f"📈 {len(agreeing)}/{len(components)} analyzers suggest LONG")
        elif direction == Direction.SHORT:
            reasons.append(f"📉 {len(agreeing)}/{len(components)} analyzers suggest SHORT")
        else:
            reasons.append("⚖️ Mixed signals - NEUTRAL stance")
        
        # Add component-specific reasoning
        for comp in components:
            for reason in comp.reasoning[:2]:  # Max 2 per component
                reasons.append(f"• {reason}")
        
        return reasons

