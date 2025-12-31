"""
Database Repository - Bot 1 Operations
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .models import (
    Signal, FeatureSnapshot, DailyState, Heartbeat, 
    Lesson, init_database, SignalStatus, DailyStatus
)


class DatabaseRepository:
    """Database operations for Bot 1"""
    
    def __init__(self, database_url: str = None, use_sqlite: bool = True, sqlite_path: str = "data/trading_bot.db"):
        self.engine, self.SessionLocal = init_database(
            database_url or "", 
            use_sqlite, 
            sqlite_path
        )
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    # ==================== Daily State ====================
    
    def get_daily_state(self, target_date: str = None) -> Optional[DailyState]:
        """Get daily state for a specific date (default: today)"""
        if target_date is None:
            target_date = date.today().isoformat()
        
        with self.get_session() as session:
            state = session.query(DailyState).filter(
                DailyState.date == target_date
            ).first()
            
            if state is None:
                # Create new daily state
                state = DailyState(date=target_date)
                session.add(state)
                session.commit()
                session.refresh(state)
            
            # Detach from session
            session.expunge(state)
            return state
    
    def update_daily_state(self, state: DailyState) -> None:
        """Update daily state"""
        with self.get_session() as session:
            existing = session.query(DailyState).filter(
                DailyState.date == state.date
            ).first()
            
            if existing:
                existing.pnl = state.pnl
                existing.trade_count = state.trade_count
                existing.wins = state.wins
                existing.losses = state.losses
                existing.consecutive_losses = state.consecutive_losses
                existing.has_position = state.has_position
                existing.status = state.status
                existing.target_hit_at = state.target_hit_at
                existing.stop_hit_at = state.stop_hit_at
                existing.updated_at = datetime.utcnow()
            else:
                session.add(state)
            
            session.commit()
    
    def reset_daily_state(self, target_date: str = None) -> DailyState:
        """Reset daily state (called at 00:00 UTC)"""
        if target_date is None:
            target_date = date.today().isoformat()
        
        with self.get_session() as session:
            state = session.query(DailyState).filter(
                DailyState.date == target_date
            ).first()
            
            if state is None:
                state = DailyState(date=target_date)
                session.add(state)
            else:
                state.pnl = 0.0
                state.trade_count = 0
                state.wins = 0
                state.losses = 0
                state.consecutive_losses = 0
                state.has_position = False
                state.status = "ACTIVE"
                state.target_hit_at = None
                state.stop_hit_at = None
                state.updated_at = datetime.utcnow()
            
            session.commit()
            session.refresh(state)
            session.expunge(state)
            return state
    
    def increment_trade_count(self) -> None:
        """Increment trade count for today"""
        target_date = date.today().isoformat()
        with self.get_session() as session:
            state = session.query(DailyState).filter(
                DailyState.date == target_date
            ).first()
            if state:
                state.trade_count += 1
                state.has_position = True
                session.commit()
    
    # ==================== Signals ====================
    
    def save_signal(self, signal: Signal) -> None:
        """Save a new trading signal"""
        with self.get_session() as session:
            session.add(signal)
            session.commit()
    
    def get_signal(self, signal_id: str) -> Optional[Signal]:
        """Get signal by ID"""
        with self.get_session() as session:
            signal = session.query(Signal).filter(
                Signal.signal_id == signal_id
            ).first()
            if signal:
                session.expunge(signal)
            return signal
    
    def get_pending_signals(self) -> List[Signal]:
        """Get all pending signals"""
        with self.get_session() as session:
            signals = session.query(Signal).filter(
                Signal.status == "PENDING"
            ).all()
            for s in signals:
                session.expunge(s)
            return signals
    
    def get_signals_today(self) -> List[Signal]:
        """Get all signals for today"""
        today = date.today().isoformat()
        with self.get_session() as session:
            signals = session.query(Signal).filter(
                Signal.created_at >= datetime.strptime(today, "%Y-%m-%d")
            ).order_by(desc(Signal.created_at)).all()
            for s in signals:
                session.expunge(s)
            return signals
    
    def get_new_results(self, limit: int = 10) -> List[Signal]:
        """Get recently completed signals that haven't been analyzed"""
        with self.get_session() as session:
            signals = session.query(Signal).filter(
                Signal.status.in_(["WIN", "LOSS", "TIMEOUT"]),
                Signal.result_analyzed == False
            ).order_by(desc(Signal.result_time)).limit(limit).all()
            for s in signals:
                session.expunge(s)
            return signals
    
    def mark_signal_analyzed(self, signal_id: str, lesson_id: str = None) -> None:
        """Mark signal as analyzed by learning engine"""
        with self.get_session() as session:
            signal = session.query(Signal).filter(
                Signal.signal_id == signal_id
            ).first()
            if signal:
                signal.result_analyzed = True
                signal.lesson_id = lesson_id
                session.commit()
    
    # ==================== Feature Snapshots ====================
    
    def save_features_snapshot(self, signal_id: str, features: Dict[str, Any]) -> None:
        """Save feature snapshot for a signal"""
        snapshot = FeatureSnapshot(
            signal_id=signal_id,
            timestamp=datetime.utcnow(),
            rsi_14=features.get('rsi_14'),
            ema_9=features.get('ema_9'),
            ema_21=features.get('ema_21'),
            ema_50=features.get('ema_50'),
            macd_histogram=features.get('macd_histogram'),
            atr_14=features.get('atr_14'),
            adx=features.get('adx'),
            bb_position=features.get('bb_position'),
            volume_ratio=features.get('volume_ratio'),
            cvd=features.get('cvd'),
            exchange_netflow=features.get('exchange_netflow'),
            whale_activity=features.get('whale_activity'),
            funding_rate=features.get('funding_rate'),
            long_liq_density=features.get('long_liq_density'),
            short_liq_density=features.get('short_liq_density'),
            all_features=features
        )
        
        with self.get_session() as session:
            session.add(snapshot)
            session.commit()
    
    # ==================== Heartbeat ====================
    
    def ping_heartbeat(
        self, 
        status: str = "running",
        signals_today: int = 0,
        current_regime: str = None,
        daily_pnl: float = 0.0,
        error_message: str = None
    ) -> None:
        """Send heartbeat ping"""
        heartbeat = Heartbeat(
            bot_name="core_brain",
            timestamp=datetime.utcnow(),
            status=status,
            signals_today=signals_today,
            current_regime=current_regime,
            daily_pnl=daily_pnl,
            error_message=error_message
        )
        
        with self.get_session() as session:
            session.add(heartbeat)
            session.commit()
    
    # ==================== Lessons ====================
    
    def save_lesson(self, lesson: Lesson) -> None:
        """Save a learning lesson"""
        with self.get_session() as session:
            session.add(lesson)
            session.commit()
    
    def get_lessons(self, limit: int = 20) -> List[Lesson]:
        """Get recent lessons"""
        with self.get_session() as session:
            lessons = session.query(Lesson).order_by(
                desc(Lesson.created_at)
            ).limit(limit).all()
            for l in lessons:
                session.expunge(l)
            return lessons
    
    def get_validated_lessons(self) -> List[Lesson]:
        """Get validated lessons for decision making"""
        with self.get_session() as session:
            lessons = session.query(Lesson).filter(
                Lesson.validated == True
            ).all()
            for l in lessons:
                session.expunge(l)
            return lessons

