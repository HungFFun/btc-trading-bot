"""
Telegram Bot 2 - Heartbeat Monitor Notifications
@HeartbeatBot
"""
import asyncio
import logging
from datetime import datetime
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
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message to the chat"""
        if not self.enabled or not self.token or not self.chat_id:
            logger.debug("Telegram disabled or not configured")
            return False
        
        try:
            session = await self._get_session()
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    return True
                else:
                    error = await response.text()
                    logger.error(f"Telegram error: {error}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def send_result_alert(self, result, daily_state, trade_iq: int = 0) -> bool:
        """Send trade result notification"""
        if result.status == "WIN":
            emoji = "✅"
            title = "WIN - Take Profit Hit!"
        elif result.status == "LOSS":
            emoji = "❌"
            title = "LOSS - Stop Loss Hit"
        else:
            emoji = "⏱️"
            title = "TIMEOUT - Position Closed"
        
        # Status message
        if daily_state.status == "TARGET_HIT":
            status_msg = "🎉 Done for today! See you tomorrow."
        elif daily_state.status == "STOP_HIT":
            status_msg = "Tomorrow is a new day! 💪"
        elif daily_state.trade_count >= 3:
            status_msg = "Max trades reached. Done for today."
        else:
            remaining = 3 - daily_state.trade_count
            status_msg = f"💪 Still in the game. {remaining} trade{'s' if remaining > 1 else ''} left."
        
        message = f"""
{emoji} <b>{title}</b>
═══════════════════════

🆔 {result.signal_id}

💰 <b>Trade:</b>
├── Entry: ${result.entry_price:,.2f}
├── Exit: ${result.result_price:,.2f}
├── PnL: ${result.result_pnl:+.2f}
└── Duration: {result.duration_minutes}m

📊 <b>Analysis:</b>
├── MFE: +{result.mfe:.2f}%
├── MAE: -{result.mae:.2f}%
└── Trade IQ: {trade_iq}/100

📅 <b>Daily Status:</b>
├── Trades: {daily_state.trade_count}/3
├── PnL: ${daily_state.pnl:+.2f}
└── Status: {daily_state.status}

{status_msg}
"""
        return await self.send_message(message.strip())
    
    async def send_target_hit(self, daily_state) -> bool:
        """Send daily target hit notification"""
        message = f"""
🎯 <b>DAILY TARGET HIT!</b>
════════════════════

📅 Date: {daily_state.date}

📊 <b>Results:</b>
├── Trades: {daily_state.trade_count}
├── Wins: {daily_state.wins}
├── Losses: {daily_state.losses}
└── PnL: ${daily_state.pnl:+.2f}

🏆 Perfect day! Trading paused.
See you tomorrow at 00:00 UTC!
"""
        return await self.send_message(message.strip())
    
    async def send_stop_hit(self, daily_state) -> bool:
        """Send daily stop hit notification"""
        message = f"""
⛔ <b>DAILY STOP HIT</b>
═════════════════

📅 Date: {daily_state.date}

📉 <b>Results:</b>
├── Trades: {daily_state.trade_count}
├── Wins: {daily_state.wins}
├── Losses: {daily_state.losses}
└── PnL: ${daily_state.pnl:+.2f}

📊 Market may be choppy today.

🔒 Trading paused until tomorrow.
Tomorrow is a new day! 💪
"""
        return await self.send_message(message.strip())
    
    async def send_health_alert(self, status: str, message: str) -> bool:
        """Send health alert"""
        if status == "CRITICAL":
            emoji = "🚨"
        elif status == "WARNING":
            emoji = "⚠️"
        else:
            emoji = "ℹ️"
        
        msg = f"""
{emoji} <b>HEALTH ALERT</b>
═══════════════════

Status: {status}
{message}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(msg.strip())
    
    async def send_iq_alert(self, level: str, message: str, action: str) -> bool:
        """Send IQ degradation alert"""
        if level == "CRITICAL":
            emoji = "🚨"
        elif level == "WARNING":
            emoji = "⚠️"
        else:
            emoji = "🧠"
        
        msg = f"""
{emoji} <b>IQ ALERT</b>
═══════════════════

Level: {level}
{message}

📋 Action: {action}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(msg.strip())
    
    async def send_daily_report(self, report) -> bool:
        """Send daily report"""
        status_emoji = "✅" if report.status == "TARGET_HIT" else "❌" if report.status == "STOP_HIT" else "📊"
        
        message = f"""
📊 <b>DAILY REPORT</b>
═══════════════
📅 {report.date}

📈 <b>PERFORMANCE</b>
├── Status: {report.status} {status_emoji}
├── Trades: {report.trades}/3
├── Wins: {report.wins} | Losses: {report.losses}
├── Win Rate: {report.win_rate:.0%}
└── PnL: ${report.pnl:+.2f}

🧠 <b>BOT IQ</b>
└── Avg IQ: {report.avg_iq:.0f}

💰 <b>ACCOUNT</b>
└── Balance: ${report.account_balance:,.2f}

📆 <b>TOMORROW</b>
└── Target: +$10 | Stop: -$15
"""
        return await self.send_message(message.strip())
    
    async def send_weekly_report(self, report) -> bool:
        """Send weekly report"""
        message = f"""
📊 <b>WEEKLY REPORT</b>
═══════════════════
📅 {report.start_date} to {report.end_date}

📈 <b>PERFORMANCE</b>
├── Total Trades: {report.total_trades}
├── Wins: {report.total_wins} | Losses: {report.total_losses}
├── Win Rate: {report.win_rate:.0%}
├── Total PnL: ${report.total_pnl:+.2f}
└── Avg Daily: ${report.avg_daily_pnl:+.2f}

🧠 <b>BOT IQ</b>
└── Avg IQ: {report.avg_iq:.0f}

📅 <b>DAILY BREAKDOWN</b>
├── Target Hit Days: {report.target_hit_days}
├── Stop Hit Days: {report.stop_hit_days}
└── Neutral Days: {7 - report.target_hit_days - report.stop_hit_days}

🎯 Keep it up! 💪
"""
        return await self.send_message(message.strip())
    
    async def send_today_status(self, daily_state, health_status) -> bool:
        """Send today's status"""
        health_emoji = "✅" if health_status['status'] == 'HEALTHY' else "⚠️"
        
        message = f"""
📊 <b>TODAY'S STATUS</b>
═══════════════════

📅 Date: {daily_state.date}

📈 <b>Progress:</b>
├── PnL: ${daily_state.pnl:+.2f}
├── Trades: {daily_state.trade_count}/3
├── Wins: {daily_state.wins}
├── Losses: {daily_state.losses}
└── Status: {daily_state.status}

🤖 <b>Bot 1:</b>
└── {health_emoji} {health_status['message']}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(message.strip())
    
    async def send_error(self, error: str) -> bool:
        """Send error notification"""
        message = f"""
❌ <b>ERROR</b>
═══════════════

{error}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(message.strip())

