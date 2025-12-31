"""
Market Microstructure Analysis Module
Features 89-100: Market Microstructure Features
"""
from typing import List, Optional
from dataclasses import dataclass
from collections import deque
import numpy as np


@dataclass
class MicrostructureFeatures:
    """Market microstructure features (89-100)"""
    cvd: float = 0.0  # Cumulative Volume Delta
    cvd_trend: float = 0.0  # CVD trend direction
    orderbook_imbalance: float = 0.0  # Bid vs Ask imbalance
    orderbook_imbalance_10: float = 0.0  # Top 10 levels imbalance
    large_order_flow: float = 0.0  # Large orders (>$100k)
    tape_speed: float = 0.0  # Trades per minute
    aggressor_ratio: float = 0.5  # Market vs Limit ratio
    spread_current: float = 0.0
    spread_percentile: float = 50.0
    depth_ratio: float = 0.0  # Liquidity near price
    vwap_distance: float = 0.0
    poc_distance: float = 0.0  # Point of Control distance


class MicrostructureAnalyzer:
    """Analyze market microstructure"""
    
    def __init__(self):
        self.cvd_history: List[float] = []
        self.spread_history: List[float] = []
        self.volume_profile: dict = {}  # Price level -> volume
    
    def calculate_cvd(self, trades: List) -> tuple:
        """Calculate Cumulative Volume Delta and trend"""
        if not trades:
            return 0.0, 0.0
        
        buy_volume = 0.0
        sell_volume = 0.0
        
        for trade in trades:
            if trade.is_buy:
                buy_volume += trade.quantity * trade.price
            else:
                sell_volume += trade.quantity * trade.price
        
        cvd = buy_volume - sell_volume
        
        # Track history
        self.cvd_history.append(cvd)
        if len(self.cvd_history) > 100:
            self.cvd_history = self.cvd_history[-100:]
        
        # Calculate trend
        if len(self.cvd_history) >= 10:
            recent = self.cvd_history[-10:]
            trend = (recent[-1] - recent[0]) / abs(recent[0]) if recent[0] != 0 else 0
        else:
            trend = 0.0
        
        return cvd, trend
    
    def calculate_orderbook_imbalance(self, orderbook) -> tuple:
        """Calculate order book imbalance"""
        if not orderbook or not orderbook.bids or not orderbook.asks:
            return 0.0, 0.0
        
        # Full orderbook imbalance
        total_bid = sum(b.quantity * b.price for b in orderbook.bids)
        total_ask = sum(a.quantity * a.price for a in orderbook.asks)
        
        total = total_bid + total_ask
        imbalance = (total_bid - total_ask) / total if total > 0 else 0
        
        # Top 10 levels
        bid_10 = sum(b.quantity * b.price for b in orderbook.bids[:10])
        ask_10 = sum(a.quantity * a.price for a in orderbook.asks[:10])
        
        total_10 = bid_10 + ask_10
        imbalance_10 = (bid_10 - ask_10) / total_10 if total_10 > 0 else 0
        
        return imbalance, imbalance_10
    
    def calculate_large_order_flow(self, trades: List, threshold: float = 100000) -> float:
        """Calculate volume from large orders (> threshold USD)"""
        if not trades:
            return 0.0
        
        large_volume = 0.0
        for trade in trades:
            trade_value = trade.quantity * trade.price
            if trade_value >= threshold:
                large_volume += trade_value
        
        return large_volume
    
    def calculate_tape_speed(self, trades: List, window_minutes: int = 1) -> float:
        """Calculate trades per minute"""
        if not trades:
            return 0.0
        
        # Simple: return count of trades in the window
        return len(trades) / window_minutes
    
    def calculate_aggressor_ratio(self, trades: List) -> float:
        """Calculate ratio of buy vs sell aggressors"""
        if not trades:
            return 0.5
        
        buy_count = sum(1 for t in trades if t.is_buy)
        return buy_count / len(trades)
    
    def calculate_spread_percentile(self, current_spread: float) -> float:
        """Calculate spread percentile vs history"""
        self.spread_history.append(current_spread)
        if len(self.spread_history) > 1000:
            self.spread_history = self.spread_history[-1000:]
        
        if len(self.spread_history) < 2:
            return 50.0
        
        count_below = sum(1 for s in self.spread_history if s < current_spread)
        return (count_below / len(self.spread_history)) * 100
    
    def calculate_depth_ratio(self, orderbook, price_range_pct: float = 0.001) -> float:
        """Calculate liquidity depth near current price"""
        if not orderbook or not orderbook.bids or not orderbook.asks:
            return 0.0
        
        mid_price = orderbook.mid_price
        range_up = mid_price * (1 + price_range_pct)
        range_down = mid_price * (1 - price_range_pct)
        
        # Volume within range
        bid_depth = sum(b.quantity for b in orderbook.bids if b.price >= range_down)
        ask_depth = sum(a.quantity for a in orderbook.asks if a.price <= range_up)
        
        # Total depth in orderbook
        total_bid = sum(b.quantity for b in orderbook.bids)
        total_ask = sum(a.quantity for a in orderbook.asks)
        total = total_bid + total_ask
        
        if total == 0:
            return 0.0
        
        near_depth = bid_depth + ask_depth
        return near_depth / total
    
    def calculate_vwap_distance(self, current_price: float, vwap: float) -> float:
        """Calculate distance from VWAP"""
        if vwap == 0:
            return 0.0
        return (current_price - vwap) / vwap
    
    def update_volume_profile(self, trades: List, num_levels: int = 50):
        """Update volume profile from trades"""
        if not trades:
            return
        
        for trade in trades:
            # Round price to create levels
            level = round(trade.price, -1)  # Round to nearest 10
            if level not in self.volume_profile:
                self.volume_profile[level] = 0.0
            self.volume_profile[level] += trade.quantity * trade.price
        
        # Keep only top N levels by volume
        if len(self.volume_profile) > num_levels * 2:
            sorted_levels = sorted(self.volume_profile.items(), key=lambda x: x[1], reverse=True)
            self.volume_profile = dict(sorted_levels[:num_levels])
    
    def find_poc(self) -> float:
        """Find Point of Control (price level with highest volume)"""
        if not self.volume_profile:
            return 0.0
        
        poc_level = max(self.volume_profile.items(), key=lambda x: x[1])
        return poc_level[0]
    
    def calculate(
        self, 
        trades: List, 
        orderbook, 
        current_price: float, 
        vwap: float
    ) -> MicrostructureFeatures:
        """Calculate all microstructure features"""
        features = MicrostructureFeatures()
        
        # CVD
        features.cvd, features.cvd_trend = self.calculate_cvd(trades)
        
        # Orderbook imbalance
        if orderbook:
            features.orderbook_imbalance, features.orderbook_imbalance_10 = \
                self.calculate_orderbook_imbalance(orderbook)
            features.spread_current = orderbook.spread_percent
            features.depth_ratio = self.calculate_depth_ratio(orderbook)
        
        # Trade analysis
        features.large_order_flow = self.calculate_large_order_flow(trades)
        features.tape_speed = self.calculate_tape_speed(trades)
        features.aggressor_ratio = self.calculate_aggressor_ratio(trades)
        
        # Spread percentile
        features.spread_percentile = self.calculate_spread_percentile(features.spread_current)
        
        # VWAP distance
        features.vwap_distance = self.calculate_vwap_distance(current_price, vwap)
        
        # Volume profile and POC
        self.update_volume_profile(trades)
        poc = self.find_poc()
        if poc > 0 and current_price > 0:
            features.poc_distance = (current_price - poc) / current_price
        
        return features
    
    def get_mock_features(self, current_price: float) -> MicrostructureFeatures:
        """Get mock features for testing"""
        import random
        
        features = MicrostructureFeatures()
        
        features.cvd = random.uniform(-1000000, 1000000)
        features.cvd_trend = random.uniform(-0.1, 0.1)
        features.orderbook_imbalance = random.uniform(-0.3, 0.3)
        features.orderbook_imbalance_10 = random.uniform(-0.4, 0.4)
        features.large_order_flow = random.uniform(500000, 5000000)
        features.tape_speed = random.uniform(50, 500)
        features.aggressor_ratio = random.uniform(0.4, 0.6)
        features.spread_current = random.uniform(0.01, 0.05)
        features.spread_percentile = random.uniform(30, 70)
        features.depth_ratio = random.uniform(0.1, 0.4)
        features.vwap_distance = random.uniform(-0.01, 0.01)
        features.poc_distance = random.uniform(-0.02, 0.02)
        
        return features

