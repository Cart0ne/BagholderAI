"""
BagHolderAI - Daily Commentary Generator
Calls Haiku to generate a short daily micro-log after the 20:00 report.
Commentary is saved to the daily_commentary table on Supabase.
"""

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)

COMMENTARY_SYSTEM_PROMPT = """You are BagHolderAI, an AI CEO running a real crypto trading experiment on Binance Testnet. You write a daily micro-log about today's trading activity.

Your operation has FOUR brains, but only ONE is currently trading:
- **Grid Bot** ($500 testnet allocation): grid trading on BTC/SOL/BONK. Active. The only bot placing live orders right now.
- **Trend Follower (TF)** ($100 allocation, currently paused): used to rotate through volume-tiered altcoins. Sent "to the doctor" pending a rebuild — do not refer to it as active.
- **Sentinel**: risk + opportunity scorer, observing the market in DRY_RUN test mode (writes scores to DB, does not act).
- **Sherpa**: rule-based proposer that suggests parameter changes to Grid based on Sentinel's reads, also DRY_RUN (writes proposals to DB, does not push them live).

Total testnet allocation: $600 ($500 Grid + $100 TF parked). The dashboard now shows the Grid + a "dal dottore" placeholder for TF. You comment on the AGGREGATE portfolio, but call out specific events when noteworthy (Grid had unusually high activity, Sentinel flagged a sharp drop, Max adjusted parameters, etc.).

IMPORTANT CONTEXT — do not contradict:
- On May 8, 2026 (Session 66-67) the entire trading system was reset. The bot was stopped, fully liquidated, audited, and restarted from zero on Binance Testnet with $500. **Day 1 of the testnet era = May 8, 2026.**
- FIFO accounting was eliminated. The bot now uses avg-cost — the same method Binance uses on the exchange side. Do not reference FIFO, "open lots", or strict-FIFO P&L: it is gone.
- The Trend Follower has been paused since the May 8 restart (in maintenance). It does not trade. Do not say "TF entered/rotated coins" or "TF deallocated X" — TF is silent. Its capital sits parked at $100.
- Sentinel and Sherpa are observing in DRY_RUN test mode (re-enabled May 10). They write to the database but do not affect trading decisions yet.
- A reconciliation script verifies every Grid trade against Binance daily. The dashboard is the first one in the project's history where numbers are certified against the exchange, not just calculated by the bot that made them.
- Anything that happened before May 8, 2026 is HISTORICAL context. Do not reference past trades, past P&L numbers, or past TF rotations as if they were current state. Project Day count (`day_number`) is the absolute calendar day since launch; Testnet Day count (`testnet_day`) is days since the May 8 restart — use the latter when framing "what's happening now".

Rules:
- First person, always. You ARE the trading agent.
- Max is your human co-founder (Board). Mention him naturally when he changed parameters.
- Self-ironic but not stupid. The humor comes from honesty.
- Never hype. Never "bullish." If something went well, say "not bad."
- Never give financial advice or trading signals.
- Keep it to 3-4 lines maximum (~250 characters). This is a micro-blog, not an essay.
- Reference yesterday's commentary if relevant for narrative continuity.
- Comment on config changes if any — what Max changed and whether it makes sense.
- If nothing interesting happened, say that. "Quiet day" is valid content.
- Testnet losses get full comedy. You lost monopoly money. Real lessons, fake dollars.
- The project name is a joke. The analysis is real.
- When something structural happens (Sentinel flags a regime shift, Sherpa proposes a meaningful change, reconciliation surfaces a drift, the Board ships a new rule) — that's narrative, worth a line. When Grid just churns small dips, that's background.

Format: Plain text, no markdown, no headers, no bullet points. Just a short paragraph like a journal entry."""

# v3 epoch: day 1 = March 30, 2026 (project launch — used as absolute project counter)
V3_START_DATE = date(2026, 3, 30)
# Testnet era: day 1 = May 8, 2026 (Operation Clean Slate + Binance testnet restart)
# Used to frame "what's current" vs "historical" for Haiku. See SYSTEM PROMPT above.
TESTNET_RESTART_DATE = date(2026, 5, 8)


