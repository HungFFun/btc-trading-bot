"""
Daily State Manager - Manage daily trading state
"""
from datetime import datetime, date
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DailyStateSnapshot:
    """Snapshot of daily state"""
    date: str
    pnl: float
    trade_count: int
    wins: int
    losses: int
    consecutive_losses: int
    has_position: bool
    status: str  # ACTIVE, TARGET_HIT, STOP_HIT, MAX_TRADES
    target_hit_at: Optional[datetime] = None
    stop_hit_at: Optional[datetime] = None
    
    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0
    
    @property
    def is_done(self) -> bool:
        return self.status != "ACTIVE"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date,
            'pnl': self.pnl,
            'trade_count': self.trade_count,
            'wins': self.wins,
            'losses': self.losses,
            'consecutive_losses': self.consecutive_losses,
            'has_position': self.has_position,
            'status': self.status,
            'win_rate': self.win_rate
        }


class DailyStateManager:
    """
    Manage daily trading state.
    
    Responsibilities:
    - Track daily PnL
    - Track trade count
    - Check if daily target/stop hit
    - Reset at 00:00 UTC
    """
    
    def __init__(
        self,
        db_repository,
        daily_target: float = 10.0,
        daily_stop: float = -15.0,
        max_trades: int = 3
    ):
        self.db = db_repository
        self.daily_target = daily_target
        self.daily_stop = daily_stop
        self.max_trades = max_trades
        
        self._current_date: Optional[str] = None
    
    def get_current_state(self) -> DailyStateSnapshot:
        """Get current daily state"""
        db_state = self.db.get_daily_state()
        
        return DailyStateSnapshot(
            date=db_state.date,
            pnl=db_state.pnl,
            trade_count=db_state.trade_count,
            wins=db_state.wins,
            losses=db_state.losses,
            consecutive_losses=db_state.consecutive_losses,
            has_position=db_state.has_position,
            status=db_state.status,
            target_hit_at=db_state.target_hit_at,
            stop_hit_at=db_state.stop_hit_at
        )
    
    def update_with_result(self, result) -> DailyStateSnapshot:
        """Update daily state with a trade result"""
        is_win = result.status == "WIN"
        pnl_change = result.result_pnl
        
        logger.info(f"Updating daily state: {'WIN' if is_win else 'LOSS'} ${pnl_change:+.2f}")
        
        db_state = self.db.update_daily_state(
            pnl_change=pnl_change,
            is_win=is_win,
            clear_position=True
        )
        
        if db_state:
            return DailyStateSnapshot(
                date=db_state.date,
                pnl=db_state.pnl,
                trade_count=db_state.trade_count,
                wins=db_state.wins,
                losses=db_state.losses,
                consecutive_losses=db_state.consecutive_losses,
                has_position=db_state.has_position,
                status=db_state.status,
                target_hit_at=db_state.target_hit_at,
                stop_hit_at=db_state.stop_hit_at
            )
        
        return self.get_current_state()
    
    def check_new_day(self) -> bool:
        """Check if it's a new trading day and reset if needed"""
        today = date.today().isoformat()
        
        if self._current_date != today:
            logger.info(f"New trading day: {today}")
            self._current_date = today
            self.db.reset_daily_state(today)
            return True
        
        return False
    
    def check_limits_hit(self, state: DailyStateSnapshot) -> tuple:
        """Check if any daily limits are hit"""
        target_hit = state.pnl >= self.daily_target
        stop_hit = state.pnl <= self.daily_stop
        max_trades_hit = state.trade_count >= self.max_trades
        
        return target_hit, stop_hit, max_trades_hit
    
    def get_progress(self, state: DailyStateSnapshot) -> Dict[str, Any]:
        """Get progress towards daily target"""
        if self.daily_target > 0:
            target_progress = (state.pnl / self.daily_target) * 100
        else:
            target_progress = 0
        
        return {
            'pnl': state.pnl,
            'target': self.daily_target,
            'target_progress': min(100, max(-100, target_progress)),
            'trades_remaining': self.max_trades - state.trade_count,
            'can_trade': state.status == "ACTIVE" and state.trade_count < self.max_trades
        }

