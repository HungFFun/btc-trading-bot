"""
Signal Tracker - Track signal outcomes and calculate MFE/MAE
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class TrackingResult:
    """Result of tracking a signal"""
    signal_id: str
    status: str  # PENDING, WIN, LOSS, TIMEOUT
    entry_price: float
    current_price: float
    result_price: Optional[float] = None
    result_pnl: Optional[float] = None
    result_reason: Optional[str] = None
    mfe: float = 0.0
    mae: float = 0.0
    duration_minutes: int = 0
    changed: bool = False


class SignalTracker:
    """
    Track pending signals and determine outcomes.
    
    Responsibilities:
    - Check if TP/SL hit
    - Track MFE/MAE
    - Handle timeouts
    - Calculate PnL
    """
    
    def __init__(
        self,
        db_repository,
        price_api_url: str = "https://fapi.binance.com",
        symbol: str = "BTCUSDT",
        win_amount: float = 15.0,
        loss_amount: float = -7.50,
        max_hold_minutes: int = 240
    ):
        self.db = db_repository
        self.price_api_url = price_api_url
        self.symbol = symbol
        self.win_amount = win_amount
        self.loss_amount = loss_amount
        self.max_hold_minutes = max_hold_minutes
        
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Track max/min prices for MFE/MAE
        self.price_extremes: Dict[str, Dict[str, float]] = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_current_price(self) -> float:
        """Fetch current BTC price"""
        try:
            session = await self._get_session()
            url = f"{self.price_api_url}/fapi/v1/ticker/price"
            params = {"symbol": self.symbol}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data.get("price", 0))
                return 0
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            return 0
    
    async def check_signals(self) -> List[TrackingResult]:
        """Check all pending signals and return results"""
        results = []
        
        # Get current price
        current_price = await self.get_current_price()
        if current_price == 0:
            logger.warning("Could not fetch current price")
            return results
        
        # Get pending signals
        pending_signals = self.db.get_pending_signals()
        
        for signal in pending_signals:
            result = await self._check_signal(signal, current_price)
            if result:
                results.append(result)
                
                # If status changed, update database
                if result.changed:
                    self.db.update_signal_result(
                        signal_id=result.signal_id,
                        status=result.status,
                        result_price=result.result_price,
                        result_pnl=result.result_pnl,
                        result_reason=result.result_reason,
                        mfe=result.mfe,
                        mae=result.mae,
                        duration_minutes=result.duration_minutes
                    )
        
        return results
    
    async def _check_signal(self, signal, current_price: float) -> TrackingResult:
        """Check a single signal"""
        signal_id = signal.signal_id
        entry_price = signal.entry_price
        stop_loss = signal.stop_loss
        take_profit = signal.take_profit
        direction = signal.direction
        created_at = signal.created_at
        
        # Track price extremes for MFE/MAE
        self._update_extremes(signal_id, current_price)
        
        # Record price for history
        self.db.add_price_tracking(signal_id, current_price)
        
        # Calculate duration
        duration_minutes = int((datetime.utcnow() - created_at).total_seconds() / 60)
        
        # Calculate MFE/MAE
        mfe, mae = self._calculate_mfe_mae(signal_id, entry_price, direction)
        
        result = TrackingResult(
            signal_id=signal_id,
            status="PENDING",
            entry_price=entry_price,
            current_price=current_price,
            mfe=mfe,
            mae=mae,
            duration_minutes=duration_minutes
        )
        
        # Check for TP hit
        if direction == "LONG":
            if current_price >= take_profit:
                result.status = "WIN"
                result.result_price = take_profit
                result.result_pnl = self.win_amount
                result.result_reason = "TP_HIT"
                result.changed = True
            elif current_price <= stop_loss:
                result.status = "LOSS"
                result.result_price = stop_loss
                result.result_pnl = self.loss_amount
                result.result_reason = "SL_HIT"
                result.changed = True
        else:  # SHORT
            if current_price <= take_profit:
                result.status = "WIN"
                result.result_price = take_profit
                result.result_pnl = self.win_amount
                result.result_reason = "TP_HIT"
                result.changed = True
            elif current_price >= stop_loss:
                result.status = "LOSS"
                result.result_price = stop_loss
                result.result_pnl = self.loss_amount
                result.result_reason = "SL_HIT"
                result.changed = True
        
        # Check for timeout
        if not result.changed and duration_minutes >= self.max_hold_minutes:
            result.status = "TIMEOUT"
            result.result_price = current_price
            result.result_reason = "TIMEOUT"
            result.changed = True
            
            # Calculate PnL for timeout
            if direction == "LONG":
                pnl_percent = (current_price - entry_price) / entry_price
            else:
                pnl_percent = (entry_price - current_price) / entry_price
            
            # Notional value: $3000 (150 * 20)
            result.result_pnl = pnl_percent * 3000
        
        # Clean up extremes if signal resolved
        if result.changed and signal_id in self.price_extremes:
            del self.price_extremes[signal_id]
        
        return result
    
    def _update_extremes(self, signal_id: str, price: float):
        """Update price extremes for a signal"""
        if signal_id not in self.price_extremes:
            self.price_extremes[signal_id] = {
                'max': price,
                'min': price
            }
        else:
            self.price_extremes[signal_id]['max'] = max(
                self.price_extremes[signal_id]['max'], 
                price
            )
            self.price_extremes[signal_id]['min'] = min(
                self.price_extremes[signal_id]['min'], 
                price
            )
    
    def _calculate_mfe_mae(
        self, 
        signal_id: str, 
        entry_price: float, 
        direction: str
    ) -> tuple:
        """Calculate Maximum Favorable/Adverse Excursion"""
        if signal_id not in self.price_extremes:
            return 0.0, 0.0
        
        extremes = self.price_extremes[signal_id]
        max_price = extremes['max']
        min_price = extremes['min']
        
        if direction == "LONG":
            # MFE = max upside, MAE = max downside
            mfe = (max_price - entry_price) / entry_price * 100
            mae = (entry_price - min_price) / entry_price * 100
        else:  # SHORT
            # MFE = max downside, MAE = max upside
            mfe = (entry_price - min_price) / entry_price * 100
            mae = (max_price - entry_price) / entry_price * 100
        
        return max(0, mfe), max(0, mae)

