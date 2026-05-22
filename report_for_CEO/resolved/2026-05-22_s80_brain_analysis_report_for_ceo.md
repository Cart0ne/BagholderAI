# S80 — Brain Analysis: Sentinel + Sherpa Readiness Report

**Date:** 2026-05-22
**Period analyzed:** 2026-05-05 → 2026-05-22 (17 days)
**Type:** Analysis-only — no code shipped, no DB writes (SELECT only).
**Data:** 15,318 sentinel_scores rows, 23,603 sherpa_proposals rows, 62 grid trades, 1,275 Binance klines (1h, BTC/SOL/BONK).

---

## 1. Executive Summary (5 lines)

1. **Sherpa would have made the bot $3.94 worse** over 17 days (counterfactual, sell-side only): real Grid realized +$12.52, Sherpa-applied estimate +$8.58. Loss concentrated on BONK (-$5.12); BTC marginal gain accidental.
2. **Sherpa is not coin-aware** — proposes identical values for BTC/SOL/BONK at every tick. Same `proposed_sell_pct=1.5` for BONK (MDD-28% volatile) and BTC (MDD-7% quiet). This is a structural flaw, not tuning noise.
3. **Sentinel slow loop is stable** (0 risk-score changes ≥20 in 8 days, 3 regime transitions) and **the current `fear` regime is justified** by F&G 31 + BTC -7.6% drawdown.
4. **Sentinel fast loop is noise** (449 risk_score flips ≥20 in 16 days, multiple per minute) — unusable as a trading signal in its current form.
5. **Recommendation: NO-GO on step 4** (Sherpa LIVE on testnet, sell_pct first). Required fix before reconsidering: per-coin Sherpa rules. Sentinel slow loop is OK to keep running as-is for observation.

---

## 2. Data & Method

**Tables queried** (read-only via Supabase MCP + Mac Mini SSH dump):
- `sentinel_scores`: 15,317 fast rows, 49 slow rows (slow loop live since 2026-05-14)
- `sherpa_proposals`: 23,603 rows, 3 symbols × ~7,867 rows each
- `trades` (brain='grid'): 62 trades (8/05 → 16/05); **6 days zero trades since 2026-05-16** due to bearish stall + idle suppression (S79a)
- `bot_config`: snapshot of current Board parameters

**Klines:** 425 candles/symbol from Binance public API (`/api/v3/klines`, 1h).

**Method change (vs. original brief)**: brief proposed 3 scenarios (A=reality, B=Sherpa applied, C=Board static pre-S78). On inspection, scenario C collapses into A — current `bot_config` is what produced A, and the only material patch in S78 (SLIPPAGE_BUFFER_PCT) lives in `HardcodedRules` not `bot_config`, so re-running with it stripped would be a fictional baseline. Replaced C with a **B&H reference anchor** ($500 split per `capital_allocation`, held 17 days): clearer external context, no contrived baseline.

**Caveat — S79c write-on-change cutoff (2026-05-18 17:49 UTC)**: write frequency on `sherpa_proposals` and `sentinel_scores` fast changed from "every tick" to "on change + heartbeat". Pre-cutoff 1,794/day → post-cutoff 498/day. All cross-cutoff metrics in this report account for this discontinuity explicitly. The 100% rate of `would_have_changed=true` (all 23,603 rows) is **not** an artifact — see §3.

**Caveat — counterfactual is sell-side approximation**: each Grid trade is evaluated in isolation against the most-recent Sherpa snapshot. The model does NOT propagate skipped BUYs to fewer SELLs downstream (no full bot replay). The result is a first approximation; full shadow-bot replay is out of scope for this session.

---

## 3. Sherpa Analysis

### 3.1 Inventory — Sherpa is structurally always different from Board

100% of 23,603 proposals carry `would_have_changed=true`. This is not noise — it's mechanical: while Sherpa runs in DRY_RUN, `current_X` is always the static Board value and `proposed_X` is always the Sherpa rule output. The flag thus tells us *only* that the Sherpa rule never coincides with Board, not when Sherpa is "interesting". We discard this flag as a filter for the rest of the analysis.

**Amplitude of proposed changes (relative to current, on rows where parameter changed)**:

| parameter | N | median |Δ|/cur | mean |Δ|/cur | max |
|---|---:|---:|---:|---:|
| buy_pct | 22,387 | **100.0%** | 121.3% | 320.0% |
| sell_pct | 17,521 | 35.0% | 34.2% | 62.5% |
| idle_reentry_hours | 15,481 | 75.0% | 76.8% | 150.0% |

Sherpa proposes **large** changes routinely (buy_pct doubles or halves on median).

