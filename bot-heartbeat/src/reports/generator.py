"""
Report Generator - Generate daily/weekly reports
"""
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DailyReport:
    """Daily performance report"""
    date: str
    status: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    pnl: float
    avg_iq: float
    best_trade: Optional[Dict]
    worst_trade: Optional[Dict]
    account_balance: float


@dataclass
class WeeklyReport:
    """Weekly performance report"""
    start_date: str
    end_date: str
    total_trades: int
    total_wins: int
    total_losses: int
    win_rate: float
    total_pnl: float
    avg_daily_pnl: float
    avg_iq: float
    best_day: Optional[Dict]
    worst_day: Optional[Dict]
    target_hit_days: int
    stop_hit_days: int


class ReportGenerator:
    """
    Generate trading reports.
    
    Report types:
    - Daily Report (00:00 UTC)
    - Weekly Report (Sunday)
    - Monthly Report (End of month)
    """
    
    def __init__(self, db_repository, initial_balance: float = 500.0):
        self.db = db_repository
        self.initial_balance = initial_balance
    
    def generate_daily_report(self, target_date: str = None) -> DailyReport:
        """Generate daily report"""
        if target_date is None:
            # Yesterday's report
            target_date = (date.today() - timedelta(days=1)).isoformat()
        
        # Get signals for the day
        start = datetime.strptime(target_date, "%Y-%m-%d")
        end = start + timedelta(days=1)
        signals = self.db.get_signals_for_period(start, end)
        
        # Get daily state
        daily_state = self.db.get_daily_state(target_date)
        
        # Calculate metrics
        wins = sum(1 for s in signals if s.status == "WIN")
        losses = sum(1 for s in signals if s.status == "LOSS")
        total = wins + losses
        
        win_rate = wins / total if total > 0 else 0
        total_pnl = sum(s.result_pnl or 0 for s in signals)
        
        # Calculate average IQ
        iqs = [s.trade_iq for s in signals if s.trade_iq]
        avg_iq = sum(iqs) / len(iqs) if iqs else 0
        
        # Find best/worst trades
        if signals:
            best = max(signals, key=lambda s: s.result_pnl or 0)
            worst = min(signals, key=lambda s: s.result_pnl or 0)
            
            best_trade = {
                'signal_id': best.signal_id,
                'pnl': best.result_pnl,
                'strategy': best.strategy,
                'iq': best.trade_iq
            }
            worst_trade = {
                'signal_id': worst.signal_id,
                'pnl': worst.result_pnl,
                'strategy': worst.strategy,
                'iq': worst.trade_iq
            }
        else:
            best_trade = None
            worst_trade = None
        
        # Get status
        if daily_state:
            status = daily_state.status
        else:
            status = "NO_DATA"
        
        # Calculate account balance (simplified)
        account_balance = self.initial_balance + total_pnl
        
        return DailyReport(
            date=target_date,
            status=status,
            trades=total,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            pnl=total_pnl,
            avg_iq=avg_iq,
            best_trade=best_trade,
            worst_trade=worst_trade,
            account_balance=account_balance
        )
    
    def generate_weekly_report(self, end_date: str = None) -> WeeklyReport:
        """Generate weekly report"""
        if end_date is None:
            end_date = date.today().isoformat()
        
        end = datetime.strptime(end_date, "%Y-%m-%d")
        start = end - timedelta(days=7)
        start_date = start.strftime("%Y-%m-%d")
        
        # Get all signals for the week
        signals = self.db.get_signals_for_period(start, end)
        
        # Calculate metrics
        wins = sum(1 for s in signals if s.status == "WIN")
        losses = sum(1 for s in signals if s.status == "LOSS")
        total = wins + losses
        
        win_rate = wins / total if total > 0 else 0
        total_pnl = sum(s.result_pnl or 0 for s in signals)
        
        # Calculate average IQ
        iqs = [s.trade_iq for s in signals if s.trade_iq]
        avg_iq = sum(iqs) / len(iqs) if iqs else 0
        
        # Get daily stats
        daily_stats = self.db.get_stats_for_period(start_date, end_date)
        
        # Find best/worst days
        if daily_stats:
            best_day_stat = max(daily_stats, key=lambda s: s.total_pnl or 0)
            worst_day_stat = min(daily_stats, key=lambda s: s.total_pnl or 0)
            
            best_day = {
                'date': best_day_stat.date,
                'pnl': best_day_stat.total_pnl,
                'trades': best_day_stat.total_signals
            }
            worst_day = {
                'date': worst_day_stat.date,
                'pnl': worst_day_stat.total_pnl,
                'trades': worst_day_stat.total_signals
            }
            
            target_hit_days = sum(1 for s in daily_stats if s.target_hit)
            stop_hit_days = sum(1 for s in daily_stats if s.stop_hit)
        else:
            best_day = None
            worst_day = None
            target_hit_days = 0
            stop_hit_days = 0
        
        avg_daily = total_pnl / 7
        
        return WeeklyReport(
            start_date=start_date,
            end_date=end_date,
            total_trades=total,
            total_wins=wins,
            total_losses=losses,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_daily_pnl=avg_daily,
            avg_iq=avg_iq,
            best_day=best_day,
            worst_day=worst_day,
            target_hit_days=target_hit_days,
            stop_hit_days=stop_hit_days
        )
    
    def save_daily_stats(self, report: DailyReport):
        """Save daily stats to database"""
        from ..database.models import DailyStats
        
        stats = DailyStats(
            date=report.date,
            total_signals=report.trades,
            wins=report.wins,
            losses=report.losses,
            win_rate=report.win_rate,
            total_pnl=report.pnl,
            avg_trade_iq=int(report.avg_iq),
            account_balance=report.account_balance,
            target_hit=report.status == "TARGET_HIT",
            stop_hit=report.status == "STOP_HIT"
        )
        
        self.db.save_daily_stats(stats)

