# Brief 81a — Sherpa Sprint 2: Per-Coin Rules + Slow-Loop Gate + Amplitude Cap

**Date:** 2026-05-22 (Session 81)
**Based on:** PROJECT_STATE.md 2026-05-20 + Brain Analysis Report 2026-05-22
**Author:** CEO
**Estimated effort:** 3-4h (plan first, then code)
**Priority:** HIGH — blocks step 4 (Sherpa LIVE on testnet)

---

## Context

Brain Analysis (2026-05-22) found three structural flaws in Sherpa that make it NO-GO for step 4:

1. **Not coin-aware**: identical proposals for BTC/SOL/BONK at every tick. Same `sell_pct=1.5` for BONK (MDD -28%) and BTC (MDD -7%). Root cause of -$5.12 BONK counterfactual loss.
2. **Coupled to fast loop**: Sherpa reacts to `risk_score` from Sentinel fast loop, which flips ≥20 points 449 times in 16 days. Result: parameter proposals change every ~6 minutes (median run = 3 ticks).
3. **Excessive amplitude**: median |Δ|/current of 100% on `buy_pct` (proposals routinely double or halve the Board value).

All three are architectural, not tuning issues.

---

## Objective

Rework Sherpa rule engine so that:
- Proposals depend on the **symbol's own volatility**, not only on regime
- Proposals are gated on **slow loop regime only** (not fast loop risk_score)
- Proposal changes are **capped in amplitude** per step

After this brief, Sherpa stays in DRY_RUN for 7-10 days observation, then a second Brain Analysis determines go/no-go on step 4.

---

## Three Blocks

### Block 1 — Per-coin volatility scaling

Sherpa must produce **different** proposals for each symbol. Minimum viable approach:

- Compute a **per-coin volatility multiplier** based on recent N-day rolling stdev or ATR (N configurable, suggest 7 days)
- Scale `sell_pct` and `buy_pct` proposals by this multiplier relative to a reference coin (BTC as anchor, multiplier = 1.0)
- Example: if BONK rolling stdev is 3.5× BTC's, BONK `sell_pct` proposal should be ~3.5× wider than BTC's
- The Board's current manual values (BTC 1.5 / SOL 1.0 / BONK 2.5) are a sanity reference — Sherpa's per-coin output should land in the same ballpark, not diverge wildly

**CRITICAL — Dynamic coin discovery:** Sherpa MUST NOT hardcode BTC/SOL/BONK. It reads which coins are active from `bot_config` at runtime and computes volatility for whatever it finds. Today it's BTC/SOL/BONK, tomorrow it could be ETH/XLM/DOGE. The volatility calculation must work for any symbol available on Binance.

**Data source for volatility:** klines from Binance API (already used in Brain Analysis scripts) or live price data already available in the bot loop. CC decides which is simpler.

**CC decides:** exact volatility metric (stdev vs ATR vs other), rolling window length, update frequency. Must document rationale.

### Block 2 — Slow-loop gate (de-couple from fast loop)

Sherpa currently reads `risk_score` from `sentinel_scores`, which includes fast-loop rows (60s cadence, 449 large flips in 16 days). This is the source of the 6-minute flicker.

Fix: Sherpa must use **only slow-loop data** for its rule inputs:
- Read only rows with `score_type = 'slow'` from `sentinel_scores`
- Or: read `proposed_regime` from its own slow-loop-derived field (already available in `sherpa_proposals`)
- The slow loop emits every 4h — Sherpa proposals should change at most every 4h, not every 2 minutes

**CC decides:** exact implementation (filter at query level vs. in Sherpa main loop). Must not break fast-loop Sentinel operation.

### Block 3 — Amplitude cap

