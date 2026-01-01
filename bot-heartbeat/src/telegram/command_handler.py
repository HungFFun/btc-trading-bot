"""
Telegram Command Handler for Bot 2 (Heartbeat Monitor)
Handles interactive commands: /health, /today, /version
"""

import asyncio
import json
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
import aiohttp

from config.version import get_version, get_full_version, CURRENT_VERSION

logger = logging.getLogger(__name__)


class TelegramCommandHandler:
    """Handle incoming Telegram commands for Heartbeat bot"""

    def __init__(self, token: str, chat_id: str, db_repository, enabled: bool = True):
        self.token = token
        self.chat_id = chat_id
        self.db = db_repository
        self.enabled = enabled
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

    async def send_message(
        self, text: str, parse_mode: str = "HTML", reply_markup: dict = None
    ) -> bool:
        """Send a message to the chat"""
        if not self.enabled or not self.token or not self.chat_id:
            logger.warning("Telegram disabled or not configured")
            return False

        try:
            session = await self._get_session()
            url = f"{self.base_url}/sendMessage"
            data = {"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode}

            if reply_markup:
                # DO NOT use json.dumps here - aiohttp's json= handles serialization
                data["reply_markup"] = reply_markup

            logger.info(
                f"Sending message to Telegram (chat_id={self.chat_id}): {text[:50]}..."
            )
            logger.info(f"Data being sent: {data}")

            async with session.post(url, json=data) as response:
                response_text = await response.text()
                if response.status == 200:
                    logger.info("Message sent successfully")
                    return True
                else:
                    logger.error(
                        f"Telegram send error (status={response.status}): {response_text}"
                    )
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
                "allowed_updates": ["message", "callback_query"],
            }

            async with session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=timeout + 5)
            ) as response:
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
            logger.warning(
                f"Ignoring command from unauthorized chat: {chat_id} (expected: {self.chat_id})"
            )
            return

        command = command.lower().strip().split("@")[0]  # Remove @botname if present
        logger.info(f"Processed command: {command}")

        if command == "/health":
            await self.cmd_health()
        elif command == "/today":
            await self.cmd_today()
        elif command == "/version":
            await self.cmd_version()
        elif command == "/help":
            await self.cmd_help()
        elif command == "/start" or command == "/menu":
            logger.info("Calling cmd_menu()")
            await self.cmd_menu()
        else:
            await self.send_message(
                f"❓ Unknown command: {command}\n\nUse /menu to see available commands."
            )

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
        if data == "health":
            await self.cmd_health()
        elif data == "today":
            await self.cmd_today()
        elif data == "version":
            await self.cmd_version()
        elif data == "help":
            await self.cmd_help()
        elif data == "menu":
            await self.cmd_menu()

    async def cmd_menu(self):
        """Show interactive menu with inline buttons"""
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

        message = f"""
💓 <b>BTC Trading Bot - Heartbeat</b>
═══════════════════════════

📦 Version: <code>{get_full_version()}</code>

<b>Chọn một trong các tùy chọn bên dưới:</b>
"""
        await self.send_message(message.strip(), reply_markup=keyboard)

    async def cmd_health(self):
        """Handle /health command"""
        try:
            health = self.db.check_heartbeat_status(
                timeout_minutes=3, critical_minutes=10
            )

            status = health.get("status", "UNKNOWN")
            message_text = health.get("message", "No data")
            last_seen = health.get("last_seen")
            minutes_ago = health.get("minutes_ago", 0)
            bot_status = health.get("bot_status", "Unknown")
            error = health.get("error")

            status_emoji = {
                "HEALTHY": "✅",
                "WARNING": "⚠️",
                "CRITICAL": "🚨",
                "UNKNOWN": "❓",
            }.get(status, "❓")

            message = f"""
🏥 <b>BOT HEALTH STATUS</b>
═══════════════════════════

{status_emoji} <b>Overall Status: {status}</b>

🤖 <b>Core Brain (Bot 1):</b>
├── Status: {bot_status}
├── Last Seen: {last_seen.strftime('%H:%M:%S') if last_seen else 'Never'}
└── Time Since: {minutes_ago:.0f} minutes ago

📊 <b>Health Check:</b>
└── {message_text}
"""

            if error:
                message += f"\n⚠️ <b>Error:</b>\n└── {error}"

            if status == "HEALTHY":
                message += "\n\n✅ All systems operational!"
            elif status == "WARNING":
                message += "\n\n⚠️ Bot 1 may be experiencing issues."
            elif status == "CRITICAL":
                message += "\n\n🚨 Bot 1 is DOWN! Immediate attention required!"

            # Check pending signals
            pending = self.db.get_pending_signals()
            if pending:
                message += f"\n\n🔄 <b>Active Signals:</b>\n└── {len(pending)} pending signal(s)"

            message += f"\n\n⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC"

            await self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error in cmd_health: {e}")
            await self.send_message(f"❌ Error fetching health status: {str(e)}")

    async def cmd_today(self):
        """Handle /today command"""
        try:
            daily_state = self.db.get_daily_state()

            # Get signals for today
            today_start = datetime.combine(date.today(), datetime.min.time())
            signals = self.db.get_signals_for_period(today_start)

            # Count by status
            wins = sum(1 for s in signals if s.status == "WIN")
            losses = sum(1 for s in signals if s.status == "LOSS")
            timeouts = sum(1 for s in signals if s.status == "TIMEOUT")
            pending = sum(1 for s in signals if s.status == "PENDING")

            win_rate = (
                (wins / daily_state.trade_count * 100)
                if daily_state.trade_count > 0
                else 0
            )

            # Calculate average trade IQ
            completed_signals = [
                s
                for s in signals
                if s.trade_iq and s.status in ["WIN", "LOSS", "TIMEOUT"]
            ]
            avg_iq = (
                sum(s.trade_iq for s in completed_signals) / len(completed_signals)
                if completed_signals
                else 0
            )

            status_emoji = {
                "ACTIVE": "🟢",
                "TARGET_HIT": "🎯",
                "STOP_HIT": "⛔",
                "MAX_TRADES": "📊",
            }.get(daily_state.status, "⚪")

            message = f"""
📊 <b>TODAY'S RESULTS</b> - {date.today().isoformat()}
═══════════════════════════

💰 <b>Performance:</b>
├── PnL: ${daily_state.pnl:+.2f}
├── Target: +$10.00
├── Progress: {(daily_state.pnl / 10 * 100):.0f}% to target
└── Status: {status_emoji} {daily_state.status}

📈 <b>Trade Summary:</b>
├── Total: {daily_state.trade_count}/3
├── ✅ Wins: {wins}
├── ❌ Losses: {losses}
├── ⏱️ Timeouts: {timeouts}
└── 🔄 Pending: {pending}

📊 <b>Statistics:</b>
├── Win Rate: {win_rate:.0f}%
├── Avg Trade IQ: {avg_iq:.0f}/100
└── Consec. Losses: {daily_state.consecutive_losses}
"""

            # Show trade details if any
            if completed_signals:
                message += "\n\n📋 <b>Trade History:</b>"
                for i, signal in enumerate(completed_signals[-3:], 1):  # Last 3 trades
                    result_emoji = (
                        "✅"
                        if signal.status == "WIN"
                        else "❌" if signal.status == "LOSS" else "⏱️"
                    )
                    direction_emoji = "🟢" if signal.direction == "LONG" else "🔴"
                    message += f"\n{i}. {result_emoji} {direction_emoji} {signal.direction} - ${signal.result_pnl:+.2f} (IQ: {signal.trade_iq or 0})"

            # Status message
            if daily_state.status == "TARGET_HIT":
                message += "\n\n🎯 <b>Target Hit!</b> Great job today!"
            elif daily_state.status == "STOP_HIT":
                message += "\n\n⛔ Stop hit. Tomorrow is a new day! 💪"
            elif daily_state.trade_count >= 3:
                message += "\n\n📊 Max trades reached. Done for today!"
            else:
                remaining = 3 - daily_state.trade_count
                to_target = 10 - daily_state.pnl
                message += f"\n\n🚀 <b>Still Active!</b>"
                message += f"\n├── {remaining} trade{'s' if remaining > 1 else ''} left"
                message += f"\n└── ${to_target:.2f} to target"

            message += f"\n\n⏰ {datetime.utcnow().strftime('%H:%M:%S')} UTC"

            await self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error in cmd_today: {e}")
            await self.send_message(f"❌ Error fetching today's results: {str(e)}")

    async def cmd_version(self):
        """Handle /version command"""
        try:
            message = f"""
💓 <b>Heartbeat Monitor</b>
└── Version: <code>{CURRENT_VERSION.full_version}</code>
"""
            await self.send_message(message.strip())

        except Exception as e:
            logger.error(f"Error in cmd_version: {e}")
            await self.send_message(f"❌ Error fetching version: {str(e)}")

    async def cmd_help(self):
        """Handle /help command"""
        message = f"""
💓 <b>Heartbeat Bot Commands</b>
═══════════════════════════

<b>Available Commands:</b>

🏥 <b>/health</b>
└── Check Bot 1 health status

📊 <b>/today</b>
└── Today's trading results & statistics

📦 <b>/version</b>
└── Show bot version and changelog

❓ <b>/help</b>
└── Show this help message

───────────────────────────
💓 Bot 2: Heartbeat Monitor
🎯 BTC Trading Bot {get_full_version()}
"""
        await self.send_message(message.strip())

    async def set_bot_commands(self):
        """Set bot commands menu in Telegram"""
        if not self.enabled or not self.token:
            return False

        commands = [
            {"command": "menu", "description": "📱 Hiển thị menu"},
            {"command": "health", "description": "🏥 Kiểm tra sức khỏe bot"},
            {"command": "today", "description": "📊 Kết quả hôm nay"},
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
