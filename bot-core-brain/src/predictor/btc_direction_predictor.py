"""
BTC Direction Predictor - Main Class
★ INDEPENDENT - Read-only, non-blocking ★
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable

from . import (
    Direction, SignalStrength, PredictionSignal,
    ConfidenceBreakdown
)
from .prediction_engine import PredictionEngine
from .confidence_calculator import ConfidenceCalculator
from .signal_formatter import SignalFormatter

logger = logging.getLogger(__name__)


class BTCDirectionPredictor:
    """
    Main predictor class - READONLY, does not modify any state
    
    Features:
    - Analyzes market data independently
    - Generates prediction signals
    - Sends notifications via Telegram
    - Does NOT execute trades
    """
    
    VERSION = "1.0.0"
    
    def __init__(
        self,
        config: Dict[str, Any],
        telegram_bot=None,
        enabled: bool = True
    ):
        """
        Initialize predictor
        
        Args:
            config: Predictor configuration
            telegram_bot: Telegram bot instance for notifications
            enabled: Whether predictor is enabled
        """
        self.config = config
        self.telegram = telegram_bot
        self.is_enabled = enabled
        
        # Initialize components
        self.engine = PredictionEngine(config)
        self.confidence_calc = ConfidenceCalculator(config)
        self.formatter = SignalFormatter(config)
        
        # State (read-only tracking)
        self._last_prediction: Optional[PredictionSignal] = None
        self._prediction_count = 0
        
        logger.info(f"BTCDirectionPredictor initialized (v{self.VERSION})")
    
    async def predict(self, market_data: Dict[str, Any]) -> Optional[PredictionSignal]:
        """
        Generate prediction from market data
        
        Args:
            market_data: Dictionary containing:
                - current_price: float
                - candles: Dict[timeframe, List[candle]]
                - funding_rate: float (optional)
                - orderbook: dict (optional)
        
        Returns:
            PredictionSignal - Always returns LONG or SHORT
        """
        if not self.is_enabled:
            logger.debug("Predictor is disabled")
            return None
        
        try:
            logger.info("🔮 Running prediction analysis...")
            
            # 1. Run analysis engine
            analysis = self.engine.analyze(market_data)
            
            if analysis is None:
                logger.warning("Analysis returned None - insufficient data")
                return None
            
            # 2. Force direction to LONG or SHORT (never NEUTRAL)
            if analysis['direction'] == Direction.NEUTRAL:
                # Use score to decide - positive = LONG, negative = SHORT
                if analysis['score'] >= 0:
                    analysis['direction'] = Direction.LONG
                else:
                    analysis['direction'] = Direction.SHORT
                logger.info(f"Forced direction from NEUTRAL to {analysis['direction'].value} (score: {analysis['score']:.1f})")
            
            # 3. Calculate confidence
            confidence = self.confidence_calc.calculate(analysis)
            
            # 4. Build prediction signal (no thresholds - always output)
            signal = self._build_signal(market_data, analysis, confidence)
            
            # Track
            self._last_prediction = signal
            self._prediction_count += 1
            
            logger.info(f"🔮 Prediction: {signal.direction.value} | Confidence: {signal.confidence:.1f}%")
            
            return signal
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            return None
    
    async def predict_and_notify(self, market_data: Dict[str, Any]) -> Optional[PredictionSignal]:
        """
        Generate prediction and send Telegram notification
        Always sends LONG or SHORT (no NEUTRAL)
        
        Args:
            market_data: Market data dictionary
        
        Returns:
            PredictionSignal if generated, None otherwise
        """
        signal = await self.predict(market_data)
        
        if signal is None:
            return None
        
        # Send notification (always LONG or SHORT now)
        if self.telegram:
            try:
                message = self.formatter.format_telegram_message(signal)
                await self.telegram.send_message(message)
                logger.info(f"📤 Prediction notification sent: {signal.direction.value}")
            except Exception as e:
                logger.error(f"Failed to send prediction notification: {e}")
        
        return signal
    
    async def run_periodic(
        self,
        data_provider: Callable,
        interval_minutes: int = 15
    ):
        """
        Run predictions periodically in separate task
        
        Usage:
            task = asyncio.create_task(
                predictor.run_periodic(get_market_data, 15)
            )
        
        Args:
            data_provider: Async function that returns market_data dict
            interval_minutes: Interval between predictions
        """
        logger.info(f"🔮 Starting periodic predictor (every {interval_minutes} minutes)")
        
        while True:
            try:
                if self.is_enabled:
                    # Get market data
                    market_data = await data_provider()
                    
                    if market_data:
                        await self.predict_and_notify(market_data)
                    else:
                        logger.warning("No market data available for prediction")
                
                # Wait for next interval
                await asyncio.sleep(interval_minutes * 60)
                
            except asyncio.CancelledError:
                logger.info("Periodic predictor cancelled")
                break
            except Exception as e:
                logger.error(f"Periodic prediction error: {e}")
                await asyncio.sleep(60)  # Wait 1 min before retry
    
    def _build_signal(
        self,
        market_data: Dict[str, Any],
        analysis: Dict[str, Any],
        confidence: ConfidenceBreakdown
    ) -> PredictionSignal:
        """Build complete prediction signal"""
        
        current_price = market_data.get('current_price', 0)
        direction = analysis['direction']
        
        # Get entry config
        entry_config = self.config.get('entry', {})
        tp_percent = entry_config.get('tp_percent', 0.50) / 100
        sl_percent = entry_config.get('sl_percent', 0.25) / 100
        leverage = entry_config.get('leverage', 20)
        position_size = entry_config.get('position_size_usd', 150)
        
        # Calculate prices
        if direction == Direction.LONG:
            suggested_tp = current_price * (1 + tp_percent)
            suggested_sl = current_price * (1 - sl_percent)
        elif direction == Direction.SHORT:
            suggested_tp = current_price * (1 - tp_percent)
            suggested_sl = current_price * (1 + sl_percent)
        else:
            suggested_tp = current_price
            suggested_sl = current_price
        
        # Calculate potential P/L
        notional = position_size * leverage
        potential_profit = notional * tp_percent
        potential_loss = notional * sl_percent
        
        # Determine signal strength
        score = abs(analysis['score'])
        if score >= 70:
            strength = SignalStrength.VERY_STRONG
        elif score >= 50:
            strength = SignalStrength.STRONG
        elif score >= 30:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK
        
        return PredictionSignal(
            prediction_id=self._generate_id(),
            timestamp=datetime.utcnow(),
            model_version=self.VERSION,
            
            direction=direction,
            strength=strength,
            
            confidence=confidence.overall_confidence,
            win_probability=confidence.win_probability,
            
            current_price=current_price,
            suggested_entry=current_price,
            suggested_tp=suggested_tp,
            suggested_sl=suggested_sl,
            tp_percent=tp_percent * 100,
            sl_percent=sl_percent * 100,
            
            suggested_leverage=leverage,
            position_size_usd=position_size,
            
            risk_reward_ratio=tp_percent / sl_percent if sl_percent > 0 else 2.0,
            potential_profit=potential_profit,
            potential_loss=potential_loss,
            
            overall_score=analysis['score'],
            indicators_summary=analysis.get('indicators_summary', {}),
            reasoning=analysis.get('reasoning', []),
            warnings=confidence.risk_factors
        )
    
    def _generate_id(self) -> str:
        """Generate unique prediction ID"""
        date_str = datetime.utcnow().strftime("%Y%m%d_%H%M")
        unique = uuid.uuid4().hex[:4].upper()
        return f"PRED_{date_str}_{unique}"
    
    # =====================================================
    # Control methods
    # =====================================================
    
    def enable(self):
        """Enable predictor"""
        self.is_enabled = True
        logger.info("Predictor enabled")
    
    def disable(self):
        """Disable predictor"""
        self.is_enabled = False
        logger.info("Predictor disabled")
    
    def get_last_prediction(self) -> Optional[PredictionSignal]:
        """Get last prediction (read-only)"""
        return self._last_prediction
    
    def get_stats(self) -> Dict[str, Any]:
        """Get predictor statistics"""
        return {
            'version': self.VERSION,
            'enabled': self.is_enabled,
            'prediction_count': self._prediction_count,
            'last_prediction': self._last_prediction.to_dict() if self._last_prediction else None
        }

