"""
Database Models - Bot 2 (Copy of Bot 1 models for independence)
"""

from datetime import datetime
from typing import Optional
import os

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    JSON,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Signal(Base):
    """Trading signals table"""

    __tablename__ = "signals"

    signal_id = Column(String(50), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Signal details
    direction = Column(String(10), nullable=False)
    strategy = Column(String(50), nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    position_margin = Column(Float, nullable=False, default=150.0)
    leverage = Column(Integer, nullable=False, default=20)

    # Quality metrics
    confidence = Column(Float, nullable=False)
    setup_quality = Column(Integer, nullable=False)
    regime = Column(String(50), nullable=False)
    reasoning = Column(Text)

    # Gate scores
    gate_1_score = Column(Float)
    gate_2_score = Column(Float)
    gate_3_score = Column(Float)
    gate_4_score = Column(Float)
    gate_5_passed = Column(Boolean)

    # Result (Bot 2 writes)
    status = Column(String(20), default="PENDING")
    result_price = Column(Float)
    result_time = Column(DateTime)
    result_pnl = Column(Float)
    result_reason = Column(String(50))

    # MFE/MAE
    mfe = Column(Float)
    mae = Column(Float)
    duration_minutes = Column(Integer)

    # Trade IQ
    trade_iq = Column(Integer)

    # Learning
    result_analyzed = Column(Boolean, default=False)
    lesson_id = Column(String(50))

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    price_tracking = relationship("PriceTracking", back_populates="signal")


class DailyState(Base):
    """Daily trading state"""

    __tablename__ = "daily_state"

    date = Column(String(10), primary_key=True)
    pnl = Column(Float, default=0.0)
    trade_count = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    consecutive_losses = Column(Integer, default=0)
    has_position = Column(Boolean, default=False)
    status = Column(String(20), default="ACTIVE")
    target_hit_at = Column(DateTime)
    stop_hit_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Heartbeat(Base):
    """Heartbeat pings from Bot 1"""

    __tablename__ = "heartbeat"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_name = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(20), nullable=False)
    signals_today = Column(Integer)
    current_regime = Column(String(50))
    daily_pnl = Column(Float)
    error_message = Column(Text)

    __table_args__ = (Index("idx_heartbeat_bot_time", "bot_name", timestamp.desc()),)


class PriceTracking(Base):
    """Price tracking for MFE/MAE calculation"""

    __tablename__ = "price_tracking"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(String(50), ForeignKey("signals.signal_id"))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    price = Column(Float, nullable=False)

    signal = relationship("Signal", back_populates="price_tracking")


class DailyStats(Base):
    """Daily performance statistics"""

    __tablename__ = "daily_stats"

    date = Column(String(10), primary_key=True)
    total_signals = Column(Integer)
    wins = Column(Integer)
    losses = Column(Integer)
    win_rate = Column(Float)
    total_pnl = Column(Float)
    avg_trade_iq = Column(Integer)
    account_balance = Column(Float)
    target_hit = Column(Boolean)
    stop_hit = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_database(
    database_url: str, use_sqlite: bool = True, sqlite_path: str = "data/trading_bot.db"
):
    """Initialize database connection and create tables"""
    if use_sqlite:
        os.makedirs(
            os.path.dirname(sqlite_path) if os.path.dirname(sqlite_path) else ".",
            exist_ok=True,
        )
        database_url = f"sqlite:///{sqlite_path}"
    else:
        # If not using SQLite, ensure we have a valid DATABASE_URL
        if not database_url or database_url.strip() == "":
            database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://btc_bot:secure_password@localhost:5432/btc_trading_bot",
            )

    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    return engine, Session
