"""
Feature Engine - Combines all 100 BTC-specific features
Bot 1: Core Brain
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging

from .technical import TechnicalAnalyzer, TechnicalFeatures
from .price_action import PriceActionAnalyzer, PriceActionFeatures
from .multi_timeframe import MTFAnalyzer, MTFFeatures
from .onchain import OnchainAnalyzer, OnchainFeatures
from .liquidation import LiquidationAnalyzer, LiquidationFeatures
from .funding import FundingAnalyzer, FundingFeatures
from .microstructure import MicrostructureAnalyzer, MicrostructureFeatures

logger = logging.getLogger(__name__)


@dataclass
class AllFeatures:
    """Container for all 100 features"""
    timestamp: datetime = None
    current_price: float = 0.0
    
    # Technical (1-20)
    technical: TechnicalFeatures = None
    
    # Price Action (21-35)
    price_action: PriceActionFeatures = None
    
    # Multi-Timeframe (36-50)
    mtf: MTFFeatures = None
    
    # On-chain (51-70)
    onchain: OnchainFeatures = None
    
    # Liquidation (71-80)
    liquidation: LiquidationFeatures = None
    
    # Funding (81-88)
    funding: FundingFeatures = None
    
    # Microstructure (89-100)
    microstructure: MicrostructureFeatures = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.technical is None:
            self.technical = TechnicalFeatures()
        if self.price_action is None:
            self.price_action = PriceActionFeatures()
        if self.mtf is None:
            self.mtf = MTFFeatures()
        if self.onchain is None:
            self.onchain = OnchainFeatures()
        if self.liquidation is None:
            self.liquidation = LiquidationFeatures()
        if self.funding is None:
            self.funding = FundingFeatures()
        if self.microstructure is None:
            self.microstructure = MicrostructureFeatures()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all features to dictionary"""
        result = {
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'current_price': self.current_price,
        }
        
        # Technical features
        tech = asdict(self.technical) if self.technical else {}
        for k, v in tech.items():
            result[k] = v
        
        # Price action features
        pa = asdict(self.price_action) if self.price_action else {}
        for k, v in pa.items():
            result[k] = v
        
        # MTF features
        mtf = asdict(self.mtf) if self.mtf else {}
        for k, v in mtf.items():
            result[k] = v
        
        # On-chain features
        oc = asdict(self.onchain) if self.onchain else {}
        for k, v in oc.items():
            result[k] = v
        
        # Liquidation features
        liq = asdict(self.liquidation) if self.liquidation else {}
        for k, v in liq.items():
            result[k] = v
        
        # Funding features
        fund = asdict(self.funding) if self.funding else {}
        for k, v in fund.items():
            result[k] = v
        
        # Microstructure features
        micro = asdict(self.microstructure) if self.microstructure else {}
        for k, v in micro.items():
            result[k] = v
        
        return result
    
    def to_feature_vector(self) -> List[float]:
        """Convert to numerical feature vector for ML"""
        features = []
        
        # Technical (20 features)
        tech = self.technical
        features.extend([
            tech.rsi_7, tech.rsi_14,
            tech.ema_9, tech.ema_21, tech.ema_50, tech.ema_200,
            tech.macd_line, tech.macd_signal, tech.macd_histogram,
            tech.bb_upper, tech.bb_lower, tech.bb_position,
            tech.atr_14, tech.atr_percentile,
            tech.adx, tech.plus_di, tech.minus_di,
            tech.stoch_k, tech.stoch_d,
            tech.vwap
        ])
        
        # Price Action (15 features)
        pa = self.price_action
        features.extend([
            pa.body_percent, pa.upper_wick_ratio, pa.lower_wick_ratio,
            pa.range_expansion, pa.breakout_strength,
            pa.swing_high_dist, pa.swing_low_dist,
            pa.hh_count, pa.ll_count, pa.hl_count, pa.lh_count,
            pa.trend_structure, pa.consolidation_bars,
            1.0 if pa.volatility_contraction else 0.0,
            pa.key_level_distance
        ])
        
        # MTF (15 features)
        mtf = self.mtf
        features.extend([
            mtf.tf_15m_trend, mtf.tf_15m_strength, mtf.tf_15m_rsi,
            mtf.tf_5m_trend, mtf.tf_5m_strength, mtf.tf_5m_rsi,
            mtf.tf_3m_momentum, mtf.tf_1m_momentum,
            mtf.mtf_alignment, mtf.mtf_confluence_score,
            mtf.htf_support_dist, mtf.htf_resistance_dist,
            1.0 if mtf.tf_divergence else 0.0,
            mtf.momentum_acceleration, mtf.trend_age_bars
        ])
        
        # On-chain (20 features)
        oc = self.onchain
        features.extend([
            oc.exchange_inflow, oc.exchange_outflow, oc.exchange_netflow,
            oc.flow_velocity, oc.flow_percentile,
            oc.large_tx_count, oc.whale_accumulation, oc.whale_distribution,
            oc.smart_money_flow, oc.whale_activity_score,
            oc.miner_reserve, oc.miner_outflow, oc.hash_rate_trend,
            oc.active_addresses, oc.transaction_count,
            oc.nvt_ratio, oc.sopr, oc.puell_multiple,
            oc.supply_on_exchange, oc.stablecoin_supply_ratio
        ])
        
        # Liquidation (10 features)
        liq = self.liquidation
        features.extend([
            liq.long_liq_density_1pct, liq.long_liq_density_2pct,
            liq.short_liq_density_1pct, liq.short_liq_density_2pct,
            liq.distance_to_long_liq, liq.distance_to_short_liq,
            liq.liq_imbalance, liq.recent_liq_volume_1h,
            liq.recent_liq_volume_24h, liq.liq_cascade_risk
        ])
        
        # Funding (8 features)
        fund = self.funding
        features.extend([
            fund.funding_current, fund.funding_predicted,
            fund.funding_trend_8h, fund.funding_trend_24h,
            1.0 if fund.funding_extreme else 0.0,
            fund.funding_vs_price_div, fund.time_to_funding,
            fund.funding_percentile
        ])
        
        # Microstructure (12 features)
        micro = self.microstructure
        features.extend([
            micro.cvd, micro.cvd_trend,
            micro.orderbook_imbalance, micro.orderbook_imbalance_10,
            micro.large_order_flow, micro.tape_speed,
            micro.aggressor_ratio, micro.spread_current,
            micro.spread_percentile, micro.depth_ratio,
            micro.vwap_distance, micro.poc_distance
        ])
        
        return features


