"""
Telegram Bot 1 - Core Brain Notifications
@CoreBrainBot
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import aiohttp

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for Core Brain notifications"""
    
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
    
    async def send_signal_alert(self, signal, daily_state) -> bool:
        """Send new signal alert"""
        direction_emoji = "🟢" if signal.direction.value == "LONG" else "🔴"
        
        message = f"""
🔔 <b>NEW TRADE</b>
═══════════════

Direction: {direction_emoji} {signal.direction.value}
Strategy: {signal.strategy.value}
Entry: ${signal.entry_price:,.2f}
Stop Loss: ${signal.stop_loss:,.2f} (-0.25%)
Take Profit: ${signal.take_profit:,.2f} (+0.50%)

📊 <b>Quality:</b>
├── Confidence: {signal.confidence:.0%}
├── Setup: {signal.setup_quality}/100
└── Regime: {signal.regime}

📅 <b>Daily Status:</b>
├── Trade: {daily_state.trade_count + 1}/{3}
├── PnL: ${daily_state.pnl:+.2f}
└── Target: $10.00

🆔 {signal.signal_id}
"""
        return await self.send_message(message.strip())
    
    async def send_regime_change(self, old_regime: str, new_regime: str, confidence: float) -> bool:
        """Send regime change notification"""
        message = f"""
🔄 <b>REGIME CHANGE</b>
═══════════════

From: {old_regime}
To: {new_regime}
Confidence: {confidence:.0%}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(message.strip())
    
    async def send_daily_start(self) -> bool:
        """Send daily start notification"""
        message = f"""
🌅 <b>NEW TRADING DAY</b>
════════════════════

📅 Date: {datetime.utcnow().strftime('%Y-%m-%d')}
💰 Starting fresh!

📊 <b>Daily Limits:</b>
├── Target: +$10 (2%)
├── Stop: -$15 (3%)
└── Max Trades: 3

🎯 Let's hit that target!
"""
        return await self.send_message(message.strip())
    
    async def send_daily_limit_reached(self, limit_type: str, pnl: float) -> bool:
        """Send daily limit reached notification"""
        if limit_type == "TARGET_HIT":
            emoji = "🎯"
            title = "DAILY TARGET HIT!"
            message_end = "Done for today! See you tomorrow."
        elif limit_type == "STOP_HIT":
            emoji = "⛔"
            title = "DAILY STOP HIT"
            message_end = "Tomorrow is a new day! 💪"
        else:
            emoji = "📊"
            title = "MAX TRADES REACHED"
            message_end = "Trading paused until tomorrow."
        
        message = f"""
{emoji} <b>{title}</b>
═══════════════

📅 Date: {datetime.utcnow().strftime('%Y-%m-%d')}
💰 PnL: ${pnl:+.2f}

{message_end}
"""
        return await self.send_message(message.strip())
    
    async def send_learning_insight(self, lesson) -> bool:
        """Send learning insight notification"""
        message = f"""
💡 <b>NEW INSIGHT</b>
═══════════════

📝 <b>Observation:</b>
{lesson.observation}

📊 <b>Conclusion:</b>
{lesson.conclusion}

✅ <b>Action:</b>
{lesson.action_suggested}

🎯 Confidence: {lesson.confidence:.0%}
📈 Sample Size: {lesson.sample_size}
"""
        return await self.send_message(message.strip())
    
    async def send_status(self, status: Dict[str, Any]) -> bool:
        """Send current status"""
        message = f"""
📊 <b>BOT STATUS</b>
═══════════════

🤖 Bot: Core Brain
⚡ Status: {status.get('status', 'Unknown')}

📈 <b>Current:</b>
├── Price: ${status.get('price', 0):,.2f}
├── Regime: {status.get('regime', 'Unknown')}
└── Signals Today: {status.get('signals_today', 0)}

📅 <b>Daily:</b>
├── PnL: ${status.get('pnl', 0):+.2f}
├── Trades: {status.get('trades', 0)}/3
└── Status: {status.get('daily_status', 'ACTIVE')}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(message.strip())
    
    async def send_error(self, error: str) -> bool:
        """Send error notification"""
        message = f"""
⚠️ <b>ERROR</b>
═══════════════

❌ {error}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(message.strip())
    
    async def send_features_summary(self, features) -> bool:
        """Send top features summary"""
        tech = features.technical
        mtf = features.mtf
        
        message = f"""
📊 <b>FEATURES SNAPSHOT</b>
═══════════════════════

<b>Technical:</b>
├── RSI(14): {tech.rsi_14:.1f}
├── ADX: {tech.adx:.1f}
├── MACD: {tech.macd_histogram:+.2f}
└── BB Position: {tech.bb_position:.2f}

<b>Multi-Timeframe:</b>
├── 15m Trend: {mtf.tf_15m_trend}
├── 5m Trend: {mtf.tf_5m_trend}
└── Alignment: {mtf.mtf_alignment}/3

<b>Funding:</b>
└── Rate: {features.funding.funding_current*100:.4f}%

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(message.strip())
    
    async def send_gates_status(self, gate_result) -> bool:
        """Send gates status"""
        lines = ["📋 <b>5-GATE STATUS</b>", "═══════════════════", ""]
        
        for gate in gate_result.gate_results:
            if gate.status.value == "PASSED":
                emoji = "✅"
            elif gate.status.value == "FAILED":
                emoji = "❌"
            else:
                emoji = "⏭️"
            
            lines.append(f"{emoji} {gate.gate_name}: {gate.score:.0%}")
            lines.append(f"   └── {gate.reason[:50]}")
        
        lines.append("")
        lines.append(f"Overall: {'✅ PASSED' if gate_result.passed else '❌ BLOCKED'}")
        if gate_result.blocking_gate:
            lines.append(f"Blocked by: {gate_result.blocking_gate}")
        
        return await self.send_message("\n".join(lines))