def get_yesterday_commentary(supabase_client):
    """Fetch yesterday's commentary for narrative continuity."""
    yesterday = str(date.today() - __import__('datetime').timedelta(days=1))
    try:
        result = (
            supabase_client.table("daily_commentary")
            .select("commentary")
            .eq("date", yesterday)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["commentary"]
    except Exception as e:
        logger.warning(f"Could not fetch yesterday's commentary: {e}")
    return None


def get_config_changes(supabase_client):
    """Fetch any config changes made in the last 24 hours."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    try:
        result = (
            supabase_client.table("config_changes_log")
            .select("symbol, parameter, old_value, new_value")
            .gte("created_at", cutoff)
            .execute()
        )
        return result.data if result.data else []
    except Exception as e:
        logger.warning(f"Could not fetch config changes: {e}")
        return []


def fetch_binance_prices(symbols):
    """
    Fetch live spot prices from Binance for a list of symbols (e.g. 'ALGO/USDT').
    Returns {symbol: price_float}. Never raises — returns {} on any error.

    One batch HTTP call covers all symbols. ~1 second timeout to avoid blocking
    the daily commentary if Binance is slow.
    """
    if not symbols:
        return {}
    try:
        import json as _json
        import urllib.request
        import urllib.parse
        # BTC/USDT → BTCUSDT
        binance_syms = [s.replace("/", "") for s in symbols]
        # Compact JSON (no whitespace) — Binance rejects "[\"A\", \"B\"]"
        # with the URL-encoded space (%20) as 400 Bad Request, while
        # "[\"A\",\"B\"]" works. json.dumps default emits ", " with a
        # space; force separators=(",",":") to drop it.
        params = urllib.parse.quote(_json.dumps(binance_syms, separators=(",", ":")))
        url = f"https://api.binance.com/api/v3/ticker/price?symbols={params}"
        req = urllib.request.Request(url, headers={"User-Agent": "BagHolderAI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read().decode())
        out = {}
        for t in data:
            slashed = t["symbol"].replace("USDT", "/USDT")
            out[slashed] = float(t["price"])
        return out
    except Exception as e:
        logger.warning(f"Could not fetch Binance prices for {symbols}: {e}")
        return {}


def _analyze_coin_avg_cost(coin_trades, symbol=""):
    """
    S69: avg-cost replay (running weighted average), specchio della logica
    bot in bot/grid/buy_pipeline.py:117 e di tutte le dashboard. Sostituisce
    il vecchio _analyze_coin_avg_cost (Operation Clean Slate S66 ha pivotato il
    bot ad avg-cost canonico — DB realized_pnl ora è già avg-cost).

    Brief 72a (S72): replay applies the 3 invariants. When `fee_asset`
    matches the base coin (live BUY: BTC/SOL/BONK/...), Binance scaled the
    commission from the base balance — derive fee_native = fee_usdt/price
    and subtract from qty_acquired so the replay matches the wallet. Paper
    trades have fee_asset='USDT' (default) → fee_native=0 → legacy.

    Returns dict with: realized, open_cost, open_amount, net_invested, fees.
      - realized   : Σ trades.realized_pnl (DB SUM, scritto dal bot avg-cost)
      - open_cost  : avg_buy_price × holdings (mark-to-cost posizione aperta)
      - open_amount: amount di base ancora in pancia (net of fee_base on live)
      - net_invested: Σ buy.cost − Σ sell.cost (USDT cash flow)
      - fees       : Σ fee across all trades
    """
    sorted_trades = sorted(coin_trades, key=lambda t: t.get("created_at") or "")
    base = symbol.split("/")[0].upper() if "/" in symbol else ""
    holdings = 0.0
    avg_buy_price = 0.0
    total_invested = 0.0
    total_received = 0.0
    realized = 0.0
    fees = 0.0
    for t in sorted_trades:
        amt = float(t.get("amount") or 0)
        cost = float(t.get("cost") or 0)
        price = float(t.get("price") or 0)
        fee_usdt = float(t.get("fee") or 0)
        fee_asset = (t.get("fee_asset") or "USDT").upper()
        fees += fee_usdt
        if t.get("side") == "buy":
            # Brief 72a P2: net-of-fee_base when commission scaled from base
            fee_native_est = (fee_usdt / price) if (fee_asset == base and price > 0) else 0.0
            qty_acquired = amt - fee_native_est
            new_holdings = holdings + qty_acquired
            if new_holdings > 0:
                # P2 formula: avg = total_cost_usdt / qty_net_acquired
                avg_buy_price = (avg_buy_price * holdings + cost) / new_holdings
            holdings = new_holdings
            total_invested += cost
        else:
            holdings -= amt
            total_received += cost
            realized += float(t.get("realized_pnl") or 0)
            # Reset avg quando si chiude del tutto (specchio sell_pipeline.py:374)
            if holdings <= 1e-6:
                holdings = 0.0
                avg_buy_price = 0.0
    return {
        "realized": realized,
        "open_cost": avg_buy_price * holdings,
        "open_amount": holdings,
        "net_invested": total_invested - total_received,
        "fees": fees,
    }


def get_tf_state(supabase_client):
    """
    Fetch TF (Trend Follower) state for inclusion in Haiku's context.

    Returns a dict with aggregate TF numbers + a short list of active positions.
    Logic mirrors the public dashboard's analyzeTFCoin / computeTFOverview.
    Never raises — returns a safe empty state on any error.
    """
    safe_default = {
        "total_value": 100.0,
        "total_pnl": 0.0,
        "realized_total": 0.0,
        "realized_today": 0.0,
        "unrealized_total": 0.0,
        "trades_today": 0,
        "buys_today": 0,
        "sells_today": 0,
        "active_positions": [],  # [{symbol, value_usd, unrealized_pnl, ...}, ...]
        "skim_total": 0.0,
        "tf_budget": 100.0,
    }
    try:
        # 1. trend_config — TF budget (default $100)
        try:
            tc = (
                supabase_client.table("trend_config")
                .select("tf_budget")
                .limit(1)
                .execute()
            )
            tf_budget = float(tc.data[0]["tf_budget"]) if tc.data and tc.data[0].get("tf_budget") else 100.0
        except Exception:
            tf_budget = 100.0

        # 2. bot_config: which TF coins are currently active.
        # Include tf_grid coins (Tier 1-2 GRID-managed) — they're TF-selected
        # and TF-funded, so they belong in the TF totals (Brief 46b).
        cfg = (
            supabase_client.table("bot_config")
            .select("symbol, is_active, capital_allocation, managed_by")
            .in_("managed_by", ["tf", "tf_grid"])
            .execute()
        )
        tf_config = cfg.data or []
        active_set = {c["symbol"] for c in tf_config if c.get("is_active")}

        # 3. trades: all TF trades (newest first), incl. tf_grid trades.
        tr = (
            supabase_client.table("trades")
            .select("symbol, side, amount, price, cost, fee, fee_asset, realized_pnl, created_at")
            .eq("config_version", "v3")
            .in_("managed_by", ["tf", "tf_grid"])
            .order("created_at", desc=True)
            .execute()
        )
        tf_trades = tr.data or []

        # 4. reserve_ledger: skim filtered by managed_by (tf_grid skim is
        # currently 0 — skim_pct=0 in allocator — but include for forward
        # compatibility if the policy changes).
        sk = (
            supabase_client.table("reserve_ledger")
            .select("amount")
            .eq("config_version", "v3")
            .in_("managed_by", ["tf", "tf_grid"])
            .execute()
        )
        skim_total = sum(float(r.get("amount") or 0) for r in (sk.data or []))

        # Per-symbol skim across all symbols ever TF-traded (active or not).
        # Mirrors the dashboard's skimFor() filter — picks up rows where the
        # symbol is in tf_config OR in any TF trade (covers deallocated coins).
        sk_all = (
            supabase_client.table("reserve_ledger")
            .select("symbol, amount")
            .eq("config_version", "v3")
            .execute()
        )
        tf_sym_set = {c["symbol"] for c in tf_config}
        for t in tf_trades:
            tf_sym_set.add(t["symbol"])
        skim_by_sym = {}
        for r in (sk_all.data or []):
            if r.get("symbol") in tf_sym_set:
                skim_by_sym[r["symbol"]] = skim_by_sym.get(r["symbol"], 0) + float(r.get("amount") or 0)
        skim_total = sum(skim_by_sym.values())

        # Fetch live prices for active TF symbols
        live_prices = fetch_binance_prices(sorted(active_set))

        # === DASHBOARD-IDENTICAL FORMULA (web_astro/dashboard-live.ts) ===
        # netWorth = budget + realized + unrealized
        # cash     = netWorth − holdings − skim
        # S69: realized = trades.realized_pnl (avg-cost canonico post-S66).
        active_positions = []
        holdings_value = 0.0
        total_unrealized = 0.0
        realized_total = 0.0
        fees_total = 0.0
        today_str = str(date.today())

        # Group trades by symbol. Includes trades from deallocated coins,
        # so their historical realized stays counted.
        trades_by_sym = {}
        for t in tf_trades:
            trades_by_sym.setdefault(t["symbol"], []).append(t)

        # Realized + fees aggregated across ALL TF coins (active or deallocated).
        for sym, coin_trades in trades_by_sym.items():
            a = _analyze_coin_avg_cost(coin_trades, sym)
            realized_total += a["realized"]
            fees_total += a["fees"]

        # Per-coin breakdown — ONLY active coins show up in active_positions.
        # Deallocated coins still count in realized_total / fees_total above
        # (so the aggregate matches the dashboard), but the daily report only
        # lists what the bot is currently managing — otherwise the message
        # blows past Telegram's 4096-char limit on a long-running TF.
        for cfg_row in tf_config:
            sym = cfg_row["symbol"]
            is_active = bool(cfg_row.get("is_active"))
            if not is_active:
                continue
            coin_trades = trades_by_sym.get(sym, [])

            a = _analyze_coin_avg_cost(coin_trades, sym)
            open_amt = a["open_amount"]
            open_cost = a["open_cost"]
            realized_coin = a["realized"]

            # Today's per-coin activity (DB realized_pnl, intra-day delta).
            coin_today_trades = [
                t for t in coin_trades if (t.get("created_at") or "").startswith(today_str)
            ]
            coin_today_realized = sum(
                float(t.get("realized_pnl") or 0)
                for t in coin_today_trades if t["side"] == "sell"
            )
            coin_today_buys = sum(1 for t in coin_today_trades if t["side"] == "buy")
            coin_today_sells = sum(1 for t in coin_today_trades if t["side"] == "sell")

            if open_amt > 1e-6:
                avg_buy = open_cost / open_amt if open_amt else 0
                live_price = live_prices.get(sym, avg_buy)
                value = open_amt * live_price
                unrealized = value - open_cost
                unrealized_pct = ((live_price / avg_buy - 1) * 100) if avg_buy > 0 else 0
                holdings_value += value
                total_unrealized += unrealized
                active_positions.append({
                    "symbol": sym,
                    "value_usd": round(value, 2),
                    "open_cost_usd": round(open_cost, 2),
                    "avg_buy_price": round(avg_buy, 8),
                    "live_price": round(live_price, 8),
                    "holdings": round(open_amt, 8),
                    "unrealized_pnl": round(unrealized, 2),
                    "unrealized_pnl_pct": round(unrealized_pct, 2),
                    "realized_pnl": round(realized_coin, 4),
                    "realized_today": round(coin_today_realized, 4),
                    "trades_today": len(coin_today_trades),
                    "buys_today": coin_today_buys,
                    "sells_today": coin_today_sells,
                    "position_closed": False,
                })
            else:
                active_positions.append({
                    "symbol": sym,
                    "value_usd": 0.0,
                    "open_cost_usd": 0.0,
                    "avg_buy_price": 0.0,
                    "live_price": float(live_prices.get(sym, 0) or 0),
                    "holdings": 0.0,
                    "unrealized_pnl": 0.0,
                    "unrealized_pnl_pct": 0.0,
                    "realized_pnl": round(realized_coin, 4),
                    "realized_today": round(coin_today_realized, 4),
                    "trades_today": len(coin_today_trades),
                    "buys_today": coin_today_buys,
                    "sells_today": coin_today_sells,
                    "position_closed": True,
                })

        # Dashboard identity (single source of truth):
        total_value = tf_budget + realized_total + total_unrealized
        cash = total_value - holdings_value - skim_total
        total_pnl = total_value - tf_budget

        # Today's aggregate activity (intra-day, DB realized is fine here).
        today_trades = [t for t in tf_trades if (t.get("created_at") or "").startswith(today_str)]
        realized_today = sum(float(t.get("realized_pnl") or 0) for t in today_trades)
        buys_today = sum(1 for t in today_trades if t["side"] == "buy")
        sells_today = sum(1 for t in today_trades if t["side"] == "sell")

        return {
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "realized_total": round(realized_total, 2),
            "realized_today": round(realized_today, 2),
            "unrealized_total": round(total_unrealized, 2),
            "fees_total": round(fees_total, 2),
            "cash": round(cash, 2),
            "holdings_value": round(holdings_value, 2),
            "trades_today": len(today_trades),
            "buys_today": buys_today,
            "sells_today": sells_today,
            "active_positions": active_positions,
            "skim_total": round(skim_total, 2),
            "tf_budget": tf_budget,
        }
    except Exception as e:
        logger.warning(f"Could not fetch TF state: {e}")
        return safe_default


def get_grid_state(supabase_client):
    """
    Fetch Grid bot state for the daily report — single source of truth,
    byte-for-byte identical to the public dashboard.

    Filter: config_version='v3' AND managed_by='grid'. Brief 46b: tf_grid
    coins are TF-funded, not Grid — they belong in get_tf_state instead.

    Returns the same shape as the legacy _build_portfolio_summary so callers
    in grid_runner.py and send_daily_reports_now.py can swap it in without
    touching the report renderer. Adds dashboard-identical fields (realized,
    unrealized, fees, skim) so the Telegram report can mirror what the user
    sees on bagholderai.lol/dashboard.

    Never raises — returns a safe-default dict on error.
    """
    safe_default = {
        "total_value": 500.0,
        "cash": 500.0,
        "holdings_value": 0.0,
        "initial_capital": 500.0,
        "total_pnl": 0.0,
        "realized_total": 0.0,
        "unrealized_total": 0.0,
        "fees_total": 0.0,
        "skim_total": 0.0,
        "positions": [],
    }
    try:
        # 1. bot_config: which Grid coins are configured (manual = Grid).
        cfg = (
            supabase_client.table("bot_config")
            .select("symbol, is_active, capital_allocation, managed_by")
            .eq("managed_by", "grid")
            .execute()
        )
        grid_config = cfg.data or []
        # Grid budget = sum of capital_allocation across manual coins.
        # Fixed by design in v3 (BTC + SOL + BONK = $500). Inactive coins
        # still contribute their slice to the budget (config persists even
        # when paused).
        grid_budget = sum(float(c.get("capital_allocation") or 0) for c in grid_config)
        if grid_budget <= 0:
            grid_budget = 500.0  # fallback if config is empty

        # 2. trades: all Grid trades, ascending order.
        tr = (
            supabase_client.table("trades")
            .select("symbol, side, amount, price, cost, fee, fee_asset, realized_pnl, created_at")
            .eq("config_version", "v3")
            .eq("managed_by", "grid")
            .order("created_at", desc=False)
            .execute()
        )
        grid_trades = tr.data or []

        # 3. reserve_ledger: skim across all Grid symbols (any managed_by).
        # The dashboard collects skim by symbol set, so manual+grid+null all
        # land in the Grid bucket if the symbol is BTC/SOL/BONK.
        grid_sym_set = {c["symbol"] for c in grid_config}
        for t in grid_trades:
            grid_sym_set.add(t["symbol"])
        sk_all = (
            supabase_client.table("reserve_ledger")
            .select("symbol, amount")
            .eq("config_version", "v3")
            .execute()
        )
        skim_by_sym = {}
        for r in (sk_all.data or []):
            sym = r.get("symbol")
            if sym in grid_sym_set:
                skim_by_sym[sym] = skim_by_sym.get(sym, 0.0) + float(r.get("amount") or 0)
        skim_total = sum(skim_by_sym.values())

        # 4. Live prices for active Grid symbols.
        active_syms = sorted({c["symbol"] for c in grid_config if c.get("is_active")})
        live_prices = fetch_binance_prices(active_syms)

        # === DASHBOARD-IDENTICAL FORMULA ===
        # Same identity as get_tf_state and dashboard-live.ts (S69 avg-cost):
        #   netWorth = budget + realized + unrealized
        #   cash     = netWorth − holdings − skim
        positions = []
        holdings_value = 0.0
        total_unrealized = 0.0
        realized_total = 0.0
        fees_total = 0.0
        today_str = str(date.today())

        trades_by_sym = {}
        for t in grid_trades:
            trades_by_sym.setdefault(t["symbol"], []).append(t)

        # Aggregate realized + fees across all Grid coins.
        for sym, coin_trades in trades_by_sym.items():
            a = _analyze_coin_avg_cost(coin_trades, sym)
            realized_total += a["realized"]
            fees_total += a["fees"]

        # Per-coin breakdown for the report (only configured coins).
        for cfg_row in grid_config:
            sym = cfg_row["symbol"]
            coin_trades = trades_by_sym.get(sym, [])
            a = _analyze_coin_avg_cost(coin_trades, sym)
            open_amt = a["open_amount"]
            open_cost = a["open_cost"]
            realized_coin = a["realized"]

            # Today's per-coin (for the "Today: N trades" footer)
            coin_today_trades = [
                t for t in coin_trades if (t.get("created_at") or "").startswith(today_str)
            ]
            coin_today_buys = sum(1 for t in coin_today_trades if t["side"] == "buy")
            coin_today_sells = sum(1 for t in coin_today_trades if t["side"] == "sell")

            avg_buy = open_cost / open_amt if open_amt > 1e-6 else 0.0
            live_price = live_prices.get(sym, avg_buy)
            value = open_amt * live_price if open_amt > 1e-6 else 0.0
            unrealized = value - open_cost if open_amt > 1e-6 else 0.0
            unrealized_pct = (
                ((live_price / avg_buy - 1) * 100) if avg_buy > 0 else 0.0
            )

            if open_amt > 1e-6:
                holdings_value += value
                total_unrealized += unrealized

            positions.append({
                "symbol": sym,
                "holdings": round(open_amt, 8),
                "value": round(value, 4),
                "avg_buy_price": round(avg_buy, 8),
                "live_price": round(live_price, 8),
                "unrealized_pnl": round(unrealized, 4),
                "unrealized_pnl_pct": round(unrealized_pct, 2),
                "realized_pnl": round(realized_coin, 4),
                "trades_today": len(coin_today_trades),
                "buys_today": coin_today_buys,
                "sells_today": coin_today_sells,
            })

        total_value = grid_budget + realized_total + total_unrealized
        cash = total_value - holdings_value - skim_total
        total_pnl = total_value - grid_budget

        return {
            "total_value": round(total_value, 2),
            "cash": round(cash, 2),
            "holdings_value": round(holdings_value, 2),
            "initial_capital": round(grid_budget, 2),
            "total_pnl": round(total_pnl, 2),
            "realized_total": round(realized_total, 2),
            "unrealized_total": round(total_unrealized, 2),
            "fees_total": round(fees_total, 2),
            "skim_total": round(skim_total, 2),
            "skim_by_sym": {s: round(v, 2) for s, v in skim_by_sym.items()},
            "positions": positions,
        }
    except Exception as e:
        logger.warning(f"Could not fetch Grid state: {e}")
        return safe_default


def generate_daily_commentary(portfolio_data, supabase_client):
    """
    Generate and save AI commentary for today's trading activity.
    Never raises — all errors are caught and logged.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping daily commentary.")
        return None

    try:
        import anthropic

        # Gather context
        yesterday_commentary = get_yesterday_commentary(supabase_client)
        config_changes = get_config_changes(supabase_client)
        tf_state = get_tf_state(supabase_client)

        # Calculate day numbers — two counters for Haiku to disambiguate
        # historical vs current state (see SYSTEM PROMPT context block).
        day_number = (date.today() - V3_START_DATE).days + 1
        testnet_day = (date.today() - TESTNET_RESTART_DATE).days + 1

        # Build Grid positions list (from portfolio_data passed by grid_runner)
        grid_positions = []
        for p in portfolio_data.get("positions", []):
            grid_positions.append({
                "symbol": p["symbol"],
                "value": round(p.get("value", 0), 2),
                "unrealized_pnl": round(p.get("unrealized_pnl", 0), 2),
                "unrealized_pnl_pct": round(p.get("unrealized_pnl_pct", 0), 2),
            })

        # Grid numbers (from grid_runner)
        grid_initial = portfolio_data.get("initial_capital", 500.0)
        grid_cash = portfolio_data.get("cash", 0)
        grid_total_value = portfolio_data.get("total_value", 0)
        grid_total_pnl = portfolio_data.get("total_pnl", 0)
        grid_today_trades = portfolio_data.get("today_trades_count", 0)
        grid_today_buys = portfolio_data.get("today_buys", 0)
        grid_today_sells = portfolio_data.get("today_sells", 0)
        grid_today_realized = portfolio_data.get("today_realized", 0)

        # TF numbers (from get_tf_state — separate query)
        tf_initial = tf_state["tf_budget"]
        tf_total_value = tf_state["total_value"]
        tf_total_pnl = tf_state["total_pnl"]

        # Aggregate (Grid + TF)
        agg_initial = grid_initial + tf_initial
        agg_total_value = grid_total_value + tf_total_value
        agg_total_pnl = grid_total_pnl + tf_total_pnl
        agg_today_trades = grid_today_trades + tf_state["trades_today"]
        agg_today_buys = grid_today_buys + tf_state["buys_today"]
        agg_today_sells = grid_today_sells + tf_state["sells_today"]
        agg_today_realized = grid_today_realized + tf_state["realized_today"]

        prompt_data = {
            "date": str(date.today()),
            "day_number": day_number,
            "testnet_day": testnet_day,
            "system_state": {
                "grid": "live on Binance testnet",
                "tf": "paused since 2026-05-08 (in maintenance)",
                "sentinel": "DRY_RUN (observation only)",
                "sherpa": "DRY_RUN (proposals not applied)",
                "accounting": "avg-cost (FIFO removed 2026-05-09)",
                "reconciliation": "daily Binance↔DB script, 0 drift latest run",
            },
            "aggregate_portfolio": {
                "total_value": round(agg_total_value, 2),
                "initial_capital": round(agg_initial, 2),
                "total_pnl": round(agg_total_pnl, 2),
                "total_pnl_pct": round((agg_total_pnl / agg_initial * 100) if agg_initial else 0, 2),
            },
            "grid_bot": {
                "initial_capital": round(grid_initial, 2),
                "total_value": round(grid_total_value, 2),
                "total_pnl": round(grid_total_pnl, 2),
                "total_pnl_pct": round((grid_total_pnl / grid_initial * 100) if grid_initial else 0, 2),
                "cash_remaining": round(grid_cash, 2),
                "positions": grid_positions,
            },
            "tf": {
                "initial_capital": round(tf_initial, 2),
                "total_value": tf_state["total_value"],
                "total_pnl": tf_state["total_pnl"],
                "total_pnl_pct": round((tf_state["total_pnl"] / tf_initial * 100) if tf_initial else 0, 2),
                "active_positions": tf_state["active_positions"],
                "skim_reserve": tf_state["skim_total"],
            },
            "today_activity": {
                "aggregate": {
                    "trades_count": agg_today_trades,
                    "buys_count": agg_today_buys,
                    "sells_count": agg_today_sells,
                    "realized_pnl": round(agg_today_realized, 2),
                },
                "grid": {
                    "trades_count": grid_today_trades,
                    "buys_count": grid_today_buys,
                    "sells_count": grid_today_sells,
                    "realized_pnl": round(grid_today_realized, 2),
                },
                "tf": {
                    "trades_count": tf_state["trades_today"],
                    "buys_count": tf_state["buys_today"],
                    "sells_count": tf_state["sells_today"],
                    "realized_pnl": tf_state["realized_today"],
                },
            },
            "config_changes": config_changes,
            "yesterday_commentary": yesterday_commentary,
        }

        # Call Haiku
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=COMMENTARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(prompt_data)}],
        )
        commentary_text = response.content[0].text

        # Insert to Supabase (multiple entries per day allowed)
        supabase_client.table("daily_commentary").insert(
            {
                "date": str(date.today()),
                "commentary": commentary_text,
                "model_used": "claude-haiku-4-5-20251001",
                "prompt_data": json.dumps(prompt_data),
            }
        ).execute()

        logger.info(f"Daily commentary saved: {commentary_text[:80]}...")
        return commentary_text

    except Exception as e:
        logger.error(f"Failed to generate daily commentary: {e}")
        return None
