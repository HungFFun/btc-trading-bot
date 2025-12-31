"""
Database Models - Shared between Bot 1 and Bot 2
SQLAlchemy ORM models matching the design schema
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    Text, ForeignKey, Index, JSON, Enum as SQLEnum,
    create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class SignalStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    WIN = "WIN"
    LOSS = "LOSS"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class DailyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    TARGET_HIT = "TARGET_HIT"
    STOP_HIT = "STOP_HIT"
    MAX_TRADES = "MAX_TRADES"


class Signal(Base):
    """Trading signals table"""
    __tablename__ = "signals"
    
    signal_id = Column(String(50), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Signal details (Bot 1 writes)
    direction = Column(String(10), nullable=False)  # LONG, SHORT
    strategy = Column(String(50), nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    position_margin = Column(Float, nullable=False, default=150.0)
    leverage = Column(Integer, nullable=False, default=20)
    
    # Quality metrics (Bot 1 writes)
    confidence = Column(Float, nullable=False)
    setup_quality = Column(Integer, nullable=False)
    regime = Column(String(50), nullable=False)
    reasoning = Column(Text)
    
    # Gate scores (Bot 1 writes)
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
    
    # MFE/MAE (Bot 2 writes)
    mfe = Column(Float)  # Max Favorable Excursion
    mae = Column(Float)  # Max Adverse Excursion
    duration_minutes = Column(Integer)
    
    # Trade IQ (Bot 2 writes)
    trade_iq = Column(Integer)
    
    # Learning (Bot 1 writes after result)
    result_analyzed = Column(Boolean, default=False)
    lesson_id = Column(String(50))
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    feature_snapshot = relationship("FeatureSnapshot", back_populates="signal", uselist=False)
    price_tracking = relationship("PriceTracking", back_populates="signal")


class FeatureSnapshot(Base):
    """Feature snapshots at signal creation time"""
    __tablename__ = "feature_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(String(50), ForeignKey("signals.signal_id"))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Technical features
    rsi_14 = Column(Float)
    ema_9 = Column(Float)
    ema_21 = Column(Float)
    ema_50 = Column(Float)
    macd_histogram = Column(Float)
    atr_14 = Column(Float)
    adx = Column(Float)
    bb_position = Column(Float)
    
    # Volume features
    volume_ratio = Column(Float)
    cvd = Column(Float)
    
    # On-chain features
    exchange_netflow = Column(Float)
    whale_activity = Column(Float)
    funding_rate = Column(Float)
    
    # Liquidation features
    long_liq_density = Column(Float)
    short_liq_density = Column(Float)
    
    # All features as JSON
    all_features = Column(JSON)
    
    # Relationship
    signal = relationship("Signal", back_populates="feature_snapshot")


class DailyState(Base):
    """Daily trading state"""
    __tablename__ = "daily_state"
    
    date = Column(String(10), primary_key=True)  # YYYY-MM-DD
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
    status = Column(String(20), nullable=False)  # running, waiting, error, daily_limit
    signals_today = Column(Integer)
    current_regime = Column(String(50))
    daily_pnl = Column(Float)
    error_message = Column(Text)
    
    __table_args__ = (
        Index('idx_heartbeat_bot_time', 'bot_name', timestamp.desc()),
    )


class PriceTracking(Base):
    """Price tracking for MFE/MAE calculation"""
    __tablename__ = "price_tracking"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(String(50), ForeignKey("signals.signal_id"))
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    price = Column(Float, nullable=False)
    
    signal = relationship("Signal", back_populates="price_tracking")


class Lesson(Base):
    """Lessons learned from trading patterns"""
    __tablename__ = "lessons"
    
    lesson_id = Column(String(50), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    signal_ids = Column(JSON)  # List of signal IDs
    pattern_type = Column(String(100))
    observation = Column(Text, nullable=False)
    conclusion = Column(Text)
    action_suggested = Column(Text)
    sample_size = Column(Integer)
    confidence = Column(Float)
    validated = Column(Boolean, default=False)


class DailyStats(Base):
    """Daily performance statistics"""
    __tablename__ = "daily_stats"
    
    date = Column(String(10), primary_key=True)  # YYYY-MM-DD
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


def init_database(database_url: str, use_sqlite: bool = True, sqlite_path: str = "data/trading_bot.db"):
    """Initialize database connection and create tables"""
    import os
    
    if use_sqlite:
        # Ensure directory exists
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
        database_url = f"sqlite:///{sqlite_path}"
    
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    return engine, Session

