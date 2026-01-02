"""
Telegram Command Handler for Bot 1 (Core Brain)
Handles interactive commands: /status, /daily, /regime, /version, /predict
"""
import asyncio
import json
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, TYPE_CHECKING
import aiohttp

from config.version import get_version, get_full_version, format_version_message, CURRENT_VERSION

if TYPE_CHECKING:
    from src.predictor import BTCDirectionPredictor

logger = logging.getLogger(__name__)


class TelegramCommandHandler:
    """Handle incoming Telegram commands for Core Brain bot"""
    
    def __init__(
        self, 
        token: str, 
        chat_id: str, 
        db_repository, 
        feature_engine, 
        regime_detector, 
        enabled: bool = True,
        predictor: "BTCDirectionPredictor" = None,
        binance_client = None
    ):
        self.token = token
        self.chat_id = chat_id
        self.db = db_repository
        self.feature_engine = feature_engine
        self.regime_detector = regime_detector
        self.enabled = enabled
        self.predictor = predictor  # BTC Direction Predictor (independent)
        self.binance = binance_client  # For getting market data
        self.base_url = f"https://api.telegram.org/bot{token}"
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_update_id = 0
        self._running = False
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        self._running = False
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def send_message(self, text: str, parse_mode: str = "HTML", reply_markup: dict = None) -> bool:
        """Send a message to the chat"""
        if not self.enabled or not self.token or not self.chat_id:
            logger.warning("Telegram disabled or not configured")
            return False
        
        try:
            session = await self._get_session()
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            if reply_markup:
                # DO NOT use json.dumps here - aiohttp's json= handles serialization
                data["reply_markup"] = reply_markup
            
            logger.info(f"Sending message to Telegram (chat_id={self.chat_id}): {text[:50]}...")
            logger.info(f"Data being sent: {data}")
            
            async with session.post(url, json=data) as response:
                response_text = await response.text()
                if response.status == 200:
                    logger.info("Message sent successfully")
                    return True
                else:
                    logger.error(f"Telegram send error (status={response.status}): {response_text}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def get_updates(self, timeout: int = 30) -> list:
        """Get updates from Telegram"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/getUpdates"
            params = {
                "offset": self._last_update_id + 1,
                "timeout": timeout,
                "allowed_updates": ["message", "callback_query"]
            }
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=timeout+5)) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("result", [])
                    if results:
                        logger.info(f"📥 Received {len(results)} update(s)")
                    return results
                else:
                    error = await response.text()
                    logger.error(f"Get updates error: {error}")
                    return []
        except asyncio.TimeoutError:
            return []
        except Exception as e:
            logger.error(f"Failed to get updates: {e}")
            return []
    
    async def answer_callback_query(self, callback_query_id: str, text: str = None):
        """Answer a callback query"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/answerCallbackQuery"
            data = {"callback_query_id": callback_query_id}
            if text:
                data["text"] = text
            
            async with session.post(url, json=data) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to answer callback: {e}")
            return False
    
    async def handle_command(self, command: str, message_data: dict):
        """Route commands to appropriate handlers"""
        chat_id = str(message_data.get("chat", {}).get("id", ""))
        
        logger.info(f"Handling command: {command}")
        logger.info(f"Message chat_id: {chat_id}, Configured chat_id: {self.chat_id}")
        
        # Only respond to configured chat_id
        if chat_id != str(self.chat_id):
            logger.warning(f"Ignoring command from unauthorized chat: {chat_id} (expected: {self.chat_id})")
            return
        
        command = command.lower().strip().split('@')[0]  # Remove @botname if present
        logger.info(f"Processed command: {command}")
        
        if command == "/status":
            await self.cmd_status()
        elif command == "/daily":
            await self.cmd_daily()
        elif command == "/regime":
            await self.cmd_regime()
        elif command == "/version":
            await self.cmd_version()
        elif command == "/help":
            await self.cmd_help()
        elif command == "/start" or command == "/menu":
            logger.info("Calling cmd_menu()")
            await self.cmd_menu()
        elif command == "/predict":
            await self.cmd_predict()
        elif command == "/last_predict":
            await self.cmd_last_predict()
        elif command == "/predictor_on":
            await self.cmd_predictor_toggle(True)
        elif command == "/predictor_off":
            await self.cmd_predictor_toggle(False)
        else:
            await self.send_message(f"❓ Unknown command: {command}\n\nUse /menu to see available commands.")
    
    async def handle_callback(self, callback_query: dict):
        """Handle inline button callbacks"""
        callback_id = callback_query.get("id")
        data = callback_query.get("data", "")
        chat_id = str(callback_query.get("message", {}).get("chat", {}).get("id", ""))
        
        # Only respond to configured chat_id
        if chat_id != self.chat_id:
            return
        
        # Answer callback to remove loading state
        await self.answer_callback_query(callback_id)
        
        # Route to appropriate handler
        if data == "status":
            await self.cmd_status()
        elif data == "daily":
            await self.cmd_daily()
        elif data == "regime":
            await self.cmd_regime()
        elif data == "version":
            await self.cmd_version()
        elif data == "help":
            await self.cmd_help()
        elif data == "menu":
            await self.cmd_menu()
        elif data == "predict":
            await self.cmd_predict()
        elif data == "last_predict":
            await self.cmd_last_predict()
        elif data == "predictor_toggle":
            if self.predictor:
                await self.cmd_predictor_toggle(not self.predictor.is_enabled)
            else:
                await self.send_message("❌ Predictor chưa được khởi tạo")
        elif data == "predictor_menu":
            await self.cmd_predictor_menu()
    
    async def cmd_menu(self):
        """Show interactive menu with inline buttons"""
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📊 Status", "callback_data": "status"},
                    {"text": "📅 Daily", "callback_data": "daily"}
                ],
                [
                    {"text": "📈 Regime", "callback_data": "regime"},
                    {"text": "📦 Version", "callback_data": "version"}
                ],
                [
                    {"text": "🔮 Predictor", "callback_data": "predictor_menu"},
                    {"text": "❓ Help", "callback_data": "help"}
                ]
            ]
        }
        
        message = f"""
🤖 <b>BTC Trading Bot - Core Brain</b>
═══════════════════════════

📦 Version: <code>{get_full_version()}</code>

<b>Chọn một trong các tùy chọn bên dưới:</b>
"""
        await self.send_message(message.strip(), reply_markup=keyboard)
    
    async def cmd_status(self):
        """Handle /status command"""
        try:
            daily_state = self.db.get_daily_state()
            signals_today = self.db.get_signals_today()
            
            # Get current price from feature engine
            price = 0
            regime = "Unknown"
            try:
                if self.feature_engine and self.feature_engine.latest_features:
                    price = self.feature_engine.latest_features.get('close', 0)
                if self.regime_detector and self.regime_detector.current_regime:
                    regime = self.regime_detector.current_regime.regime_type
            except:
                pass
            
            status_emoji = {
                "ACTIVE": "🟢",
                "TARGET_HIT": "🎯",
                "STOP_HIT": "⛔",
                "MAX_TRADES": "📊"
            }.get(daily_state.status, "⚪")
            
            message = f"""
📊 <b>BOT STATUS</b> - @CoreBrainBot
═══════════════════════════

🤖 <b>Core Brain Bot 1</b>
⚡ Status: Running
📡 Market Data: Connected

💹 <b>Current Market:</b>
├── BTC Price: ${price:,.2f}
├── Regime: {regime}
└── Time: {datetime.utcnow().strftime('%H:%M:%S')} UTC

📅 <b>Today ({date.today().isoformat()}):</b>
├── Status: {status_emoji} {daily_state.status}
├── Signals: {len(signals_today)}
├── Trades: {daily_state.trade_count}/3
├── PnL: ${daily_state.pnl:+.2f}
└── Target: ${10.00 - daily_state.pnl:.2f} to go

🎯 <b>Daily Limits:</b>
├── Target: +$10.00 (2%)
├── Stop: -$15.00 (3%)
└── Max Trades: 3

💪 Bot is actively monitoring the market!
"""
            await self.send_message(message.strip())
            
        except Exception as e:
            logger.error(f"Error in cmd_status: {e}")
            await self.send_message(f"❌ Error fetching status: {str(e)}")
    
    async def cmd_daily(self):
        """Handle /daily command"""
        try:
            daily_state = self.db.get_daily_state()
            signals_today = self.db.get_signals_today()
            
            # Count by status
            wins = sum(1 for s in signals_today if s.status == "WIN")
            losses = sum(1 for s in signals_today if s.status == "LOSS")
            timeouts = sum(1 for s in signals_today if s.status == "TIMEOUT")
            pending = sum(1 for s in signals_today if s.status == "PENDING")
            
            win_rate = (wins / daily_state.trade_count * 100) if daily_state.trade_count > 0 else 0
            
            status_emoji = {
                "ACTIVE": "🟢 Active",
                "TARGET_HIT": "🎯 Target Hit!",
                "STOP_HIT": "⛔ Stop Hit",
                "MAX_TRADES": "📊 Max Trades"
            }.get(daily_state.status, "⚪ Unknown")
            
            message = f"""
📅 <b>DAILY STATE</b> - {date.today().isoformat()}
═══════════════════════════

💰 <b>Performance:</b>
├── PnL: ${daily_state.pnl:+.2f}
├── Target: +$10.00
├── Stop: -$15.00
└── Status: {status_emoji}

📊 <b>Trades ({daily_state.trade_count}/3):</b>
├── ✅ Wins: {wins}
├── ❌ Losses: {losses}
├── ⏱️ Timeouts: {timeouts}
├── 🔄 Pending: {pending}
└── 📈 Win Rate: {win_rate:.0f}%

🔥 <b>Streak:</b>
└── Consecutive Losses: {daily_state.consecutive_losses}

📋 <b>Position:</b>
└── Has Position: {"Yes 📍" if daily_state.has_position else "No"}

⏰ Last Updated: {daily_state.updated_at.strftime('%H:%M:%S')} UTC
"""
            
            if daily_state.status == "TARGET_HIT":
                message += "\n🎉 Great job! Target reached. See you tomorrow!"
            elif daily_state.status == "STOP_HIT":
                message += "\n💪 Tomorrow is a new day. Keep learning!"
            elif daily_state.trade_count >= 3:
                message += "\n📊 Max trades reached. Done for today!"
            else:
                remaining = 3 - daily_state.trade_count
                message += f"\n🚀 Still in the game! {remaining} trade{'s' if remaining > 1 else ''} remaining."
            
            await self.send_message(message.strip())
            
        except Exception as e:
            logger.error(f"Error in cmd_daily: {e}")
            await self.send_message(f"❌ Error fetching daily state: {str(e)}")
    
    async def cmd_regime(self):
        """Handle /regime command"""
        try:
            regime_info = "Unknown"
            confidence = 0
            trend = "N/A"
            volatility = "N/A"
            
            if self.regime_detector and self.regime_detector.current_regime:
                regime = self.regime_detector.current_regime
                regime_info = regime.regime_type
                confidence = regime.confidence
                trend = regime.details.get('trend', 'N/A')
                volatility = regime.details.get('volatility', 'N/A')
            
            regime_emoji = {
                "BULL_TRENDING": "🐂",
                "BEAR_TRENDING": "🐻",
                "RANGING": "↔️",
                "CHOPPY": "〰️",
                "BREAKOUT": "💥"
            }.get(regime_info, "❓")
            
            message = f"""
📈 <b>MARKET REGIME</b>
═══════════════════════════

{regime_emoji} <b>Current Regime:</b>
└── {regime_info}

📊 <b>Details:</b>
├── Confidence: {confidence:.0%}
├── Trend: {trend}
└── Volatility: {volatility}

💡 <b>Trading Implications:</b>
"""
            
            if regime_info == "BULL_TRENDING":
                message += "├── ✅ Favor LONG entries\n"
                message += "├── 📈 Ride the trend\n"
                message += "└── ⚠️ Watch for exhaustion"
            elif regime_info == "BEAR_TRENDING":
                message += "├── ✅ Favor SHORT entries\n"
                message += "├── 📉 Follow the trend\n"
                message += "└── ⚠️ Watch for reversal"
            elif regime_info == "RANGING":
                message += "├── ↔️ Buy support, sell resistance\n"
                message += "├── 📊 Mean reversion strategy\n"
                message += "└── ⚠️ Avoid breakout chasing"
            elif regime_info == "CHOPPY":
                message += "├── ⚠️ Difficult conditions\n"
                message += "├── 🛑 Consider reducing risk\n"
                message += "└── 💡 Wait for clearer signals"
            elif regime_info == "BREAKOUT":
                message += "├── 💥 High momentum\n"
                message += "├── ⚡ Quick entries/exits\n"
                message += "└── ⚠️ Manage risk carefully"
            else:
                message += "└── 📊 Analyzing market conditions..."
            
            message += f"\n\n⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC"
            
            await self.send_message(message.strip())
            
        except Exception as e:
            logger.error(f"Error in cmd_regime: {e}")
            await self.send_message(f"❌ Error fetching regime: {str(e)}")
    
    async def cmd_version(self):
        """Handle /version command"""
        try:
            message = f"""
🤖 <b>Core Brain</b>
└── Version: <code>{CURRENT_VERSION.full_version}</code>
"""
            await self.send_message(message.strip())
            
        except Exception as e:
            logger.error(f"Error in cmd_version: {e}")
            await self.send_message(f"❌ Error fetching version: {str(e)}")
    
    async def cmd_predictor_menu(self):
        """Show predictor sub-menu"""
        predictor_status = "🟢 ON" if (self.predictor and self.predictor.is_enabled) else "🔴 OFF"
        toggle_text = "🔴 Tắt Predictor" if (self.predictor and self.predictor.is_enabled) else "🟢 Bật Predictor"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🔮 Dự đoán ngay", "callback_data": "predict"}
                ],
                [
                    {"text": "📊 Dự đoán gần nhất", "callback_data": "last_predict"}
                ],
                [
                    {"text": toggle_text, "callback_data": "predictor_toggle"}
                ],
                [
                    {"text": "⬅️ Quay lại Menu", "callback_data": "menu"}
                ]
            ]
        }
        
        message = f"""
🔮 <b>BTC Direction Predictor</b>
═══════════════════════════

<b>Status:</b> {predictor_status}

<b>Predictor là gì?</b>
Module phân tích và dự đoán hướng BTC 
(LONG/SHORT) dựa trên:
├── Technical: RSI, MACD, EMA, BB, ADX
├── Structure: Support/Resistance
└── Sentiment: Funding, L/S Ratio

⚡ <b>Chỉ là GỢI Ý - Không tự động trade</b>

<b>Chọn một tùy chọn:</b>
"""
        await self.send_message(message.strip(), reply_markup=keyboard)
    
    async def cmd_predict(self):
        """Generate prediction now"""
        if not self.predictor:
            await self.send_message("❌ Predictor chưa được khởi tạo. Vui lòng khởi động lại bot.")
            return
        
        if not self.predictor.is_enabled:
            await self.send_message("⚠️ Predictor đang tắt. Bật lại bằng lệnh /predictor_on")
            return
        
        await self.send_message("🔮 Đang phân tích thị trường...")
        
        try:
            # Get market data
            market_data = await self._get_market_data_for_predictor()
            
            if not market_data:
                await self.send_message("❌ Không thể lấy dữ liệu thị trường")
                return
            
            # Run prediction
            signal = await self.predictor.predict(market_data)
            
            if signal:
                # Format and send
                from src.predictor.signal_formatter import SignalFormatter
                formatter = SignalFormatter({})
                message = formatter.format_telegram_message(signal)
                await self.send_message(message)
            else:
                await self.send_message(
                    "📊 <b>Không có tín hiệu rõ ràng</b>\n\n"
                    "Điều kiện thị trường chưa đủ mạnh để đưa ra dự đoán.\n"
                    "Thử lại sau hoặc chờ điều kiện tốt hơn."
                )
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            await self.send_message(f"❌ Lỗi khi dự đoán: {str(e)}")
    
    async def cmd_last_predict(self):
        """Show last prediction"""
        if not self.predictor:
            await self.send_message("❌ Predictor chưa được khởi tạo")
            return
        
        last_signal = self.predictor.get_last_prediction()
        
        if not last_signal:
            await self.send_message("📊 Chưa có dự đoán nào. Sử dụng /predict để tạo mới.")
            return
        
        # Format and send
        from src.predictor.signal_formatter import SignalFormatter
        formatter = SignalFormatter({})
        message = formatter.format_telegram_message(last_signal)
        
        # Add note about when it was generated
        time_diff = datetime.utcnow() - last_signal.timestamp
        minutes_ago = int(time_diff.total_seconds() / 60)
        
        message += f"\n\n⏱️ <i>Dự đoán từ {minutes_ago} phút trước</i>"
        
        await self.send_message(message)
    
    async def cmd_predictor_toggle(self, enable: bool):
        """Toggle predictor on/off"""
        if not self.predictor:
            await self.send_message("❌ Predictor chưa được khởi tạo")
            return
        
        if enable:
            self.predictor.enable()
            await self.send_message("🟢 Predictor đã được <b>BẬT</b>")
        else:
            self.predictor.disable()
            await self.send_message("🔴 Predictor đã được <b>TẮT</b>")
    
    async def _get_market_data_for_predictor(self) -> Optional[Dict[str, Any]]:
        """Get market data for predictor - independent from core logic"""
        try:
            # Try to get data from binance client
            if self.binance:
                data = self.binance.get_data()
                logger.info(f"Binance data: last_price={data.last_price if data else 'None'}")
                
                if data and data.last_price:
                    # Convert candles to predictor format
                    # data.candles is Dict[str, deque[Candle]]
                    candles_dict = {}
                    
                    for tf in ['5m', '15m', '1m']:
                        if tf in data.candles and len(data.candles[tf]) > 0:
                            candles_dict[tf] = [
                                {
                                    'open': c.open,
                                    'high': c.high,
                                    'low': c.low,
                                    'close': c.close,
                                    'volume': c.volume
                                }
                                for c in data.candles[tf]
                            ]
                            logger.info(f"Got {len(candles_dict[tf])} candles for {tf}")
                    
                    # Get funding rate
                    funding_rate = 0
                    if data.funding:
                        funding_rate = data.funding.funding_rate
                    
                    return {
                        'current_price': data.last_price,
                        'candles': candles_dict,
                        'funding_rate': funding_rate,
                        'long_short_ratio': None,  # Not available from basic binance data
                        'oi_change_pct': None,
                        'price_change_pct': None
                    }
            
            # Fallback: use feature engine
            if self.feature_engine and hasattr(self.feature_engine, 'latest_features') and self.feature_engine.latest_features:
                features = self.feature_engine.latest_features
                logger.info("Using feature engine for predictor data")
                return {
                    'current_price': features.get('close', 0),
                    'candles': {},
                    'funding_rate': features.get('funding_rate', 0)
                }
            
            logger.warning("No data source available for predictor")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get market data for predictor: {e}", exc_info=True)
            return None
    
    async def cmd_help(self):
        """Handle /help command"""
        message = f"""
🤖 <b>Core Brain Bot Commands</b>
═══════════════════════════

<b>📊 Trading Commands:</b>

/status - Trạng thái bot
/daily - Kết quả hôm nay
/regime - Phân tích regime

<b>🔮 Predictor Commands:</b>

/predict - Dự đoán ngay
/last_predict - Xem dự đoán gần nhất
/predictor_on - Bật predictor
/predictor_off - Tắt predictor

<b>📱 Other Commands:</b>

/menu - Menu chính
/version - Phiên bản bot
/help - Trợ giúp

───────────────────────────
🤖 Bot 1: Core Brain
🎯 BTC Trading Bot {get_full_version()}
"""
        await self.send_message(message.strip())
    
    async def set_bot_commands(self):
        """Set bot commands menu in Telegram"""
        if not self.enabled or not self.token:
            return False
        
        commands = [
            {"command": "menu", "description": "📱 Hiển thị menu"},
            {"command": "status", "description": "📊 Trạng thái bot"},
            {"command": "daily", "description": "📅 Kết quả hôm nay"},
            {"command": "regime", "description": "📈 Phân tích regime"},
            {"command": "predict", "description": "🔮 Dự đoán BTC"},
            {"command": "last_predict", "description": "📊 Dự đoán gần nhất"},
            {"command": "version", "description": "📦 Phiên bản bot"},
            {"command": "help", "description": "❓ Trợ giúp"},
        ]
        
        try:
            session = await self._get_session()
            url = f"{self.base_url}/setMyCommands"
            data = {"commands": commands}
            
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    logger.info("✅ Bot commands menu updated successfully")
                    return True
                else:
                    error = await response.text()
                    logger.error(f"Failed to set bot commands: {error}")
                    return False
        except Exception as e:
            logger.error(f"Error setting bot commands: {e}")
            return False
    
    async def start_polling(self):
        """Start polling for commands"""
        logger.info(f"=== START POLLING ===")
        logger.info(f"Enabled: {self.enabled}")
        logger.info(f"Token: {self.token[:10]}..." if self.token else "Token: None")
        logger.info(f"Chat ID: {self.chat_id}")
        
        if not self.enabled or not self.token:
            logger.info("Command handler disabled or not configured")
            return
        
        # Set bot commands menu on startup
        await self.set_bot_commands()
        
        self._running = True
        logger.info("🎮 Telegram command handler started (polling mode)")
        
        while self._running:
            try:
                updates = await self.get_updates()
                
                for update in updates:
                    self._last_update_id = update.get("update_id", 0)
                    
                    # Handle regular messages/commands
                    message = update.get("message", {})
                    text = message.get("text", "")
                    
                    if text.startswith("/"):
                        logger.info(f"Received command: {text}")
                        await self.handle_command(text, message)
                    
                    # Handle callback queries (inline button clicks)
                    callback_query = update.get("callback_query")
                    if callback_query:
                        logger.info(f"Received callback: {callback_query.get('data')}")
                        await self.handle_callback(callback_query)
                
                # Small delay to avoid hammering the API
                if not updates:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(5)
        
        logger.info("Telegram command handler stopped")

