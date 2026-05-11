"""
BagHolderAI - State manager (Phase 1 split from grid_bot.py).

Boot-time state restoration from DB.

Brief s70 FASE 2 (2026-05-09): la legacy FIFO queue replay è stata
rimossa, e la legacy `restore_state_from_db` (fixed-mode v1) è stata
rimossa insieme al cleanup completo del fixed-mode (vedi commit 9).
Avg-cost trading consulta solo state.avg_buy_price e state.holdings.

Brief 72a (Fee Unification, S72 2026-05-11): replay applies the 3
invariants (P1/P2/P3). Holdings is set from `exchange.fetch_balance()`
in live mode as a golden source — the replay cannot reconstruct holdings
exactly because it doesn't know about initial testnet balances or
monthly resets. The replay provides avg_buy_price, realized_pnl, and
cash bookkeeping; Binance provides ground truth for holdings.
"""

import logging
import os
from datetime import datetime, timezone
from utils.formatting import fmt_price
from config.settings import TradingMode

logger = logging.getLogger("bagholderai.grid")


# Brief 72a (S72): post-fill reconciliation flag — CEO 2026-05-11 specified
# OFF by default, ON ready for mainnet. When ON, every buy/sell will call
# fetch_balance() after the in-memory state update and log a warn if the
# wallet diverges. Boot reconcile is the primary mechanism; this is an
# extra safety net for mainnet where money is real.
RECONCILE_AFTER_FILL = os.environ.get("RECONCILE_AFTER_FILL", "false").lower() in (
    "true", "1", "yes", "on"
)


def init_avg_cost_state_from_db(bot):
    """
    Restore avg-cost percentage-mode state from DB on startup.

    Replays all v3 trades for this symbol chronologically and recomputes:
    - state.avg_buy_price (running weighted average; reset to 0 on full sell)
    - state.realized_pnl (sum of (sell_price - avg_at_sell) × sell_qty − fee_sell)
    - state.total_invested, state.total_received
    - bot._pct_last_buy_price (price del trade buy più recente)
    - bot._last_trade_time (timestamp del trade più recente, per idle path)

    state.holdings:
    - paper mode: replayed qty (legacy)
    - live mode: overridden by `exchange.fetch_balance()` as golden source
      (P1). Refuses to start if gap > 2%; warns if gap > 0.5% (CEO 2026-05-11).

    Brief s70 FASE 2: niente più FIFO queue replay. La queue era usata
    per guidare il Strategy A trigger per-lot pre-S70; con avg-cost
    trading il trigger guarda solo state.avg_buy_price.
    """
    if not bot.trade_logger:
        return
    try:
        result = (
            bot.trade_logger.client.table("trades")
            .select("side,amount,price,cost,fee,fee_asset,created_at")
            .eq("symbol", bot.symbol)
            .eq("config_version", "v3")
            .order("created_at", desc=False)
            .execute()
        )
        trades = result.data or []
    except Exception as e:
        logger.warning(f"[{bot.symbol}] Could not load avg-cost state from DB: {e}")
        return

    base_coin = bot.symbol.split("/")[0].upper() if "/" in bot.symbol else ""

    last_buy_price = 0.0
    last_sell_price = 0.0  # Brief 70a Parte 3: sell ladder reference (Grid manual)
    total_invested = 0.0
    total_received = 0.0
    avg = 0.0
    qty = 0.0
    realized = 0.0

    for t in trades:
        side = t.get("side")
        amount = float(t.get("amount", 0))
        price = float(t.get("price", 0))
        cost = float(t.get("cost") or (amount * price))
        fee_usdt = float(t.get("fee") or 0)
        fee_asset = (t.get("fee_asset") or "USDT").upper()

        if side == "buy":
            # Brief 72a P2 (S72): qty_acquired = filled − fee_native when
            # fee was scaled from the base coin. fee_native is derived from
            # fee_usdt/price (Binance testnet doesn't return fee_base in
            # fetch_order; the USDT-equivalent in DB does retain the info).
            # Paper trades have fee_asset='USDT' default → fee_native_est=0
            # → qty_acquired = amount (legacy paper behaviour preserved).
            if fee_asset == base_coin and price > 0:
                fee_native_est = fee_usdt / price
            else:
                fee_native_est = 0.0
            qty_acquired = amount - fee_native_est
            total_invested += cost
            last_buy_price = price
            new_qty = qty + qty_acquired
            if new_qty > 0:
                # P2 formula: avg = total_cost_usdt / qty_net_acquired
                avg = (avg * qty + cost) / new_qty
            qty = new_qty
        elif side == "sell":
            revenue = amount * price
            total_received += revenue
            if qty > 1e-12:
                # Brief 72a P3 (S72): realized = (price − avg) × qty − fee_sell
                # Pre-72a was just (price − avg) × qty → systematically
                # overstated P&L by the sell fee (~0.1% per trade).
                realized += (price - avg) * amount - fee_usdt
                qty -= amount
                if qty <= 1e-9:
                    qty = 0.0
                    avg = 0.0  # reset on full sell-out
                    last_sell_price = 0.0  # 70a: reset ladder on full exit
                else:
                    last_sell_price = price  # 70a: partial sell → next ladder step

    bot._pct_last_buy_price = last_buy_price
    bot._last_sell_price = last_sell_price

    # Restore last trade time so idle re-entry countdown is correct.
    # Convert to UTC-naive so comparison with datetime.utcnow() is always correct
    # regardless of the timezone offset stored in the DB timestamp.
    if trades:
        try:
            dt_str = trades[-1].get("created_at", "")
            if dt_str:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                # Only overwrite if DB value is newer than in-memory value.
                # The idle-recalibrate path sets _last_trade_time = utcnow() without
                # writing to DB; this re-init must not clobber that.
                if bot._last_trade_time is None or dt > bot._last_trade_time:
                    bot._last_trade_time = dt
                    bot._idle_logged_hour = -1  # reset so first eval logs immediately
                    logger.info(f"[{bot.symbol}] Restored _last_trade_time = {dt:%Y-%m-%d %H:%M:%S} UTC")
                else:
                    logger.info(
                        f"[{bot.symbol}] DB _last_trade_time ({dt:%Y-%m-%d %H:%M:%S}) "
                        f"older than in-memory ({bot._last_trade_time:%Y-%m-%d %H:%M:%S}), keeping in-memory"
                    )
        except Exception:
            pass
    else:
        logger.info(f"[{bot.symbol}] No v3 trades found — _last_trade_time stays None")

    # Reconstruct cash accounting so sell logic fires correctly.
    # Brief 72a P1 (S72): holdings is set here from the replay as default,
    # then overridden below from `exchange.fetch_balance()` in live mode.
    if bot.state:
        bot.state.total_invested = total_invested
        bot.state.total_received = total_received
        bot.state.holdings = qty
        bot.state.avg_buy_price = avg
        bot.state.realized_pnl = realized

    available = bot.capital - total_invested + total_received
    reserve_str = ""
    if bot.reserve_ledger:
        try:
            reserve = bot.reserve_ledger.get_reserve_total(bot.symbol)
            if reserve > 0:
                available -= reserve
                reserve_str = f" - ${reserve:.2f} reserve"
        except Exception as e:
            logger.warning(f"[{bot.symbol}] Could not fetch reserve total for cash log: {e}")

    last_sell_log = (
        f", last sell {fmt_price(last_sell_price)} (ladder active)"
        if last_sell_price > 0 else ""
    )
    logger.info(
        f"[{bot.symbol}] Avg-cost state restored: holdings={bot.state.holdings:.6f}, "
        f"avg_buy={fmt_price(bot.state.avg_buy_price)}, "
        f"realized=${bot.state.realized_pnl:.4f}, "
        f"last buy {fmt_price(last_buy_price)}{last_sell_log}"
    )
    logger.info(
        f"[{bot.symbol}] Cash restored: ${bot.capital:.2f} allocated"
        f" - ${total_invested:.2f} invested"
        f" + ${total_received:.2f} sold"
        f"{reserve_str}"
        f" = ${available:.2f} available"
    )

    # Brief 72a P1 (S72): live-mode boot reconcile against fetch_balance().
    # In paper mode this is a no-op — state.holdings stays at the replayed
    # value above. In live mode this overrides state.holdings with the real
    # Binance wallet balance, the only source of truth that survives initial
    # testnet balances, monthly resets, and untracked transfers.
    _reconcile_holdings_against_exchange(bot, replayed_qty=qty, base_coin=base_coin)