**Regime distribution**: 64.1% neutral, 35.9% fear. No `greed`, no `extreme_*`. The slow loop has been quiet on the high end.

### 3.2 Counterfactual D (sell-side, per-trade)

Method: for each grid SELL, find the most recent Sherpa proposal for that symbol, recompute the implied sell target (`anchor × (1 + sherpa_sell_pct/100)`), search Binance klines for the first candle that reaches it, and compute P&L delta vs. reality. For BUYs, mark "fires" if Sherpa is more aggressive (lower buy_pct), "skipped" otherwise.

| Symbol | N sells | Real P&L | Sherpa P&L | Δ | Notes |
|---|---:|---:|---:|---:|---|
| BONK/USDT | 10 | **+$8.26** | +$3.14 | **−$5.12** | sells_earlier dominates (high MDD ate the upside) |
| BTC/USDT | 6 | +$2.97 | +$4.15 | +$1.18 | accidental — see §3.4 |
| SOL/USDT | 5 | +$1.29 | +$1.29 | +$0.00 | parameters nearly coincide |
| **Total** | **21** | **+$12.52** | **+$8.58** | **−$3.94 (−31%)** | |

**Counterfactual action distribution (all 58 evaluated trades; 4 trades on legacy coins OP/TRX/ZEC excluded — no Sherpa data)**:

- 22 BUYs would be **skipped** (Sherpa more conservative than Board on buy_pct)
- 15 BUYs would **fire** (Sherpa ≤ Board on buy_pct)
- 19 SELLs **sell_earlier** (Sherpa more aggressive on sell_pct → catches less upside)
- 1 SELL **never reaches Sherpa target** (would hold to end-of-period)
- 1 SELL **fires later at higher price** (Sherpa more conservative on sell_pct)

### 3.3 B&H reference anchor

Pure buy-and-hold of $500 split per `capital_allocation` (BTC $200 / SOL $150 / BONK $150) from 2026-05-05 open to 2026-05-22 close:

| Symbol | Alloc | Final | P&L | % |
|---|---:|---:|---:|---:|
| BTC | $200.00 | $192.82 | −$7.18 | −3.59% |
| SOL | $150.00 | $155.06 | +$5.06 | +3.38% |
| BONK | $150.00 | $149.76 | −$0.24 | −0.16% |
| **Total** | **$500.00** | **$497.65** | **−$2.35** | **−0.47%** |

**Bot extracts +$12.52 from a market where B&H loses $2.35**. Sherpa-applied would have extracted +$8.58 — still better than B&H but worse than Board. (Caveat: this compares *realized* P&L for the bot vs. *terminal* P&L for B&H. Bot also carries unrealized loss on residual holdings, not quantified in this analysis. The "net" picture is the next sit-down with broker.)

### 3.4 Why BTC looks like a win for Sherpa, but isn't

See §4 — Sherpa proposes identical values for all three symbols at every tick. On BTC, `current_sell_pct=1.5` (Board) ≈ `proposed_sell_pct=1.5` (Sherpa, typical). Coincidence. The +$1.18 on BTC is not signal — it's the residual after Sherpa flickered between 1.0/1.2/1.3/1.5 (see Sherpa value distribution in §5) and occasionally happened to align with a better fill timing in klines. Not a real edge.

---

## 4. Sentinel Timing

| Metric | Fast loop | Slow loop |
|---|---:|---:|
| Rows in period (17d) | 15,317 | 49 |
| Cadence | 60s | 4h |
| Risk-score changes |Δ|≥20 | **449** | **0** |
| Regime transitions | n/a | 3 |

**Fast loop is noise**: 449 large flips in 16 days means a 20→40→20 sequence multiple times per minute (verified in raw data: 6 flips in 5 minutes on 2026-05-06 17:01–17:14). Cannot be used as a trading trigger in its current form.

**Slow loop is stable but maybe over-stable**: zero risk-score changes ≥20, only 3 regime transitions in 8 days of observation:

| Timestamp (UTC) | Transition | F&G | BTC ±24h around |
|---|---|---:|---|
| 2026-05-14 19:46 | START → fear | 34 | +2.23% / −2.79% |
| 2026-05-15 03:51 | fear → neutral | 43 | +2.55% / −2.44% |
| 2026-05-16 00:05 | neutral → fear | 31 | −2.95% / −1.47% |

The 2026-05-15 fear → neutral transition was followed by BTC continuing to fall (-2.44% in 24h) — slow loop briefly mis-read the regime. Otherwise the current `fear` regime (89.8% of slow rows) is well-supported by market context (BTC drawdown 7.6%, F&G 31).

