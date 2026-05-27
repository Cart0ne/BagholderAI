> ⚠️ **PARTIAL SHIP:** Session 1 of 4 SHIPPED (S83 — RSS feeds only, standalone).
> Sessions 2-4 pending — see PROJECT_STATE §10 S83 + §6.
> Sprint 1 scope changed vs this brief: see `brief_s83b_newskeeper_rss_pivot.md`.

# BRIEF — NewsKeeper Architecture (5th Brain)

**From:** CEO (Claude) — architectural design  
**For:** CC (Claude Code) — implementation in 4 sessions  
**Date:** May 23, 2026  
**Based on:** PROJECT_STATE.md as of S81 + Board brainstorming session May 23  
**Status:** APPROVED by Board. Moved from post-mainnet to PRE GO-LIVE.  
**Priority:** HIGH — blocking for mainnet go-live  

---

## Why This Changed Priority

Board exercise on May 23: retroactive analysis of the May 18-22 BTC crash ($82K → $76.8K). Results:

| Signal | Source | Available | Days before crash |
|--------|--------|-----------|-------------------|
| CPI 3.8% + PPI 6% | Macro news | May 13-14 | **4 days** |
| ETF outflows $635M | Financial data | May 14 | **4 days** |
| F&G 50 → 31 | alternative.me | May 6-16 | **2+ days** |
| Waller turns hawkish | Fed statement | May 20-21 | Confirmation |
| Google Trends "bear market" spike | Search trends | Weeks before | **Weeks** |

**Conclusion:** Sentinel Sprint 2 (F&G + regime) is reactive — it sees the crash when it's happening. NewsKeeper (macro news + ETF data) is predictive — it could have given 4 days of advance warning. Board decision: NewsKeeper is pre-mainnet, not post-mainnet.

---

## Architecture Overview

NewsKeeper is the **5th independent brain** — not bolted onto Sentinel. It has its own loop, its own data sources, its own DB table. It's designed as a **modular reader system**: each data source is a plugin.

```
                    ┌─────────────────┐
                    │   NewsKeeper    │  bot/newskeeper/
                    │   (5th brain)   │  independent process
                    └────────┬────────┘
                             │ writes
                             ▼
                    ┌─────────────────┐
                    │  newskeeper_    │  Supabase table
                    │  signals        │  
                    └────────┬────────┘
                             │ reads
                             ▼
        ┌────────────────────────────────────────┐
        │          Strategy Orchestrator          │
        │  reads: sentinel_scores + newskeeper_   │
        │  signals → calls Haiku → produces       │
        │  unified strategy recommendation        │
        └────────────────────┬───────────────────┘
                             │ writes
                             ▼
                    ┌─────────────────┐
                    │   bot_config    │  (via Sherpa or direct)
                    └─────────────────┘
```

### Key Design Principles

1. **Modular readers** — each data source is a file in `bot/newskeeper/readers/`. Adding a new source = adding one file, no changes to existing code
2. **Write-on-change** — follows S79 pattern: write to DB only when signal changes or heartbeat (10 min). Not every loop tick
3. **Haiku as strategist** — the LLM doesn't read raw news. It reads structured signals from Sentinel + NewsKeeper and outputs a strategy assessment. Cheap (~$0.001/call), fast, deterministic prompt
4. **Independent process** — if NewsKeeper crashes, Sentinel + Sherpa + Grid continue with last known state. Same isolation pattern as all other brains

---

## Implementation Plan: 4 Sessions

### Sessions 1-2: NewsKeeper Bot

**Deliverable:** `bot/newskeeper/` running as managed process in orchestrator, writing signals to `newskeeper_signals` table.

#### File structure

```
bot/newskeeper/
    __init__.py
    main.py              # Main loop (every 15 min default, configurable)
    signal_writer.py     # Write-on-change to Supabase
    readers/
        __init__.py
        cryptopanic.py   # Module 1: CryptoPanic free API
        etf_flows.py     # Module 2: ETF flow data (source TBD)
        macro_calendar.py # Module 3: scheduled macro events (CPI, FOMC, etc.)
```

#### DB table: `newskeeper_signals`

```sql
CREATE TABLE newskeeper_signals (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    source TEXT NOT NULL,           -- 'cryptopanic', 'etf_flows', 'macro_calendar'
    signal_type TEXT NOT NULL,      -- 'bearish_news', 'bullish_news', 'etf_outflow', 'rate_hike_signal', etc.
    severity TEXT NOT NULL,         -- 'low', 'medium', 'high', 'critical'
    summary TEXT NOT NULL,          -- human-readable 1-liner
    raw_data JSONB,                 -- original API response for audit
    expires_at TIMESTAMPTZ          -- signal relevance window (e.g., +24h for news, +7d for macro)
);
```

#### Module 1: CryptoPanic (`readers/cryptopanic.py`)

- **API:** `https://cryptopanic.com/api/free/v1/posts/` (free tier, no key needed for public posts)
- **Frequency:** every 15 min
- **Logic:** fetch latest posts, filter by `kind=news` and `currencies=BTC,SOL`, classify sentiment by CryptoPanic's own `votes` field (bearish/bullish/important)
- **Write:** only when a HIGH or CRITICAL severity news appears (≥3 bearish votes, or tagged "important" by community)
- **Cost:** €0

#### Module 2: ETF Flows (`readers/etf_flows.py`)

- **Source options (CC to evaluate):**
  - Farside Investors (scraping, fragile but free)
  - CoinGlass API (free tier may work)
  - Fallback: manual Board input via simple Supabase INSERT
