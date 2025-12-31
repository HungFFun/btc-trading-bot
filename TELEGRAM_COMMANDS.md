# Telegram Interactive Commands Feature

## 🎯 Overview

Added interactive Telegram commands for both bots to query status and information on-demand.

## ✅ New Commands

### Bot 1 (@CoreBrainBot) Commands:

| Command | Description |
|---------|-------------|
| `/status` | Current bot status and market overview |
| `/daily` | Today's trading state (PnL, trades, win rate) |
| `/regime` | Current market regime analysis |
| `/help` | Show available commands |

### Bot 2 (@HeartbeatBot) Commands:

| Command | Description |
|---------|-------------|
| `/health` | Bot 1 health status |
| `/today` | Today's trading results and statistics |
| `/help` | Show available commands |

## 🔒 Security

- Only responds to authorized `TELEGRAM_CHAT_ID` from environment
- All unauthorized commands are logged and ignored
- Uses long polling (no webhooks required)

## 🏗️ Implementation Details

### New Files:
- `bot-core-brain/src/telegram/command_handler.py` - Command handler for Bot 1
- `bot-heartbeat/src/telegram/command_handler.py` - Command handler for Bot 2

### Modified Files:
- `bot-core-brain/src/main.py` - Integrated command polling task
- `bot-heartbeat/src/main.py` - Integrated command polling task

### How It Works:
1. Command handler runs in separate async task
2. Long polling to Telegram API (`getUpdates`)
3. Parses incoming messages starting with `/`
4. Routes commands to appropriate handlers
5. Queries database/components for current state
6. Sends formatted response back to user

## 🧪 Testing (Before Merging to Production)

### Option 1: Test on Local Machine

```bash
# Switch to feature branch
git checkout feature/telegram-commands

# Set up environment
cd bot-core-brain
cp env.example .env
# Edit .env with your test Telegram bot token

# Run locally
python src/main.py
```

Then send commands to your test Telegram bot.

### Option 2: Test on Staging Server

```bash
# On staging server
git clone https://github.com/HungFFun/btc-trading-bot.git bot-staging
cd bot-staging
git checkout feature/telegram-commands

# Configure with staging credentials
# Run with docker-compose
docker-compose up -d
```

### Option 3: Test with Separate Telegram Bot

Create a new test Telegram bot via @BotFather and use it for testing without affecting production.

## 📋 Test Checklist

Before merging to production, verify:

- [ ] `/status` command returns current bot status
- [ ] `/daily` command shows today's PnL and trades
- [ ] `/regime` command displays current market regime
- [ ] `/health` command (Bot 2) shows Bot 1 health
- [ ] `/today` command (Bot 2) shows trading results
- [ ] `/help` command displays available commands
- [ ] Unauthorized chat IDs are rejected
- [ ] Commands don't interfere with main bot loop
- [ ] Bot gracefully shuts down when stopped

## 🚀 Deploying to Production

### Step 1: Test Feature Branch

Test the feature branch thoroughly on a non-production environment.

### Step 2: Merge to Main

```bash
# Switch to main branch
git checkout main

# Merge feature branch
git merge feature/telegram-commands

# Push to GitHub
git push origin main
```

### Step 3: Deploy to Production

```bash
# On production server (Vultr)
cd /path/to/bot_featured
git pull origin main

# Restart services
docker-compose restart
```

### Step 4: Verify

Send a test command to your production bot:
```
/status
```

You should receive a formatted response with current bot status.

## 🔄 Rollback Plan

If issues occur after deployment:

```bash
# On production server
git checkout main
git reset --hard <previous-commit-hash>
docker-compose restart
```

Or simply checkout main branch and don't merge the feature branch.

## 📊 Performance Impact

- **Minimal overhead**: Command polling uses 30-second timeout
- **Non-blocking**: Runs in separate async task
- **No impact on trading**: Main loop continues independently
- **Memory**: ~1-2MB additional for command handler

## ❓ FAQ

**Q: Will commands slow down the trading bot?**
A: No, commands run in a separate async task and don't block the main trading loop.

**Q: Can anyone send commands to the bot?**
A: No, only the chat ID specified in `TELEGRAM_CHAT_ID` environment variable can use commands.

**Q: What if Telegram API is down?**
A: The command handler will log errors but won't crash the main bot. Trading continues normally.

**Q: Can I disable commands?**
A: Yes, set `TELEGRAM_ENABLED=false` in environment variables.

## 📝 Notes

- Feature branch: `feature/telegram-commands`
- Main branch: `main` (production)
- The feature is completely separate from production until you merge

## 🎉 Benefits

1. **On-demand status checks** without waiting for scheduled reports
2. **Quick health monitoring** during trading hours
3. **Better situational awareness** of bot performance
4. **Instant regime information** for manual trading decisions
5. **User-friendly interface** via Telegram chat

---

**Created:** 2025-12-31
**Branch:** feature/telegram-commands
**Status:** Ready for testing

