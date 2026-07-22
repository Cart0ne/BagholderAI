#!/usr/bin/env python3.13
"""Fee-drag readout per il collaudo Kraken (S122, brief `sherpa-on-kraken` §4).

READ-ONLY. Produce i quattro numeri che il Board vuole osservare durante la
Fase 2b (abbiamo scelto di OSSERVARE il fee-drag invece di aggiungere subito un
minimo sell_pct Kraken-aware — questo script è lo strumento di quella scelta):

  1. numero di trade eseguiti (buy / sell)
  2. fee totale pagata
  3. P&L lordo vs P&L netto (la differenza È il costo delle fee)
  4. sell_pct medio proposto da Sherpa nel periodo

Le righe Kraken sono /USD, il testnet Binance è /USDT → il default filtra sul
suffisso /USD, così non serve una colonna `venue` sulla tabella `trades`.

Uso:
  venv/bin/python3.13 scripts/kraken_fee_drag_report.py
  venv/bin/python3.13 scripts/kraken_fee_drag_report.py --symbol BTC/USD --since 2026-07-22
  venv/bin/python3.13 scripts/kraken_fee_drag_report.py --cycle kraken_test
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import get_client


def _fmt(x, nd=4):
    return f"{x:,.{nd}f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Kraken collaudo fee-drag readout (read-only)")
    ap.add_argument("--symbol", default=None, help="es. BTC/USD (default: tutti i /USD)")
    ap.add_argument("--cycle", default=None, help="filtra per cycle (es. kraken_test)")
    ap.add_argument("--since", default=None, help="ISO date/time, es. 2026-07-22")
    args = ap.parse_args()

    c = get_client()

    q = c.table("trades").select(
        "symbol,side,cost,fee,realized_pnl,cycle,created_at,price"
    )
    if args.symbol:
        q = q.eq("symbol", args.symbol)
    if args.cycle:
        q = q.eq("cycle", args.cycle)
    if args.since:
        q = q.gte("created_at", args.since)
    trades = q.order("created_at").execute().data or []

    # Se non è stato passato --symbol, tieni solo le righe Kraken (/USD, NON /USDT).
    if not args.symbol:
        trades = [t for t in trades if str(t.get("symbol", "")).endswith("/USD")]

    print("=" * 64)
    print("KRAKEN COLLAUDO — FEE-DRAG READOUT (read-only)")
    filt = args.symbol or "tutti i /USD"
    print(f"  filtro: symbol={filt}"
          + (f" cycle={args.cycle}" if args.cycle else "")
          + (f" since={args.since}" if args.since else ""))
    print("=" * 64)

    if not trades:
        print("  Nessun trade Kraken nel periodo. (collaudo non ancora partito?)")
        return 0

    buys = [t for t in trades if t.get("side") == "buy"]
    sells = [t for t in trades if t.get("side") == "sell"]
    total_fees = sum(float(t.get("fee") or 0) for t in trades)
    buy_cost = sum(float(t.get("cost") or 0) for t in buys)
    sell_rev = sum(float(t.get("cost") or 0) for t in sells)
    realized_net = sum(float(t.get("realized_pnl") or 0) for t in sells)
    turnover = sum(abs(float(t.get("cost") or 0)) for t in trades)

    # P&L lordo (prima delle fee) vs netto. Il netto autorevole è la somma dei
    # realized_pnl (avg-cost, già al netto delle fee); il lordo = netto + fee.
    gross_pnl = realized_net + total_fees

    # (1) conteggio
    print(f"\n1) TRADE eseguiti: {len(trades)}  ({len(buys)} buy · {len(sells)} sell)")

    # (2) fee
    print(f"2) FEE totale pagata: ${_fmt(total_fees)}")

    # (3) lordo vs netto
    print(f"3) P&L realizzato:")
    print(f"     lordo (pre-fee):  ${_fmt(gross_pnl)}")
    print(f"     netto (post-fee): ${_fmt(realized_net)}")
    print(f"     → costo fee sul realizzato: ${_fmt(total_fees)}", end="")
    if abs(gross_pnl) > 1e-9:
        print(f"  ({_fmt(total_fees / abs(gross_pnl) * 100, 1)}% del lordo)")
    else:
        print()
    if turnover > 0:
        print(f"     fee / turnover: {_fmt(total_fees / turnover * 100, 2)}%  (drag per giro di capitale)")

    # (4) sell_pct medio proposto da Sherpa
    try:
        sym_for_sherpa = args.symbol or (sells[0].get("symbol") if sells else buys[0].get("symbol"))
        sq = c.table("sherpa_proposals").select(
            "proposed_sell_pct,proposed_regime,volatility_tier,created_at"
        ).eq("symbol", sym_for_sherpa)
        if args.since:
            sq = sq.gte("created_at", args.since)
        props = sq.order("created_at").execute().data or []
        vals = [float(p["proposed_sell_pct"]) for p in props if p.get("proposed_sell_pct") is not None]
        print(f"4) sell_pct medio proposto da Sherpa ({sym_for_sherpa}): ", end="")
        if vals:
            print(f"{_fmt(sum(vals) / len(vals), 3)}%  (N={len(vals)}, "
                  f"min {_fmt(min(vals),2)} / max {_fmt(max(vals),2)})")
            if props:
                last = props[-1]
                print(f"     ultimo: regime={last.get('proposed_regime')} "
                      f"tier={last.get('volatility_tier')} @ {str(last.get('created_at'))[:19]}")
        else:
            print("nessuna proposta Sherpa nel periodo.")
    except Exception as e:
        print(f"4) sell_pct medio: errore lettura sherpa_proposals: {e}")

    print("\n" + "=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
