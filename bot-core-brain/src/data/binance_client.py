"""
Binance WebSocket and REST Client
Data Collector for Bot 1
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import deque
import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed
import hmac
import hashlib
import time

logger = logging.getLogger(__name__)


@dataclass
class Candle:
    """OHLCV Candle data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    trades: int
    is_closed: bool = False
    
    @property
    def body(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def range(self) -> float:
        return self.high - self.low
    
    @property
    def body_percent(self) -> float:
        if self.range == 0:
            return 0
        return self.body / self.range
    
    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open


@dataclass
class Trade:
    """Trade data"""
    timestamp: datetime
    price: float
    quantity: float
    is_buyer_maker: bool  # True = sell aggressor, False = buy aggressor
    
    @property
    def is_buy(self) -> bool:
        return not self.is_buyer_maker


@dataclass
class OrderBookLevel:
    """Order book level"""
    price: float
    quantity: float


@dataclass
class OrderBook:
    """Order book snapshot"""
    timestamp: datetime
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    
    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0
    
    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 0
    
    @property
    def mid_price(self) -> float:
        return (self.best_bid + self.best_ask) / 2
    
    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid
    
    @property
    def spread_percent(self) -> float:
        if self.mid_price == 0:
            return 0
        return (self.spread / self.mid_price) * 100
    
    def get_imbalance(self, levels: int = 10) -> float:
        """Calculate order book imbalance"""
        bid_volume = sum(b.quantity for b in self.bids[:levels])
        ask_volume = sum(a.quantity for a in self.asks[:levels])
        total = bid_volume + ask_volume
        if total == 0:
            return 0
        return (bid_volume - ask_volume) / total


@dataclass
class FundingRate:
    """Funding rate data"""
    timestamp: datetime
    funding_rate: float
    mark_price: float
    next_funding_time: datetime


@dataclass
class MarketData:
    """Container for all market data"""
    candles: Dict[str, List[Candle]] = field(default_factory=dict)
    trades: deque = field(default_factory=lambda: deque(maxlen=1000))
    orderbook: Optional[OrderBook] = None
    funding: Optional[FundingRate] = None
    last_price: float = 0.0
    last_update: Optional[datetime] = None


class BinanceClient:
    """Binance Futures WebSocket and REST client"""
    
    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True,
        symbol: str = "BTCUSDT"
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.symbol = symbol.lower()
        self.symbol_upper = symbol.upper()
        
        # WebSocket URLs
        if testnet:
            self.ws_base_url = "wss://stream.binancefuture.com/ws"
            self.rest_base_url = "https://testnet.binancefuture.com"
        else:
            self.ws_base_url = "wss://fstream.binance.com/ws"
            self.rest_base_url = "https://fapi.binance.com"
        
        # Data storage
        self.data = MarketData()
        self.data.candles = {
            "1m": deque(maxlen=500),
            "3m": deque(maxlen=500),
            "5m": deque(maxlen=500),
            "15m": deque(maxlen=500)
        }
        
        # Connection state
        self._ws_connection = None
        self._running = False
        self._callbacks: List[Callable] = []
        
        # Session for REST API
        self._session: Optional[aiohttp.ClientSession] = None
    
    def add_callback(self, callback: Callable):
        """Add callback for data updates"""
        self._callbacks.append(callback)
    
    async def _notify_callbacks(self):
        """Notify all callbacks"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.data)
                else:
                    callback(self.data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    def _sign_request(self, params: Dict) -> Dict:
        """Sign request with API secret"""
        params['timestamp'] = int(time.time() * 1000)
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params['signature'] = signature
        return params
    
    async def fetch_historical_candles(self, timeframe: str, limit: int = 500) -> List[Candle]:
        """Fetch historical candles via REST API"""
        session = await self._get_session()
        url = f"{self.rest_base_url}/fapi/v1/klines"
        params = {
            "symbol": self.symbol_upper,
            "interval": timeframe,
            "limit": limit
        }
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    candles = []
                    for item in data:
                        candle = Candle(
                            timestamp=datetime.fromtimestamp(item[0] / 1000),
                            open=float(item[1]),
                            high=float(item[2]),
                            low=float(item[3]),
                            close=float(item[4]),
                            volume=float(item[5]),
                            quote_volume=float(item[7]),
                            trades=int(item[8]),
                            is_closed=True
                        )
                        candles.append(candle)
                    return candles
                else:
                    logger.error(f"Failed to fetch candles: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching candles: {e}")
            return []
    
    async def fetch_funding_rate(self) -> Optional[FundingRate]:
        """Fetch current funding rate"""
        session = await self._get_session()
        url = f"{self.rest_base_url}/fapi/v1/premiumIndex"
        params = {"symbol": self.symbol_upper}
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return FundingRate(
                        timestamp=datetime.utcnow(),
                        funding_rate=float(data.get("lastFundingRate", 0)),
                        mark_price=float(data.get("markPrice", 0)),
                        next_funding_time=datetime.fromtimestamp(
                            int(data.get("nextFundingTime", 0)) / 1000
                        )
                    )
                return None
        except Exception as e:
            logger.error(f"Error fetching funding rate: {e}")
            return None
    
    async def fetch_orderbook(self, limit: int = 20) -> Optional[OrderBook]:
        """Fetch order book snapshot"""
        session = await self._get_session()
        url = f"{self.rest_base_url}/fapi/v1/depth"
        params = {"symbol": self.symbol_upper, "limit": limit}
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return OrderBook(
                        timestamp=datetime.utcnow(),
                        bids=[OrderBookLevel(float(b[0]), float(b[1])) for b in data["bids"]],
                        asks=[OrderBookLevel(float(a[0]), float(a[1])) for a in data["asks"]]
                    )
                return None
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return None
    
    async def get_current_price(self) -> float:
        """Get current price"""
        session = await self._get_session()
        url = f"{self.rest_base_url}/fapi/v1/ticker/price"
        params = {"symbol": self.symbol_upper}
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data.get("price", 0))
                return 0
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            return 0
    
    def _build_stream_url(self) -> str:
        """Build combined stream URL"""
        streams = [
            f"{self.symbol}@kline_1m",
            f"{self.symbol}@kline_3m",
            f"{self.symbol}@kline_5m",
            f"{self.symbol}@kline_15m",
            f"{self.symbol}@aggTrade",
            f"{self.symbol}@depth20@100ms",
            f"{self.symbol}@markPrice@1s"
        ]
        stream_path = "/".join(streams)
        return f"{self.ws_base_url}/{stream_path}"
    
    async def _process_message(self, message: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            if "e" not in data:
                return
            
            event_type = data["e"]
            
            if event_type == "kline":
                await self._handle_kline(data)
            elif event_type == "aggTrade":
                await self._handle_trade(data)
            elif event_type == "depthUpdate":
                await self._handle_depth(data)
            elif event_type == "markPriceUpdate":
                await self._handle_mark_price(data)
            
            self.data.last_update = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _handle_kline(self, data: Dict):
        """Handle kline/candlestick update"""
        k = data["k"]
        interval = k["i"]
        
        candle = Candle(
            timestamp=datetime.fromtimestamp(k["t"] / 1000),
            open=float(k["o"]),
            high=float(k["h"]),
            low=float(k["l"]),
            close=float(k["c"]),
            volume=float(k["v"]),
            quote_volume=float(k["q"]),
            trades=k["n"],
            is_closed=k["x"]
        )
        
        self.data.last_price = candle.close
        
        if interval in self.data.candles:
            candles = self.data.candles[interval]
            
            # Update or append
            if candles and not candle.is_closed:
                # Update current candle
                if candles[-1].timestamp == candle.timestamp:
                    candles[-1] = candle
                else:
                    candles.append(candle)
            elif candle.is_closed:
                candles.append(candle)
    
    async def _handle_trade(self, data: Dict):
        """Handle aggregate trade"""
        trade = Trade(
            timestamp=datetime.fromtimestamp(data["T"] / 1000),
            price=float(data["p"]),
            quantity=float(data["q"]),
            is_buyer_maker=data["m"]
        )
        
        self.data.trades.append(trade)
        self.data.last_price = trade.price
    
    async def _handle_depth(self, data: Dict):
        """Handle order book update"""
        self.data.orderbook = OrderBook(
            timestamp=datetime.utcnow(),
            bids=[OrderBookLevel(float(b[0]), float(b[1])) for b in data.get("b", [])],
            asks=[OrderBookLevel(float(a[0]), float(a[1])) for a in data.get("a", [])]
        )
    
    async def _handle_mark_price(self, data: Dict):
        """Handle mark price/funding update"""
        self.data.funding = FundingRate(
            timestamp=datetime.utcnow(),
            funding_rate=float(data.get("r", 0)),
            mark_price=float(data.get("p", 0)),
            next_funding_time=datetime.fromtimestamp(
                int(data.get("T", 0)) / 1000
            ) if data.get("T") else datetime.utcnow()
        )
    
    async def connect(self):
        """Connect to WebSocket and start receiving data"""
        logger.info("Connecting to Binance WebSocket...")
        
        # Load historical data first
        for tf in ["1m", "3m", "5m", "15m"]:
            candles = await self.fetch_historical_candles(tf, 500)
            self.data.candles[tf] = deque(candles, maxlen=500)
            logger.info(f"Loaded {len(candles)} {tf} candles")
        
        # Fetch initial orderbook and funding
        self.data.orderbook = await self.fetch_orderbook()
        self.data.funding = await self.fetch_funding_rate()
        
        self._running = True
        stream_url = self._build_stream_url()
        
        while self._running:
            try:
                async with websockets.connect(stream_url) as ws:
                    self._ws_connection = ws
                    logger.info("WebSocket connected")
                    
                    while self._running:
                        try:
                            message = await asyncio.wait_for(
                                ws.recv(),
                                timeout=30.0
                            )
                            await self._process_message(message)
                        except asyncio.TimeoutError:
                            # Send ping to keep alive
                            await ws.ping()
                        except ConnectionClosed:
                            logger.warning("WebSocket connection closed, reconnecting...")
                            break
                            
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if self._running:
                    await asyncio.sleep(5)
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self._running = False
        if self._ws_connection:
            await self._ws_connection.close()
        if self._session and not self._session.closed:
            await self._session.close()
        logger.info("Disconnected from Binance")
    
    def get_data(self) -> MarketData:
        """Get current market data"""
        return self.data
    
    def get_candles(self, timeframe: str) -> List[Candle]:
        """Get candles for a specific timeframe"""
        return list(self.data.candles.get(timeframe, []))
    
    def get_recent_trades(self, count: int = 100) -> List[Trade]:
        """Get recent trades"""
        return list(self.data.trades)[-count:]

