"""
Database Repository - Bot 2 Operations
Shares models with Bot 1
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import os

Base = declarative_base()

# Import shared models (will be created as copies for independence)
from .models import (
    Signal, DailyState, Heartbeat, DailyStats, PriceTracking,
    init_database
)


class DatabaseRepository:
    """Database operations for Bot 2 (Heartbeat Monitor)"""
    
    def __init__(self, database_url: str = None, use_sqlite: bool = True, sqlite_path: str = "data/trading_bot.db"):
        self.engine, self.SessionLocal = init_database(
            database_url or "",
            use_sqlite,
            sqlite_path
        )
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    # ==================== Health Monitoring ====================
    
    def get_last_heartbeat(self, bot_name: str = "core_brain") -> Optional[Heartbeat]:
        """Get last heartbeat from Bot 1"""
        with self.get_session() as session:
            heartbeat = session.query(Heartbeat).filter(
                Heartbeat.bot_name == bot_name
            ).order_by(desc(Heartbeat.timestamp)).first()
            
            if heartbeat:
                session.expunge(heartbeat)
            return heartbeat
    
    def check_heartbeat_status(self, timeout_minutes: int = 3, critical_minutes: int = 10) -> Dict[str, Any]:
        """Check Bot 1 health status"""
        heartbeat = self.get_last_heartbeat()
        
        if not heartbeat:
            return {
                'status': 'UNKNOWN',
                'message': 'No heartbeat found',
                'last_seen': None,
                'minutes_ago': None
            }
        
        now = datetime.utcnow()
        time_diff = now - heartbeat.timestamp
        minutes_ago = time_diff.total_seconds() / 60
        
        if minutes_ago > critical_minutes:
            status = 'CRITICAL'
            message = f'Bot 1 DOWN! No heartbeat for {minutes_ago:.0f} minutes'
        elif minutes_ago > timeout_minutes:
            status = 'WARNING'
            message = f'Bot 1 not responding ({minutes_ago:.0f} minutes)'
        else:
            status = 'HEALTHY'
            message = f'Bot 1 running ({heartbeat.status})'
        
        return {
            'status': status,
            'message': message,
            'last_seen': heartbeat.timestamp,
            'minutes_ago': minutes_ago,
            'bot_status': heartbeat.status,
            'error': heartbeat.error_message
        }
    
    # ==================== Signal Tracking ====================
    
    def get_pending_signals(self) -> List[Signal]:
        """Get all pending signals (not yet resolved)"""
        with self.get_session() as session:
            signals = session.query(Signal).filter(
                Signal.status == "PENDING"
            ).order_by(Signal.created_at).all()
            
            for s in signals:
                session.expunge(s)
            return signals
    
    def update_signal_result(
        self,
        signal_id: str,
        status: str,
        result_price: float,
        result_pnl: float,
        result_reason: str,
        mfe: float = 0,
        mae: float = 0,
        duration_minutes: int = 0,
        trade_iq: int = 0
    ):
        """Update signal with result"""
        with self.get_session() as session:
            signal = session.query(Signal).filter(
                Signal.signal_id == signal_id
            ).first()
            
            if signal:
                signal.status = status
                signal.result_price = result_price
                signal.result_time = datetime.utcnow()
                signal.result_pnl = result_pnl
                signal.result_reason = result_reason
                signal.mfe = mfe
                signal.mae = mae
                signal.duration_minutes = duration_minutes
                signal.trade_iq = trade_iq
                signal.updated_at = datetime.utcnow()
                
                session.commit()
    
    def add_price_tracking(self, signal_id: str, price: float):
        """Add price tracking entry for MFE/MAE calculation"""
        tracking = PriceTracking(
            signal_id=signal_id,
            timestamp=datetime.utcnow(),
            price=price
        )
        
        with self.get_session() as session:
            session.add(tracking)
            session.commit()
    
    def get_price_history(self, signal_id: str) -> List[PriceTracking]:
        """Get price history for a signal"""
        with self.get_session() as session:
            history = session.query(PriceTracking).filter(
                PriceTracking.signal_id == signal_id
            ).order_by(PriceTracking.timestamp).all()
            
            for h in history:
                session.expunge(h)
            return history
    
    # ==================== Daily State ====================
    
    def get_daily_state(self, target_date: str = None) -> Optional[DailyState]:
        """Get daily state"""
        if target_date is None:
            target_date = date.today().isoformat()
        
        with self.get_session() as session:
            state = session.query(DailyState).filter(
                DailyState.date == target_date
            ).first()
            
            if state is None:
                state = DailyState(date=target_date)
                session.add(state)
                session.commit()
                session.refresh(state)
            
            session.expunge(state)
            return state
    
    def update_daily_state(
        self,
        pnl_change: float,
        is_win: bool,
        clear_position: bool = True
    ) -> DailyState:
        """Update daily state with trade result"""
        target_date = date.today().isoformat()
        
        with self.get_session() as session:
            state = session.query(DailyState).filter(
                DailyState.date == target_date
            ).first()
            
            if state:
                state.pnl += pnl_change
                
                if is_win:
                    state.wins += 1
                    state.consecutive_losses = 0
                else:
                    state.losses += 1
                    state.consecutive_losses += 1
                
                if clear_position:
                    state.has_position = False
                
                # Check limits
                if state.pnl >= 10:
                    state.status = "TARGET_HIT"
                    state.target_hit_at = datetime.utcnow()
                elif state.pnl <= -15:
                    state.status = "STOP_HIT"
                    state.stop_hit_at = datetime.utcnow()
                elif state.trade_count >= 3:
                    state.status = "MAX_TRADES"
                
                state.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(state)
                session.expunge(state)
                return state
            
            return None
    
    def reset_daily_state(self, target_date: str = None) -> DailyState:
        """Reset daily state for new day"""
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
    
    # ==================== Statistics ====================
    
    def save_daily_stats(self, stats: DailyStats):
        """Save daily statistics"""
        with self.get_session() as session:
            existing = session.query(DailyStats).filter(
                DailyStats.date == stats.date
            ).first()
            
            if existing:
                for key, value in vars(stats).items():
                    if not key.startswith('_'):
                        setattr(existing, key, value)
            else:
                session.add(stats)
            
            session.commit()
    
    def get_recent_signals(self, limit: int = 50) -> List[Signal]:
        """Get recent signals for analysis"""
        with self.get_session() as session:
            signals = session.query(Signal).filter(
                Signal.status.in_(["WIN", "LOSS", "TIMEOUT"])
            ).order_by(desc(Signal.result_time)).limit(limit).all()
            
            for s in signals:
                session.expunge(s)
            return signals
    
    def get_signals_for_period(
        self, 
        start_date: datetime, 
        end_date: datetime = None
    ) -> List[Signal]:
        """Get signals for a date range"""
        if end_date is None:
            end_date = datetime.utcnow()
        
        with self.get_session() as session:
            signals = session.query(Signal).filter(
                Signal.created_at >= start_date,
                Signal.created_at <= end_date
            ).order_by(Signal.created_at).all()
            
            for s in signals:
                session.expunge(s)
            return signals
    
    def get_stats_for_period(
        self, 
        start_date: str, 
        end_date: str = None
    ) -> List[DailyStats]:
        """Get daily stats for a period"""
        if end_date is None:
            end_date = date.today().isoformat()
        
        with self.get_session() as session:
            stats = session.query(DailyStats).filter(
                DailyStats.date >= start_date,
                DailyStats.date <= end_date
            ).order_by(DailyStats.date).all()
            
            for s in stats:
                session.expunge(s)
            return stats

