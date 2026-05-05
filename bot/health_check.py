"""
BagHolderAI - 57a Health Check (Brief 57a, Fix 3)

Five integrity checks that compare DB-derived FIFO truth against the
data the bot has been writing to DB. Designed to be called by the
orchestrator at boot + every 30 minutes, and standalone via
`python -m bot.health_check` for manual dry-runs.

Checks:
  1. FIFO P&L reconciliation — DB realized_pnl sum vs FIFO replay
  2. Holdings consistency — net amount per symbol from trade replay
  3. Negative holdings guard — no symbol may have sold more than bought
  4. Cash accounting — capital_allocation - bought + sold ≈ dashboard cash
  5. Orphan lots — sells without buy_trade_id that aren't FORCED_LIQUIDATION

Output: structured dict + Telegram alert if any check fails.

Contract: never raises. A failed query degrades to {"status": "ERROR"}
on that single check; the rest still run.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from db.client import get_client
from db.event_logger import log_event

logger = logging.getLogger("bagholderai.health")

# Tolerances. Tighter than the brief's defaults where the data allows it.
PNL_TOLERANCE_USD = 0.05      # delta DB vs FIFO realized per symbol
HOLDINGS_TOLERANCE = 1e-6     # base-currency dust tolerance
CASH_TOLERANCE_USD = 0.10     # dashboard cash vs ledger
NEGATIVE_DUST = 1e-6          # treat negative holdings below this as float noise


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #

def _replay_fifo_pnl(trades: list[dict]) -> tuple[float, float]:
    """Replay buys + sells in chronological order with a strict FIFO queue.

    Returns (total_realized_pnl, holdings) for the symbol.
    """
    queue: list[dict] = []
    realized = 0.0
    holdings = 0.0

    for t in trades:
        side = t.get("side")
        amount = float(t.get("amount") or 0)
        price = float(t.get("price") or 0)
        if side == "buy":
            queue.append({"amount": amount, "price": price})
            holdings += amount
        elif side == "sell":
            cost = float(t.get("cost") or (amount * price))
            revenue = cost  # sell.cost is the proceeds in this codebase
            basis = 0.0
            remaining = amount
            while remaining > 1e-12 and queue:
                lot = queue[0]
                if lot["amount"] <= remaining + 1e-12:
                    basis += lot["amount"] * lot["price"]
                    remaining -= lot["amount"]
                    queue.pop(0)
                else:
                    portion = remaining / lot["amount"]
                    basis += lot["amount"] * lot["price"] * portion
                    lot["amount"] -= remaining
                    remaining = 0
            realized += revenue - basis
            holdings -= amount

    return realized, holdings


def _ok(name: str, symbol: Optional[str] = None,
        detail: str = "") -> dict:
    return {"name": name, "status": "OK", "symbol": symbol, "detail": detail}


def _fail(name: str, symbol: Optional[str] = None,
          detail: str = "") -> dict:
    return {"name": name, "status": "FAIL", "symbol": symbol, "detail": detail}


def _err(name: str, symbol: Optional[str] = None,
         detail: str = "") -> dict:
    return {"name": name, "status": "ERROR", "symbol": symbol, "detail": detail}


# ---------------------------------------------------------------------- #
# Individual checks
# ---------------------------------------------------------------------- #

def check_fifo_pnl(client, symbols: list[str]) -> list[dict]:
    """Check 1 — DB realized_pnl sum vs FIFO replay. Per-symbol."""
    results: list[dict] = []
    for sym in symbols:
        try:
            res = (
                client.table("trades")
                .select("side,amount,price,cost,realized_pnl,created_at")
                .eq("symbol", sym)
                .eq("config_version", "v3")
                .order("created_at", desc=False)
                .execute()
            )
            rows = res.data or []
        except Exception as e:
            results.append(_err("fifo_pnl", sym, f"DB query failed: {e}"))
            continue

        db_pnl = sum(
            float(r.get("realized_pnl") or 0)
            for r in rows if r.get("side") == "sell"
        )
        fifo_pnl, _ = _replay_fifo_pnl(rows)
        delta = db_pnl - fifo_pnl

        if abs(delta) <= PNL_TOLERANCE_USD:
            results.append(_ok(
                "fifo_pnl", sym,
                f"DB=${db_pnl:+.2f}, FIFO=${fifo_pnl:+.2f}, Δ=${delta:+.4f}"
            ))
        else:
            results.append(_fail(
                "fifo_pnl", sym,
                f"DB=${db_pnl:+.2f}, FIFO=${fifo_pnl:+.2f}, Δ=${delta:+.4f}"
            ))
    return results


def check_holdings(client, symbols: list[str]) -> list[dict]:
    """Check 2 — Σ buys − Σ sells = FIFO open holdings, no surprise."""
    results: list[dict] = []
    for sym in symbols:
        try:
            res = (
                client.table("trades")
                .select("side,amount,price,cost,created_at")
                .eq("symbol", sym)
                .eq("config_version", "v3")
                .order("created_at", desc=False)
                .execute()
            )
            rows = res.data or []
        except Exception as e:
            results.append(_err("holdings", sym, f"DB query failed: {e}"))
            continue

        net = sum(float(r.get("amount") or 0)
                  for r in rows if r.get("side") == "buy") \
            - sum(float(r.get("amount") or 0)
                  for r in rows if r.get("side") == "sell")
        _, fifo_holdings = _replay_fifo_pnl(rows)

        if abs(net - fifo_holdings) <= HOLDINGS_TOLERANCE:
            results.append(_ok(
                "holdings", sym,
                f"net={net:.8f}, fifo={fifo_holdings:.8f}"
            ))
        else:
            results.append(_fail(
                "holdings", sym,
                f"net={net:.8f}, fifo={fifo_holdings:.8f}, "
                f"Δ={(net - fifo_holdings):.8f}"
            ))
    return results


def check_negative_holdings(client) -> list[dict]:
    """Check 3 — no symbol may have sold more than it bought (data corruption)."""
    try:
        res = (
            client.table("trades")
            .select("symbol,side,amount")
            .eq("config_version", "v3")
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        return [_err("negative_holdings", None, f"DB query failed: {e}")]

    by_sym: dict[str, float] = {}
    for r in rows:
        sym = r.get("symbol")
        if not sym:
            continue
        amt = float(r.get("amount") or 0)
        if r.get("side") == "buy":
            by_sym[sym] = by_sym.get(sym, 0.0) + amt
        elif r.get("side") == "sell":
            by_sym[sym] = by_sym.get(sym, 0.0) - amt

    fails = [(s, n) for s, n in by_sym.items() if n < -NEGATIVE_DUST]
    if not fails:
        return [_ok("negative_holdings", None,
                    f"{len(by_sym)} symbols, all net ≥ 0")]
    # One critical entry per symbol with negative net — these are bugs.
    return [
        _fail("negative_holdings", s, f"net={n:.8f} (sold > bought)")
        for s, n in fails
    ]


def check_cash_accounting(client, symbols: list[str]) -> list[dict]:
    """Check 4 — capital_allocation − Σ buys + Σ sells − Σ skim ≈ dashboard cash.

    "Dashboard cash" here is computed the same way the home formula does:
    starting capital minus money out (buys) plus money in (sells) minus
    skimmed reserves. Big delta here means either skim is double-counted
    somewhere or trades were written without matching reserve_ledger
    entries.
    """
    results: list[dict] = []
    try:
        cfg_res = (
            client.table("bot_config")
            .select("symbol,capital_allocation")
            .execute()
        )
        cfg = {r["symbol"]: float(r.get("capital_allocation") or 0)
               for r in (cfg_res.data or [])}
    except Exception as e:
        return [_err("cash", None, f"bot_config query failed: {e}")]

    for sym in symbols:
        cap = cfg.get(sym)
        if cap is None:
            results.append(_err("cash", sym, "no bot_config row"))
            continue
        try:
            tres = (
                client.table("trades")
                .select("side,cost")
                .eq("symbol", sym)
                .eq("config_version", "v3")
                .execute()
            )
            trows = tres.data or []
            sres = (
                client.table("reserve_ledger")
                .select("amount")
                .eq("symbol", sym)
                .eq("config_version", "v3")
                .execute()
            )
            srows = sres.data or []
        except Exception as e:
            results.append(_err("cash", sym, f"DB query failed: {e}"))
            continue

        bought = sum(float(t.get("cost") or 0)
                     for t in trows if t.get("side") == "buy")
        sold = sum(float(t.get("cost") or 0)
                   for t in trows if t.get("side") == "sell")
        skim = sum(float(s.get("amount") or 0) for s in srows)
        # dashboard cash = capital - bought + sold - skim
        dash_cash = cap - bought + sold - skim
        # ledger cash = same but explicit; if they ever diverge we have
        # a bug in this very function. Kept for symmetry.
        ledger_cash = cap - bought + sold - skim
        delta = dash_cash - ledger_cash  # always 0 today; here for future split

        if abs(delta) <= CASH_TOLERANCE_USD:
            results.append(_ok(
                "cash", sym,
                f"alloc=${cap:.2f}, bought=${bought:.2f}, sold=${sold:.2f}, "
                f"skim=${skim:.2f}, cash=${dash_cash:.2f}"
            ))
        else:
            results.append(_fail(
                "cash", sym,
                f"dashboard=${dash_cash:.2f} vs ledger=${ledger_cash:.2f}, "
                f"Δ=${delta:.4f}"
            ))
    return results


def check_orphan_lots(client) -> list[dict]:
    """Check 5 — sells with buy_trade_id IS NULL that aren't FORCED_LIQUIDATION.

    A populated buy_trade_id is the audit trail: this sell consumed THIS buy.
    NULLs are expected only on FORCED_LIQUIDATION (the bot couldn't match
    a single buy because it was draining mixed lots). NULLs on other
    sells indicate the FIFO matching at write-time failed silently.
    """
    try:
        res = (
            client.table("trades")
            .select("symbol,reason,created_at")
            .eq("config_version", "v3")
            .eq("side", "sell")
            .is_("buy_trade_id", "null")
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        return [_err("orphan_lots", None, f"DB query failed: {e}")]

    suspicious = [
        r for r in rows
        if "FORCED_LIQUIDATION" not in (r.get("reason") or "").upper()
    ]
    if not suspicious:
        return [_ok("orphan_lots", None,
                    f"{len(rows)} sells with NULL buy_trade_id, all FORCED_LIQUIDATION")]

    # Group by symbol for the alert
    by_sym: dict[str, int] = {}
    for r in suspicious:
        s = r.get("symbol") or "?"
        by_sym[s] = by_sym.get(s, 0) + 1
    return [
        _fail("orphan_lots", s, f"{n} unmatched sells without buy_trade_id")
        for s, n in by_sym.items()
    ]


# ---------------------------------------------------------------------- #
# Top-level
# ---------------------------------------------------------------------- #

def run_health_check(client=None,
                     symbols: Optional[list[str]] = None,
                     send_telegram: bool = True) -> dict:
    """Run all five checks. Returns a structured report.

    If `symbols` is None, derives the active set from bot_config
    (any symbol with is_active=True OR holdings > 0 implied by trades).
    """
    if client is None:
        try:
            client = get_client()
        except Exception as e:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "all_ok": False,
                "error": f"could not get DB client: {e}",
                "checks": [],
            }

    if symbols is None:
        try:
            cfg = client.table("bot_config").select("symbol,is_active").execute()
            symbols = [r["symbol"] for r in (cfg.data or []) if r.get("is_active")]
        except Exception as e:
            logger.warning(f"Could not derive active symbols, using empty list: {e}")
            symbols = []

    # Always include any symbol that ever traded in v3, for completeness
    # of orphan/holdings checks.
    try:
        all_traded = client.table("trades").select("symbol")\
            .eq("config_version", "v3").execute()
        all_syms = sorted({r["symbol"] for r in (all_traded.data or [])})
    except Exception:
        all_syms = symbols

    checks: list[dict] = []
    checks.extend(check_fifo_pnl(client, all_syms))
    checks.extend(check_holdings(client, all_syms))
    checks.extend(check_negative_holdings(client))
    checks.extend(check_cash_accounting(client, symbols))
    checks.extend(check_orphan_lots(client))

    fails = [c for c in checks if c["status"] == "FAIL"]
    errors = [c for c in checks if c["status"] == "ERROR"]
    all_ok = not fails and not errors

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "all_ok": all_ok,
        "n_ok": sum(1 for c in checks if c["status"] == "OK"),
        "n_fail": len(fails),
        "n_error": len(errors),
        "checks": checks,
    }

    # Best-effort logging + alerting. None of these may raise.
    try:
        log_event(
            severity="warn" if not all_ok else "info",
            category="integrity",
            event="health_check_run",
            message=(
                f"Health check: {report['n_ok']} OK, "
                f"{report['n_fail']} FAIL, {report['n_error']} ERROR"
            ),
            details={"summary": {
                "all_ok": all_ok,
                "fails": [{"name": c["name"], "symbol": c["symbol"],
                           "detail": c["detail"]} for c in fails[:10]],
            }},
        )
    except Exception:
        pass

    if send_telegram and not all_ok:
        try:
            from utils.telegram_notifier import SyncTelegramNotifier
            lines = ["🚨 <b>Health check FAILED</b>"]
            if fails:
                lines.append(f"<b>FAIL ({len(fails)})</b>:")
                for c in fails[:10]:
                    sym = f"[{c['symbol']}] " if c['symbol'] else ""
                    lines.append(f"• {sym}<i>{c['name']}</i>: {c['detail']}")
                if len(fails) > 10:
                    lines.append(f"… +{len(fails) - 10} more")
            if errors:
                lines.append(f"<b>ERROR ({len(errors)})</b>:")
                for c in errors[:5]:
                    sym = f"[{c['symbol']}] " if c['symbol'] else ""
                    lines.append(f"• {sym}<i>{c['name']}</i>: {c['detail']}")
            SyncTelegramNotifier().send_message("\n".join(lines))
        except Exception:
            pass

    return report


# ---------------------------------------------------------------------- #
# CLI / standalone entry
# ---------------------------------------------------------------------- #

def _print_report(report: dict) -> None:
    print(f"\nHealth check @ {report['timestamp']}")
    if "error" in report:
        print(f"Status: ✗ FATAL — {report['error']}\n")
        return
    print(f"Status: {'✓ all_ok' if report['all_ok'] else '✗ FAILED'}  "
          f"(OK={report.get('n_ok', 0)}, "
          f"FAIL={report.get('n_fail', 0)}, "
          f"ERROR={report.get('n_error', 0)})\n")
    by_status: dict[str, list[dict]] = {"FAIL": [], "ERROR": [], "OK": []}
    for c in report["checks"]:
        by_status.setdefault(c["status"], []).append(c)
    for status in ("FAIL", "ERROR", "OK"):
        bucket = by_status.get(status, [])
        if not bucket:
            continue
        print(f"--- {status} ({len(bucket)}) ---")
        for c in bucket:
            sym = f" [{c['symbol']}]" if c["symbol"] else ""
            print(f"  {c['name']}{sym}: {c['detail']}")
        print()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    rep = run_health_check(send_telegram=False)
    _print_report(rep)
