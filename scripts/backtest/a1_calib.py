"""
A.1 (S130) — Passo 2: il simulatore rifà le operazioni vere?

Prova ANCORATA: per ogni operazione reale k si riparte dallo stato vero dopo k
(quantità, costo medio, cassa, riserva e scala dal database; riferimento
d'acquisto dalla prima riga "Range:" del log del bot dopo k) e si guarda la
prima operazione che fa il simulatore. Deve coincidere con l'operazione reale
k+1 (stesso lato, tempo e prezzo vicini). Così si provano le REGOLE senza che
un centesimo di differenza tra venue faccia divergere tutto il resto della storia.

Uso: python a1_calib.py <log_grid_BTC.utc> <log_grid_SOL.utc> [binance|coinbase]
"""

from __future__ import annotations

import re
import sys

import pandas as pd

import a1_data as D
from a1_sim import A1Grid, run_sim, trades_df

RANGE_RE = re.compile(r"^(\S+ \S+) .*Range:\s+\$([\d,\.]+) \(-([\d\.]+)% from last buy\)")


def log_refs(path: str) -> pd.DataFrame:
    rows = []
    for line in open(path, errors="replace"):
        m = RANGE_RE.match(line)
        if m:
            trig = float(m.group(2).replace(",", ""))
            pct = float(m.group(3))
            rows.append((pd.Timestamp(m.group(1), tz="UTC"), trig / (1 - pct / 100)))
    return pd.DataFrame(rows, columns=["dt", "ref"])


def state_after(real: pd.DataFrame, k: int):
    """Stato contabile vero dopo l'operazione k (stesse regole di state_manager)."""
    qty = avg = inv = rec = reserve = 0.0
    last_sell = 0.0
    last_buy_dt = None
    for i in range(k + 1):
        t = real.iloc[i]
        if t.side == "buy":
            cost_eff = t.cost + t.fee
            inv += cost_eff
            avg = (avg * qty + cost_eff) / (qty + t.amount)
            qty += t.amount
            last_buy_dt = t["dt"]
        else:
            rec += t.amount * t.price - t.fee
            r = (t.price - avg) * t.amount - t.fee
            if r > 0:
                reserve += r * 0.30
            qty -= t.amount
            if qty <= 1e-9:
                qty = avg = 0.0
                last_sell = 0.0
            else:
                last_sell = t.price
    return qty, avg, inv, rec, reserve, last_sell, last_buy_dt


def anchored(symbol: str, refs: pd.DataFrame, px: pd.DataFrame, horizon_h: float = 72):
    c = D.COINS[symbol]
    real = D.real_trades(symbol)
    pf_all = D.param_frame(symbol, px)
    out = []
    for k in range(len(real) - 1):
        t0 = real.iloc[k]
        t1 = real.iloc[k + 1]
        qty, avg, inv, rec, reserve, last_sell, last_buy_dt = state_after(real, k)
        cap = [v for ts, v in c["capital"] if ts <= t0["dt"]][-1]
        g = A1Grid(symbol, c["cpt"], c["skim"], c["cooldown"], c["min_qty"])
        g.set_capital(cap)
        g.cash = cap - inv + rec
        g.holdings, g.avg, g.reserve, g.last_sell_price = qty, avg, reserve, last_sell
        g.last_trade_time = g.dz_clock = t0["dt"]
        g.last_buy_time = last_buy_dt
        r = refs[(refs.dt > t0["dt"]) & (refs.dt <= t0["dt"] + pd.Timedelta("20min"))]
        if t0.side == "sell" and qty <= 1e-9:
            g.last_buy_price = t0.price
        elif len(r):
            g.last_buy_price = float(r.iloc[0].ref)
        else:
            g.last_buy_price = t0.price if t0.side == "buy" else 0.0
        # storia minima per restart(): ultimo acquisto vero + operazione k
        prev_buys = real.iloc[:k + 1][real.iloc[:k + 1].side == "buy"]
        if t0.side == "sell" and len(prev_buys):
            b = prev_buys.iloc[-1]
            g.trades.append({"dt": b["dt"], "side": "buy", "price": b.price})
        g.trades.append({"dt": t0["dt"], "side": t0.side, "price": t0.price})
        n0 = len(g.trades)
        mask = (px.dt > t0["dt"]) & (px.dt <= t1["dt"] + pd.Timedelta(hours=horizon_h))
        sl = px[mask].reset_index(drop=True)
        pf = pf_all[mask.values].reset_index(drop=True)
        caps = [(ts, v) for ts, v in c["capital"] if ts > t0["dt"]]
        rst = [ts for ts in D.RESTARTS if ts > t0["dt"]]
        # fermati alla prima operazione simulata
        for i in range(len(sl)):
            run_sim(g, sl.iloc[i:i + 1], pf.iloc[i:i + 1], caps, rst, D.DOWNTIME)
            caps = [(ts, v) for ts, v in caps if ts > sl.dt[i]]
            rst = [ts for ts in rst if ts > sl.dt[i]]
            if len(g.trades) > n0:
                break
        s = g.trades[n0] if len(g.trades) > n0 else None
        out.append({
            "k": k + 1, "real_dt": t1["dt"], "real_side": t1.side, "real_px": t1.price,
            "sim_dt": s["dt"] if s else None, "sim_side": s["side"] if s else None,
            "sim_px": s["price"] if s else None,
            "dmin": round((s["dt"] - t1["dt"]).total_seconds() / 60) if s else None,
        })
    return pd.DataFrame(out)


if __name__ == "__main__":
    src = sys.argv[3] if len(sys.argv) > 3 else "binance"
    pd.set_option("display.width", 200)
    for symbol, logp in (("BTC/USD", sys.argv[1]), ("SOL/USD", sys.argv[2])):
        px = D.prices(symbol, src)
        res = anchored(symbol, log_refs(logp), px)
        ok = (res.sim_side == res.real_side) & (res.dmin.abs() <= 30)
        res["esito"] = ok.map({True: "OK", False: "diverso"})
        print(f"== {symbol} ({src}): {ok.sum()}/{len(res)} operazioni rifatte (stesso lato, entro 30 min)")
        print(res.to_string())
