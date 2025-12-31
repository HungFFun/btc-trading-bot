"""
Liquidation Data Analysis Module
Features 71-80: Liquidation Features
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class LiquidationFeatures:
    """Liquidation features (71-80)"""
    long_liq_density_1pct: float = 0.0  # Long liquidations within 1%
    long_liq_density_2pct: float = 0.0  # Long liquidations within 2%
    short_liq_density_1pct: float = 0.0  # Short liquidations within 1%
    short_liq_density_2pct: float = 0.0  # Short liquidations within 2%
    distance_to_long_liq: float = 0.0  # Distance to nearest long liq zone
    distance_to_short_liq: float = 0.0  # Distance to nearest short liq zone
    liq_imbalance: float = 0.0  # Long vs Short liq ratio
    recent_liq_volume_1h: float = 0.0  # Liquidation volume in last hour
    recent_liq_volume_24h: float = 0.0  # Liquidation volume in last 24h
    liq_cascade_risk: float = 0.0  # Risk of cascade liquidation (0-1)


@dataclass
class LiquidationLevel:
    """Represents a liquidation level"""
    price: float
    volume: float
    side: str  # 'long' or 'short'


class LiquidationClient:
    """Client for fetching liquidation data"""
    
    def __init__(self, coinglass_api_key: str = ""):
        self.coinglass_api_key = coinglass_api_key
        self._session: Optional[aiohttp.ClientSession] = None
        self.liq_levels: List[LiquidationLevel] = []
        self.recent_liquidations: List[Dict] = []
        self.last_update: Optional[datetime] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def fetch_liquidation_levels(self) -> List[LiquidationLevel]:
        """Fetch liquidation heatmap from Coinglass"""
        if not self.coinglass_api_key:
            return []
        
        session = await self._get_session()
        url = "https://open-api.coinglass.com/public/v2/liquidation_heatmap"
        
        headers = {"coinglassSecret": self.coinglass_api_key}
        params = {"symbol": "BTC"}
        
        try:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    levels = []
                    
                    if data.get("success") and data.get("data"):
                        for item in data["data"]:
                            levels.append(LiquidationLevel(
                                price=float(item.get("price", 0)),
                                volume=float(item.get("volume", 0)),
                                side=item.get("side", "long")
                            ))
                    
                    return levels
                return []
        except Exception as e:
            logger.error(f"Error fetching liquidation levels: {e}")
            return []
    
    async def fetch_recent_liquidations(self, time_type: str = "h1") -> float:
        """Fetch recent liquidation volume"""
        if not self.coinglass_api_key:
            return 0.0
        
        session = await self._get_session()
        url = "https://open-api.coinglass.com/public/v2/liquidation_info"
        
        headers = {"coinglassSecret": self.coinglass_api_key}
        params = {"symbol": "BTC", "time_type": time_type}
        
        try:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("data"):
                        return float(data["data"].get("volUsd", 0))
                return 0.0
        except Exception as e:
            logger.error(f"Error fetching recent liquidations: {e}")
            return 0.0
    
    async def update(self):
        """Update liquidation data"""
        self.liq_levels = await self.fetch_liquidation_levels()
        self.last_update = datetime.utcnow()


class LiquidationAnalyzer:
    """Analyze liquidation data and generate features"""
    
    def __init__(self, coinglass_api_key: str = ""):
        self.client = LiquidationClient(coinglass_api_key)
    
    async def close(self):
        await self.client.close()
    
    def _calculate_density(
        self, 
        levels: List[LiquidationLevel], 
        current_price: float, 
        side: str, 
        pct_range: float
    ) -> float:
        """Calculate liquidation density within a percentage range"""
        if not levels or current_price == 0:
            return 0.0
        
        if side == "long":
            # Long liquidations are below current price
            price_threshold = current_price * (1 - pct_range)
            relevant = [l for l in levels if l.side == "long" and l.price >= price_threshold and l.price < current_price]
        else:
            # Short liquidations are above current price
            price_threshold = current_price * (1 + pct_range)
            relevant = [l for l in levels if l.side == "short" and l.price <= price_threshold and l.price > current_price]
        
        total_volume = sum(l.volume for l in relevant)
        return total_volume
    
    def _find_nearest_liq_zone(
        self, 
        levels: List[LiquidationLevel], 
        current_price: float, 
        side: str,
        min_volume: float = 1000000  # $1M minimum
    ) -> float:
        """Find distance to nearest significant liquidation zone"""
        if not levels or current_price == 0:
            return 0.0
        
        if side == "long":
            # Find nearest long liq zone (below price)
            relevant = [l for l in levels if l.side == "long" and l.volume >= min_volume and l.price < current_price]
            if relevant:
                nearest = max(relevant, key=lambda x: x.price)
                return (current_price - nearest.price) / current_price
        else:
            # Find nearest short liq zone (above price)
            relevant = [l for l in levels if l.side == "short" and l.volume >= min_volume and l.price > current_price]
            if relevant:
                nearest = min(relevant, key=lambda x: x.price)
                return (nearest.price - current_price) / current_price
        
        return 0.1  # Default 10% if no significant zone found
    
    def _calculate_imbalance(self, levels: List[LiquidationLevel]) -> float:
        """Calculate imbalance between long and short liquidations"""
        if not levels:
            return 0.0
        
        long_volume = sum(l.volume for l in levels if l.side == "long")
        short_volume = sum(l.volume for l in levels if l.side == "short")
        
        total = long_volume + short_volume
        if total == 0:
            return 0.0
        
        # Positive = more longs, Negative = more shorts
        return (long_volume - short_volume) / total
    
    def _calculate_cascade_risk(
        self, 
        features: LiquidationFeatures, 
        current_price: float
    ) -> float:
        """Calculate risk of cascade liquidation"""
        risk = 0.0
        
        # High density near current price increases risk
        if features.long_liq_density_1pct > 10000000:  # $10M
            risk += 0.2
        if features.short_liq_density_1pct > 10000000:
            risk += 0.2
        
        # Low distance to liq zone increases risk
        if features.distance_to_long_liq < 0.01:  # Less than 1%
            risk += 0.3
        elif features.distance_to_long_liq < 0.02:
            risk += 0.15
        
        if features.distance_to_short_liq < 0.01:
            risk += 0.3
        elif features.distance_to_short_liq < 0.02:
            risk += 0.15
        
        return min(1.0, risk)
    
    async def calculate(self, current_price: float) -> LiquidationFeatures:
        """Calculate all liquidation features"""
        features = LiquidationFeatures()
        
        # Update liquidation data
        await self.client.update()
        levels = self.client.liq_levels
        
        if not levels:
            return features
        
        # Calculate densities
        features.long_liq_density_1pct = self._calculate_density(levels, current_price, "long", 0.01)
        features.long_liq_density_2pct = self._calculate_density(levels, current_price, "long", 0.02)
        features.short_liq_density_1pct = self._calculate_density(levels, current_price, "short", 0.01)
        features.short_liq_density_2pct = self._calculate_density(levels, current_price, "short", 0.02)
        
        # Distance to liquidation zones
        features.distance_to_long_liq = self._find_nearest_liq_zone(levels, current_price, "long")
        features.distance_to_short_liq = self._find_nearest_liq_zone(levels, current_price, "short")
        
        # Imbalance
        features.liq_imbalance = self._calculate_imbalance(levels)
        
        # Recent liquidation volumes
        features.recent_liq_volume_1h = await self.client.fetch_recent_liquidations("h1")
        features.recent_liq_volume_24h = await self.client.fetch_recent_liquidations("h24")
        
        # Cascade risk
        features.liq_cascade_risk = self._calculate_cascade_risk(features, current_price)
        
        return features
    
    def get_mock_features(self, current_price: float) -> LiquidationFeatures:
        """Get mock features for testing"""
        import random
        
        features = LiquidationFeatures()
        
        features.long_liq_density_1pct = random.uniform(1000000, 20000000)
        features.long_liq_density_2pct = features.long_liq_density_1pct * random.uniform(1.5, 3)
        features.short_liq_density_1pct = random.uniform(1000000, 20000000)
        features.short_liq_density_2pct = features.short_liq_density_1pct * random.uniform(1.5, 3)
        
        features.distance_to_long_liq = random.uniform(0.005, 0.03)
        features.distance_to_short_liq = random.uniform(0.005, 0.03)
        
        total = features.long_liq_density_2pct + features.short_liq_density_2pct
        if total > 0:
            features.liq_imbalance = (features.long_liq_density_2pct - features.short_liq_density_2pct) / total
        
        features.recent_liq_volume_1h = random.uniform(5000000, 50000000)
        features.recent_liq_volume_24h = features.recent_liq_volume_1h * random.uniform(10, 30)
        
        features.liq_cascade_risk = random.uniform(0.1, 0.4)
        
        return features

