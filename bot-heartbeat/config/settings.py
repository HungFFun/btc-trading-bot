"""
Bot 2: Heartbeat Monitor - Configuration Settings
BTC Trading Bot v5.0
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration (same as Bot 1)"""
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://btc_bot:secure_password@localhost:5432/btc_trading_bot"
    )
    USE_SQLITE: bool = os.getenv("USE_SQLITE", "true").lower() == "true"
    SQLITE_PATH: str = os.getenv("SQLITE_PATH", "../bot-core-brain/data/trading_bot.db")


@dataclass
class TelegramConfig:
    """Telegram Bot 2 configuration"""
    TOKEN: str = os.getenv("BOT_2_TELEGRAM_TOKEN", "")
    CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    ENABLED: bool = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"


@dataclass
class PriceConfig:
    """Price API configuration"""
    BINANCE_REST_URL: str = "https://fapi.binance.com"
    BINANCE_TESTNET_REST_URL: str = "https://testnet.binancefuture.com"
    USE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
    SYMBOL: str = "BTCUSDT"
    
    @property
    def rest_url(self) -> str:
        return self.BINANCE_TESTNET_REST_URL if self.USE_TESTNET else self.BINANCE_REST_URL


@dataclass
class MonitoringConfig:
    """Monitoring thresholds"""
    # Health monitoring
    HEALTH_CHECK_INTERVAL: int = 60  # seconds
    HEARTBEAT_TIMEOUT: int = 180  # 3 minutes - warning
    HEARTBEAT_CRITICAL: int = 600  # 10 minutes - critical
    
    # Signal tracking
    SIGNAL_CHECK_INTERVAL: int = 30  # seconds
    MAX_HOLD_MINUTES: int = 240  # 4 hours timeout
    
    # Daily limits
    DAILY_TARGET: float = 10.0  # +$10
    DAILY_STOP: float = -15.0  # -$15
    MAX_TRADES: int = 3
    
    # Trade parameters
    TP_PERCENT: float = 0.005  # 0.5%
    SL_PERCENT: float = 0.0025  # 0.25%
    WIN_AMOUNT: float = 15.0  # +$15
    LOSS_AMOUNT: float = -7.50  # -$7.50


@dataclass
class IQConfig:
    """Bot IQ calculation settings"""
    # Weights
    DECISION_WEIGHT: float = 0.45
    EXECUTION_WEIGHT: float = 0.30
    RISK_WEIGHT: float = 0.25
    
    # Thresholds
    IQ_WARNING_THRESHOLD: int = 60
    IQ_CRITICAL_THRESHOLD: int = 50
    IQ_CHECK_TRADES: int = 10  # Check last N trades


@dataclass
class ReportConfig:
    """Report generation settings"""
    DAILY_REPORT_HOUR: int = 0  # 00:00 UTC
    WEEKLY_REPORT_DAY: int = 6  # Sunday


class Settings:
    """Main settings container"""
    database = DatabaseConfig()
    telegram = TelegramConfig()
    price = PriceConfig()
    monitoring = MonitoringConfig()
    iq = IQConfig()
    report = ReportConfig()


settings = Settings()