def _reconcile_holdings_against_exchange(bot, replayed_qty: float, base_coin: str) -> None:
    """Brief 72a P1 (S72): boot-time golden source reconciliation.

    Calls exchange.fetch_balance() and compares with the replayed qty.
    The drift direction matters (Max 2026-05-11 S72, asymmetric thresholds):

      - **Negative drift** (Binance < replayed): the bot believes it owns
        coins that aren't on the wallet — phantom holdings, risk of
        InsufficientFunds on every sell attempt. This is the BONK
        InsufficientFunds class of bug, a sign of capital-at-risk on
        mainnet. Thresholds:
          > 2.0%: raise RuntimeError — refuse to start
          > 0.5%: log warn + write bot_events_log

      - **Positive drift** (Binance > replayed): the wallet has more coins
        than the bot expects. On testnet this is the initial-balance
        phantom (Binance gifts ~1 BTC, ~18K BONK, etc at account creation).
        On mainnet this can only happen if the user manually deposited
        coins outside the bot — informational, not a bug. Thresholds:
          > 0.5%: log warn (never fail)

    In all live cases (within or above thresholds), sets bot.state.holdings
    = real_qty so future trades use the wallet truth. The only exception is
    fetch_balance failure, where we keep the replay value.

    Paper / no exchange / no base_coin: no-op.
    """
    if not TradingMode.is_live() or bot.exchange is None or not base_coin:
        return
    try:
        balance = bot.exchange.fetch_balance()
    except Exception as e:
        logger.warning(
            f"[{bot.symbol}] Boot reconcile: fetch_balance failed ({type(e).__name__}: {e}), "
            f"keeping replayed holdings={replayed_qty}"
        )
        return

    coin_bal = balance.get(base_coin, {}) or {}
    real_qty = float(coin_bal.get("total", 0) or 0)
    gap_signed = real_qty - replayed_qty  # +ve = wallet has more, -ve = wallet has less
    if replayed_qty > 1e-9:
        gap_pct = abs(gap_signed) / replayed_qty * 100
    elif abs(gap_signed) > 1e-9:
        gap_pct = 100.0
    else:
        gap_pct = 0.0
    direction = "phantom_holdings" if gap_signed < 0 else "wallet_surplus"

    msg_base = (
        f"replayed={replayed_qty:.6f} vs Binance={real_qty:.6f} "
        f"(gap={gap_signed:+.6f} {base_coin}, |{gap_pct:.4f}%|, "
        f"direction={direction})"
    )

    # Negative drift > 2%: phantom holdings → capital at risk → FAIL
    if gap_signed < 0 and gap_pct > 2.0:
        try:
            from db.event_logger import log_event
            log_event(
                severity="error",
                category="integrity",
                event="holdings_drift_fail",
                symbol=bot.symbol,
                message=f"REFUSE START: phantom holdings >2% — {msg_base}",
                details={
                    "replayed_qty": replayed_qty,
                    "real_qty": real_qty,
                    "gap_signed": gap_signed,
                    "gap_pct": gap_pct,
                    "threshold_pct": 2.0,
                    "direction": direction,
                },
            )
        except Exception:
            pass
        raise RuntimeError(
            f"[{bot.symbol}] Brief 72a boot reconcile FAILED: phantom holdings "
            f"{gap_pct:.2f}% (real < replayed) exceeds 2% threshold. "
            f"{msg_base}. Refusing to start (Max+CEO 2026-05-11). The bot "
            f"believes it owns more {base_coin} than the wallet actually "
            f"holds, every sell will be rejected. Investigate untracked "
            f"sells, manual transfers out, or DB row corruption before "
            f"restarting."
        )

    # Any drift > 0.5%: WARN. Asymmetric — negative is more alarming.
    if gap_pct > 0.5:
        severity = "warn" if gap_signed < 0 else "info"
        try:
            from db.event_logger import log_event
            log_event(
                severity=severity,
                category="integrity",
                event="holdings_drift_warn",
                symbol=bot.symbol,
                message=f"holdings drift {gap_pct:.4f}% ({direction}): {msg_base}",
                details={
                    "replayed_qty": replayed_qty,
                    "real_qty": real_qty,
                    "gap_signed": gap_signed,
                    "gap_pct": gap_pct,
                    "threshold_pct": 0.5,
                    "direction": direction,
                },
            )
        except Exception:
            pass
        if gap_signed < 0:
            logger.warning(f"[{bot.symbol}] Boot reconcile WARN (phantom): {msg_base}")
        else:
            logger.info(f"[{bot.symbol}] Boot reconcile NOTE (surplus): {msg_base}")
    else:
        logger.info(f"[{bot.symbol}] Boot reconcile OK: {msg_base}")

    if bot.state:
        bot.state.holdings = real_qty
        logger.info(
            f"[{bot.symbol}] Holdings synced from Binance: {base_coin}={real_qty}"
        )


