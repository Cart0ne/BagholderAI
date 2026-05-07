# BRIEF — Evaluate External Trading Skills for Claude Code

## Context

We've discovered that the Claude Code skill ecosystem includes trading-specific skills that could accelerate our development — especially for Sentinel (Phase 3) and Trend Follower improvements. Before building everything custom, we want to evaluate what exists and what's worth adopting.

This is an **exploration brief**, not an implementation brief. The goal is: install, read, test, and report back.

## Priority 1: `tradermonty/claude-trading-skills`

**Repo:** https://github.com/tradermonty/claude-trading-skills

**Why it matters:** This repo contains skills specifically designed for market analysis and timing — exactly what Sentinel needs to do. Two skills in particular are directly relevant:

### Market Top Detector
- Detects distribution days (O'Neil methodology)
- Monitors leading stock deterioration
- Tactical timing system for identifying topping patterns
- **Sentinel relevance:** This is basically the "bear market incoming" signal we need

### Follow-Through Day (FTD) Detector
- Confirms market bottoms after corrections
- Generates a quality score (0-100) with exposure guidance
- Dual-index tracking (S&P 500 + NASDAQ)
- **Sentinel relevance:** This is the "safe to re-enter" signal — the other half of Sentinel's job

### Other potentially useful skills in the same repo:
- Signal Quality Auditor — could help us measure TF signal quality over time
- Downtrend Duration Analyzer — historical analysis of how long downtrends last
- Data Quality Checker — validates market data before use

### What to do:
1. Clone the repo
2. Read each SKILL.md — understand what they do, what APIs they need (some require FMP API key)
3. Check compatibility: do they work with crypto, or are they equity-only?
4. Check data requirements: what do they need that we don't have?
5. Install the most promising ones in `.claude/skills/`
6. Try running the Market Top Detector and FTD against current BTC/crypto data
7. Report: what works, what doesn't, what needs adaptation

## Priority 2: `JoelLewis/finance_skills` — Risk Management

**Repo:** https://github.com/JoelLewis/finance_skills

**Why it matters:** ATR-based position sizing and portfolio heat monitoring. We already use ATR for grid steps — this could formalize our risk management.

### What to do:
1. Look at the `wealth-management` plugin, specifically the `risk-measurement` skill
2. Check if the ATR-based stop and sizing logic is compatible with our grid bot approach
3. Report: useful as-is, needs adaptation, or not relevant?

## Priority 3: `ScientiaCapital/skills` — Signal Generation

**Repo:** https://github.com/scientiacapital/skills

**Why it matters:** Translates strategy rules from natural language to vectorized Python. Could speed up testing new TF strategies.

### What to do:
1. Read the `active/signal-generation` SKILL.md
2. Assess: would this help us iterate on TF scan logic faster?
3. Report back — low priority, just a read-and-assess

## Deliverable

A short report (can be in chat, doesn't need to be a doc) covering:

1. **What's directly usable** — skills that work with crypto data and our existing setup
2. **What needs adaptation** — skills designed for equities that could be modified for crypto
3. **What's not relevant** — skills we can skip
4. **API requirements** — any paid APIs needed (FMP, EODHD, etc.) and rough costs
5. **Recommendation** — which skills to install permanently, which to skip

## Important Notes

- This is exploration only. Don't integrate anything into the trading bots yet.
- Some skills may require API keys we don't have (FMP, EODHD). Note which ones and their costs.
- Our data source is Binance API — check if the skills can work with that or need adaptation.
- We trade crypto only (BTC, SOL, BONK + TF rotation coins). Equity-only skills may still have useful logic we can adapt.
- Report honestly if nothing is worth adopting. Building custom is fine if the existing skills don't fit.
