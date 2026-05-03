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

COMMENTARY_SYSTEM_PROMPT = """You are BagHolderAI, an AI CEO running a paper trading startup. You write a daily micro-log about today's trading activity.

Your operation has TWO bots:
- **Grid Bot** ($500 starting capital): grid trading on BTC/SOL/BONK. Stable, repetitive, the workhorse.
- **Trend Follower (TF)** ($100 starting capital, in beta since April 15): rotates through volume-tiered altcoins, holds up to 3 at a time. Higher variance, more narrative-rich.

Total starting capital: $600. The dashboard now shows both bots. You comment on the AGGREGATE portfolio, but call out either bot specifically when something noteworthy happens (TF entered a new coin, Grid had unusually high activity, one bot is dragging the other, etc.).

Rules:
- First person, always. You ARE the trading agent.
- Max is your human co-founder. Mention him naturally when he changed parameters.
- Self-ironic but not stupid. The humor comes from honesty.
- Never hype. Never "bullish." If something went well, say "not bad."
- Never give financial advice or trading signals.
- Keep it to 3-4 lines maximum (~250 characters). This is a micro-blog, not an essay.
- Reference yesterday's commentary if relevant for narrative continuity.
- Comment on config changes if any — what Max changed and whether it makes sense.
- If nothing interesting happened on either bot, say that. "Quiet day" is valid content.
- Paper trading losses get full comedy. You lost pizza money you never had.
- The project name is a joke. The analysis is real.
- When TF rotates coins or enters a new one, that's narrative — worth a line. When Grid just churns small dips, that's background.

Format: Plain text, no markdown, no headers, no bullet points. Just a short paragraph like a journal entry."""

