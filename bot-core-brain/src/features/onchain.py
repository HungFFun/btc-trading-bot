"""
On-Chain Data Analysis Module
Features 51-70: On-Chain Features
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, field
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class OnchainFeatures:
    """On-chain features (51-70)"""
    # Exchange flows
    exchange_inflow: float = 0.0
    exchange_outflow: float = 0.0
    exchange_netflow: float = 0.0
    flow_velocity: float = 0.0
    flow_percentile: float = 50.0
    
    # Whale activity
    large_tx_count: int = 0
    whale_accumulation: float = 0.0
    whale_distribution: float = 0.0
    smart_money_flow: float = 0.0
    whale_activity_score: float = 50.0
    
    # Miner activity
    miner_reserve: float = 0.0
    miner_outflow: float = 0.0
    hash_rate_trend: float = 0.0
    
    # Network activity
    active_addresses: int = 0
    transaction_count: int = 0
    nvt_ratio: float = 0.0
    sopr: float = 1.0  # Spent Output Profit Ratio
    puell_multiple: float = 1.0
    
    # Supply metrics
    supply_on_exchange: float = 0.0
    stablecoin_supply_ratio: float = 0.0


@dataclass
class OnchainDataCache:
    """Cache for on-chain data"""
    data: Dict = field(default_factory=dict)
    last_update: Optional[datetime] = None
    update_interval: int = 300  # 5 minutes
    
    def is_stale(self) -> bool:
        if self.last_update is None:
            return True
        return (datetime.utcnow() - self.last_update).total_seconds() > self.update_interval


class OnchainClient:
    """Client for fetching on-chain data"""
    
    def __init__(self, glassnode_api_key: str = "", coinglass_api_key: str = ""):
        self.glassnode_api_key = glassnode_api_key
        self.coinglass_api_key = coinglass_api_key
        self.cache = OnchainDataCache()
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Historical data for percentile calculations
        self.flow_history: List[float] = []
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def fetch_glassnode_metric(self, metric: str, asset: str = "BTC") -> Optional[float]:
        """Fetch a metric from Glassnode API"""
        if not self.glassnode_api_key:
            return None
        
        session = await self._get_session()
        url = f"https://api.glassnode.com/v1/metrics/{metric}"
        
        params = {
            "a": asset,
            "api_key": self.glassnode_api_key,
            "i": "24h"  # Daily interval
        }
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        return float(data[-1].get("v", 0))
                return None
        except Exception as e:
            logger.error(f"Glassnode API error: {e}")
            return None
    
    async def fetch_coinglass_data(self, endpoint: str) -> Optional[Dict]:
        """Fetch data from Coinglass API"""
        if not self.coinglass_api_key:
            return None
        
        session = await self._get_session()
        url = f"https://open-api.coinglass.com/public/v2/{endpoint}"
        
        headers = {
            "coinglassSecret": self.coinglass_api_key
        }
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Coinglass API error: {e}")
            return None
    
    async def update_cache(self):
        """Update on-chain data cache"""
        if not self.cache.is_stale():
            return
        
        # Exchange flows
        inflow = await self.fetch_glassnode_metric("transactions/transfers_to_exchanges_count")
        outflow = await self.fetch_glassnode_metric("transactions/transfers_from_exchanges_count")
        
        if inflow is not None:
            self.cache.data['exchange_inflow'] = inflow
        if outflow is not None:
            self.cache.data['exchange_outflow'] = outflow
        
        # Active addresses
        active = await self.fetch_glassnode_metric("addresses/active_count")
        if active is not None:
            self.cache.data['active_addresses'] = int(active)
        
        # Transaction count
        tx_count = await self.fetch_glassnode_metric("transactions/count")
        if tx_count is not None:
            self.cache.data['transaction_count'] = int(tx_count)
        
        # SOPR
        sopr = await self.fetch_glassnode_metric("indicators/sopr")
        if sopr is not None:
            self.cache.data['sopr'] = sopr
        
        # Miner data
        miner_reserve = await self.fetch_glassnode_metric("mining/balance")
        if miner_reserve is not None:
            self.cache.data['miner_reserve'] = miner_reserve
        
        # Supply on exchanges
        supply_exchanges = await self.fetch_glassnode_metric("distribution/balance_exchanges")
        if supply_exchanges is not None:
            self.cache.data['supply_on_exchange'] = supply_exchanges
        
        self.cache.last_update = datetime.utcnow()
        logger.debug("On-chain cache updated")


class OnchainAnalyzer:
    """Analyze on-chain data and generate features"""
    
    def __init__(self, glassnode_api_key: str = "", coinglass_api_key: str = ""):
        self.client = OnchainClient(glassnode_api_key, coinglass_api_key)
        self.flow_history: List[float] = []
    
    async def close(self):
        await self.client.close()
    
    def _calculate_flow_percentile(self, current_flow: float) -> float:
        """Calculate current flow percentile vs history"""
        if not self.flow_history:
            return 50.0
        
        count_below = sum(1 for f in self.flow_history if f < current_flow)
        return (count_below / len(self.flow_history)) * 100
    
    def _calculate_whale_score(self, features: OnchainFeatures) -> float:
        """Calculate composite whale activity score (0-100)"""
        score = 50.0  # Neutral baseline
        
        # Adjust based on large transactions
        if features.large_tx_count > 100:
            score += 10
        elif features.large_tx_count < 20:
            score -= 10
        
        # Adjust based on accumulation/distribution
        net_whale = features.whale_accumulation - features.whale_distribution
        if net_whale > 0:
            score += min(20, net_whale * 2)
        else:
            score -= min(20, abs(net_whale) * 2)
        
        return max(0, min(100, score))
    
    async def calculate(self) -> OnchainFeatures:
        """Calculate all on-chain features"""
        features = OnchainFeatures()
        
        # Update cache
        await self.client.update_cache()
        cache = self.client.cache.data
        
        # Exchange flows
        features.exchange_inflow = cache.get('exchange_inflow', 0)
        features.exchange_outflow = cache.get('exchange_outflow', 0)
        features.exchange_netflow = features.exchange_inflow - features.exchange_outflow
        
        # Track flow history for percentile
        self.flow_history.append(features.exchange_netflow)
        if len(self.flow_history) > 30 * 24:  # ~30 days of hourly data
            self.flow_history = self.flow_history[-30*24:]
        
        features.flow_percentile = self._calculate_flow_percentile(features.exchange_netflow)
        
        # Flow velocity (change rate)
        if len(self.flow_history) >= 2:
            features.flow_velocity = features.exchange_netflow - self.flow_history[-2]
        
        # Network activity
        features.active_addresses = cache.get('active_addresses', 0)
        features.transaction_count = cache.get('transaction_count', 0)
        features.sopr = cache.get('sopr', 1.0)
        
        # Miner activity
        features.miner_reserve = cache.get('miner_reserve', 0)
        
        # Supply metrics
        features.supply_on_exchange = cache.get('supply_on_exchange', 0)
        
        # Calculate whale activity score
        features.whale_activity_score = self._calculate_whale_score(features)
        
        return features
    
    def get_mock_features(self) -> OnchainFeatures:
        """Get mock features for testing without API keys"""
        import random
        
        features = OnchainFeatures()
        
        # Mock values (realistic ranges)
        features.exchange_inflow = random.uniform(5000, 15000)
        features.exchange_outflow = random.uniform(4000, 14000)
        features.exchange_netflow = features.exchange_inflow - features.exchange_outflow
        features.flow_velocity = random.uniform(-500, 500)
        features.flow_percentile = random.uniform(30, 70)
        
        features.large_tx_count = random.randint(50, 150)
        features.whale_accumulation = random.uniform(0, 100)
        features.whale_distribution = random.uniform(0, 100)
        features.whale_activity_score = random.uniform(40, 60)
        
        features.active_addresses = random.randint(800000, 1200000)
        features.transaction_count = random.randint(200000, 400000)
        features.sopr = random.uniform(0.98, 1.02)
        
        return features

