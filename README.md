# BTC Trading Bot v5.0

[![Deploy to Vultr](https://github.com/HungFFun/btc-trading-bot/actions/workflows/deploy.yml/badge.svg)](https://github.com/HungFFun/btc-trading-bot/actions/workflows/deploy.yml)
![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.13-blue)
![Docker](https://img.shields.io/badge/docker-ready-green)

## 2 BOT Architecture - Daily Target $10

**Vốn:** $500  
**Target:** +$10/ngày (2%) → DỪNG  
**Tài sản:** Chỉ BTC/USDT  

---

## 🏗️ Kiến trúc

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SHARED DATABASE                                      │
│                        (PostgreSQL/SQLite)                                   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       │                       ▼
┌─────────────────────────┐      │      ┌─────────────────────────┐
│   BOT 1: CORE BRAIN     │      │      │ BOT 2: HEARTBEAT        │
│   (Trading Logic)       │◄─────┘      │ (Monitoring)            │
│                         │             │                         │
│ • Data Collector        │             │ • Health Monitor        │
│ • 100 BTC Features      │             │ • Signal Tracker        │
│ • Regime Detector       │             │ • Daily State Manager   │
│ • 5-Gate System         │             │ • Bot IQ Calculator     │
│ • Signal Generator      │             │ • Report Generator      │
│ • AI Model              │             │                         │
│ • Learning Engine       │             │                         │
└─────────────────────────┘             └─────────────────────────┘
```

## 📁 Cấu trúc Project

```
bot_featured/
├── bot-core-brain/          # Bot 1: Trading Logic
│   ├── src/
│   │   ├── data/            # Binance WebSocket client
│   │   ├── features/        # 100 BTC features
│   │   ├── gates/           # 5-Gate System
│   │   ├── signals/         # Signal generator
│   │   ├── ai/              # AI models
│   │   ├── learning/        # Learning engine
│   │   └── main.py
│   └── Dockerfile
│
├── bot-heartbeat/           # Bot 2: Monitoring
│   ├── src/
│   │   ├── health/          # Health monitor
│   │   ├── tracking/        # Signal tracker
│   │   ├── daily/           # Daily state manager
│   │   ├── iq/              # Bot IQ calculator
│   │   ├── reports/         # Report generator
│   │   └── main.py
│   └── Dockerfile
│
├── docker-compose.yml       # Docker orchestration
├── init-db.sql             # Database schema
└── README.md
```

## 🚀 Quick Start

### 1. Cài đặt

```bash
# Clone project
cd bot_featured

# Setup Bot 1
cd bot-core-brain
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# Edit .env with your API keys

# Setup Bot 2 (new terminal)
cd ../bot-heartbeat
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# Edit .env
```

### 2. Chạy với Docker (Recommended)

```bash
# Copy environment files
cp bot-core-brain/env.example bot-core-brain/.env
cp bot-heartbeat/env.example bot-heartbeat/.env
# Edit both .env files

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 3. Chạy Manual

```bash
# Terminal 1 - Bot 1
cd bot-core-brain
source venv/bin/activate
python src/main.py

# Terminal 2 - Bot 2
cd bot-heartbeat
source venv/bin/activate
python src/main.py
```

## 💰 Trading Parameters (FIXED)

| Parameter | Value |
|-----------|-------|
| Position Margin | $150 (30% of $500) |
| Leverage | 20x |
| Notional | $3,000 |
| Take Profit | 0.5% = +$15 |
| Stop Loss | 0.25% = -$7.50 |
| R:R Ratio | 2:1 |
| Daily Target | +$10 → STOP |
| Daily Stop | -$15 → STOP |
| Max Trades | 3/day |

## 📊 5-Gate System

```
Signal → [Gate 1] → [Gate 2] → [Gate 3] → [Gate 4] → [Gate 5] → Execute
            ↓          ↓          ↓          ↓          ↓
         Context    Regime     Quality      AI       Daily
                                                    Limits
```

Chỉ ~10-15% signals vượt qua tất cả gates.

## 🎯 Expected Performance

| Metric | Target |
|--------|--------|
| Win Rate | ≥55% |
| Daily PnL | +$8-12 |
| Monthly | +$100-150 (20-30%) |
| Max Drawdown | ≤10% |
| 6 months | $500 → $2,000+ |

## 📱 Telegram Bots

### @CoreBrainBot (Bot 1)

**Notifications:**
- 🔔 New signals
- 📊 Features & Regime
- 💡 Learning insights

**Interactive Commands:**
- `/status` - Current bot status and market overview
- `/daily` - Today's trading state (PnL, trades, win rate)
- `/regime` - Market regime analysis
- `/help` - Show available commands

### @HeartbeatBot (Bot 2)

**Notifications:**
- ✅/❌ Trade results
- 🎯 Target/Stop alerts
- 📊 Daily/Weekly reports
- 🧠 IQ monitoring

**Interactive Commands:**
- `/health` - Bot 1 health status
- `/today` - Today's trading results & statistics
- `/help` - Show available commands

## 🚀 CI/CD Deployment

### Auto-Deploy to Vultr with GitHub Actions

Every push to `main` branch automatically deploys to your Vultr server!

**Setup:**
1. See [.github/DEPLOY_SETUP.md](.github/DEPLOY_SETUP.md) for detailed instructions
2. Add GitHub Secrets (VULTR_HOST, VULTR_SSH_KEY, etc.)
3. Push code → Auto deploy! 🎉

**Features:**
- ✅ Automatic deployment on push
- ✅ Manual trigger available
- ✅ Container health checks
- ✅ Deployment logs & monitoring
- ✅ Zero-downtime deployment

**Workflow:**
```
Push to main → GitHub Actions → SSH to Vultr → Pull & Restart → Done!
```

## ⚙️ Environment Variables

### Bot 1 (.env)
```
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BINANCE_TESTNET=true
BOT_1_TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Bot 2 (.env)
```
SQLITE_PATH=../bot-core-brain/data/trading_bot.db
BOT_2_TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 📈 Scaling Strategy

| Account | Daily Target | Position |
|---------|--------------|----------|
| $500 | $10 (2%) | $150 |
| $750 | $15 (2%) | $225 |
| $1,000 | $20 (2%) | $300 |
| $1,500 | $25 (1.7%) | $375 |
| $2,000 | $30 (1.5%) | $450 |

## ⚠️ Disclaimer

Trading cryptocurrency involves significant risk. This bot is for educational purposes. 
Use at your own risk and never trade with money you can't afford to lose.

---

## 📚 Documentation

- [Telegram Commands Guide](TELEGRAM_COMMANDS.md) - Interactive command usage
- [CI/CD Setup Guide](.github/DEPLOY_SETUP.md) - GitHub Actions deployment
- [Docker Compose](docker-compose.yml) - Container orchestration
- [Database Schema](init-db.sql) - PostgreSQL setup

---

**Version:** 1.1.0  
**Architecture:** 2 BOT (Core Brain + Heartbeat Monitor)  
**Target:** $500 → $10/day  
**Deployment:** Auto-deploy via GitHub Actions  