class FeatureEngine:
    """Main feature engine combining all analyzers"""
    
    def __init__(
        self,
        glassnode_api_key: str = "",
        coinglass_api_key: str = "",
        use_mock: bool = False
    ):
        self.use_mock = use_mock
        
        # Initialize analyzers
        self.technical = TechnicalAnalyzer()
        self.price_action = PriceActionAnalyzer()
        self.mtf = MTFAnalyzer()
        self.onchain = OnchainAnalyzer(glassnode_api_key, coinglass_api_key)
        self.liquidation = LiquidationAnalyzer(coinglass_api_key)
        self.funding = FundingAnalyzer()
        self.microstructure = MicrostructureAnalyzer()
        
        self.last_features: Optional[AllFeatures] = None
    
    async def close(self):
        """Close async resources"""
        await self.onchain.close()
        await self.liquidation.close()
    
    async def calculate(self, market_data) -> AllFeatures:
        """
        Calculate all 100 features from market data.
        
        Args:
            market_data: MarketData object from BinanceClient
        
        Returns:
            AllFeatures object with all 100 features
        """
        features = AllFeatures()
        features.timestamp = datetime.utcnow()
        features.current_price = market_data.last_price
        
        try:
            # Get candles
            candles_1m = list(market_data.candles.get('1m', []))
            candles_3m = list(market_data.candles.get('3m', []))
            candles_5m = list(market_data.candles.get('5m', []))
            candles_15m = list(market_data.candles.get('15m', []))
            
            # Technical features (use 5m as primary)
            if candles_5m:
                features.technical = self.technical.calculate(candles_5m)
            
            # Price action features
            if candles_5m:
                features.price_action = self.price_action.calculate(candles_5m)
            
            # MTF features
            candles_dict = {
                '1m': candles_1m,
                '3m': candles_3m,
                '5m': candles_5m,
                '15m': candles_15m
            }
            features.mtf = self.mtf.calculate(candles_dict)
            
            # On-chain features
            if self.use_mock:
                features.onchain = self.onchain.get_mock_features()
            else:
                features.onchain = await self.onchain.calculate()
            
            # Liquidation features
            if self.use_mock:
                features.liquidation = self.liquidation.get_mock_features(features.current_price)
            else:
                features.liquidation = await self.liquidation.calculate(features.current_price)
            
            # Funding features
            if market_data.funding:
                features.funding = self.funding.calculate(
                    current_funding=market_data.funding.funding_rate,
                    next_funding_time=market_data.funding.next_funding_time,
                    current_price=features.current_price
                )
            elif self.use_mock:
                features.funding = self.funding.get_mock_features(features.current_price)
            
            # Microstructure features
            trades = list(market_data.trades)
            vwap = features.technical.vwap if features.technical else 0
            
            if self.use_mock:
                features.microstructure = self.microstructure.get_mock_features(features.current_price)
            else:
                features.microstructure = self.microstructure.calculate(
                    trades=trades,
                    orderbook=market_data.orderbook,
                    current_price=features.current_price,
                    vwap=vwap
                )
            
            self.last_features = features
            logger.debug(f"Calculated features at {features.timestamp}")
            
        except Exception as e:
            logger.error(f"Error calculating features: {e}")
            raise
        
        return features
    
    def get_last_features(self) -> Optional[AllFeatures]:
        """Get last calculated features"""
        return self.last_features