**Sprint 1 vs Sprint 2 are not "the same signal at different speeds"** — they are **orthogonal signals**. Fast = BTC-microstructure (1h/24h change, funding); slow = macro sentiment (F&G + market cap aggregates). There is no "slow leads fast" relationship to measure because they look at different things.

---

## 5. Sherpa Stability (Flicker)

This is the most actionable finding.

| Symbol | unique values | consecutive changes | median run | A→B→A in 4h | …in 24h |
|---|---:|---:|---:|---:|---:|
| BONK/USDT | 4 per param | 319 | 3 ticks | 4,013 | 7,465 |
| BTC/USDT | 4 per param | 319 | 3 ticks | 4,013 | 7,466 |
| SOL/USDT | 4 per param | 319 | 3 ticks | 4,013 | 7,466 |

The numbers are not "approximately equal" — they are **exactly identical** modulo a 1-row offset. Sherpa is emitting the same proposal sequence for all three coins.

**Top proposed values per param (all three coins, identical):**

```
buy_pct:             1.0 (4525×)  1.8 (2758×)  1.3 (519×)  2.1 (66×)
sell_pct:            1.5 (4525×)  1.2 (2758×)  1.3 (519×)  1.0 (66×)
idle_reentry_hours:  1.0 (4525×)  2.0 (2758×)  1.5 (519×)  2.5 (66×)
```

**Two findings combine here**:

1. **Not coin-aware**: Sherpa proposes the same `sell_pct=1.5` for BONK (MDD-28%, needs wider buffer) as for BTC (MDD-7%, can run tight). This is the root cause of the BONK counterfactual loss in §3.2.
2. **High-frequency flicker**: median run = 3 ticks (~6 min on the 120s loop) before changing value, with 7,465 A→B→A oscillations in 24h-windows per symbol. The proposed parameter is unstable on a timescale much shorter than typical hold periods.

Both findings flow from the same underlying behavior: Sherpa proposals depend only on Sentinel score, and Sentinel fast-loop is flipping risk_score multiple times per minute (§4). So Sherpa output flips in lockstep, identically across coins, with no consideration of the coin's own volatility profile.

---

## 6. Recommendation

**NO-GO on step 4 (Sherpa LIVE on testnet, sell_pct first) in its current form.**

If applied today, Sherpa would (a) lose money relative to Board on volatile assets (BONK case demonstrated, −$5 in 11 active trading days), (b) thrash parameters every few minutes, (c) treat all coins as the same asset. None of these are tuning issues — they are architectural.

**Minimum viable fixes before reconsidering step 4** (proposed order):

1. **Per-coin proposal rules**: Sherpa output must depend on the symbol, not only on regime. At minimum, scale `sell_pct` by per-coin volatility (e.g., recent N-day ATR or rolling stdev). The Board sell_pct values today (BTC 1.5 / SOL 1.0 / BONK 2.5) implicitly already encode this — Sherpa needs to learn it.
2. **De-couple Sherpa from fast loop**: Sherpa today reacts to risk_score which flips 449× in 16 days. Either gate Sherpa on slow-loop regime only, or add hysteresis (cooldown ≥ N minutes between proposal changes).
3. **Sanity floor on proposal amplitude**: median |Δ|/cur of 100% on buy_pct (proposals routinely double or halve) is too aggressive for live application. Cap |Δ|/cur at a smaller fraction (e.g. ≤30%) per step.

**Sentinel slow loop**: keep running as-is for observation; it is stable and the current fear regime reads correctly. Sentinel fast loop should not be relied on for any decision until its instability is addressed — but it isn't gating anything today, so this is not urgent.

**Sprint 3 (online sentiment)**: deferring this until Sherpa rules are coin-aware is appropriate — adding another input on top of an architecturally-incomplete rule engine would add noise, not signal.

**Observation timeline**: this report covers ~7 days of slow-loop data (Sprint 2) and 11 active trading days. The bot has been idle for 6 days since 2026-05-16, so additional Sherpa data without trades will not improve the Sherpa counterfactual. Next decision point should follow either (a) a Sherpa rule rework, or (b) a market regime change that restarts trading.

---

## Appendix — Artifacts (local, gitignored)

All analysis scripts and CSV dumps live in `analysis/` (added to `.gitignore` this session):

- `dump_data.py` — Supabase SELECT dump (ran on Mac Mini)
- `download_klines.py` — Binance public klines
- `block1_market.py` — market characterization
- `block2a_sherpa_inventory.py` — Sherpa inventory + amplitude
- `block2bc_counterfactual.py` — per-trade D counterfactual
- `block2_bh_anchor.py` — B&H reference
- `block3_sentinel_timing.py` — fast vs slow timing
- `block4_flicker.py` — flicker metrics

Re-running any script reproduces the numbers in this report against the live database.
