"""
Bot 1: Core Brain - Main Entry Point
BTC Trading Bot v5.0
"""
import asyncio
import logging
from datetime import datetime, date
import sys
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from config.version import get_full_version, CURRENT_VERSION
from src.data.binance_client import BinanceClient
from src.features.feature_engine import FeatureEngine
from src.features.regime import RegimeDetector
from src.gates.gate_system import FiveGateSystem, DailyState
from src.signals.signal_generator import SignalGenerator
from src.ai.model import AIModel
from src.learning.learning_engine import LearningEngine, TradeResult
from src.database.repository import DatabaseRepository
from src.telegram.bot import TelegramBot
from src.telegram.command_handler import TelegramCommandHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/core_brain.log')
    ]
)
logger = logging.getLogger(__name__)


class CoreBrainBot:
    """
    Bot 1: Core Brain
    
    Main responsibilities:
    - Collect market data from Binance
    - Calculate 100 BTC-specific features
    - Detect market regime
    - Filter signals through 5-Gate System
    - Generate trading signals
    - Learn from results
    """
    
    def __init__(self):
        # Initialize components
        self.binance = BinanceClient(
            api_key=settings.api.BINANCE_API_KEY,
            api_secret=settings.api.BINANCE_API_SECRET,
            testnet=settings.api.BINANCE_TESTNET,
            symbol=settings.trading.SYMBOL
        )
        
        self.features = FeatureEngine(
            glassnode_api_key=settings.api.GLASSNODE_API_KEY,
            coinglass_api_key=settings.api.COINGLASS_API_KEY,
            use_mock=True  # Use mock data for on-chain/liquidation
        )
        
        self.regime_detector = RegimeDetector()
        
        self.gate_system = FiveGateSystem(
            context_min_score=settings.gates.CONTEXT_MIN_SCORE,
            regime_confidence_min=settings.gates.REGIME_CONFIDENCE_MIN,
            exhaustion_risk_max=settings.gates.EXHAUSTION_RISK_MAX,
            structure_quality_min=settings.gates.STRUCTURE_QUALITY_MIN,
            setup_quality_min=settings.gates.SETUP_QUALITY_MIN,
            mtf_confluence_min=settings.gates.MTF_CONFLUENCE_MIN,
            ai_confidence_min=settings.gates.AI_CONFIDENCE_MIN,
            max_risk_factors=settings.gates.MAX_RISK_FACTORS,
            daily_target=settings.trading.DAILY_TARGET,
            daily_stop=settings.trading.DAILY_STOP,
            max_trades=settings.trading.MAX_TRADES,
            max_consecutive_losses=settings.trading.MAX_CONSEC_LOSSES,
            cooldown_minutes=settings.trading.COOLDOWN_MINUTES
        )
        
        self.signal_generator = SignalGenerator(
            tp_percent=settings.trading.TP_PERCENT,
            sl_percent=settings.trading.SL_PERCENT,
            position_margin=settings.trading.POSITION_MARGIN,
            leverage=settings.trading.LEVERAGE
        )
        
        self.ai_model = AIModel(
            model_path=settings.ai.MODEL_PATH,
            confidence_threshold=settings.ai.CONFIDENCE_THRESHOLD
        )
        
        self.learning_engine = LearningEngine()
        
        self.db = DatabaseRepository(
            database_url=settings.database.DATABASE_URL,
            use_sqlite=settings.database.USE_SQLITE,
            sqlite_path=settings.database.SQLITE_PATH
        )
        
        self.telegram = TelegramBot(
            token=settings.telegram.TOKEN,
            chat_id=settings.telegram.CHAT_ID,
            enabled=settings.telegram.ENABLED
        )
        
        # Telegram command handler (interactive commands)
        self.telegram_commands = TelegramCommandHandler(
            token=settings.telegram.TOKEN,
            chat_id=settings.telegram.CHAT_ID,
            db_repository=self.db,
            feature_engine=self.features,
            regime_detector=self.regime_detector,
            enabled=settings.telegram.ENABLED
        )
        
        # State
        self._running = False
        self._last_regime = None
        self._current_date = None
        self._command_task = None
    
    async def start(self):
        """Start the bot"""
        logger.info("=" * 60)
        logger.info(f"Starting Core Brain Bot {get_full_version()}")
        logger.info("=" * 60)
        for item in CURRENT_VERSION.changelog[:3]:  # Show first 3 changelog items
            logger.info(f"  {item}")
        logger.info("=" * 60)
        
        self._running = True
        
        # Ensure logs directory exists
        Path("logs").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        
        # Connect to Binance
        binance_task = asyncio.create_task(self.binance.connect())
        
        # Start Telegram command handler
        self._command_task = asyncio.create_task(self.telegram_commands.start_polling())
        logger.info("✅ Telegram command handler started")
        
        # Wait for initial data
        await asyncio.sleep(5)
        
        # Send startup notification with interactive menu
        await self._send_startup_menu()
        
        try:
            await self._main_loop()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            await self.telegram.send_error(str(e))
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping Core Brain Bot...")
        self._running = False
        
        # Stop command handler
        await self.telegram_commands.close()
        if self._command_task:
            self._command_task.cancel()
            try:
                await self._command_task
            except asyncio.CancelledError:
                pass
        
        await self.binance.disconnect()
        await self.features.close()
        await self.telegram.close()
        
        logger.info("Core Brain Bot stopped")
    
    async def _main_loop(self):
        """Main trading loop"""
        logger.info("Entering main loop...")
        
        while self._running:
            try:
                # Check for new day
                await self._check_new_day()
                
                # Get daily state
                daily_state = self._get_daily_state()
                
                # Check if should stop trading today
                if daily_state.should_stop:
                    self.db.ping_heartbeat(
                        status='daily_limit',
                        signals_today=daily_state.trade_count,
                        daily_pnl=daily_state.pnl
                    )
                    await asyncio.sleep(60)
                    continue
                
                # Get market data
                market_data = self.binance.get_data()
                
                if not market_data.last_price:
                    logger.warning("No market data available")
                    await asyncio.sleep(10)
                    continue
                
                # Calculate features
                features = await self.features.calculate(market_data)
                
                # Detect regime
                regime = self.regime_detector.detect(features)
                
                # Check for regime change
                if self._last_regime and self._last_regime.regime_type != regime.regime_type:
                    await self.telegram.send_regime_change(
                        self._last_regime.regime_type.value,
                        regime.regime_type.value,
                        regime.confidence
                    )
                self._last_regime = regime
                
                # Skip if CHOPPY
                if not regime.is_tradeable:
                    logger.debug(f"Regime CHOPPY - skipping")
                    self.db.ping_heartbeat(
                        status='waiting',
                        current_regime=regime.regime_type.value
                    )
                    await asyncio.sleep(60)
                    continue
                
                # Generate potential signal
                potential_signal = self.signal_generator.generate(features, regime)
                
                if potential_signal:
                    logger.info(f"Potential signal: {potential_signal.direction.value}")
                    
                    # Get AI prediction
                    logger.info("Getting AI prediction...")
                    try:
                        ai_result = self.ai_model.predict(features)
                        logger.info(f"AI result: confidence={ai_result.confidence:.2%}, direction={ai_result.direction}")
                    except Exception as e:
                        logger.error(f"AI prediction failed: {e}")
                        ai_result = None
                    
                    # Run through 5-Gate System
                    logger.info("Running 5-Gate System...")
                    try:
                        gate_result = self.gate_system.evaluate(
                            features=features,
                            regime=regime,
                            signal={
                                'direction': potential_signal.direction.value,
                                'setup_quality': potential_signal.setup_quality
                            },
                            daily_state=daily_state,
                            ai_result=ai_result.to_dict() if ai_result else None
                        )
                        logger.info(f"Gate result: passed={gate_result.passed}, blocking_gate={gate_result.blocking_gate}")
                    except Exception as e:
                        logger.error(f"Gate evaluation failed: {e}")
                        gate_result = None
                        continue
                    
                    if gate_result and gate_result.passed:
                        logger.info("All 5 gates passed!")
                        
                        # Check AI confidence
                        if ai_result and ai_result.confidence >= settings.ai.CONFIDENCE_THRESHOLD:
                            
                            # FINAL VALIDATION: Check AI direction matches signal direction
                            ai_direction = ai_result.direction
                            signal_direction = potential_signal.direction.value
                            
                            # If AI says NO_TRADE, reject
                            if ai_direction == "NO_TRADE":
                                logger.warning(f"Signal rejected: AI says NO_TRADE")
                            # If AI direction conflicts with signal direction
                            elif ai_direction != signal_direction:
                                logger.warning(
                                    f"Signal rejected: AI direction ({ai_direction}) != "
                                    f"Signal direction ({signal_direction})"
                                )
                            else:
                                # All checks passed!
                                logger.info(f"Signal APPROVED: {potential_signal.signal_id}")
                                logger.info(f"  Direction: {signal_direction} (AI confirms)")
                                logger.info(f"  Confidence: {ai_result.confidence:.0%}")
                                logger.info(f"  Regime: {regime.regime_type.value}")
                                
                                # Update signal with gate scores
                                potential_signal.confidence = ai_result.confidence
                                potential_signal.gate_scores = {
                                    f'gate_{i+1}': g.score 
                                    for i, g in enumerate(gate_result.gate_results)
                                }
                                
                                # Save to database
                                self._save_signal(potential_signal, features)
                                
                                # Send alert
                                await self.telegram.send_signal_alert(
                                    potential_signal, 
                                    daily_state
                                )
                        else:
                            logger.info(f"Signal rejected: AI confidence {ai_result.confidence:.0%} < {settings.ai.CONFIDENCE_THRESHOLD:.0%}")
                    else:
                        logger.debug(f"Signal blocked at: {gate_result.blocking_gate}")
                
                # Check for new results to learn from
                logger.debug("Checking for new results to learn from...")
                new_results = self.db.get_new_results()
                if new_results:
                    self._process_learning(new_results)
                
                # Send heartbeat
                logger.info(f"Sending heartbeat... Regime: {regime.regime_type.value}")
                self.db.ping_heartbeat(
                    status='running',
                    signals_today=daily_state.trade_count,
                    current_regime=regime.regime_type.value,
                    daily_pnl=daily_state.pnl
                )
                
                # Wait for next cycle
                logger.info(f"Cycle complete. Waiting {settings.MAIN_LOOP_INTERVAL}s...")
                await asyncio.sleep(settings.MAIN_LOOP_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.db.ping_heartbeat(status='error', error_message=str(e))
                await asyncio.sleep(10)
    
    async def _check_new_day(self):
        """Check if it's a new trading day"""
        today = date.today().isoformat()
        
        if self._current_date != today:
            logger.info(f"New trading day: {today}")
            self._current_date = today
            
            # Reset daily state
            self.db.reset_daily_state(today)
            
            # Send notification
            await self.telegram.send_daily_start()
    
    def _get_daily_state(self) -> DailyState:
        """Get current daily state from database"""
        db_state = self.db.get_daily_state()
        
        return DailyState(
            date=db_state.date,
            pnl=db_state.pnl,
            trade_count=db_state.trade_count,
            wins=db_state.wins,
            losses=db_state.losses,
            consecutive_losses=db_state.consecutive_losses,
            has_position=db_state.has_position,
            status=db_state.status
        )
    
    def _save_signal(self, signal, features):
        """Save signal and features to database"""
        from src.database.models import Signal as DBSignal
        
        db_signal = DBSignal(
            signal_id=signal.signal_id,
            created_at=signal.created_at,
            direction=signal.direction.value,
            strategy=signal.strategy.value,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            position_margin=signal.position_margin,
            leverage=signal.leverage,
            confidence=signal.confidence,
            setup_quality=signal.setup_quality,
            regime=signal.regime,
            reasoning=signal.reasoning,
            gate_1_score=signal.gate_scores.get('gate_1', 0),
            gate_2_score=signal.gate_scores.get('gate_2', 0),
            gate_3_score=signal.gate_scores.get('gate_3', 0),
            gate_4_score=signal.gate_scores.get('gate_4', 0),
            gate_5_passed=signal.gate_scores.get('gate_5', 0) > 0
        )
        
        self.db.save_signal(db_signal)
        self.db.save_features_snapshot(signal.signal_id, features.to_dict())
        self.db.increment_trade_count()
    
    def _process_learning(self, results):
        """Process new results for learning"""
        trade_results = []
        
        for result in results:
            # Get features snapshot
            features_dict = {}  # Would load from database
            
            trade_result = TradeResult(
                signal_id=result.signal_id,
                direction=result.direction,
                strategy=result.strategy,
                regime=result.regime,
                setup_quality=result.setup_quality,
                confidence=result.confidence,
                result=result.status,
                pnl=result.result_pnl or 0,
                mfe=result.mfe or 0,
                mae=result.mae or 0,
                duration_minutes=result.duration_minutes or 0,
                features=features_dict
            )
            trade_results.append(trade_result)
        
        # Analyze patterns
        new_lessons = self.learning_engine.analyze(trade_results)
        
        # Send insights
        for lesson in new_lessons:
            asyncio.create_task(self.telegram.send_learning_insight(lesson))
        
        # Mark as analyzed
        for result in results:
            self.db.mark_signal_analyzed(result.signal_id)
    
    async def _send_startup_menu(self):
        """Send startup message with interactive menu buttons"""
        logger.info("=== SENDING STARTUP MENU ===")
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📊 Status", "callback_data": "status"},
                    {"text": "📅 Daily", "callback_data": "daily"},
                ],
                [
                    {"text": "📈 Regime", "callback_data": "regime"},
                    {"text": "📦 Version", "callback_data": "version"},
                ],
                [
                    {"text": "❓ Help", "callback_data": "help"},
                ],
            ]
        }
        
        logger.info(f"Keyboard: {keyboard}")
        
        message = f"""
🤖 <b>Core Brain Bot Started!</b>
═══════════════════════════

📦 Version: <code>{get_full_version()}</code>
⏰ Time: {datetime.utcnow().strftime('%H:%M:%S')} UTC

<b>Chọn một tùy chọn bên dưới:</b>
"""
        result = await self.telegram_commands.send_message(message.strip(), reply_markup=keyboard)
        logger.info(f"Startup menu send result: {result}")


async def main():
    """Main entry point"""
    bot = CoreBrainBot()
    
    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.stop()))
    
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())

