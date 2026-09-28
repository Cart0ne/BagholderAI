"""
A.1 (S130) — Passo 3: le alternative del piano §4, a parità di capitale, fermi,
riavvii e commissioni (0,80%), su due fonti di prezzo indipendenti.

  REALE  operazioni vere (database), valutate allo stesso prezzo finale
  BASE   simulatore = la strategia che abbiamo fatto girare (Sherpa, bug incluso)
  A      compra e tieni dal primo acquisto (stesso capitale, stesse date)
  B      acquisti a rate settimanali (stesso totale), niente vendite
  C      grid a parametri fissi (valori di partenza), senza Sherpa
  D      zona morta funzionante (cronometro suo)
  D2     come D, ma il reset non tocca il riferimento d'acquisto
  E1/E2/E3  zona morta funzionante: 6h fisse / tabella Sherpa x3 / 24h fisse
  F      commissione maker 0,25% (regole di BASE)
  G      sell_pct +1 punto (regole di BASE)

Guadagno = valore finale (cassa + moneta x prezzo finale) - capitale versato.
Attribuzione per regime = somma delle variazioni di valore minuto per minuto,
etichettate col regime Sherpa in vigore ("fermo" se il bot era giù).

Uso: python a1_run.py [binance|coinbase]  -> stampa + CSV in audits/backtest/a1/
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

import a1_data as D
from a1_sim import A1Grid, equity_df, run_sim, trades_df

FEE = 0.008
# Tabella Sherpa attuale della zona morta (board_parameter_rules.py BOARD_TABLE)
DZ_TABLE = {"extreme_fear": 2, "fear": 1, "neutral": 2, "greed": 2, "extreme_greed": 3}

VARIANTS = {
    "BASE": {},
    "C": {"fixed": True},
    "D": {"dz_fix": True},
    "D2": {"dz_fix": True, "dz_keep_buy_ref": True},
    "E1": {"dz_fix": True, "dz_hours_fn": lambda r: 6.0},
    "E2": {"dz_fix": True, "dz_hours_fn": lambda r: 3.0 * DZ_TABLE.get(r, 2)},
    "E3": {"dz_fix": True, "dz_hours_fn": lambda r: 24.0},
    "F": {"fee_rate": 0.0025},
    "G": {"sell_pct_add": 1.0},
    # S131a: regola esplicita — zona morta spenta in neutrale/avidità/avidità
    # estrema, come oggi in paura/paura estrema, il reset non tocca il riferimento
    # S131a Q3: F' = commissione 0,25% con soglie di vendita calcolate a 0,80%
    "F2": {"fee_rate": 0.0025, "trigger_fee_rate": 0.008},
    "R": {"dz_off_regimes": ("neutral", "greed", "extreme_greed"), "dz_keep_buy_ref": True},
}


def run_variant(symbol: str, px: pd.DataFrame, name: str):
    c = D.COINS[symbol]
    v = dict(VARIANTS[name])
    fixed = v.pop("fixed", False)
    pf = D.param_frame(symbol, px, fixed=fixed)
    g = A1Grid(symbol, c["cpt"], c["skim"], c["cooldown"], c["min_qty"], **v)
    run_sim(g, px, pf, c["capital"], D.RESTARTS, D.DOWNTIME)
    return g, equity_df(g), trades_df(g)


def _downmask(dts: pd.Series) -> np.ndarray:
    m = np.zeros(len(dts), dtype=bool)
    for a, b in D.DOWNTIME:
        m |= ((dts >= a) & (dts < b)).values
    return m


def passive(symbol: str, px: pd.DataFrame, kind: str) -> pd.DataFrame:
    """A = compra e tieni, B = rate settimanali. Equity minuto per minuto."""
    c = D.COINS[symbol]
    caps = c["capital"]
    events = []  # (ts, usd da investire)
    if kind == "A":
        prev = 0.0
        for ts, cap in caps:
            events.append((ts, cap - prev)); prev = cap
    else:
        total = caps[-1][1]
        start, end = px.dt.iloc[0], px.dt.iloc[-1]
        n = int((end - start).days // 7) + 1
        per = total / n
        events = [(start + pd.Timedelta(days=7 * i), per) for i in range(n)]
    dts = list(px.dt)
    close = px.close.values
    qty = np.zeros(len(px))
    cash = np.zeros(len(px))
    inj = np.zeros(len(px))
    q = cs = injected = 0.0
    ei = ci = 0
    for i, t in enumerate(dts):
        while ci < len(caps) and caps[ci][0] <= t:
            injected = caps[ci][1]; ci += 1
        while ei < len(events) and events[ei][0] <= t:
            usd = events[ei][1]
            q += usd * (1 - FEE) / close[i]
            cs -= usd
            ei += 1
        qty[i], cash[i], inj[i] = q, cs, injected
    cash = cash + inj
    return pd.DataFrame({"dt": px.dt, "price": close, "equity": cash + qty * close,
                         "injected": inj, "down": _downmask(px.dt)})


def real_equity(symbol: str, px: pd.DataFrame) -> pd.DataFrame:
    c = D.COINS[symbol]
    real = D.real_trades(symbol)
    st = []
    cash_delta = qty = 0.0
    for _, t in real.iterrows():
        if t.side == "buy":
            cash_delta -= t.cost + t.fee; qty += t.amount
        else:
            cash_delta += t.cost - t.fee; qty -= t.amount
        st.append((t["dt"], cash_delta, qty))
    s = pd.DataFrame(st, columns=["dt", "cd", "qty"])
    m = pd.merge_asof(px[["dt", "close"]], s, on="dt", direction="backward").fillna(0)
    capdf = pd.DataFrame(c["capital"], columns=["dt", "cap"])
    inj = pd.merge_asof(px[["dt"]], capdf, on="dt", direction="backward").cap.fillna(0).values
    return pd.DataFrame({"dt": px.dt, "price": px.close, "equity": inj + m.cd + m.qty * m.close,
                         "injected": inj, "down": _downmask(px.dt)})


def attribution(eq: pd.DataFrame, regime: pd.Series) -> pd.Series:
    d = eq.equity.diff().fillna(0) - eq.injected.diff().fillna(0)
    lab = np.where(eq.down.values, "fermo", regime.values)
    return d.groupby(lab).sum()


def main(src: str):
    rows, attr_rows = [], []
    for symbol in D.COINS:
        px = D.prices(symbol, src)
        regime = D.param_frame(symbol, px).regime
        final = px.close.iloc[-1]
        curves = {"REALE": (real_equity(symbol, px), None),
                  "A": (passive(symbol, px, "A"), None),
                  "B": (passive(symbol, px, "B"), None)}
        for name in VARIANTS:
            g, eq, tr = run_variant(symbol, px, name)
            curves[name] = (eq, (g, tr))
        for name, (eq, extra) in curves.items():
            inj = eq.injected.iloc[-1]
            pnl = eq.equity.iloc[-1] - inj
            r = {"coin": symbol, "variante": name, "guadagno_$": round(pnl, 2),
                 "guadagno_%": round(pnl / inj * 100, 2)}
            if extra:
                g, tr = extra
                r.update({"acquisti": int((tr.side == "buy").sum()) if len(tr) else 0,
                          "vendite": int((tr.side == "sell").sum()) if len(tr) else 0,
                          "realizzato_$": round(g.realized, 2), "commissioni_$": round(g.total_fees, 2),
                          "moneta_in_mano_$": round(g.holdings * final, 2), "reset_zona_morta": g.dz_resets})
            rows.append(r)
            a = attribution(eq, regime)
            attr_rows.append({"coin": symbol, "variante": name, **{k: round(v, 2) for k, v in a.items()}})
    res = pd.DataFrame(rows)
    att = pd.DataFrame(attr_rows).fillna(0)
    os.makedirs(D.A1, exist_ok=True)
    res.to_csv(os.path.join(D.A1, f"a1_alternative_{src}.csv"), index=False)
    att.to_csv(os.path.join(D.A1, f"a1_regimi_{src}.csv"), index=False)
    pd.set_option("display.width", 220)
    print(f"=== fonte prezzi: {src}")
    print(res.to_string(index=False))
    print("\n--- guadagno per regime ($, variazione del valore mentre era in vigore quel regime)")
    print(att.to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "binance")
