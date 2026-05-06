# Sentinel + Sherpa — Design Decisions v1

**Session:** 61 · May 6, 2026
**Status:** Board-approved design. Zero code yet.
**Next step:** First CC brief after Board go/no-go on live trading (~May 12)

---

## Architecture overview

```
Data Inputs → Sentinel → risk/opportunity score → Supabase → Sherpa → bot_config → Grid Bots
                                                                  ↑
                                                            Board (veto/override)
```

Visual diagram: `sentinel_sherpa_architecture_v2.html`

---

## Sentinel — the eyes

**Role:** Watches external data, produces a risk/opportunity score. Does NOT decide. Does NOT modify parameters.

**Structure:** `bot/sentinel/` — multifile from day zero.

```
bot/sentinel/
    price_monitor.py       # Fast loop: BTC price from Binance
    regime_analyzer.py     # Slow loop: F&G + CMC + funding
    score_engine.py        # Combines signals into risk/opportunity score

bot/sentinel/inputs/       # One file per data source, plug-and-play
    binance_btc.py         # Sprint 1: BTC price action
    binance_funding.py     # Sprint 1: Funding rates
    alternative_fng.py     # Sprint 2: Fear & Greed Index
    cmc_global.py          # Sprint 2: BTC dominance + market cap + volume
```

### Two-speed architecture

| Loop | Frequency | Inputs | Purpose |
|------|-----------|--------|---------|
| **Fast** | Every 1-2 min | BTC price (Binance), funding rates (Binance) | Detect crashes/pumps in real time. The "night guard." |
| **Slow** | Every 4-6h | Fear & Greed (alternative.me), BTC dominance + global metrics (CMC) | Set market regime (bull/bear/lateral). The "meteorologist." |

### Input details

