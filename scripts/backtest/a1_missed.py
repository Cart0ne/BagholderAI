"""
A.1 (S130) — Passo 0b: vendite mancate per il bug della zona morta (misura
diretta, senza simulatore).

Per ogni minuto in cui il bot era acceso, con lo stato VERO (ricostruito dalle
operazioni reali) e i parametri in vigore in quel momento:
  - c'era una posizione vera, la scala era attiva (vendita precedente > 0) e il
    prezzo era sopra il costo medio;
  - il prezzo era sopra la soglia "costo medio + margine" (vendibile dopo il
    reset) ma sotto la soglia della scala (bloccato);
  - erano passate almeno `dead_zone_hours` dall'ultima operazione vera.
Ogni tratto consecutivo così è almeno UNA vendita che una zona morta funzionante
avrebbe fatto (al primo minuto del tratto). Tetto massimo: una vendita ogni
`dead_zone_hours` finché dura il tratto, senza superare i lotti in mano.

Uso: python a1_missed.py [binance|coinbase]
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import a1_data as D

FEE = 0.008


def real_state(symbol: str, px: pd.DataFrame) -> pd.DataFrame:
    """Stato vero (quantità, costo medio, scala, ultima operazione) a ogni minuto."""
    real = D.real_trades(symbol)
    rows = []
    qty = avg = last_sell = 0.0
    for _, t in real.iterrows():
        if t.side == "buy":
            avg = (avg * qty + t.cost + t.fee) / (qty + t.amount)
            qty += t.amount
        else:
            qty -= t.amount
            if qty <= 1e-9:
                qty = avg = last_sell = 0.0
            else:
                last_sell = t.price
        rows.append((t["dt"], qty, avg, last_sell, t["dt"]))
    st = pd.DataFrame(rows, columns=["dt", "qty", "avg", "last_sell", "last_trade"])
    m = pd.merge_asof(px[["dt", "close"]], st, on="dt", direction="backward")
    m[["qty", "avg", "last_sell"]] = m[["qty", "avg", "last_sell"]].fillna(0)
    return m


def missed(symbol: str, src: str = "binance") -> pd.DataFrame:
    px = D.prices(symbol, src)
    pf = D.param_frame(symbol, px)
    s = real_state(symbol, px)
    s = pd.concat([s, pf[["sell_pct", "dz_h", "regime"]]], axis=1)
    down = np.zeros(len(s), dtype=bool)
    for a, b in D.DOWNTIME:
        down |= ((s.dt >= a) & (s.dt < b)).values
    minq = D.COINS[symbol]["min_qty"]
    t_avg = s.avg * (1 + s.sell_pct / 100) / (1 - FEE)
    t_lad = s.last_sell * (1 + s.sell_pct / 100) / (1 - FEE)
    since_h = (s.dt - pd.to_datetime(s.last_trade, utc=True)).dt.total_seconds() / 3600
    cond = ((~down) & (s.qty >= minq) & (s.last_sell > 0) & (s.close > s.avg)
            & (s.close >= t_avg) & (s.close < t_lad) & (since_h >= s.dz_h))
    # Tra due operazioni vere lo stato non cambia. Una zona morta funzionante,
    # dopo dz_h ore con prezzo sopra la media e scala attiva, azzera la scala;
    # da lì il bot vende appena il prezzo tocca la soglia "media + margine"
    # (un tick dopo il reset). Conta la PRIMA vendita così per intervallo, se
    # arriva prima dell'operazione vera successiva (misura prudente: "almeno").
    dz_ok = ((~down) & (s.qty >= minq) & (s.last_sell > 0) & (s.close > s.avg)
             & (since_h >= s.dz_h))
    sell_ok = (~down) & (s.close >= t_avg) & (s.close < t_lad)
    out = []
    cpt = D.COINS[symbol]["cpt"]
    real = D.real_trades(symbol)
    for key, g in s.groupby("last_trade"):
        idx = g.index
        first_dz = idx[dz_ok[idx].values]
        if not len(first_dz):
            continue
        m1 = first_dz[0]
        cand = idx[(idx > m1 + 1) & sell_ok[idx].values]
        if not len(cand):
            continue
        a = s.loc[cand[0]]
        nxt = real[real["dt"] > pd.Timestamp(key)]
        real_next = nxt.iloc[0] if len(nxt) else None
        lot = min(cpt / a.close, a.qty)
        profit = (a.close - a.avg) * lot - a.close * lot * FEE
        stuck_h = (a["dt"] - s.loc[m1, "dt"]).total_seconds() / 3600
        out.append({
            "vendita_mancata": a["dt"], "regime": a.regime, "prezzo": round(a.close, 2),
            "sopra_media_%": round((a.close / a.avg - 1) * 100, 1),
            "soglia_scala": round(t_lad[a.name], 2), "zona_morta_h": a.dz_h,
            "profitto_lotto_$": round(profit, 2),
            "vendita_vera_dopo": (real_next["dt"].strftime("%m-%d %H:%M") + f" {real_next.side} {real_next.price:.2f}") if real_next is not None else "nessuna",
            "attesa_h": round(((real_next["dt"] if real_next is not None else s.dt.iloc[-1]) - a["dt"]).total_seconds() / 3600, 1),
        })
    return pd.DataFrame(out)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "binance"
    pd.set_option("display.width", 220)
    for symbol in D.COINS:
        m = missed(symbol, src)
        print(f"== {symbol} ({src}): {len(m)} intervalli con vendita mancata")
        if len(m):
            print(m.to_string())
            print(f"   almeno {len(m)} vendite mancate, profitto dei lotti ~${m['profitto_lotto_$'].sum():.2f}")
            print(m.groupby("regime").agg(vendite=("prezzo", "size"),
                                          profitto=("profitto_lotto_$", "sum")).to_string())
