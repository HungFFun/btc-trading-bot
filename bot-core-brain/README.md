# Bot 1: Core Brain

## BTC Trading Bot v5.0 - Trading Logic

Bot 1 là "bộ não" chính của hệ thống, chịu trách nhiệm về logic giao dịch.

## Chức năng chính

1. **Thu thập dữ liệu** - Binance WebSocket (price, trades, orderbook)
2. **Tính toán 100 features** - Technical, On-chain, Liquidation, Funding, Microstructure
3. **Phát hiện Market Regime** - TRENDING_UP, TRENDING_DOWN, RANGING, HIGH_VOLATILITY, CHOPPY
4. **Lọc qua 5-Gate System** - Context, Regime, Signal Quality, AI, Daily Limits
5. **Tạo trading signals** - 4 strategies (Trend Momentum, Liquidation Hunt, Funding Fade, Range Scalping)
6. **Học từ kết quả** - Pattern analysis và lessons learned

## Cài đặt

```bash
# Clone và cd vào thư mục
cd bot-core-brain

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc: venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Copy và cấu hình environment
cp env.example .env
# Chỉnh sửa .env với API keys của bạn
```

## Cấu hình

Các biến môi trường quan trọng trong `.env`:

```
# Binance API
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BINANCE_TESTNET=true

# Telegram
BOT_1_TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Chạy Bot

```bash
# Development
python src/main.py

# Với Docker
docker build -t btc-bot-core .
docker run -d --name core-brain btc-bot-core
```

## Cấu trúc thư mục

```
bot-core-brain/
├── config/
│   └── settings.py         # Cấu hình
├── src/
│   ├── data/               # Binance client, data collector
│   ├── features/           # 100 features engine
│   ├── gates/              # 5-Gate system
│   ├── signals/            # Signal generator
│   ├── ai/                 # AI model
│   ├── learning/           # Learning engine
│   ├── database/           # Database models & repository
│   ├── telegram/           # Telegram notifications
│   └── main.py             # Entry point
├── models/                 # Trained ML models
├── logs/                   # Log files
└── data/                   # SQLite database
```

## Trading Parameters (FIXED in v5.0)

| Parameter | Value |
|-----------|-------|
| Position Margin | $150 (30% of $500) |
| Leverage | 20x |
| Take Profit | 0.5% = +$15 |
| Stop Loss | 0.25% = -$7.50 |
| Daily Target | +$10 → STOP |
| Daily Stop | -$15 → STOP |
| Max Trades | 3/day |

## Telegram Commands

```
/status      - Trạng thái hiện tại
/daily       - Daily state
/features    - Current features
/regime      - Market regime
/gates       - 5-Gate status
/pause       - Tạm dừng
/resume      - Tiếp tục
```

## Giao tiếp với Bot 2

Bot 1 giao tiếp với Bot 2 qua database:
- Ghi signals vào bảng `signals`
- Ghi heartbeat vào bảng `heartbeat`
- Đọc daily_state từ bảng `daily_state`
- Đọc kết quả để học từ bảng `signals`