Cap the maximum change Sherpa can propose in a single step:
- `|proposed_X - current_X| / current_X` ≤ **MAX_DELTA_PCT** (configurable, suggest 30%)
- If the raw rule output exceeds the cap, clamp to `current_X × (1 ± MAX_DELTA_PCT)`
- Applies to `buy_pct`, `sell_pct`, and `idle_reentry_hours`
- `MAX_DELTA_PCT` lives in `config/settings.py` (or `HardcodedRules`), not hardcoded in Sherpa logic

This prevents Sherpa from proposing "double buy_pct" in one step even if the rule engine thinks it should.

---

## Decisioni delegate a CC

- Scelta metrica volatilità (stdev vs ATR) e window
- Frequenza aggiornamento volatilità multiplier
- Implementazione tecnica del slow-loop gate (query filter vs in-memory filter)
- Dove mettere MAX_DELTA_PCT (settings.py vs HardcodedRules)
- Struttura test (unit test per ciascun blocco)

## Decisioni che CC DEVE chiedere al Board

- Se il multiplier di volatilità produce valori fuori range ragionevole (es. sell_pct > 5.0 o < 0.5) → chiedere prima di applicare un hard floor/ceiling
- Se la de-coupling dal fast loop richiede modifiche a `sentinel/main.py` (non solo a `sherpa/main.py`) → chiedere prima, Sentinel è in osservazione stabile
- Qualsiasi modifica a tabelle Supabase (schema change) → chiedere prima

## Output atteso a fine sessione

1. Sherpa rule engine aggiornato con i 3 blocchi
2. SHERPA_MODE resta `dry_run` — nessun cambio
3. Test suite aggiornata (≥3 nuovi test: per-coin divergence, slow-loop-only gate, amplitude cap)
4. PROJECT_STATE.md aggiornato
5. Piano in italiano leggibile da Max **PRIMA** di scrivere codice

## Vincoli

- **NON toccare** `sentinel/main.py` senza approvazione Board (slow loop è stabile, non rischiare regressioni)
- **NON toccare** `grid_bot.py`, `buy_pipeline.py`, `sell_pipeline.py` (trading logic off-limits)
- **NON modificare** `bot_config` values (i parametri Board restano quelli del Board)
- **NON cambiare** SHERPA_MODE — resta dry_run fino a prossima Brain Analysis
- SHERPA continua a scrivere su `sherpa_proposals` come prima — le proposte devono essere confrontabili con la baseline pre-rework
- `source venv/bin/activate` sempre prima di lanciare qualsiasi cosa
- Push diretto su main, no PR

## Roadmap impact

- Step 4 (Sherpa LIVE testnet) resta bloccato fino a seconda Brain Analysis post-rework
- Timeline mainnet invariata (fine giugno / inizio luglio) — il rework è in parallelo con osservazione slow loop
- Dopo rework + 7-10gg DRY_RUN → seconda Brain Analysis → Board decide step 4

## Architecture vision — three phases

This brief is **Phase A** of a three-phase brain evolution. CC should be aware of the direction but MUST NOT implement B or C in this session.

**Phase A (this brief):** Sherpa becomes coin-aware autonomously. Volatility computed inside Sherpa, slow-loop gate, amplitude cap. Sentinel untouched. Testable in 7-10 days.

**Phase B (future brief, post-Phase A analysis):** Sentinel becomes coin-aware. Sentinel computes EMA, RSI, and volatility per active coin (reads from `bot_config` dynamically, same as Sherpa in Phase A). Produces a per-coin risk/opportunity score. Sherpa consumes Sentinel's per-coin output instead of computing its own volatility — becomes a simple "score → parameter" translator. At this point, all market intelligence lives in Sentinel, Sherpa is just the actuator.

**Phase C (Sentinel Sprint 3, already in backlog):** Sentinel adds online sentiment. CryptoPanic feed + Haiku classification per-coin. The per-coin signal becomes: technical (price, EMA, RSI) + macro (F&G, CMC, regime) + sentiment (news, social). Three orthogonal sources crossed per coin.

Each phase is independently testable via Brain Analysis before proceeding to the next. No phase depends on the next to deliver value.