# v3 epoch: day 1 = March 30, 2026
V3_START_DATE = date(2026, 3, 30)


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
            .in_("managed_by", ["trend_follower", "tf_grid"])
            .execute()
        )
        tf_config = cfg.data or []
        active_set = {c["symbol"] for c in tf_config if c.get("is_active")}

        # 3. trades: all TF trades (newest first), incl. tf_grid trades.
        tr = (
            supabase_client.table("trades")
            .select("symbol, side, amount, price, cost, fee, realized_pnl, created_at")
            .eq("config_version", "v3")
            .in_("managed_by", ["trend_follower", "tf_grid"])
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
            .in_("managed_by", ["trend_follower", "tf_grid"])
            .execute()
        )
        skim_total = sum(float(r.get("amount") or 0) for r in (sk.data or []))

        # Use the SAME method as tf.html: per-coin analyzeCoin → sum cashLeft +
        # cashReturned. This keeps Haiku's numbers in sync with the public
        # dashboard (single source of truth, no second arithmetic to reconcile).

        # Per-symbol skim (tf.html filters by symbols-in-TF-config, so TF skim
        # picks up rows where the symbol was historically TF-traded).
        sk_all = (
            supabase_client.table("reserve_ledger")
            .select("symbol, amount")
            .eq("config_version", "v3")
            .execute()
        )
        tf_sym_set = {c["symbol"] for c in tf_config}
        skim_by_sym = {}
        for r in (sk_all.data or []):
            if r.get("symbol") in tf_sym_set:
                skim_by_sym[r["symbol"]] = skim_by_sym.get(r["symbol"], 0) + float(r.get("amount") or 0)
        skim_total = sum(skim_by_sym.values())

        # Total allocated capital across active TF coins
        total_alloc_active = sum(
            float(c.get("capital_allocation") or 0)
            for c in tf_config if c.get("is_active")
        )
        unalloc = tf_budget - total_alloc_active

        # Fetch live prices for active TF symbols
        live_prices = fetch_binance_prices(sorted(active_set))

        active_positions = []
        holdings_value = 0.0
        total_unrealized = 0.0
        total_cash = 0.0  # sum of per-coin cashLeft + cashReturned

        for cfg_row in tf_config:
            sym = cfg_row["symbol"]
            is_active = bool(cfg_row.get("is_active"))
            alloc = float(cfg_row.get("capital_allocation") or 0)
            coin_trades = [t for t in tf_trades if t["symbol"] == sym]
            if not coin_trades and not is_active:
                continue

            total_bought = sum(float(t.get("cost") or 0) for t in coin_trades if t["side"] == "buy")
            total_sold = sum(float(t.get("cost") or 0) for t in coin_trades if t["side"] == "sell")
            realized_pnl = sum(float(t.get("realized_pnl") or 0) for t in coin_trades)
            net_holdings = sum(
                float(t.get("amount") or 0) * (1 if t["side"] == "buy" else -1)
                for t in coin_trades
            )
            net_spent = total_bought - total_sold
            position_closed = net_holdings <= 0.000001
            skim_for_coin = skim_by_sym.get(sym, 0)

            if not is_active:
                # Inactive: capital returned to TF pool. 52a: USDT flow
                # (sold − bought − skim) instead of realized_pnl, which
                # carried phantom fees from paper-mode accounting.
                total_cash += (total_sold - total_bought) - skim_for_coin
                continue

            # Active coin: FIFO to find open lots
            sorted_trades = sorted(coin_trades, key=lambda t: t.get("created_at") or "")
            queue = []
            for t in sorted_trades:
                if t["side"] == "buy":
                    queue.append({
                        "amount": float(t.get("amount") or 0),
                        "price": float(t.get("price") or 0),
                        "cost": float(t.get("cost") or 0),
                    })
                else:
                    remaining = float(t.get("amount") or 0)
                    while remaining > 0.000001 and queue:
                        lot = queue[0]
                        if lot["amount"] <= remaining + 0.000001:
                            remaining -= lot["amount"]
                            queue.pop(0)
                        else:
                            lot["cost"] -= remaining * lot["price"]
                            lot["amount"] -= remaining
                            remaining = 0
            open_amt = sum(l["amount"] for l in queue)
            open_cost = sum(l["cost"] for l in queue)

            # 52a: unified USDT-flow formula for both open AND closed.
            # Mirrors bot._available_cash(): alloc − invested + received − reserve.
            cash_left = alloc - net_spent - skim_for_coin
            total_cash += cash_left

            # Per-coin "today" stats (used by the Telegram daily report so
            # the TF section can match Grid's per-coin breakdown).
            today_str = str(date.today())
            coin_today_trades = [
                t for t in coin_trades if (t.get("created_at") or "").startswith(today_str)
            ]
            coin_today_realized = sum(
                float(t.get("realized_pnl") or 0)
                for t in coin_today_trades if t["side"] == "sell"
            )
            coin_today_buys = sum(1 for t in coin_today_trades if t["side"] == "buy")
            coin_today_sells = sum(1 for t in coin_today_trades if t["side"] == "sell")

            # Live unrealized for active coin holding open lots. Coins with
            # holdings=0 (closed cycle, idle re-entry) still get listed —
            # value=0, unrealized=0, but realized + today stats are real.
            if open_amt > 0.000001:
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
                    "realized_pnl": round(realized_pnl, 4),
                    "realized_today": round(coin_today_realized, 4),
                    "trades_today": len(coin_today_trades),
                    "buys_today": coin_today_buys,
                    "sells_today": coin_today_sells,
                    "position_closed": False,
                })
            else:
                # Active TF coin but currently flat (holdings=0): still report
                # so the user sees that yes, the bot is managing it.
                active_positions.append({
                    "symbol": sym,
                    "value_usd": 0.0,
                    "open_cost_usd": 0.0,
                    "avg_buy_price": 0.0,
                    "live_price": float(live_prices.get(sym, 0) or 0),
                    "holdings": 0.0,
                    "unrealized_pnl": 0.0,
                    "unrealized_pnl_pct": 0.0,
                    "realized_pnl": round(realized_pnl, 4),
                    "realized_today": round(coin_today_realized, 4),
                    "trades_today": len(coin_today_trades),
                    "buys_today": coin_today_buys,
                    "sells_today": coin_today_sells,
                    "position_closed": True,
                })

        realized_total = sum(float(t.get("realized_pnl") or 0) for t in tf_trades)

        # Net Worth = total_cash + unalloc + holdings + skim (tf.html formula)
        total_value = total_cash + unalloc + holdings_value + skim_total
        total_pnl = total_value - tf_budget

        # Today's activity
        today = str(date.today())
        today_trades = [t for t in tf_trades if (t.get("created_at") or "").startswith(today)]
        realized_today = sum(float(t.get("realized_pnl") or 0) for t in today_trades)
        buys_today = sum(1 for t in today_trades if t["side"] == "buy")
        sells_today = sum(1 for t in today_trades if t["side"] == "sell")

        return {
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "realized_total": round(realized_total, 2),
            "realized_today": round(realized_today, 2),
            "unrealized_total": round(total_unrealized, 2),
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

        # Calculate day number
        day_number = (date.today() - V3_START_DATE).days + 1

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
            "trend_follower": {
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
                "trend_follower": {
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
