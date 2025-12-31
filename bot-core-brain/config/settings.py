"""
Bot 1: Core Brain - Configuration Settings
BTC Trading Bot v5.0
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TradingConfig:
    """Fixed trading parameters - v5.0"""

    SYMBOL: str = "BTCUSDT"
    POSITION_MARGIN: float = 150.0  # $150 (30% of $500)
    LEVERAGE: int = 20
    NOTIONAL_VALUE: float = 3000.0  # $150 × 20

    TP_PERCENT: float = 0.005  # 0.5% = +$15
    SL_PERCENT: float = 0.0025  # 0.25% = -$7.50

    DAILY_TARGET: float = 10.0  # +$10 → STOP
    DAILY_STOP: float = -15.0  # -$15 → STOP
    MAX_TRADES: int = 3  # Max trades per day
    MAX_CONSEC_LOSSES: int = 2  # Wait 1h after 2 losses
    MAX_HOLD_MINUTES: int = 240  # 4 hours timeout

    COOLDOWN_MINUTES: int = 60  # Cooldown after consecutive losses


@dataclass
class APIConfig:
    """API credentials and endpoints"""

    # Binance
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")
    BINANCE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

    # WebSocket endpoints
    BINANCE_WS_URL: str = "wss://fstream.binance.com/ws"
    BINANCE_TESTNET_WS_URL: str = "wss://stream.binancefuture.com/ws"

    # REST endpoints
    BINANCE_REST_URL: str = "https://fapi.binance.com"
    BINANCE_TESTNET_REST_URL: str = "https://testnet.binancefuture.com"

    # On-chain data
    GLASSNODE_API_KEY: str = os.getenv("GLASSNODE_API_KEY", "")
    COINGLASS_API_KEY: str = os.getenv("COINGLASS_API_KEY", "")

    @property
    def ws_url(self) -> str:
        return (
            self.BINANCE_TESTNET_WS_URL if self.BINANCE_TESTNET else self.BINANCE_WS_URL
        )

    @property
    def rest_url(self) -> str:
        return (
            self.BINANCE_TESTNET_REST_URL
            if self.BINANCE_TESTNET
            else self.BINANCE_REST_URL
        )


@dataclass
class DatabaseConfig:
    """Database configuration"""

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://btc_bot:secure_password@localhost:5432/btc_trading_bot",
    )
    USE_SQLITE: bool = os.getenv("USE_SQLITE", "true").lower() == "true"
    SQLITE_PATH: str = os.getenv("SQLITE_PATH", "data/trading_bot.db")


@dataclass
class TelegramConfig:
    """Telegram Bot 1 configuration"""

    TOKEN: str = os.getenv("BOT_1_TELEGRAM_TOKEN", "")
    CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    ENABLED: bool = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"


@dataclass
class AIConfig:
    """AI Model configuration"""

    MODEL_PATH: str = "models/"
    CONFIDENCE_THRESHOLD: float = 0.65  # Minimum 65% confidence
    XGBOOST_WEIGHT: float = 0.40
    LIGHTGBM_WEIGHT: float = 0.40
    LOGISTIC_WEIGHT: float = 0.20
    RETRAIN_INTERVAL_TRADES: int = 50  # Retrain after 50 trades


@dataclass
class GateConfig:
    """5-Gate System thresholds"""

    # Gate 1: Context
    CONTEXT_MIN_SCORE: float = 0.5
    FUNDING_BUFFER_MINUTES: int = 20

    # Gate 2: Regime
    REGIME_CONFIDENCE_MIN: float = 0.65
    EXHAUSTION_RISK_MAX: float = 0.5
    STRUCTURE_QUALITY_MIN: float = 0.6

    # Gate 3: Signal Quality
    SETUP_QUALITY_MIN: int = 70
    MTF_CONFLUENCE_MIN: int = 2  # 2/3 timeframes
    HISTORICAL_WIN_RATE_MIN: float = 0.5

    # Gate 4: AI Confirmation
    AI_CONFIDENCE_MIN: float = 0.65
    MAX_RISK_FACTORS: int = 1
    MODEL_AGREEMENT_MIN: float = 0.65


class Settings:
    """Main settings container"""

    trading = TradingConfig()
    api = APIConfig()
    database = DatabaseConfig()
    telegram = TelegramConfig()
    ai = AIConfig()
    gates = GateConfig()

    # Timeframes used
    TIMEFRAMES = ["1m", "3m", "5m", "15m"]

    # Feature count
    TOTAL_FEATURES = 100

    # Loop intervals
    MAIN_LOOP_INTERVAL: int = 60  # seconds
    HEARTBEAT_INTERVAL: int = 30  # seconds


settings = Settings()
