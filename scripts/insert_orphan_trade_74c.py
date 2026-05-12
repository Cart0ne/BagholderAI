"""
Brief 74c — Cleanup orphan trade 21190 (BONK partial fill, 2026-05-12).

Context: pre-fix `_normalize_order_response` treated a Binance response
with status='expired' AND filled>0 as a no-op. Binance executed the
partial fill (1,368,998 BONK landed in the testnet wallet) but the bot
did not write the row in `trades`. Result: DRIFT_BINANCE_ORPHAN on the
nightly reconcile (cron_reconcile, run 2026-05-12T16:18:01Z).

This script fetches the real fills from Binance for order id 21190 and
inserts the corresponding row into `trades`. Dry-run by default: prints
the row it would insert and exits without writing. Pass --write to
actually INSERT.

Why a script and not a hand-written SQL: we need the *real* fill price,
the *real* fee, and the *real* fee currency from the Binance fill log,
not approximations. Hand-written SQL would risk wrong avg_buy_price on
the next DB replay (bot post-72a reconstructs avg from DB trades).

Usage (Mac Mini, where the bot runs):
    cd /Volumes/Archivio/bagholderai
    source venv/bin/activate
    python3.13 scripts/insert_orphan_trade_74c.py            # dry-run
    python3.13 scripts/insert_orphan_trade_74c.py --write    # apply

Safety: if a trade with `exchange_order_id='21190'` already exists in
`trades`, the script refuses to INSERT (avoids duplicate). After
--write succeeds, re-run `scripts/reconcile_binance.py --write` and
verify `binance_orphan=0` on BONK.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.exchange import create_exchange
from config.settings import TradingMode
from db.client import get_client, TradeLogger


ORDER_ID = "21190"
SYMBOL = "BONK/USDT"
# Brief 74c context (from reconcile log + grid_BONK_USDT.log):
EXPECTED_TS_ISO = "2026-05-12T10:30:11Z"


def fetch_order_fills(exchange, symbol: str, order_id: str) -> list:
    """Pull every fill that Binance recorded against `order_id`.

    Binance can split a single market order into multiple fills (the
    'expired' status here means: book ran out of liquidity midway, the
    fills already accepted are settled, the rest is voided). We pull
    the whole tape for the symbol and filter — `fetch_order(order_id)`
    is unreliable for non-'closed' orders on testnet.
    """
    fills = exchange.fetch_my_trades(symbol=symbol, limit=1000)
    matching = [f for f in fills if str(f.get("order")) == order_id]
    return matching


def aggregate_fills(fills: list) -> dict:
    """Collapse N fills of the same order into one logical trade row.

    Returns dict with: side, qty (filled lordo), avg_price, cost USDT,
    fee_native_amount, fee_currency, fee_usdt, ts_ms.
    """
    if not fills:
        raise RuntimeError(f"No fills found for order {ORDER_ID}")

    sides = {f["side"].lower() for f in fills}
    if len(sides) != 1:
        raise RuntimeError(f"Inconsistent sides in fills: {sides}")
    side = sides.pop()

    total_qty = sum(float(f["amount"]) for f in fills)
    total_cost = sum(float(f["cost"]) for f in fills)
    avg_price = total_cost / total_qty if total_qty > 0 else 0.0

    fee_native = 0.0
    fee_currency = ""
    for f in fills:
        fee = f.get("fee") or {}
        fcurr = (fee.get("currency") or "").upper()
        fcost = float(fee.get("cost", 0) or 0)
        if not fee_currency:
            fee_currency = fcurr
        elif fee_currency != fcurr:
            raise RuntimeError(
                f"Mixed fee currencies in fills: {fee_currency} vs {fcurr}"
            )
        fee_native += fcost

    # Mirror _normalize_order_response USDT-conversion logic
    base_coin = SYMBOL.split("/")[0].upper()
    quote_coin = SYMBOL.split("/")[1].upper()
    if fee_native <= 0 or not fee_currency:
        fee_usdt = 0.0
    elif fee_currency == quote_coin:
        fee_usdt = fee_native
    elif fee_currency == base_coin and avg_price > 0:
        fee_usdt = fee_native * avg_price
    else:
        fee_usdt = 0.0  # BNB-discount path; defer cross-rate

    last_ts = max(int(f["timestamp"]) for f in fills)
    return {
        "side": side,
        "qty": total_qty,
        "avg_price": avg_price,
        "cost": total_cost,
        "fee_native_amount": fee_native,
        "fee_currency": fee_currency,
        "fee_usdt": fee_usdt,
        "ts_ms": last_ts,
        "n_fills": len(fills),
    }


def already_inserted(client) -> bool:
    res = (
        client.table("trades")
        .select("id,created_at,amount,price")
        .eq("exchange_order_id", ORDER_ID)
        .execute()
    )
    return bool(res.data)


def build_trade_payload(agg: dict) -> dict:
    """Compose the row passed to TradeLogger.log_trade."""
    reason = (
        f"Brief 74c manual recovery: partial fill orphan, "
        f"Binance order {ORDER_ID} status='expired' filled={agg['qty']:.0f} "
        f"({agg['n_fills']} fills). Bot dropped response pre-fix; this row "
        f"re-syncs DB with the wallet balance Binance already settled."
    )
    return {
        "symbol": SYMBOL,
        "side": agg["side"],
        "amount": agg["qty"],
        "price": agg["avg_price"],
        "cost": agg["cost"],
        "fee": agg["fee_usdt"],
        "strategy": "A",
        "brain": "grid",
        "reason": reason,
        "mode": "live",
        "exchange_order_id": ORDER_ID,
        "managed_by": "grid",
        "fee_asset": agg["fee_currency"],
        "config_version": "v3",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--write", action="store_true",
                        help="Apply the INSERT (default: dry-run)")
    args = parser.parse_args()

    if not TradingMode.is_live():
        print(f"ERROR: TradingMode={TradingMode.MODE!r}, expected 'live'. "
              f"Set TRADING_MODE=live in env.", file=sys.stderr)
        return 2

    print(f"Fetching fills for order {ORDER_ID} on {SYMBOL}...")
    exchange = create_exchange()
    fills = fetch_order_fills(exchange, SYMBOL, ORDER_ID)
    if not fills:
        print(f"ERROR: no fills found for order {ORDER_ID}. "
              f"Possible causes: (a) wrong order id, (b) testnet reset "
              f"wiped the fill history, (c) wrong symbol.", file=sys.stderr)
        return 2

    agg = aggregate_fills(fills)
    print(f"Aggregated {agg['n_fills']} fill(s):")
    print(f"  side       = {agg['side']}")
    print(f"  qty        = {agg['qty']:.0f} {SYMBOL.split('/')[0]}")
    print(f"  avg_price  = ${agg['avg_price']:.10f}")
    print(f"  cost       = ${agg['cost']:.6f} USDT")
    print(f"  fee_native = {agg['fee_native_amount']} {agg['fee_currency']}")
    print(f"  fee_usdt   = ${agg['fee_usdt']:.6f}")
    print(f"  ts_ms      = {agg['ts_ms']} (expected ~{EXPECTED_TS_ISO})")

    client = get_client()
    if already_inserted(client):
        print(f"\nABORT: a trade with exchange_order_id='{ORDER_ID}' already "
              f"exists in `trades`. Nothing to do.", file=sys.stderr)
        return 1

    payload = build_trade_payload(agg)
    print(f"\nPlanned INSERT into `trades`:")
    for k, v in payload.items():
        print(f"  {k}: {v!r}")

    if not args.write:
        print(f"\nDry-run — re-run with --write to apply.")
        return 0

    print(f"\nWriting...")
    logger = TradeLogger()
    inserted = logger.log_trade(**payload)
    print(f"OK. Inserted trade id={inserted.get('id')}")
    print(f"Next step: re-run `scripts/reconcile_binance.py --write` and "
          f"verify binance_orphan=0 on BONK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
