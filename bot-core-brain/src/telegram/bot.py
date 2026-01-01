"""
Telegram Bot 1 - Core Brain Notifications
@CoreBrainBot

OPTIMIZED v5.1 - Chỉ gửi thông báo quan trọng:
1. 🔔 NEW SIGNAL - Khi có tín hiệu trading
2. 🔄 REGIME CHANGE - Khi market regime thay đổi
3. ⚠️ ERROR - Khi có lỗi nghiêm trọng

Các thông báo khác (daily start, limits, reports) do Bot 2 đảm nhận.
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
    # THÔNG BÁO CHÍNH - Chỉ giữ 3 loại quan trọng
    # =====================================================
    
    async def send_signal_alert(self, signal, daily_state) -> bool:
        """
        🔔 NEW SIGNAL - Thông báo khi có tín hiệu giao dịch mới
        Đây là thông báo quan trọng nhất của Bot 1
        """
        logger.info(f"📣 Preparing signal alert for {signal.signal_id}")
        
        try:
            direction_emoji = "🟢" if signal.direction.value == "LONG" else "🔴"
            
            # Tính toán risk/reward
            risk_percent = abs((signal.stop_loss - signal.entry_price) / signal.entry_price * 100)
            reward_percent = abs((signal.take_profit - signal.entry_price) / signal.entry_price * 100)
            
            message = f"""
🔔 <b>NEW TRADE SIGNAL</b>
═══════════════════════════

{direction_emoji} <b>Direction:</b> {signal.direction.value}
📈 <b>Strategy:</b> {signal.strategy.value}

💰 <b>Price Levels:</b>
├── Entry: <code>${signal.entry_price:,.2f}</code>
├── Stop Loss: <code>${signal.stop_loss:,.2f}</code> (-{risk_percent:.2f}%)
└── Take Profit: <code>${signal.take_profit:,.2f}</code> (+{reward_percent:.2f}%)

📊 <b>Signal Quality:</b>
├── AI Confidence: <b>{signal.confidence:.0%}</b>
├── Setup Score: {signal.setup_quality}/100
├── Risk:Reward: 1:{reward_percent/risk_percent:.1f}
└── Regime: {signal.regime}

📅 <b>Today's Progress:</b>
├── This is trade #{daily_state.trade_count + 1}/3
├── Current PnL: ${daily_state.pnl:+.2f}
└── Target: ${10.0 - daily_state.pnl:.2f} remaining

🆔 <code>{signal.signal_id}</code>
⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
            result = await self.send_message(message.strip())
            
            if result:
                logger.info(f"✅ Signal alert sent for {signal.signal_id}")
            else:
                logger.error(f"❌ Failed to send signal alert for {signal.signal_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error preparing signal alert: {e}")
            return False
    
    async def send_regime_change(self, old_regime: str, new_regime: str, confidence: float, details: Dict = None) -> bool:
        """
        🔄 REGIME CHANGE - Thông báo khi market regime thay đổi
        """
        logger.info(f"📣 Regime change: {old_regime} → {new_regime}")
        
        regime_emoji = {
            "TRENDING_UP": "🐂",
            "TRENDING_DOWN": "🐻",
            "RANGING": "↔️",
            "HIGH_VOLATILITY": "⚡",
            "CHOPPY": "〰️"
        }
        
        old_emoji = regime_emoji.get(old_regime, "❓")
        new_emoji = regime_emoji.get(new_regime, "❓")
        
        # Trading implications
        if new_regime == "TRENDING_UP":
            implication = "✅ Ưu tiên LONG | Theo trend | Cẩn thận exhaustion"
        elif new_regime == "TRENDING_DOWN":
            implication = "✅ Ưu tiên SHORT | Theo trend | Cẩn thận reversal"
        elif new_regime == "RANGING":
            implication = "↔️ Range trading | Mua support, bán resistance"
        elif new_regime == "HIGH_VOLATILITY":
            implication = "⚠️ Volatility cao | Giảm size | Quản lý risk chặt"
        else:
            implication = "⚠️ Thị trường khó đoán | Cân nhắc chờ đợi"
        
        message = f"""
🔄 <b>REGIME CHANGE</b>
═══════════════════════════

{old_emoji} <b>From:</b> {old_regime}
{new_emoji} <b>To:</b> {new_regime}

📊 <b>Confidence:</b> {confidence:.0%}

💡 <b>Trading Implication:</b>
└── {implication}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(message.strip())
    
    async def send_error(self, error: str, critical: bool = False) -> bool:
        """
        ⚠️ ERROR - Thông báo khi có lỗi nghiêm trọng
        """
        emoji = "🚨" if critical else "⚠️"
        title = "CRITICAL ERROR" if critical else "WARNING"
        
        message = f"""
{emoji} <b>{title}</b>
═══════════════════════════

❌ {error}

⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC
"""
        return await self.send_message(message.strip())
    
    # =====================================================
    # DEPRECATED - Các hàm này không còn sử dụng
    # Bot 2 sẽ đảm nhận các thông báo này
    # =====================================================
    
    async def send_daily_start(self) -> bool:
        """DEPRECATED - Bot 2 handles this"""
        logger.debug("send_daily_start() deprecated - Bot 2 handles new day notifications")
        return True
    
    async def send_daily_limit_reached(self, limit_type: str, pnl: float) -> bool:
        """DEPRECATED - Bot 2 handles this"""
        logger.debug(f"send_daily_limit_reached() deprecated - Bot 2 handles {limit_type}")
        return True
    
    async def send_learning_insight(self, lesson) -> bool:
        """DEPRECATED - Learning insights logged, not sent to Telegram"""
        logger.info(f"Learning insight: {lesson.observation[:100] if lesson else 'N/A'}")
        return True
    
    async def send_status(self, status: Dict[str, Any]) -> bool:
        """DEPRECATED - Use /status command instead"""
        logger.debug("send_status() deprecated - Use /status command")
        return True
    
    async def send_features_summary(self, features) -> bool:
        """DEPRECATED - Features logged internally"""
        logger.debug("send_features_summary() deprecated")
        return True
    
    async def send_gates_status(self, gate_result) -> bool:
        """DEPRECATED - Gate status logged internally"""
        logger.debug("send_gates_status() deprecated")
        return True