| Input | Source | Cost | Frequency | Signal type |
|-------|--------|------|-----------|-------------|
| BTC price action | Binance API | Free | Real-time | **Anticipatory** (speed of fall, not just magnitude) |
| Funding rates | Binance API | Free | Every 8h | **Anticipatory** (over-leverage = pre-crash signal) |
| Fear & Greed Index | alternative.me API | Free | 1x/day | **Reactive** (confirms regime, doesn't predict) |
| BTC dominance | CMC `/v1/global-metrics/quotes/latest` | Free (10K credits/mo) | Every ~1 min available | **Slow trend** (capital flows alt↔BTC) |
| Total market cap | CMC (same endpoint) | Free | Same call | **Slow trend** (market expansion/contraction) |
| Total 24h volume | CMC (same endpoint) | Free | Same call | **Slow trend** (liquidity indicator) |

**Total API cost: €0/month**

### Sprint 3 — future inputs (NOT in MVP)

| Input | Source | Cost | Notes |
|-------|--------|------|-------|
| Crypto news | CryptoPanic API (free tier) or CMC content feeds ($29/mo) | Free or $29/mo | Requires LLM layer for classification |
| X sentiment | Grok/xAI scanner | ~$0.04/scan | Already built, needs automation |
| On-chain whale alerts | TBD | TBD | Exploratory |

News input requires `news_reader.py` + LLM (Haiku for cost). File: `bot/sentinel/inputs/news_cryptopanic.py`

### Important distinction

- **BTC as Sentinel input** = confirmed regardless of portfolio (it's a market indicator)
- **BTC as Grid asset** = TBD for live trading (high transfer/conversion costs)

---

## Sherpa — the coordinator

**Role:** Reads Sentinel score, translates into concrete parameter changes, writes to `bot_config` via Supabase. The decision-maker.

**Structure:** `bot/sherpa/` — separate Python process, multifile.

```
bot/sherpa/
    parameter_rules.py     # Logic: if score X → parameters Y
    config_writer.py       # Writes to bot_config via Supabase
    cooldown_manager.py    # Respects Board manual overrides
```

### What Sherpa controls (Level A / MVP)

| Parameter | Range | Bullish effect | Bearish effect |
|-----------|-------|----------------|----------------|
| `buy_pct` | 0.3% – 3.0% | Lower (buy more often) | Higher (buy only on deep dips) |
| `sell_pct` | 0.8% – 4.0% | Higher (let profits run) | Lower (take profit early) |
| `idle_reentry_hours` | 0.5h – 6h | Lower (more aggressive) | Higher (more cautious) |

### What Sherpa does NOT control (Level A)

| Parameter | Controller | Unlock condition |
|-----------|-----------|------------------|
| `capital_per_trade` | **Board-only** | Level B: after 3 manopole proven. Guardrails: max 20% of unallocated cash, hard cap per trade, logged. |

### Regime → parameter mapping (two layers)

**Slow loop sets the base:**

| Regime | buy_pct base | sell_pct base | idle_reentry base |
|--------|-------------|--------------|------------------|
| Extreme Fear (F&G 0-25) | 2.5% | 1.0% | 4h |
| Fear (25-45) | 1.8% | 1.2% | 2h |
| Neutral (45-55) | 1.0% | 1.5% | 1h |
| Greed (55-75) | 0.8% | 2.0% | 0.75h |
| Extreme Greed (75-100) | 0.5% | 3.0% | 0.5h |

**Fast loop adjusts on top:**

| Signal | Adjustment |
|--------|------------|
| BTC -3% in 1h | Tighten: buy_pct +50%, sell_pct -30%, idle_reentry +100% |
| BTC -5% in 1h | Full defensive: max buy_pct, min sell_pct, max idle_reentry |
| BTC +3% in 1h | Loosen: buy_pct -30%, sell_pct +50%, idle_reentry -50% |
| BTC +5% in 1h | Full aggressive: min buy_pct, max sell_pct, min idle_reentry |
| BTC flat | No adjustment (base from slow loop applies) |

Effects stack: bullish regime + bullish pump = double aggressive. Bearish regime + crash = double defensive.

### Cooldown mechanism

- Board modifies a parameter manually → logged in `config_changes_log` with source `manual-board`
- Sherpa detects the manual change → does NOT touch that specific parameter on that specific bot for **24 hours**
- After 24h → Sherpa resumes control, logs "cooldown expired"
- **Level B future:** configurable cooldown (12h / 24h / 48h / permanent lock)

### Communication

All three processes (Sentinel, Sherpa, Orchestrator) communicate **only via Supabase**. No direct connections. If one crashes, the others continue with last known state.

---

## Process architecture

Three independent Python processes:

| Process | File | Role | Crash impact |
|---------|------|------|-------------|
| `sentinel.py` | `bot/sentinel/` | Watches data, writes score | Sherpa uses last known score, Grid continues |
| `sherpa.py` | `bot/sherpa/` | Reads score, writes params | Grid continues with current params |
| `orchestrator.py` | existing | Launches/monitors bots | Bots restart on recovery |

Orchestrator may launch Sentinel and Sherpa as managed processes (TBD in implementation brief).

---

## Implementation sequence

| Sprint | What | Inputs | Deliverable |
|--------|------|--------|-------------|
| **1** | Sentinel fast loop + Sherpa base | BTC price + funding (Binance only) | Guardian: reacts to crashes/pumps in minutes |
| **2** | Sentinel slow loop | + Fear & Greed + CMC dominance | Meteorologist: sets bull/bear/lateral regime |
| **3** | News layer | + CryptoPanic / CMC content + LLM | Newspaper reader: interprets events |

Each sprint adds files to `bot/sentinel/inputs/` without modifying existing code.

### Prerequisites before Sprint 1

- [ ] Go/no-go on live trading (~May 12) — FIFO + health check gate
- [ ] Grid refactoring not blocking (Sherpa writes to `bot_config`, Grid reads — interface unchanged)
- [ ] CMC API key registered (free, immediate)

---

## Open items (to discuss in future sessions)

1. **TF → Grid coin flow:** when Sentinel/Sherpa coordinate, they need awareness of coins allocated by TF to Grid. Node identified in diagram, details TBD.
2. **Capital rebalancing (Level B):** Sherpa allocates extra budget from unallocated cash to specific bots during bullish regime. 20% cap proposed. Needs Board approval after Level A proven.
3. **Grid refactoring:** 2000+ line monolith. Planned modularization (S50). Not blocking for Sentinel/Sherpa but desirable. Can run in parallel.
4. **Trading skills evaluation:** brief_evaluate_trading_skills.md — Market Top Detector and FTD logic from external repos may become Sprint 3+ inputs if adaptable to crypto.
5. **Exact threshold calibration:** regime boundaries and fast-loop percentages are proposals. Need backtesting with historical data.
6. **BTC in live portfolio:** high transfer/conversion costs. Decision deferred to live trading go/no-go.

---

## CC rules (from Board)

- **Multifile from day zero.** No monoliths. One module per concern.
- **Direct push to main.** No PRs, no feature branches. Revert if broken.
- **Every commit updates roadmap** if impacted.
- **Sentinel and Sherpa are separate processes.** Never merge them.
