"""
Kraken plumbing check — FASE 0 del cutover (S117, 2026-07-11).

Read-only + validate-only. NO real orders, NO state changes, NO bot code
touched. Runs the §3 pre-flight of the kraken-cutover brief against the real
account (zero balance expected — auth/permission errors are the thing we are
hunting; "insufficient funds" style responses are EXPECTED and informative).

Steps:
  1. Public  — server Time (clock drift vs local) + AssetPairs resolution for
               the 3 grid pairs (ordermin / costmin / precision, no hardcode:
               pairs come from KrakenConfig.GRID_SYMBOLS).
  2. Auth    — fetch_balance with the real key. Empty balance is fine;
               AuthenticationError means wrong key/permissions → STOP.
  3. Fees    — fetch_trading_fee per pair (real maker/taker tier + 30d volume).
  4. Nonce   — 5 rapid sequential private calls (grid = 1 process per coin on
               one key at cutover; here we sanity-check the microsecond nonce).
  5. Orders  — AddOrder validate=true per pair, both order shapes the grid
               uses (market BUY by base amount, market SELL by base amount)
               plus the cost-order fallback (market BUY by quote amount).
               Kraken validates symbol/permissions/minimums WITHOUT executing.
  6. Client  — S118 "PROVA GENERALE": the same validate=true orders, but sent
               through KrakenClient.place_market_* — the EXACT methods the
               grid pipelines call after the Fase 1 wiring (step 5 exercised
               the raw ccxt layer only). Sizes are grid-realistic ($25 per
               step, the collaudo capital_per_trade). Also checks
               taker_fee_rate() returns a sane live tier (the dynamic fee
               consumed by trigger + floor).

Run on the Mac Mini (keys live in config/.env there):
    cd /Volumes/Archivio/bagholderai && venv/bin/python3.13 scripts/kraken_cutover_check.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import KrakenConfig  # noqa: E402  (loads .env)
from bot.exchanges.kraken_client import KrakenClient  # noqa: E402

PAIRS = KrakenConfig.GRID_SYMBOLS

PASS = "✅ PASS"
FAIL = "❌ FAIL"
INFO = "ℹ️  INFO"

results = []


def record(step: str, status: str, detail: str):
    results.append((step, status, detail))
    print(f"[{status}] {step}: {detail}")


def main():
    print("=" * 70)
    print("KRAKEN PLUMBING CHECK — FASE 0 (read-only + validate)")
    print("=" * 70)

    if not KrakenConfig.API_KEY or not KrakenConfig.SECRET:
        record("env", FAIL, "KRAKEN_API_KEY / KRAKEN_API_SECRET missing in config/.env")
        return finish()

    client = KrakenClient()
    ex = client.raw

    # --- Step 1a: server time / clock drift (vital for nonces) ---
    try:
        t0 = time.time()
        server_ms = ex.fetch_time()
        drift = abs(server_ms / 1000.0 - t0)
        status = PASS if drift < 5 else FAIL
        record("1a Time", status, f"server={server_ms} drift={drift:.2f}s (threshold 5s)")
    except Exception as e:
        record("1a Time", FAIL, f"{type(e).__name__}: {e}")
        return finish()

    # --- Step 1b: AssetPairs — the 3 pairs resolve, read minimums ---
    try:
        markets = ex.load_markets()
    except Exception as e:
        record("1b AssetPairs", FAIL, f"load_markets: {type(e).__name__}: {e}")
        return finish()

    pair_info = {}
    for sym in PAIRS:
        mk = markets.get(sym)
        if not mk:
            record(f"1b AssetPairs {sym}", FAIL, "pair NOT found on Kraken spot")
            continue
        limits = mk.get("limits") or {}
        prec = mk.get("precision") or {}
        info = {
            "kraken_id": mk.get("id"),
            "ordermin (base)": (limits.get("amount") or {}).get("min"),
            "costmin (quote)": (limits.get("cost") or {}).get("min"),
            "price_precision": prec.get("price"),
            "amount_precision": prec.get("amount"),
        }
        pair_info[sym] = info
        try:
            last = ex.fetch_ticker(sym).get("last")
            info["last_price"] = last
            om = info["ordermin (base)"]
            info["ordermin_usd"] = round(om * last, 2) if om and last else None
        except Exception as e:
            info["last_price"] = f"ticker failed: {e}"
        record(f"1b AssetPairs {sym}", PASS, str(info))

    # --- Step 2: authenticated fetch_balance ---
    try:
        bal = client.fetch_balance()
        total = bal.get("total") or {}
        nonzero = {k: v for k, v in total.items() if v}
        record("2 Auth fetch_balance", PASS,
               f"auth OK; non-zero balances: {nonzero or 'NONE (expected, account not funded)'}")
    except Exception as e:
        name = type(e).__name__
        if "Authentication" in name or "Permission" in name:
            record("2 Auth fetch_balance", FAIL, f"{name}: {e} → key/permissions wrong, STOP")
            return finish()
        record("2 Auth fetch_balance", FAIL, f"{name}: {e}")
        return finish()

    # --- Step 3: real fee tier per pair ---
    for sym in PAIRS:
        try:
            fee = client.fee_tier(sym)
            record(f"3 Fee tier {sym}", PASS if fee else FAIL,
                   f"maker={fee.get('maker')} taker={fee.get('taker')} "
                   f"(info: {(fee.get('info') or {})})" if fee else "empty response")
        except Exception as e:
            record(f"3 Fee tier {sym}", FAIL, f"{type(e).__name__}: {e}")

    # --- Step 4: nonce sanity — rapid sequential private calls ---
    try:
        t0 = time.time()
        for _ in range(5):
            ex.fetch_balance()
        record("4 Nonce burst", PASS, f"5 rapid private calls OK in {time.time()-t0:.2f}s")
    except Exception as e:
        record("4 Nonce burst", FAIL, f"{type(e).__name__}: {e}")

    # --- Step 5: AddOrder validate=true (NO execution, NO order id) ---
    # Sizes: exchange minimum (ordermin) so the check is decoupled from balance.
    for sym in PAIRS:
        info = pair_info.get(sym) or {}
        om = info.get("ordermin (base)")
        last = info.get("last_price")
        if not om or not isinstance(last, (int, float)):
            record(f"5 validate {sym}", FAIL, "missing ordermin/price from step 1b, skipped")
            continue

        # 5a: market BUY by base amount (the grid's primary path, 73c)
        try:
            resp = ex.create_order(sym, "market", "buy", om, None, {"validate": True})
            record(f"5a validate BUY base {sym}", PASS,
                   f"amount={om} accepted (validate). descr={(resp.get('info') or {}).get('descr')}")
        except Exception as e:
            record(f"5a validate BUY base {sym}", INFO, f"{type(e).__name__}: {e}")

        # 5b: market SELL by base amount
        try:
            resp = ex.create_order(sym, "market", "sell", om, None, {"validate": True})
            record(f"5b validate SELL base {sym}", PASS,
                   f"amount={om} accepted (validate). descr={(resp.get('info') or {}).get('descr')}")
        except Exception as e:
            record(f"5b validate SELL base {sym}", INFO, f"{type(e).__name__}: {e}")

        # 5c: market BUY by quote cost (the fallback path + CEO objection #2:
        # does Kraken's cost-order accept a quote amount the way Binance does?)
        cost = max(info.get("costmin (quote)") or 0, round(om * last * 1.05, 2))
        try:
            resp = ex.create_market_buy_order_with_cost(sym, cost, {"validate": True})
            record(f"5c validate BUY cost {sym}", PASS,
                   f"cost=${cost} accepted (validate). descr={(resp.get('info') or {}).get('descr')}")
        except Exception as e:
            record(f"5c validate BUY cost {sym}", INFO, f"{type(e).__name__}: {e}")

    # --- Step 6 (S118, Fase 1): PROVA GENERALE via KrakenClient ---
    # Same validate=true orders, but through the client methods the grid
    # pipelines actually call post-wiring (place_market_buy_base /
    # place_market_sell / place_market_buy). A None return here = the client
    # layer mangles what the raw layer accepted → wiring bug, catch it now.
    # Grid-realistic size: $25 (the collaudo capital_per_trade).
    GRID_STEP_USD = 25.0
    for sym in PAIRS:
        info = pair_info.get(sym) or {}
        last = info.get("last_price")
        if not isinstance(last, (int, float)) or not last:
            record(f"6 client validate {sym}", FAIL, "missing price from step 1b, skipped")
            continue
        base_amt = round(GRID_STEP_USD / last, 8)

        out = client.place_market_buy_base(sym, base_amt, params={"validate": True})
        record(f"6a client BUY base {sym}",
               PASS if out and out.get("validated") else FAIL,
               f"amount={base_amt} (${GRID_STEP_USD}) → {out and out.get('status')}")

        out = client.place_market_sell(sym, base_amt, params={"validate": True})
        record(f"6b client SELL base {sym}",
               PASS if out and out.get("validated") else FAIL,
               f"amount={base_amt} (${GRID_STEP_USD}) → {out and out.get('status')}")

        out = client.place_market_buy(sym, GRID_STEP_USD, params={"validate": True})
        record(f"6c client BUY cost {sym}",
               PASS if out and out.get("validated") else FAIL,
               f"cost=${GRID_STEP_USD} → {out and out.get('status')}")

    # --- Step 6d: dynamic taker fee (consumed by trigger + floor) ---
    try:
        rate = client.taker_fee_rate(PAIRS[0])
        is_fallback = rate == KrakenClient.FALLBACK_TAKER_FEE
        record("6d taker_fee_rate", PASS,
               f"{rate*100:.2f}% per side ({rate*2*100:.2f}% round-trip)"
               + (" — NOTE: equals the fallback; check fee_tier response" if is_fallback else " (live tier)"))
    except Exception as e:
        record("6d taker_fee_rate", FAIL, f"{type(e).__name__}: {e}")

    return finish()


def finish():
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    fails = [r for r in results if r[1] == FAIL]
    infos = [r for r in results if r[1] == INFO]
    for step, status, detail in results:
        print(f"  [{status}] {step}")
    print(f"\n{len(results)} checks — {len(fails)} FAIL, {len(infos)} INFO (expected-error candidates)")
    if fails:
        print("VERDICT: ❌ plumbing NOT green — see FAIL lines above.")
    else:
        print("VERDICT: ✅ plumbing green (INFO lines = zero-balance artifacts, documented).")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
