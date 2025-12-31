# Bot 2: Heartbeat Monitor

## BTC Trading Bot v5.0 - Monitoring & Reporting

Bot 2 là "người giám sát" của hệ thống, theo dõi Bot 1 và đánh giá kết quả.

## Chức năng chính

1. **Giám sát Bot 1** - Heartbeat monitoring, health alerts
2. **Theo dõi Signal** - Track Win/Loss, calculate MFE/MAE
3. **Quản lý Daily State** - PnL, trade count, target/stop check
4. **Tính Bot IQ** - Score từng trade và trend analysis
5. **Tạo Reports** - Daily/Weekly performance reports

## Cài đặt

```bash
# Clone và cd vào thư mục
cd bot-heartbeat

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc: venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Copy và cấu hình environment
cp env.example .env
# Chỉnh sửa .env
```

## Cấu hình

Các biến môi trường quan trọng trong `.env`:

```
# Database (same as Bot 1)
USE_SQLITE=true
SQLITE_PATH=../bot-core-brain/data/trading_bot.db

# Telegram
BOT_2_TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Chạy Bot

```bash
# Development
python src/main.py

# Với Docker
docker build -t btc-bot-heartbeat .
docker run -d --name heartbeat btc-bot-heartbeat
```

## Cấu trúc thư mục

```
bot-heartbeat/
├── config/
│   └── settings.py         # Cấu hình
├── src/
│   ├── health/             # Health monitoring
│   ├── tracking/           # Signal tracking, MFE/MAE
│   ├── daily/              # Daily state manager
│   ├── iq/                 # Bot IQ calculator
│   ├── reports/            # Report generator
│   ├── database/           # Database models & repository
│   ├── telegram/           # Telegram notifications
│   └── main.py             # Entry point
└── logs/                   # Log files
```

## Bot IQ Scoring

Mỗi trade được đánh giá IQ (0-100):

| Component | Weight |
|-----------|--------|
| Decision Quality | 45% |
| Execution Quality | 30% |
| Risk Adherence | 25% |

### IQ Thresholds

| IQ | Meaning | Action |
|----|---------|--------|
| 90-100 | Excellent | Continue |
| 75-89 | Good | Monitor |
| 60-74 | Acceptable | Review |
| 50-59 | Poor | PAUSE |
| 0-49 | Critical | SHUTDOWN |

## Telegram Commands

```
/health      - Bot 1 health status
/today       - Today's progress
/pending     - Pending signals
/stats       - Performance metrics
/week        - Weekly summary
/iq          - Bot IQ statistics
/report      - Generate report
```

## Automatic Alerts

- ✅/❌ Signal result với Trade IQ
- 🎯 Daily Target hit (+$10)
- ⛔ Daily Stop hit (-$15)
- 📊 Max trades reached (3)
- 🚨 Bot 1 health issues
- 🧠 IQ degradation warning
- 📊 Daily/Weekly reports

## Giao tiếp với Bot 1

Bot 2 giao tiếp với Bot 1 qua database:
- Đọc signals từ bảng `signals`
- Đọc heartbeat từ bảng `heartbeat`
- Ghi results vào bảng `signals`
- Ghi daily_state vào bảng `daily_state`
- Ghi stats vào bảng `daily_stats`

