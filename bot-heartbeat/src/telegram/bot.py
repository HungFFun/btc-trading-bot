"""
Telegram Bot 2 - Heartbeat Monitor Notifications
@HeartbeatBot

OPTIMIZED v5.1 - Gộp thông báo, loại bỏ trùng lặp:
1. 🌅 NEW DAY - Bắt đầu ngày mới (gộp cả startup info)
2. 💰 TRADE RESULT - Kết quả giao dịch (gộp luôn daily progress)
3. 🎯 DAILY COMPLETE - Khi đạt target/stop/max trades (gộp summary)
4. 🚨 ALERT - Health hoặc IQ warnings
5. 📊 END OF DAY - Summary cuối ngày
6. 📊 WEEKLY SUMMARY - Summary tuần

Loại bỏ: Các thông báo riêng lẻ target_hit, stop_hit, today_status
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for Heartbeat Monitor notifications"""
    
    def __init__(self, token: str, chat_id: str, enabled: bool = True):
        self.token = token
        self.chat_id = chat_id
        self.enabled = enabled
        self.base_url = f"https://api.telegram.org/bot{token}"
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Log initialization
        logger.info(f"TelegramBot initialized: enabled={enabled}, chat_id={chat_id}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message to the chat"""
        if not self.enabled:
            logger.warning("Telegram is DISABLED in settings")
            return False
        
        if not self.token or not self.chat_id:
            logger.error(f"Telegram not configured: token={bool(self.token)}, chat_id={bool(self.chat_id)}")
            return False
        
        try:
            session = await self._get_session()
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            logger.info(f"📤 Sending Telegram message: {text[:80]}...")
            
            async with session.post(url, json=data) as response:
                response_text = await response.text()
                if response.status == 200:
                    logger.info("✅ Message sent successfully")
                    return True
                else:
                    logger.error(f"❌ Telegram error (status={response.status}): {response_text}")
                    return False
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
            return False
    
    # =====================================================
    # THÔNG BÁO CHÍNH - 6 loại quan trọng
    # =====================================================
    
    async def send_new_day(self, daily_state=None) -> bool:
        """
        🌅 NEW DAY - Bắt đầu ngày trading mới
        Gộp: startup notification + daily limits info
        """
        from config.version import get_full_version
        
        today = date.today().isoformat()
        prev_pnl = daily_state.pnl if daily_state else 0
        
        message = f"""
🌅 <b>NEW TRADING DAY</b>
═══════════════════════════

📅 Date: {today}
📦 Version: <code>{get_full_version()}</code>

📊 <b>Daily Limits:</b>
├── 🎯 Target: +$10.00 (2%)
├── ⛔ Stop: -$15.00 (3%)
└── 📈 Max Trades: 3

💰 <b>Starting Balance:</b>
└── Previous PnL: ${prev_pnl:+.2f}

🤖 Bot đang chạy. Bấm /menu để xem options.

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(message.strip())
    
    async def send_trade_result(self, result, daily_state, trade_iq: int = 0) -> bool:
        """
        💰 TRADE RESULT - Kết quả giao dịch
        Gộp: result + daily progress + next action
        """
        logger.info(f"📣 Trade result for {result.signal_id}: {result.status}")
        
        # Result emoji & title
        if result.status == "WIN":
            emoji = "✅"
            title = "WIN - Take Profit Hit!"
            result_color = "🟢"
        elif result.status == "LOSS":
            emoji = "❌"
            title = "LOSS - Stop Loss Hit"
            result_color = "🔴"
        else:
            emoji = "⏱️"
            title = "TIMEOUT - Position Closed"
            result_color = "🟡"
        
        # Daily status determination
        if daily_state.status == "TARGET_HIT":
            daily_emoji = "🎯"
            next_action = "🎉 Target reached! Done for today."
        elif daily_state.status == "STOP_HIT":
            daily_emoji = "⛔"
            next_action = "Tomorrow is a new day! 💪"
        elif daily_state.trade_count >= 3:
            daily_emoji = "📊"
            next_action = "Max trades reached. Done for today."
        else:
            remaining = 3 - daily_state.trade_count
            to_target = 10.0 - daily_state.pnl
            daily_emoji = "🟢"
            next_action = f"💪 {remaining} trade{'s' if remaining > 1 else ''} left | ${to_target:.2f} to target"
        
        # Trade IQ assessment
        if trade_iq >= 80:
            iq_assessment = "🌟 Excellent"
        elif trade_iq >= 60:
            iq_assessment = "✅ Good"
        elif trade_iq >= 40:
            iq_assessment = "⚠️ Average"
        else:
            iq_assessment = "❌ Poor"
        
        message = f"""
{emoji} <b>{title}</b>
═══════════════════════════

💰 <b>Trade Details:</b>
├── Entry: <code>${result.entry_price:,.2f}</code>
├── Exit: <code>${result.result_price:,.2f}</code>
├── PnL: <b>${result.result_pnl:+.2f}</b> {result_color}
└── Duration: {result.duration_minutes}m

📊 <b>Performance:</b>
├── MFE (Max Profit): +{result.mfe:.2f}%
├── MAE (Max Loss): -{result.mae:.2f}%
└── Trade IQ: {trade_iq}/100 {iq_assessment}

{daily_emoji} <b>Daily Progress ({daily_state.date}):</b>
├── Trades: {daily_state.trade_count}/3
├── W/L: {daily_state.wins}W - {daily_state.losses}L
├── PnL: <b>${daily_state.pnl:+.2f}</b>
└── Status: {daily_state.status}

📌 <b>Next:</b> {next_action}

🆔 <code>{result.signal_id}</code>
"""
        return await self.send_message(message.strip())
    
    async def send_daily_complete(self, daily_state, completion_type: str) -> bool:
        """
        🎯 DAILY COMPLETE - Khi đạt target/stop/max trades
        Gộp: completion notification + summary
        """
        if completion_type == "TARGET_HIT":
            emoji = "🎯"
            title = "DAILY TARGET REACHED!"
            message_footer = "🏆 Great job! See you tomorrow at 00:00 UTC."
        elif completion_type == "STOP_HIT":
            emoji = "⛔"
            title = "DAILY STOP HIT"
            message_footer = "💪 Tomorrow is a new day. Keep learning!"
        else:
            emoji = "📊"
            title = "MAX TRADES REACHED"
            message_footer = "📈 Daily limit reached. See you tomorrow."
        
        win_rate = (daily_state.wins / daily_state.trade_count * 100) if daily_state.trade_count > 0 else 0
        
        message = f"""
{emoji} <b>{title}</b>
═══════════════════════════

📅 <b>Date:</b> {daily_state.date}

📊 <b>Day Summary:</b>
├── Trades: {daily_state.trade_count}/3
├── Wins: {daily_state.wins}
├── Losses: {daily_state.losses}
├── Win Rate: {win_rate:.0f}%
└── PnL: <b>${daily_state.pnl:+.2f}</b>

🔒 Trading paused until tomorrow.

{message_footer}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(message.strip())
    
    async def send_alert(self, alert_type: str, level: str, message: str, action: str = None) -> bool:
        """
        🚨 ALERT - Health hoặc IQ warnings
        Gộp: health_alert + iq_alert
        """
        if level == "CRITICAL":
            emoji = "🚨"
        elif level == "WARNING":
            emoji = "⚠️"
        else:
            emoji = "ℹ️"
        
        msg = f"""
{emoji} <b>{alert_type} - {level}</b>
═══════════════════════════

{message}
"""
        if action:
            msg += f"\n📋 <b>Action:</b> {action}\n"
        
        msg += f"\n⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC"
        
        return await self.send_message(msg.strip())
    
    async def send_end_of_day(self, daily_state, avg_iq: float, balance: float) -> bool:
        """
        📊 END OF DAY - Summary cuối ngày
        """
        status_emoji = "✅" if daily_state.status == "TARGET_HIT" else "❌" if daily_state.status == "STOP_HIT" else "📊"
        win_rate = (daily_state.wins / daily_state.trade_count * 100) if daily_state.trade_count > 0 else 0
        
        message = f"""
📊 <b>END OF DAY SUMMARY</b>
═══════════════════════════
📅 {daily_state.date}

📈 <b>Performance:</b>
├── Status: {daily_state.status} {status_emoji}
├── Trades: {daily_state.trade_count}/3
├── Wins: {daily_state.wins} | Losses: {daily_state.losses}
├── Win Rate: {win_rate:.0f}%
└── PnL: <b>${daily_state.pnl:+.2f}</b>

🧠 <b>Bot IQ:</b>
└── Average: {avg_iq:.0f}/100

💰 <b>Account:</b>
└── Balance: ${balance:,.2f}

📆 <b>Tomorrow:</b>
├── Target: +$10.00
└── Stop: -$15.00

🌙 Good night! See you tomorrow.
"""
        return await self.send_message(message.strip())
    
    async def send_weekly_summary(self, report) -> bool:
        """
        📊 WEEKLY SUMMARY - Summary tuần
        """
        message = f"""
📊 <b>WEEKLY SUMMARY</b>
═══════════════════════════
📅 {report.start_date} to {report.end_date}

📈 <b>Performance:</b>
├── Total Trades: {report.total_trades}
├── Wins: {report.total_wins} | Losses: {report.total_losses}
├── Win Rate: {report.win_rate:.0%}
├── Total PnL: <b>${report.total_pnl:+.2f}</b>
└── Avg Daily: ${report.avg_daily_pnl:+.2f}

🧠 <b>Bot IQ:</b>
└── Weekly Avg: {report.avg_iq:.0f}/100

📅 <b>Daily Breakdown:</b>
├── 🎯 Target Hit: {report.target_hit_days} days
├── ⛔ Stop Hit: {report.stop_hit_days} days
└── ⚪ Neutral: {7 - report.target_hit_days - report.stop_hit_days} days

🎯 Keep it up! 💪
"""
        return await self.send_message(message.strip())
    
    async def send_error(self, error: str) -> bool:
        """
        ❌ ERROR - Khi có lỗi nghiêm trọng
        """
        message = f"""
❌ <b>ERROR</b>
═══════════════════════════

{error}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(message.strip())
    
    # =====================================================
    # DEPRECATED - Các hàm cũ, map sang hàm mới
    # =====================================================
    
    async def send_result_alert(self, result, daily_state, trade_iq: int = 0) -> bool:
        """DEPRECATED - Use send_trade_result()"""
        return await self.send_trade_result(result, daily_state, trade_iq)
    
    async def send_target_hit(self, daily_state) -> bool:
        """DEPRECATED - Use send_daily_complete()"""
        return await self.send_daily_complete(daily_state, "TARGET_HIT")
    
    async def send_stop_hit(self, daily_state) -> bool:
        """DEPRECATED - Use send_daily_complete()"""
        return await self.send_daily_complete(daily_state, "STOP_HIT")
    
    async def send_health_alert(self, status: str, message: str) -> bool:
        """DEPRECATED - Use send_alert()"""
        return await self.send_alert("HEALTH", status, message)
    
    async def send_iq_alert(self, level: str, message: str, action: str) -> bool:
        """DEPRECATED - Use send_alert()"""
        return await self.send_alert("IQ", level, message, action)
    
    async def send_daily_report(self, report) -> bool:
        """DEPRECATED - Use send_end_of_day()"""
        logger.debug("send_daily_report() -> routing to send_end_of_day()")
        # Create a minimal daily_state-like object from report
        class DailyState:
            pass
        ds = DailyState()
        ds.date = report.date
        ds.status = report.status
        ds.trade_count = report.trades
        ds.wins = report.wins
        ds.losses = report.losses
        ds.pnl = report.pnl
        return await self.send_end_of_day(ds, report.avg_iq, report.account_balance)
    
    async def send_weekly_report(self, report) -> bool:
        """DEPRECATED - Use send_weekly_summary()"""
        return await self.send_weekly_summary(report)
    
    async def send_today_status(self, daily_state, health_status) -> bool:
        """DEPRECATED - Use /today command instead"""
        logger.debug("send_today_status() deprecated - Use /today command")
        return True