- **Frequency:** daily (ETF data is daily)
- **Logic:** flag when daily outflows exceed threshold (e.g., >$500M = HIGH, >$1B = CRITICAL)
- **Cost:** €0 (free sources) or minimal

#### Module 3: Macro Calendar (`readers/macro_calendar.py`)

- **Approach:** static JSON of known scheduled events (FOMC dates, CPI release dates, tariff expiration July 24 2026)
- **Logic:** 48h before a scheduled event → write `signal_type='macro_event_upcoming'`, severity based on event type
- **No API needed** — this is a curated calendar updated manually by CEO/Board
- **Cost:** €0

#### Decisions delegated to CC

- Best free source for ETF flow data
- CryptoPanic API rate limits on free tier
- Whether to use `requests` directly or add a lightweight wrapper

#### Decisions CC MUST ask Board

- Any paid API (must stay at €0/month for now)
- Any change to orchestrator's process management beyond adding NewsKeeper as managed process

---

### Sessions 3-4: Strategy Orchestrator + Haiku Integration

**Deliverable:** A strategy layer that reads Sentinel + NewsKeeper, calls Haiku, and outputs a unified strategy recommendation.

#### File structure

```
bot/strategist/
    __init__.py
    main.py              # Loop every 30 min (or on-demand when signals change)
    signal_aggregator.py # Reads sentinel_scores + newskeeper_signals
    haiku_client.py      # Calls Anthropic API with structured prompt
    strategy_writer.py   # Writes recommendation to strategy_state table
```

#### DB table: `strategy_state`

```sql
CREATE TABLE strategy_state (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    regime TEXT NOT NULL,            -- from Sentinel: 'fear', 'neutral', 'greed', etc.
    news_context TEXT NOT NULL,      -- from NewsKeeper: 'bearish_macro', 'neutral', 'bullish_catalyst'
    recommendation TEXT NOT NULL,    -- Haiku output: 'defensive', 'neutral', 'aggressive'
    reasoning TEXT NOT NULL,         -- Haiku's 2-3 sentence explanation
    confidence FLOAT,               -- 0-1 scale
    active_signals JSONB,           -- list of signals that informed this decision
    expires_at TIMESTAMPTZ          -- recommendation validity (e.g., +4h)
);
```

#### Haiku Prompt Design (CEO will refine)

```
You are a crypto market strategist for a small grid trading bot (€100 capital, BTC/SOL/BONK).

Current data:
- Sentinel regime: {regime} (risk: {risk_score}, opportunity: {opp_score})
- Fear & Greed Index: {fng_value} ({fng_label})
- BTC dominance: {btc_dom}%
- Active news signals: {signals_list}
- Recent ETF flows: {etf_summary}
- Upcoming macro events: {macro_events}

Based on this data, output a JSON object:
{
  "recommendation": "defensive" | "neutral" | "aggressive",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 sentences explaining why"
}

Rules:
- If multiple HIGH/CRITICAL bearish signals + fear regime → defensive
- If no significant signals + neutral/greed regime → neutral or aggressive
- When in doubt, be defensive (€100 capital, preservation > growth)
- Output ONLY the JSON, no preamble
```

#### How Sherpa reads the strategy

Sherpa already reads `sentinel_scores` to pick regime. New behavior:
- Also reads latest `strategy_state` row
- If recommendation = "defensive" → use fear-row from BASE_TABLE regardless of Sentinel regime
- If recommendation = "aggressive" → use greed-row
- If recommendation = "neutral" → use Sentinel regime as before (no change)

This is the minimal integration point. Sherpa's existing code changes by ~10-15 lines.

#### Decisions delegated to CC

- Haiku API call implementation (use existing Anthropic SDK or raw requests)
- Exact polling frequency for signal_aggregator
- Whether strategist runs as its own process or as a function called by Sherpa's loop

#### Decisions CC MUST ask Board

- Any Haiku prompt changes beyond formatting
- Cost estimate per month for Haiku calls (should be <$1/month at 30min intervals)
- Any changes to Sherpa's parameter selection logic beyond the 3-line regime override

---

## Testing Plan

**Dry run from day one.** NewsKeeper + Strategist write to DB but don't affect bot_config.

**Go-live criteria (Board decides, no fixed date):**
- System has observed at least one period each of: bear, bull, lateral
- NewsKeeper correctly flagged at least one significant event before price moved
- Haiku recommendations are consistent and not contradictory to Sentinel
- Zero crashes, zero orphan signals, write-on-change working (IO budget OK)
- Board reads dashboard and says: "this makes sense"

**Dashboard:** add NewsKeeper + Strategist widgets to `/admin` (separate brief, after core is working).

---

## What This Brief Does NOT Cover

- Grok/X scanner module (post-mainnet, requires premium API)
- On-chain whale alerts (exploratory, no timeline)
- Per-coin NewsKeeper signals (start BTC-only, expand later)
- Changes to Grid bot logic (Grid stays untouched)
- Changes to TF logic (TF stays untouched)

---

## Roadmap Impact

- Sentinel Sprint 3 line item → replaced by "NewsKeeper + Strategist"
- Go-live sequence updated: Brain Analysis → NewsKeeper build → Sherpa testnet → dry_run observation → Board approval → mainnet
- No fixed date for mainnet — depends on market conditions providing test scenarios

---

## Cost Summary

| Item | Monthly cost |
|------|-------------|
| CryptoPanic API | €0 (free tier) |
| ETF data source | €0 (free source) |
| Macro calendar | €0 (static JSON) |
| Haiku API calls (~48/day) | <€1/month |
| Supabase writes | Within free tier (write-on-change) |
| **Total** | **<€1/month** |

---

*Brief by CEO (Claude), BagHolderAI. Approved by Board (Max), May 23, 2026.*
