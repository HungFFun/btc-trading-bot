"""
Bot 2: Heartbeat Monitor - Main Entry Point
BTC Trading Bot v5.0
"""

import asyncio
import logging
from datetime import datetime, date
import sys
import signal as sig
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.database.repository import DatabaseRepository
from src.health.monitor import HealthMonitor
from src.tracking.signal_tracker import SignalTracker
from src.daily.manager import DailyStateManager
from src.iq.calculator import BotIQCalculator
from src.reports.generator import ReportGenerator
from src.telegram.bot import TelegramBot
from src.telegram.command_handler import TelegramCommandHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/heartbeat.log")],
)
logger = logging.getLogger(__name__)


class HeartbeatBot:
    """
    Bot 2: Heartbeat Monitor

    Main responsibilities:
    - Monitor Bot 1 health
    - Track signal outcomes (Win/Loss)
    - Calculate MFE/MAE
    - Update daily state
    - Calculate Bot IQ scores
    - Generate reports
    """

    def __init__(self):
        # Initialize database (same as Bot 1)
        self.db = DatabaseRepository(
            database_url=settings.database.DATABASE_URL,
            use_sqlite=settings.database.USE_SQLITE,
            sqlite_path=settings.database.SQLITE_PATH,
        )

        # Initialize components
        self.health_monitor = HealthMonitor(
            db_repository=self.db,
            warning_timeout=settings.monitoring.HEARTBEAT_TIMEOUT,
            critical_timeout=settings.monitoring.HEARTBEAT_CRITICAL,
        )

        self.signal_tracker = SignalTracker(
            db_repository=self.db,
            price_api_url=settings.price.rest_url,
            symbol=settings.price.SYMBOL,
            win_amount=settings.monitoring.WIN_AMOUNT,
            loss_amount=settings.monitoring.LOSS_AMOUNT,
            max_hold_minutes=settings.monitoring.MAX_HOLD_MINUTES,
        )

        self.daily_manager = DailyStateManager(
            db_repository=self.db,
            daily_target=settings.monitoring.DAILY_TARGET,
            daily_stop=settings.monitoring.DAILY_STOP,
            max_trades=settings.monitoring.MAX_TRADES,
        )

        self.iq_calculator = BotIQCalculator(
            decision_weight=settings.iq.DECISION_WEIGHT,
            execution_weight=settings.iq.EXECUTION_WEIGHT,
            risk_weight=settings.iq.RISK_WEIGHT,
            warning_threshold=settings.iq.IQ_WARNING_THRESHOLD,
            critical_threshold=settings.iq.IQ_CRITICAL_THRESHOLD,
        )

        self.report_generator = ReportGenerator(db_repository=self.db)

        self.telegram = TelegramBot(
            token=settings.telegram.TOKEN,
            chat_id=settings.telegram.CHAT_ID,
            enabled=settings.telegram.ENABLED,
        )

        # Telegram command handler (interactive commands)
        self.telegram_commands = TelegramCommandHandler(
            token=settings.telegram.TOKEN,
            chat_id=settings.telegram.CHAT_ID,
            db_repository=self.db,
            enabled=settings.telegram.ENABLED,
        )

        # State
        self._running = False
        self._last_report_date = None
        self._last_weekly_report = None
        self._command_task = None

    async def start(self):
        """Start the bot"""
        logger.info("Starting Heartbeat Monitor Bot v5.0...")
        self._running = True

        # Ensure logs directory exists
        Path("logs").mkdir(exist_ok=True)

        # Start Telegram command handler
        self._command_task = asyncio.create_task(self.telegram_commands.start_polling())
        logger.info("✅ Telegram command handler started")

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
        logger.info("Stopping Heartbeat Monitor Bot...")
        self._running = False

        # Stop command handler
        await self.telegram_commands.close()
        if self._command_task:
            self._command_task.cancel()
            try:
                await self._command_task
            except asyncio.CancelledError:
                pass

        await self.signal_tracker.close()
        await self.telegram.close()

        logger.info("Heartbeat Monitor Bot stopped")

    async def _main_loop(self):
        """Main monitoring loop"""
        logger.info("Entering main loop...")

        while self._running:
            try:
                # Check for new day
                is_new_day = self.daily_manager.check_new_day()
                if is_new_day:
                    await self._handle_new_day()

                # 1. Check Bot 1 health
                logger.info("Checking Bot 1 health...")
                health_result = self.health_monitor.check()
                logger.info(
                    f"Health status: {health_result.status.value} - {health_result.message}"
                )
                if health_result.alert_needed:
                    await self.telegram.send_alert(
                        "HEALTH", health_result.status.value, health_result.message
                    )

                # 2. Track pending signals
                logger.info("Checking pending signals...")
                results = await self.signal_tracker.check_signals()
                logger.info(f"Pending signals: {len(results)}")

                for result in results:
                    if result.changed:
                        await self._handle_signal_result(result)

                # 3. Check for IQ degradation
                iq_alert = self.iq_calculator.check_degradation()
                if iq_alert:
                    await self.telegram.send_alert(
                        "IQ", iq_alert["level"], iq_alert["message"], iq_alert["action"]
                    )

                # 4. Check for scheduled reports
                await self._check_scheduled_reports()

                # 5. Wait for next cycle
                logger.info(
                    f"Cycle complete. Waiting {settings.monitoring.SIGNAL_CHECK_INTERVAL}s..."
                )
                await asyncio.sleep(settings.monitoring.SIGNAL_CHECK_INTERVAL)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(10)

    async def _handle_new_day(self):
        """Handle new trading day"""
        logger.info("New trading day detected")

        # Generate previous day's report (end of day summary)
        if self._last_report_date:
            report = self.report_generator.generate_daily_report(self._last_report_date)
            self.report_generator.save_daily_stats(report)
            
            # Create daily_state-like object for send_end_of_day
            class DailyState:
                pass
            ds = DailyState()
            ds.date = report.date
            ds.status = report.status
            ds.trade_count = report.trades
            ds.wins = report.wins
            ds.losses = report.losses
            ds.pnl = report.pnl
            
            await self.telegram.send_end_of_day(ds, report.avg_iq, report.account_balance)

        self._last_report_date = date.today().isoformat()

        # Check for weekly report (Sunday)
        if date.today().weekday() == settings.report.WEEKLY_REPORT_DAY:
            await self._send_weekly_report()
        
        # Send new day notification
        daily_state = self.db.get_daily_state()
        await self.telegram.send_new_day(daily_state)

    async def _handle_signal_result(self, result):
        """Handle a signal result (win/loss/timeout)"""
        logger.info(f"Signal result: {result.signal_id} - {result.status}")

        # Get signal details from database
        signal = self.db.get_pending_signals()
        signal = next((s for s in signal if s.signal_id == result.signal_id), None)

        if not signal:
            # Signal might already be processed, get from recent
            signals = self.db.get_recent_signals(10)
            signal = next((s for s in signals if s.signal_id == result.signal_id), None)

        # Calculate IQ score
        if signal:
            iq_score = self.iq_calculator.calculate(signal, result)
            trade_iq = iq_score.total

            # Update signal with IQ
            self.db.update_signal_result(
                signal_id=result.signal_id,
                status=result.status,
                result_price=result.result_price,
                result_pnl=result.result_pnl,
                result_reason=result.result_reason,
                mfe=result.mfe,
                mae=result.mae,
                duration_minutes=result.duration_minutes,
                trade_iq=trade_iq,
            )
        else:
            trade_iq = 0

        # Update daily state
        daily_state = self.daily_manager.update_with_result(result)

        # Send result notification (includes daily progress and next action)
        await self.telegram.send_trade_result(result, daily_state, trade_iq)
        
        # Note: send_trade_result already includes daily status
        # No need for separate target_hit/stop_hit notifications

    async def _check_scheduled_reports(self):
        """Check for and send scheduled reports"""
        now = datetime.utcnow()

        # Daily report at midnight UTC
        if now.hour == settings.report.DAILY_REPORT_HOUR and now.minute == 0:
            if self._last_report_date != date.today().isoformat():
                # Already handled in _handle_new_day
                pass

    async def _send_weekly_report(self):
        """Send weekly report"""
        report = self.report_generator.generate_weekly_report()
        await self.telegram.send_weekly_summary(report)
        self._last_weekly_report = date.today().isoformat()

    async def _send_startup_menu(self):
        """Send startup message with interactive menu buttons"""
        from config.version import get_full_version
        
        logger.info("=== SENDING STARTUP MENU ===")
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🏥 Health", "callback_data": "health"},
                    {"text": "📊 Today", "callback_data": "today"},
                ],
                [
                    {"text": "📦 Version", "callback_data": "version"},
                    {"text": "❓ Help", "callback_data": "help"},
                ],
            ]
        }
        
        logger.info(f"Keyboard: {keyboard}")
        
        message = f"""
🔔 <b>Heartbeat Monitor Started!</b>
═══════════════════════════

📦 Version: <code>{get_full_version()}</code>
⏰ Time: {datetime.utcnow().strftime('%H:%M:%S')} UTC

<b>Chọn một tùy chọn bên dưới:</b>
"""
        result = await self.telegram_commands.send_message(message.strip(), reply_markup=keyboard)
        logger.info(f"Startup menu send result: {result}")


async def main():
    """Main entry point"""
    bot = HeartbeatBot()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    for s in (sig.SIGINT, sig.SIGTERM):
        loop.add_signal_handler(s, lambda: asyncio.create_task(bot.stop()))

    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
