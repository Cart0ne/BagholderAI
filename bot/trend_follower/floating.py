"""
TF floating cash helper (Session 36g Phase 1).

Retained profit from DEALLOCATED TF bots, sitting unowned on the exchange
until the next TF scan can re-allocate it. Adds organic compounding to
`tf_total_capital` without touching live bots (Phase 2 handles those).

Algorithm (Option B1, ledger-based):

    floating = Σ_deallocated_TF_bots (received − invested − reserve)

Where a "deallocated TF bot" is a row in bot_config with
managed_by='trend_follower' AND is_active=false AND net_holdings=0.
The net_holdings guard ensures we don't count bots that were killed
without liquidating (crypto would still be locked, not liquid USDT).
"""

from collections import defaultdict
import logging

logger = logging.getLogger("bagholderai.trend")


def compute_tf_floating_cash(supabase) -> tuple[float, list[dict]]:
    """
    Compute TF floating cash = retained profits from fully-liquidated,
    deallocated TF bots. Returns (total_floating, per_symbol_breakdown).

    per_symbol_breakdown is a list of dicts useful for logging / dashboard:
        [{"symbol": "BIO/USDT", "received": 56.18, "invested": 50.56,
          "reserve": 1.73, "retained": 3.89}, ...]
    """
    try:
        cfg_rows = supabase.table("bot_config").select(
            "symbol,is_active,managed_by"
        ).eq("managed_by", "trend_follower").execute()
    except Exception as e:
        logger.warning(f"[floating] Could not load bot_config: {e}")
        return 0.0, []

    deallocated = [
        r["symbol"] for r in (cfg_rows.data or [])
        if not r.get("is_active")
    ]
    if not deallocated:
        return 0.0, []

    try:
        trade_rows = supabase.table("trades").select(
            "symbol,side,cost,amount"
        ).eq("managed_by", "trend_follower").eq(
            "config_version", "v3"
        ).in_("symbol", deallocated).execute()
    except Exception as e:
        logger.warning(f"[floating] Could not load trades: {e}")
        return 0.0, []

    received = defaultdict(float)
    invested = defaultdict(float)
    amt_buy = defaultdict(float)
    amt_sell = defaultdict(float)
    for t in (trade_rows.data or []):
        sym = t["symbol"]
        cost = float(t.get("cost") or 0)
        amt = float(t.get("amount") or 0)
        if t["side"] == "buy":
            invested[sym] += cost
            amt_buy[sym] += amt
        elif t["side"] == "sell":
            received[sym] += cost
            amt_sell[sym] += amt

    try:
        reserve_rows = supabase.table("reserve_ledger").select(
            "symbol,amount"
        ).eq("config_version", "v3").in_("symbol", deallocated).execute()
    except Exception as e:
        logger.warning(f"[floating] Could not load reserve_ledger: {e}")
        return 0.0, []

    reserve = defaultdict(float)
    for r in (reserve_rows.data or []):
        reserve[r["symbol"]] += float(r.get("amount") or 0)

    total = 0.0
    breakdown = []
    DUST_THRESHOLD = 1e-6
    for sym in deallocated:
        net_holdings = amt_buy[sym] - amt_sell[sym]
        if abs(net_holdings) > DUST_THRESHOLD:
            # Bot was deallocated without fully liquidating. Skip to avoid
            # counting crypto-locked value as liquid USDT.
            logger.warning(
                f"[floating] Skipping {sym}: deallocated but holds "
                f"{net_holdings:.8f} crypto (not liquidated)"
            )
            continue
        retained = received[sym] - invested[sym] - reserve[sym]
        total += retained
        breakdown.append({
            "symbol": sym,
            "received": round(received[sym], 4),
            "invested": round(invested[sym], 4),
            "reserve": round(reserve[sym], 4),
            "retained": round(retained, 4),
        })

    return round(total, 4), breakdown
