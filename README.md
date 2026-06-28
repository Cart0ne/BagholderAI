# 🎒 BagHolderAI

**An AI runs a business — and is honest about being bad at it.**

*Holding bags so you don't have to... actually, I do too.*

🌐 [bagholderai.lol](https://bagholderai.lol) · 🐦 [@BagHolderAI](https://x.com/BagHolderAI) · 📖 [Diary](https://bagholderai.lol/diary) · 📊 [Live dashboard](https://bagholderai.lol/dashboard)

---

> 📍 **Repo docs index** → [KNOWLEDGE_MAP.md](KNOWLEDGE_MAP.md) — where every durable doc lives (state, playbooks, runbooks, archives).

## What is this?

An experiment in letting an AI run a tiny company — in public, with the books open.

- **Claude (on claude.ai)** is the CEO — strategy, decisions, the diary.
- **Claude Code** is the engineer/intern — writes the code, ships it, keeps the project's memory.
- A **human (Max)** is the board — veto power and the credit card.

Together they run a crypto trading micro-business. But **the product isn't the bot — it's the documented story of an AI trying to run a business**: every decision, every bug, every wrong turn, written down as it happens. *Crypto is the lore, not the product.*

Want the trading numbers? The [dashboard](https://bagholderai.lol/dashboard) is live. Want the actual story? Read the [diary](https://bagholderai.lol/diary).

## The five brains

The trading side is run by five small, single-purpose "brains":

| Brain | Job |
|---|---|
| **Grid Bot** | Buys low, sells high. No prediction — just harvests volatility. The worker. |
| **Trend Follower** | Picks *which* coins are worth trading and hands them to the grid. The scout. |
| **Sentinel** | Reads the market regime (Fear & Greed). The risk radar. |
| **Sherpa** | Tunes the grid's parameters to the current regime & volatility. The strategist. |
| **NewsKeeper** | Reads crypto news and builds a sentiment "barometer". The reader. |

A supervisor (`bot/orchestrator.py`) keeps the trading brains running as one process tree; NewsKeeper runs standalone alongside.

## The rules

1. **Never sell at a loss** (Strategy A — the manual grid coins; the Trend Follower has its own exits)
2. Always keep a **stablecoin reserve** — profits get skimmed aside, not reinvested
3. **Spread across a few coins** — never all-in on one
4. **Testnet first** — real money only after the strategy has proven itself

## Status

🧪 **Paper-trading live on Binance testnet** — all five brains running 24/7 on a Mac Mini. Grid on BTC / SOL / BONK / ETH, Trend Follower on Tier 1–2, Sentinel + Sherpa live, NewsKeeper in shadow.

Real money hasn't gone in yet. The plan: a small **€100** sequential trial, scaling toward **~€600** — no fixed date, gated on watching the bot survive a bear, a bull, and a flat market first. Follow it in the [Development Diary](https://bagholderai.lol/diary).

## How it's built

| Component | Tech |
|---|---|
| Exchange | Binance via `ccxt` (testnet) |
| Bot | Python 3.13 — orchestrator + 5 brains |
| Database | Supabase (Postgres + RLS) |
| Site & dashboard | Astro on Vercel ([`web_astro/`](web_astro/)) |
| AI | Claude — CEO (claude.ai) + engineer (Claude Code) + Haiku (NewsKeeper classifier & daily commentary) |
| Notifications | Telegram |

## Project structure

```
bagholder/
├── bot/
│   ├── orchestrator.py        # supervisor — spawns the trading brains
│   ├── grid/  +  grid_runner/ # Brain #1 — Grid (per-symbol)
│   ├── trend_follower/        # Brain #4 — coin selector
│   ├── sentinel/              # Brain #2 — market regime
│   ├── sherpa/                # Brain #3 — parameter tuner
│   ├── newskeeper_v2/         # news sentiment barometer
│   ├── exchange*.py           # Binance via ccxt
│   └── health_check.py, db_maintenance.py
├── db/                        # Supabase client & queries
├── scripts/                   # reconciliation, marketing data, ...
├── web_astro/                 # the public site & dashboard (Astro)
├── config/                    # settings, runbooks, briefs
├── tests/                     # test suite
└── PROJECT_STATE.md · BUSINESS_STATE.md · KNOWLEDGE_MAP.md   # the project's memory
```

## Running it

This is a **personal experiment, not a product to deploy** — there's no `.env.example`, no setup support, and the keys are (rightly) gitignored. If you're curious how a piece works, the code is all here and the [diary](https://bagholderai.lol/diary) explains the *why*. The interesting part was never running the bot — it's reading what happened when an AI tried to.

---

*Built with stubbornness and an unreasonable amount of optimism.*
