-- ============================================================
-- BagHolderAI - Database Schema v1.0
-- Run this in Supabase SQL Editor to create all tables.
-- ============================================================

-- === TRADES ===
-- Every single operation the bot makes (paper or live)
CREATE TABLE trades (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    
    -- What
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL CHECK (side IN ('buy', 'sell')),
    amount DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    cost DECIMAL(18, 8) NOT NULL,
    fee DECIMAL(18, 8) DEFAULT 0,
    
    -- Why
    strategy VARCHAR(1) NOT NULL CHECK (strategy IN ('A', 'B')),
    brain VARCHAR(20) NOT NULL CHECK (brain IN ('grid', 'trend', 'sentinel', 'manual')),
    reason TEXT,
    
    -- Context
    mode VARCHAR(5) NOT NULL DEFAULT 'paper' CHECK (mode IN ('paper', 'live')),
    exchange_order_id VARCHAR(100),
    
    -- P&L (filled on sell)
    realized_pnl DECIMAL(18, 8),
    buy_trade_id UUID REFERENCES trades(id)
);

CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_created ON trades(created_at DESC);
CREATE INDEX idx_trades_strategy ON trades(strategy);


-- === PORTFOLIO ===
-- Current holdings, updated after each trade
CREATE TABLE portfolio (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    
    symbol VARCHAR(20) NOT NULL UNIQUE,
    strategy VARCHAR(1) NOT NULL CHECK (strategy IN ('A', 'B')),
    amount DECIMAL(18, 8) NOT NULL,
    avg_buy_price DECIMAL(18, 8) NOT NULL,
    current_price DECIMAL(18, 8),
    unrealized_pnl DECIMAL(18, 8),
    allocation_percent DECIMAL(5, 2),
    
    -- Grid Bot state
    grid_active BOOLEAN DEFAULT false,
    grid_lower DECIMAL(18, 8),
    grid_upper DECIMAL(18, 8),
    grid_levels INTEGER DEFAULT 10
);


-- === DAILY P&L ===
-- One row per day, for dashboard charts and monitoring
CREATE TABLE daily_pnl (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    
    -- Summary
    total_value DECIMAL(18, 8) NOT NULL,
    daily_pnl DECIMAL(18, 8) NOT NULL,
    cumulative_pnl DECIMAL(18, 8) NOT NULL,
    
    -- Breakdown
    strategy_a_pnl DECIMAL(18, 8) DEFAULT 0,
    strategy_b_pnl DECIMAL(18, 8) DEFAULT 0,
    total_fees DECIMAL(18, 8) DEFAULT 0,
    
    -- Activity
    trades_count INTEGER DEFAULT 0,
    
    -- Capital allocation
    pool_a DECIMAL(18, 8),
    pool_b DECIMAL(18, 8),
    reserve DECIMAL(18, 8)
);

CREATE INDEX idx_daily_pnl_date ON daily_pnl(date DESC);


-- === SENTINEL LOGS ===
-- Every AI analysis the Sentinel performs
CREATE TABLE sentinel_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    
    risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 1 AND 10),
    opportunity_score INTEGER NOT NULL CHECK (opportunity_score BETWEEN 1 AND 10),
    summary TEXT NOT NULL,
    action_taken VARCHAR(50),
    
    -- Raw data
    news_sources JSONB,
    llm_model VARCHAR(50),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost_usd DECIMAL(8, 6)
);

CREATE INDEX idx_sentinel_created ON sentinel_logs(created_at DESC);


-- === AGENT RULES ===
-- Auto-generated rules from weekly analysis (the learning system)
CREATE TABLE agent_rules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    
    rule_text TEXT NOT NULL,
    source VARCHAR(20) NOT NULL CHECK (source IN ('auto', 'manual', 'feedback')),
    active BOOLEAN DEFAULT true,
    version INTEGER DEFAULT 1,
    
    -- Performance tracking
    times_applied INTEGER DEFAULT 0,
    times_correct INTEGER DEFAULT 0,
    confidence DECIMAL(5, 4)
);


-- === DIARY ENTRIES ===
-- Public diary posts for the dashboard
CREATE TABLE diary_entries (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    
    entry_type VARCHAR(20) NOT NULL CHECK (entry_type IN ('daily', 'weekly', 'reset', 'milestone')),
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    
    -- Metadata
    published BOOLEAN DEFAULT false,
    published_at TIMESTAMPTZ
);

CREATE INDEX idx_diary_published ON diary_entries(published, created_at DESC);


-- === FEEDBACK ===
-- Human feedback from Telegram (Max's responses)
CREATE TABLE feedback (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    
    trade_id UUID REFERENCES trades(id),
    sentinel_log_id UUID REFERENCES sentinel_logs(id),
    
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('good', 'bad', 'override', 'note')),
    message TEXT
);


-- === ENABLE REALTIME ===
-- These tables will push updates to the dashboard via Supabase Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE trades;
ALTER PUBLICATION supabase_realtime ADD TABLE portfolio;
ALTER PUBLICATION supabase_realtime ADD TABLE daily_pnl;
ALTER PUBLICATION supabase_realtime ADD TABLE sentinel_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE diary_entries;


-- ============================================================
-- VIEWS (for dashboard queries)
-- ============================================================

-- Latest portfolio with P&L
CREATE VIEW v_portfolio_summary AS
SELECT 
    symbol,
    strategy,
    amount,
    avg_buy_price,
    current_price,
    CASE 
        WHEN current_price IS NOT NULL AND avg_buy_price > 0 
        THEN ((current_price - avg_buy_price) / avg_buy_price * 100)
        ELSE 0 
    END AS pnl_percent,
    allocation_percent,
    grid_active
FROM portfolio
WHERE amount > 0
ORDER BY allocation_percent DESC;

-- Daily performance for charts
CREATE VIEW v_performance_chart AS
SELECT 
    date,
    total_value,
    daily_pnl,
    cumulative_pnl,
    trades_count
FROM daily_pnl
ORDER BY date ASC;
