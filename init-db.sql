-- BTC Trading Bot v5.0 - Database Initialization
-- Shared between Bot 1 (Core Brain) and Bot 2 (Heartbeat Monitor)

-- Signals table
CREATE TABLE IF NOT EXISTS signals (
    signal_id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Signal details (Bot 1 writes)
    direction VARCHAR(10) NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    stop_loss DECIMAL(20, 8) NOT NULL,
    take_profit DECIMAL(20, 8) NOT NULL,
    position_margin DECIMAL(10, 2) NOT NULL DEFAULT 150,
    leverage INT NOT NULL DEFAULT 20,
    
    -- Quality metrics (Bot 1 writes)
    confidence DECIMAL(5, 4) NOT NULL,
    setup_quality INT NOT NULL,
    regime VARCHAR(50) NOT NULL,
    reasoning TEXT,
    
    -- Gate scores (Bot 1 writes)
    gate_1_score DECIMAL(5, 4),
    gate_2_score DECIMAL(5, 4),
    gate_3_score DECIMAL(5, 4),
    gate_4_score DECIMAL(5, 4),
    gate_5_passed BOOLEAN,
    
    -- Result (Bot 2 writes)
    status VARCHAR(20) DEFAULT 'PENDING',
    result_price DECIMAL(20, 8),
    result_time TIMESTAMP,
    result_pnl DECIMAL(10, 2),
    result_reason VARCHAR(50),
    
    -- MFE/MAE (Bot 2 writes)
    mfe DECIMAL(10, 4),
    mae DECIMAL(10, 4),
    duration_minutes INT,
    
    -- Trade IQ (Bot 2 writes)
    trade_iq INT,
    
    -- Learning (Bot 1 writes after result)
    result_analyzed BOOLEAN DEFAULT FALSE,
    lesson_id VARCHAR(50),
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feature snapshots table
CREATE TABLE IF NOT EXISTS feature_snapshots (
    id SERIAL PRIMARY KEY,
    signal_id VARCHAR(50) REFERENCES signals(signal_id),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Technical features
    rsi_14 DECIMAL(10, 4),
    ema_9 DECIMAL(20, 8),
    ema_21 DECIMAL(20, 8),
    ema_50 DECIMAL(20, 8),
    macd_histogram DECIMAL(20, 8),
    atr_14 DECIMAL(20, 8),
    adx DECIMAL(10, 4),
    bb_position DECIMAL(10, 4),
    
    -- Volume features
    volume_ratio DECIMAL(10, 4),
    cvd DECIMAL(20, 8),
    
    -- On-chain features
    exchange_netflow DECIMAL(20, 8),
    whale_activity DECIMAL(10, 4),
    funding_rate DECIMAL(10, 6),
    
    -- Liquidation features
    long_liq_density DECIMAL(10, 4),
    short_liq_density DECIMAL(10, 4),
    
    -- All features as JSON
    all_features JSONB
);

-- Daily state table
CREATE TABLE IF NOT EXISTS daily_state (
    date VARCHAR(10) PRIMARY KEY,
    pnl DECIMAL(10, 2) DEFAULT 0,
    trade_count INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    consecutive_losses INT DEFAULT 0,
    has_position BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    target_hit_at TIMESTAMP,
    stop_hit_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Heartbeat table
CREATE TABLE IF NOT EXISTS heartbeat (
    id SERIAL PRIMARY KEY,
    bot_name VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    signals_today INT,
    current_regime VARCHAR(50),
    daily_pnl DECIMAL(10, 2),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_heartbeat_bot_time ON heartbeat(bot_name, timestamp DESC);

-- Price tracking table
CREATE TABLE IF NOT EXISTS price_tracking (
    id SERIAL PRIMARY KEY,
    signal_id VARCHAR(50) REFERENCES signals(signal_id),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    price DECIMAL(20, 8) NOT NULL
);

-- Lessons table
CREATE TABLE IF NOT EXISTS lessons (
    lesson_id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    signal_ids JSONB,
    pattern_type VARCHAR(100),
    observation TEXT NOT NULL,
    conclusion TEXT,
    action_suggested TEXT,
    sample_size INT,
    confidence DECIMAL(5, 4),
    validated BOOLEAN DEFAULT FALSE
);

-- Daily stats table
CREATE TABLE IF NOT EXISTS daily_stats (
    date VARCHAR(10) PRIMARY KEY,
    total_signals INT,
    wins INT,
    losses INT,
    win_rate DECIMAL(5, 4),
    total_pnl DECIMAL(10, 2),
    avg_trade_iq INT,
    account_balance DECIMAL(20, 8),
    target_hit BOOLEAN,
    stop_hit BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_daily_state_date ON daily_state(date);

