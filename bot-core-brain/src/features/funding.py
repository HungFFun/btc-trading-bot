"""
Funding Rate Analysis Module
Features 81-88: Funding Rate Features
"""
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class FundingFeatures:
    """Funding rate features (81-88)"""
    funding_current: float = 0.0
    funding_predicted: float = 0.0
    funding_trend_8h: float = 0.0
    funding_trend_24h: float = 0.0
    funding_extreme: bool = False  # > 0.1% or < -0.1%
    funding_vs_price_div: float = 0.0  # Divergence with price
    time_to_funding: int = 0  # Minutes to next funding
    funding_percentile: float = 50.0  # vs 30 days


class FundingAnalyzer:
    """Analyze funding rate data"""
    
    def __init__(self):
        self.funding_history: List[float] = []
        self.price_at_funding: List[float] = []
    
    def calculate(
        self, 
        current_funding: float,
        next_funding_time: datetime,
        current_price: float,
        funding_history_8h: List[float] = None,
        funding_history_24h: List[float] = None
    ) -> FundingFeatures:
        """Calculate funding rate features"""
        features = FundingFeatures()
        
        # Current funding
        features.funding_current = current_funding
        
        # Track history
        self.funding_history.append(current_funding)
        self.price_at_funding.append(current_price)
        
        # Keep 30 days of 8-hour funding (3 per day = 90 entries)
        if len(self.funding_history) > 90:
            self.funding_history = self.funding_history[-90:]
            self.price_at_funding = self.price_at_funding[-90:]
        
        # Predicted funding (simple: use current if no other info)
        features.funding_predicted = current_funding
        
        # Funding trends
        if funding_history_8h and len(funding_history_8h) >= 2:
            features.funding_trend_8h = funding_history_8h[-1] - funding_history_8h[0]
        
        if funding_history_24h and len(funding_history_24h) >= 2:
            features.funding_trend_24h = funding_history_24h[-1] - funding_history_24h[0]
        
        # Funding extreme (>0.1% or <-0.1%)
        features.funding_extreme = abs(current_funding) > 0.001
        
        # Time to next funding
        now = datetime.utcnow()
        if next_funding_time > now:
            features.time_to_funding = int((next_funding_time - now).total_seconds() / 60)
        else:
            # Calculate next funding time (every 8 hours: 00:00, 08:00, 16:00 UTC)
            hours_until = 8 - (now.hour % 8)
            if hours_until == 8:
                hours_until = 0
            features.time_to_funding = hours_until * 60 - now.minute
        
        # Funding percentile
        if len(self.funding_history) > 1:
            count_below = sum(1 for f in self.funding_history if f < current_funding)
            features.funding_percentile = (count_below / len(self.funding_history)) * 100
        
        # Funding vs Price divergence
        features.funding_vs_price_div = self._calculate_divergence(
            current_funding, 
            current_price
        )
        
        return features
    
    def _calculate_divergence(self, current_funding: float, current_price: float) -> float:
        """
        Calculate divergence between funding rate and price movement.
        Positive = funding bullish but price falling (or vice versa)
        """
        if len(self.funding_history) < 3 or len(self.price_at_funding) < 3:
            return 0.0
        
        # Get recent history
        recent_funding = self.funding_history[-3:]
        recent_prices = self.price_at_funding[-3:]
        
        # Funding trend direction
        funding_change = recent_funding[-1] - recent_funding[0]
        funding_bullish = funding_change > 0
        
        # Price trend direction
        price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        price_bullish = price_change > 0
        
        # Divergence if opposite directions
        if funding_bullish != price_bullish:
            divergence = abs(funding_change * 1000) + abs(price_change * 100)
            return divergence if funding_bullish else -divergence
        
        return 0.0
    
    def get_mock_features(self, current_price: float) -> FundingFeatures:
        """Get mock features for testing"""
        import random
        
        features = FundingFeatures()
        
        features.funding_current = random.uniform(-0.001, 0.001)
        features.funding_predicted = features.funding_current + random.uniform(-0.0001, 0.0001)
        features.funding_trend_8h = random.uniform(-0.0003, 0.0003)
        features.funding_trend_24h = random.uniform(-0.0005, 0.0005)
        features.funding_extreme = abs(features.funding_current) > 0.001
        features.time_to_funding = random.randint(0, 480)
        features.funding_percentile = random.uniform(30, 70)
        features.funding_vs_price_div = random.uniform(-0.5, 0.5)
        
        return features

