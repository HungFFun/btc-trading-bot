"""
Signal Generator - Creates trading signals based on strategies
"""
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import uuid
import logging

from ..features.feature_engine import AllFeatures
from ..features.regime import RegimeResult, RegimeType

logger = logging.getLogger(__name__)


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class StrategyType(str, Enum):
    TREND_MOMENTUM = "TREND_MOMENTUM"  # 40% of trades
    LIQUIDATION_HUNT = "LIQUIDATION_HUNT"  # 25% of trades
    FUNDING_FADE = "FUNDING_FADE"  # 15% of trades
    RANGE_SCALPING = "RANGE_SCALPING"  # 20% of trades


@dataclass
class Signal:
    """Trading signal"""
    signal_id: str
    created_at: datetime
    
    # Signal details
    direction: SignalDirection
    strategy: StrategyType
    entry_price: float
    stop_loss: float
    take_profit: float
    
    # Fixed parameters (v5.0)
    position_margin: float = 150.0  # $150
    leverage: int = 20
    
    # Quality metrics
    confidence: float = 0.0
    setup_quality: int = 0
    regime: str = ""
    reasoning: str = ""
    
    # Gate scores
    gate_scores: Dict[str, float] = None
    
    def __post_init__(self):
        if self.gate_scores is None:
            self.gate_scores = {}
    
    @property
    def notional_value(self) -> float:
        return self.position_margin * self.leverage
    
    @property
    def risk_amount(self) -> float:
        """Risk in USD (SL distance × position)"""
        sl_distance = abs(self.entry_price - self.stop_loss) / self.entry_price
        return self.notional_value * sl_distance
    
    @property
    def reward_amount(self) -> float:
        """Reward in USD (TP distance × position)"""
        tp_distance = abs(self.take_profit - self.entry_price) / self.entry_price
        return self.notional_value * tp_distance
    
    @property
    def risk_reward_ratio(self) -> float:
        if self.risk_amount == 0:
            return 0
        return self.reward_amount / self.risk_amount
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'signal_id': self.signal_id,
            'created_at': self.created_at.isoformat(),
            'direction': self.direction.value,
            'strategy': self.strategy.value,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_margin': self.position_margin,
            'leverage': self.leverage,
            'confidence': self.confidence,
            'setup_quality': self.setup_quality,
            'regime': self.regime,
            'reasoning': self.reasoning,
            'risk_amount': self.risk_amount,
            'reward_amount': self.reward_amount,
            'risk_reward_ratio': self.risk_reward_ratio
        }


