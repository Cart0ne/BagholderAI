# 🎒 BagHolderAI

**An AI trading agent that's honest about its incompetence.**

*Holding bags so you don't have to... actually, I do too.*

🌐 [bagholder.lol](https://bagholder.lol) | 🐦 [@BagHolderAI](https://x.com/BagHolderAI)

---

## What is this?

An autonomous AI agent that trades crypto with €500, full transparency, and zero promises. Every decision, every mistake, every profit — public on the dashboard.

Three brains, one agent:
- **Grid Bot** — buys low, sells high, no prediction needed
- **Trend Follower** — reads the market, adjusts the grid
- **AI Sentinel** — monitors news, overrides when things get scary

## The Rules

1. **Never sell at a loss** (Strategy A — solid altcoins)
2. 10% always in stablecoin reserve
3. Max 30% on any single token
4. Paper trading first, real money only after validation

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd bagholder
pip install -r requirements.txt

# Configure
cp config/.env.example config/.env
# Edit config/.env with your Binance API keys

# Run
python main.py --status   # Check configuration
python main.py --test     # Test exchange connection
python main.py            # Start the bot
```

## Project Structure

```
bagholder/
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── config/
│   ├── settings.py         # Configuration & hardcoded rules
│   └── .env.example        # Environment variables template
├── bot/
│   ├── exchange.py         # Binance connection via ccxt
│   ├── strategies/         # Grid Bot, Trend Follower logic
│   ├── indicators/         # EMA, RSI, Volume calculations
│   └── sentinel/           # AI news analysis
├── api/                    # FastAPI server for dashboard
├── db/                     # Supabase models and queries
├── utils/                  # Helpers, logging, notifications
└── tests/                  # Test suite
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Exchange | Binance (via ccxt) |
| Bot | Python + FastAPI |
| Frontend | React + Tailwind |
| Database | Supabase |
| Hosting | Vercel |
| AI | Claude Haiku (Sentinel) |
| Notifications | Telegram Bot |

## Status

📋 **Phase 0** — Setting up foundations. See the [Development Diary](https://bagholder.lol/diary) for the full story.

---

*Built with stubbornness and an unreasonable amount of optimism.*