def maybe_reconcile_after_fill(bot, base_coin: str = "") -> None:
    """Brief 72a P1 (S72): post-fill safety check — OFF by default.

    Triggered by RECONCILE_AFTER_FILL env flag. When ON (mainnet), every
    buy/sell calls fetch_balance() and logs a warn if state.holdings
    diverges from the wallet. CEO 2026-05-11 wants this code-ready so
    mainnet flip is a single env flag away. Boot reconcile is the
    primary mechanism; this is paranoia for live capital.
    """
    if not RECONCILE_AFTER_FILL:
        return
    if not TradingMode.is_live() or bot.exchange is None or not bot.state:
        return
    coin = base_coin or (bot.symbol.split("/")[0].upper() if "/" in bot.symbol else "")
    if not coin:
        return
    try:
        balance = bot.exchange.fetch_balance()
    except Exception as e:
        logger.debug(f"[{bot.symbol}] post-fill reconcile: fetch_balance failed ({e})")
        return
    real_qty = float((balance.get(coin) or {}).get("total", 0) or 0)
    local_qty = float(bot.state.holdings or 0)
    gap_abs = real_qty - local_qty
    gap_pct = abs(gap_abs) / max(local_qty, 1e-9) * 100
    if gap_pct > 0.5:
        try:
            from db.event_logger import log_event
            log_event(
                severity="warn",
                category="integrity",
                event="post_fill_drift",
                symbol=bot.symbol,
                message=(
                    f"post-fill drift >0.5%: local={local_qty:.6f} vs "
                    f"Binance={real_qty:.6f} ({gap_pct:.4f}%)"
                ),
                details={"local_qty": local_qty, "real_qty": real_qty,
                         "gap_pct": gap_pct},
            )
        except Exception:
            pass