class SignalGenerator:
    """
    Generate trading signals based on strategies.
    
    Fixed parameters (v5.0):
    - TP: 0.5%
    - SL: 0.25%
    - R:R: 2:1
    """
    
    def __init__(
        self,
        tp_percent: float = 0.005,  # 0.5%
        sl_percent: float = 0.0025,  # 0.25%
        position_margin: float = 150.0,
        leverage: int = 20
    ):
        self.tp_percent = tp_percent
        self.sl_percent = sl_percent
        self.position_margin = position_margin
        self.leverage = leverage
    
    def generate(
        self, 
        features: AllFeatures, 
        regime: RegimeResult
    ) -> Optional[Signal]:
        """
        Generate a potential signal based on current conditions.
        
        Args:
            features: Current market features
            regime: Current regime detection result
        
        Returns:
            Signal if conditions met, None otherwise
        """
        if not regime.is_tradeable:
            logger.debug(f"Regime not tradeable: {regime.regime_type.value}")
            return None
        
        # Select strategy based on conditions
        strategy, direction = self._select_strategy(features, regime)
        
        if strategy is None or direction is None:
            logger.debug("No valid strategy/direction found")
            return None
        
        # FINAL VALIDATION: Direction MUST align with regime (CRITICAL!)
        if not self._validate_direction_vs_regime(direction, regime):
            logger.warning(
                f"REJECTED: {direction.value} not allowed in {regime.regime_type.value} "
                f"(exhaustion: {regime.exhaustion_risk:.2f})"
            )
            return None
        
        # Calculate setup quality
        setup_quality = self._calculate_setup_quality(features, strategy, direction)
        
        if setup_quality < 70:  # Minimum threshold
            logger.debug(f"Setup quality too low: {setup_quality}/100")
            return None
        
        # Calculate entry, SL, TP
        entry_price = features.current_price
        stop_loss, take_profit = self._calculate_prices(entry_price, direction)
        
        # Generate signal
        signal = Signal(
            signal_id=self._generate_id(),
            created_at=datetime.utcnow(),
            direction=direction,
            strategy=strategy,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_margin=self.position_margin,
            leverage=self.leverage,
            confidence=regime.confidence,
            setup_quality=setup_quality,
            regime=regime.regime_type.value,
            reasoning=self._generate_reasoning(features, regime, strategy, direction)
        )
        
        logger.info(f"Generated signal: {signal.signal_id} - {direction.value} {strategy.value} in {regime.regime_type.value}")
        return signal
    
    def _validate_direction_vs_regime(
        self, 
        direction: SignalDirection, 
        regime: RegimeResult
    ) -> bool:
        """
        FINAL VALIDATION: Ensure direction aligns with regime.
        
        Rules:
        - TRENDING_UP → Only LONG (exception: exhaustion > 0.7)
        - TRENDING_DOWN → Only SHORT (exception: exhaustion > 0.7)
        - RANGING, HIGH_VOLATILITY → Both allowed
        """
        # TRENDING_UP: Chỉ được LONG
        if regime.regime_type == RegimeType.TRENDING_UP and direction == SignalDirection.SHORT:
            if regime.exhaustion_risk > 0.7:
                logger.info(f"Counter-trend SHORT allowed due to high exhaustion: {regime.exhaustion_risk:.2f}")
                return True
            return False
        
        # TRENDING_DOWN: Chỉ được SHORT
        if regime.regime_type == RegimeType.TRENDING_DOWN and direction == SignalDirection.LONG:
            if regime.exhaustion_risk > 0.7:
                logger.info(f"Counter-trend LONG allowed due to high exhaustion: {regime.exhaustion_risk:.2f}")
                return True
            return False
        
        return True
    
    def _select_strategy(
        self, 
        features: AllFeatures, 
        regime: RegimeResult
    ) -> tuple:
        """
        Select appropriate strategy and direction.
        
        IMPORTANT: All strategies MUST validate direction against regime!
        - TRENDING_UP → Only LONG allowed
        - TRENDING_DOWN → Only SHORT allowed
        - RANGING, HIGH_VOLATILITY → Both allowed
        """
        
        # Check for special conditions first
        
        # Funding Fade (extreme funding)
        if features.funding and features.funding.funding_extreme:
            direction = self._validate_funding_fade(features, regime)
            if direction:
                logger.info(f"Strategy: FUNDING_FADE | Direction: {direction.value}")
                return StrategyType.FUNDING_FADE, direction
        
        # Liquidation Hunt (liq zone nearby)
        liq = features.liquidation
        if liq.distance_to_long_liq < 0.02 or liq.distance_to_short_liq < 0.02:
            direction = self._validate_liquidation_hunt(features, regime)
            if direction:
                logger.info(f"Strategy: LIQUIDATION_HUNT | Direction: {direction.value}")
                return StrategyType.LIQUIDATION_HUNT, direction
        
        # Select based on regime
        if regime.regime_type == RegimeType.TRENDING_UP:
            setup = self._validate_trend_momentum(features, SignalDirection.LONG)
            if setup:
                logger.info(f"Strategy: TREND_MOMENTUM | Direction: LONG (TRENDING_UP)")
                return StrategyType.TREND_MOMENTUM, SignalDirection.LONG
        
        elif regime.regime_type == RegimeType.TRENDING_DOWN:
            setup = self._validate_trend_momentum(features, SignalDirection.SHORT)
            if setup:
                logger.info(f"Strategy: TREND_MOMENTUM | Direction: SHORT (TRENDING_DOWN)")
                return StrategyType.TREND_MOMENTUM, SignalDirection.SHORT
        
        elif regime.regime_type == RegimeType.RANGING:
            direction = self._validate_range_scalping(features)
            if direction:
                logger.info(f"Strategy: RANGE_SCALPING | Direction: {direction.value}")
                return StrategyType.RANGE_SCALPING, direction
        
        elif regime.regime_type == RegimeType.HIGH_VOLATILITY:
            direction = self._validate_liquidation_hunt(features, regime)
            if direction:
                logger.info(f"Strategy: LIQUIDATION_HUNT | Direction: {direction.value} (HIGH_VOLATILITY)")
                return StrategyType.LIQUIDATION_HUNT, direction
        
        return None, None
    
    def _validate_trend_momentum(
        self, 
        features: AllFeatures, 
        direction: SignalDirection
    ) -> bool:
        """Validate Trend Momentum strategy conditions"""
        tech = features.technical
        mtf = features.mtf
        micro = features.microstructure
        onchain = features.onchain
        
        if direction == SignalDirection.LONG:
            # EMA alignment
            if not (tech.ema_9 > tech.ema_21 > tech.ema_50):
                return False
            
            # Pullback to EMA21 zone (±0.3%)
            ema21_distance = abs(features.current_price - tech.ema_21) / tech.ema_21
            if ema21_distance > 0.003:
                return False
            
            # RSI not extreme
            if tech.rsi_14 < 40 or tech.rsi_14 > 60:
                return False
            
            # CVD positive
            if micro.cvd_trend < 0:
                return False
            
            # Funding not too positive
            if features.funding and features.funding.funding_current > 0.0005:
                return False
            
            return True
        
        else:  # SHORT
            # EMA alignment
            if not (tech.ema_9 < tech.ema_21 < tech.ema_50):
                return False
            
            # Pullback to EMA21
            ema21_distance = abs(features.current_price - tech.ema_21) / tech.ema_21
            if ema21_distance > 0.003:
                return False
            
            # RSI
            if tech.rsi_14 < 40 or tech.rsi_14 > 60:
                return False
            
            # CVD negative
            if micro.cvd_trend > 0:
                return False
            
            return True
    
    def _validate_liquidation_hunt(
        self, 
        features: AllFeatures, 
        regime: RegimeResult
    ) -> Optional[SignalDirection]:
        """
        Validate Liquidation Hunt strategy.
        
        CRITICAL: Direction MUST align with regime!
        - TRENDING_UP → Only hunt short liquidations (LONG)
        - TRENDING_DOWN → Only hunt long liquidations (SHORT)
        - RANGING/HIGH_VOLATILITY → Hunt both based on zone proximity
        """
        liq = features.liquidation
        micro = features.microstructure
        
        # Trong TRENDING_UP: Chỉ được LONG (hunt short liquidations)
        if regime.regime_type == RegimeType.TRENDING_UP:
            # Check short liq zone above (hunt shorts → go LONG)
            if liq.distance_to_short_liq < 0.02 and liq.short_liq_density_2pct > 5000000:
                if micro.orderbook_imbalance > 0.1 and micro.cvd_trend > 0:
                    logger.info(f"Liquidation Hunt: LONG in TRENDING_UP (short liq zone: {liq.distance_to_short_liq:.3f})")
                    return SignalDirection.LONG
            # Không được SHORT trong TRENDING_UP!
            return None
        
        # Trong TRENDING_DOWN: Chỉ được SHORT (hunt long liquidations)
        if regime.regime_type == RegimeType.TRENDING_DOWN:
            # Check long liq zone below (hunt longs → go SHORT)
            if liq.distance_to_long_liq < 0.02 and liq.long_liq_density_2pct > 5000000:
                if micro.orderbook_imbalance < -0.1 and micro.cvd_trend < 0:
                    logger.info(f"Liquidation Hunt: SHORT in TRENDING_DOWN (long liq zone: {liq.distance_to_long_liq:.3f})")
                    return SignalDirection.SHORT
            # Không được LONG trong TRENDING_DOWN!
            return None
        
        # Trong RANGING hoặc HIGH_VOLATILITY: Có thể hunt cả hai
        # Ưu tiên zone nào gần hơn VÀ có setup rõ ràng hơn
        
        # Large short liq zone above (hunt shorts → LONG)
        if liq.distance_to_short_liq < 0.02 and liq.short_liq_density_2pct > 5000000:
            if micro.orderbook_imbalance > 0.1 and micro.cvd_trend > 0:
                logger.info(f"Liquidation Hunt: LONG in {regime.regime_type.value} (short liq zone)")
                return SignalDirection.LONG
        
        # Large long liq zone below (hunt longs → SHORT)
        if liq.distance_to_long_liq < 0.02 and liq.long_liq_density_2pct > 5000000:
            if micro.orderbook_imbalance < -0.1 and micro.cvd_trend < 0:
                logger.info(f"Liquidation Hunt: SHORT in {regime.regime_type.value} (long liq zone)")
                return SignalDirection.SHORT
        
        return None
    
    def _validate_funding_fade(
        self, 
        features: AllFeatures, 
        regime: RegimeResult
    ) -> Optional[SignalDirection]:
        """
        Validate Funding Fade strategy.
        
        CRITICAL: Direction MUST align with regime!
        - TRENDING_UP → Only LONG (fade negative funding)
        - TRENDING_DOWN → Only SHORT (fade positive funding)
        - RANGING/HIGH_VOLATILITY → Both allowed based on funding extreme
        
        Exception: Allow counter-trend if exhaustion_risk > 0.7
        """
        funding = features.funding
        tech = features.technical
        
        if not funding:
            return None
        
        # Check exhaustion for counter-trend exception
        allow_counter_trend = regime.exhaustion_risk > 0.7
        
        # Trong TRENDING_UP: Chỉ được LONG (fade negative funding)
        if regime.regime_type == RegimeType.TRENDING_UP:
            # Extreme negative funding → LONG (align với trend)
            if funding.funding_current < -0.001:
                if tech.rsi_14 < 50:  # Not overbought
                    logger.info(f"Funding Fade: LONG in TRENDING_UP (funding: {funding.funding_current:.4f})")
                    return SignalDirection.LONG
            # Extreme positive funding → SHORT (counter-trend)
            if funding.funding_current > 0.001 and allow_counter_trend:
                if tech.rsi_14 > 70:  # Overbought + exhaustion
                    logger.info(f"Funding Fade: SHORT in TRENDING_UP (counter-trend, exhaustion: {regime.exhaustion_risk:.2f})")
                    return SignalDirection.SHORT
            return None
        
        # Trong TRENDING_DOWN: Chỉ được SHORT (fade positive funding)
        if regime.regime_type == RegimeType.TRENDING_DOWN:
            # Extreme positive funding → SHORT (align với trend)
            if funding.funding_current > 0.001:
                if tech.rsi_14 > 50:  # Not oversold
                    logger.info(f"Funding Fade: SHORT in TRENDING_DOWN (funding: {funding.funding_current:.4f})")
                    return SignalDirection.SHORT
            # Extreme negative funding → LONG (counter-trend)
            if funding.funding_current < -0.001 and allow_counter_trend:
                if tech.rsi_14 < 30:  # Oversold + exhaustion
                    logger.info(f"Funding Fade: LONG in TRENDING_DOWN (counter-trend, exhaustion: {regime.exhaustion_risk:.2f})")
                    return SignalDirection.LONG
            return None
        
        # Trong RANGING hoặc HIGH_VOLATILITY: Cả hai direction OK
        # Extreme positive funding → SHORT
        if funding.funding_current > 0.001:
            if tech.rsi_14 > 60:  # RSI divergence
                logger.info(f"Funding Fade: SHORT in {regime.regime_type.value} (funding: {funding.funding_current:.4f})")
                return SignalDirection.SHORT
        
        # Extreme negative funding → LONG
        if funding.funding_current < -0.001:
            if tech.rsi_14 < 40:
                logger.info(f"Funding Fade: LONG in {regime.regime_type.value} (funding: {funding.funding_current:.4f})")
                return SignalDirection.LONG
        
        return None
    
    def _validate_range_scalping(self, features: AllFeatures) -> Optional[SignalDirection]:
        """Validate Range Scalping strategy"""
        tech = features.technical
        pa = features.price_action
        micro = features.microstructure
        
        # At support → LONG
        if tech.rsi_14 < 35 and pa.lower_wick_ratio > 0.5:
            if micro.cvd > 0:
                return SignalDirection.LONG
        
        # At resistance → SHORT
        if tech.rsi_14 > 65 and pa.upper_wick_ratio > 0.5:
            if micro.cvd < 0:
                return SignalDirection.SHORT
        
        return None
    
    def _calculate_setup_quality(
        self, 
        features: AllFeatures, 
        strategy: StrategyType,
        direction: SignalDirection
    ) -> int:
        """
        Calculate setup quality score (0-100).
        
        Components:
        - MTF Confluence: 20%
        - Volume/CVD: 20%
        - Key Levels: 15%
        - On-chain: 15%
        - Momentum: 15%
        - Microstructure: 15%
        """
        score = 0
        
        mtf = features.mtf
        tech = features.technical
        micro = features.microstructure
        pa = features.price_action
        onchain = features.onchain
        
        # MTF Confluence (20 points)
        mtf_score = mtf.mtf_confluence_score / 100 * 20
        score += mtf_score
        
        # Volume/CVD (20 points)
        if direction == SignalDirection.LONG:
            cvd_score = 10 if micro.cvd_trend > 0 else 0
            aggressor_score = 10 if micro.aggressor_ratio > 0.5 else 5
        else:
            cvd_score = 10 if micro.cvd_trend < 0 else 0
            aggressor_score = 10 if micro.aggressor_ratio < 0.5 else 5
        score += cvd_score + aggressor_score
        
        # Key Levels (15 points)
        level_score = 15 if pa.key_level_distance < 0.005 else 10 if pa.key_level_distance < 0.01 else 5
        score += level_score
        
        # On-chain (15 points)
        if onchain.whale_activity_score > 60:
            score += 15
        elif onchain.whale_activity_score > 40:
            score += 10
        else:
            score += 5
        
        # Momentum (15 points)
        if direction == SignalDirection.LONG:
            if tech.macd_histogram > 0 and mtf.tf_3m_momentum > 0:
                score += 15
            elif tech.macd_histogram > 0 or mtf.tf_3m_momentum > 0:
                score += 10
            else:
                score += 5
        else:
            if tech.macd_histogram < 0 and mtf.tf_3m_momentum < 0:
                score += 15
            elif tech.macd_histogram < 0 or mtf.tf_3m_momentum < 0:
                score += 10
            else:
                score += 5
        
        # Microstructure (15 points)
        if micro.orderbook_imbalance > 0.1 and direction == SignalDirection.LONG:
            score += 15
        elif micro.orderbook_imbalance < -0.1 and direction == SignalDirection.SHORT:
            score += 15
        elif abs(micro.orderbook_imbalance) < 0.1:
            score += 10
        else:
            score += 5
        
        return int(min(100, max(0, score)))
    
    def _calculate_prices(
        self, 
        entry: float, 
        direction: SignalDirection
    ) -> tuple:
        """Calculate SL and TP prices"""
        if direction == SignalDirection.LONG:
            stop_loss = entry * (1 - self.sl_percent)  # -0.25%
            take_profit = entry * (1 + self.tp_percent)  # +0.5%
        else:
            stop_loss = entry * (1 + self.sl_percent)  # +0.25%
            take_profit = entry * (1 - self.tp_percent)  # -0.5%
        
        return stop_loss, take_profit
    
    def _generate_id(self) -> str:
        """Generate unique signal ID"""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        unique = uuid.uuid4().hex[:6].upper()
        return f"SIG_{date_str}_{unique}"
    
    def _generate_reasoning(
        self,
        features: AllFeatures,
        regime: RegimeResult,
        strategy: StrategyType,
        direction: SignalDirection
    ) -> str:
        """Generate human-readable reasoning"""
        parts = [
            f"Regime: {regime.regime_type.value}",
            f"Strategy: {strategy.value}",
            f"Direction: {direction.value}",
            f"RSI: {features.technical.rsi_14:.1f}",
            f"ADX: {features.technical.adx:.1f}",
            f"MTF: {features.mtf.mtf_alignment}/3 aligned"
        ]
        
        if features.funding:
            parts.append(f"Funding: {features.funding.funding_current*100:.3f}%")
        
        return " | ".join(parts)

