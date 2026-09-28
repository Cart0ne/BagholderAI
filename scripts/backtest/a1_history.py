"""
A.1 (S130) — Passo 4: le stesse alternative su tratti storici di discesa,
laterale e salita (i 2 mesi reali sono quasi tutti rialzo).

Nessun Sherpa storico: i parametri si ricavano come fa Sherpa oggi, dal regime
Fear & Greed del giorno (alternative.me, stessa soglia di
sentinel/regime_analyzer.py) e dalle sue due tabelle:
  - parameter_rules.BASE_TABLE      buy_pct / sell_pct / idle (x volatilità)
  - board_parameter_rules.BOARD_TABLE  blocco perdita / sblocco / zona morta
Semplificazione dichiarata: il cambio di parametri è istantaneo (Sherpa li
muove a piccoli passi) e la volatilità è fissa (BTC 1,0 = LOW, SOL 1,53 = MID).
Nessun fermo e nessun riavvio. Ogni variante gira su N disturbi di prezzo
(confronto appaiato con BASE, come a1_robust.py).

Uso: python a1_history.py [N]
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

import a1_data as D
from a1_run import DZ_TABLE, FEE
from a1_sim import A1Grid, run_sim

BASE_TABLE = {
    "extreme_fear": (2.5, 1.0, 4.0), "fear": (1.8, 1.2, 2.0), "neutral": (1.0, 1.5, 1.0),
    "greed": (0.8, 2.0, 0.75), "extreme_greed": (0.5, 3.0, 0.5),
}
# (sb_dd, unlock_h, dz_h) per tier LOW (BTC) / MID (SOL)
BOARD = {
    "extreme_fear": {"LOW": (3, 12, 2), "MID": (4, 12, 2)},
    "fear": {"LOW": (4, 6, 1), "MID": (5, 6, 1)},
    "neutral": {"LOW": (1, 2, 2), "MID": (2, 2, 2)},
    "greed": {"LOW": (1, 2, 2), "MID": (1, 2, 2)},
    "extreme_greed": {"LOW": (1, 2, 3), "MID": (1, 2, 3)},
}
COIN = {
    "BTC": dict(mult=1.0, tier="LOW", capital=250.0, cpt=33.33, cooldown=1800, min_qty=5e-05,
                init=(1.8, 1.2, 2.0, 2.0, 3.0, 12.0)),  # valori di partenza BTC 22-lug
    "SOL": dict(mult=1.53, tier="MID", capital=150.0, cpt=20.0, cooldown=900, min_qty=0.06,
                init=(2.25, 1.5, 2.0, 2.0, 3.0, 12.0)),  # valori di partenza SOL 7-ago (a1_data.initial_params)
}
WINDOWS = [("BTC", l) for l in ("bear_2022_06", "feb_2023", "apr_2023", "jul_2023", "lat_2023_08",
                                 "lat_2023_09", "sep_2024", "bull_2024_11")] + \
          [("SOL", l) for l in ("sol_bearish_2022_11", "sol_laterale_2026_04", "sol_bullish_2021_02")]
SIGMA = 0.0007
DZ_FNS = {"E1": lambda r: 6.0, "E2": lambda r: 3.0 * DZ_TABLE.get(r, 2), "E3": lambda r: 24.0}
VARS = {"BASE": {}, "C": {}, "D": {"dz_fix": True}, "D2": {"dz_fix": True, "dz_keep_buy_ref": True},
        "E1": {"dz_fix": True, "dz_hours_fn": DZ_FNS["E1"]},
        "E2": {"dz_fix": True, "dz_hours_fn": DZ_FNS["E2"]},
        "E3": {"dz_fix": True, "dz_hours_fn": DZ_FNS["E3"]},
        "F": {"fee_rate": 0.0025}, "G": {"sell_pct_add": 1.0},
        "F2": {"fee_rate": 0.0025, "trigger_fee_rate": 0.008},
        "R": {"dz_off_regimes": ("neutral", "greed", "extreme_greed"), "dz_keep_buy_ref": True}}


def fng_regimes() -> pd.DataFrame:
    d = json.load(open(os.path.join(D.A1, "fng_history.json")))["data"]
    r = pd.DataFrame(d)
    r["dt"] = pd.to_datetime(r.timestamp.astype(int), unit="s", utc=True)
    v = r.value.astype(int)
    lab = r.value_classification.str.lower()
    r["regime"] = np.select(
        [(lab == "extreme fear") | (v <= 25), v <= 40, v <= 60, v <= 80],
        ["extreme_fear", "fear", "neutral", "greed"], "extreme_greed")
    return r.sort_values("dt")[["dt", "regime"]]


def params_for(px: pd.DataFrame, base: str, fng: pd.DataFrame, fixed: bool) -> pd.DataFrame:
    c = COIN[base]
    fng = fng.assign(dt=fng.dt.astype(px.dt.dtype))
    rg = pd.merge_asof(px[["dt"]], fng, on="dt", direction="backward").regime.fillna("neutral")
    if fixed:
        b, s, i, dz, sb, un = c["init"]
        return pd.DataFrame({"buy_pct": b, "sell_pct": s, "idle_h": i, "dz_h": dz,
                             "sb_dd": sb, "sb_unlock": un, "regime": rg.values})
    rows = []
    for r in rg.values:
        b, s, i = BASE_TABLE[r]
        sb, un, dz = BOARD[r][c["tier"]]
        rows.append((min(max(b * c["mult"], 0.3), 3.0), min(max(s * c["mult"], 0.8), 4.0),
                     min(max(i, 0.5), 6.0), dz, sb, un, r))
    return pd.DataFrame(rows, columns=["buy_pct", "sell_pct", "idle_h", "dz_h", "sb_dd", "sb_unlock", "regime"])


def run_one(base: str, px: pd.DataFrame, pf: pd.DataFrame, name: str) -> float:
    c = COIN[base]
    g = A1Grid(base, c["cpt"], 30.0, c["cooldown"], c["min_qty"], **VARS[name])
    start = px.dt.iloc[0]
    run_sim(g, px, pf, [(start, c["capital"])], [], [])
    return g.equity(px.close.iloc[-1]) - c["capital"]


def passive(base: str, px: pd.DataFrame, kind: str) -> float:
    cap = COIN[base]["capital"]
    close = px.close.values
    if kind == "A":
        q = cap * (1 - FEE) / close[0]
        return q * close[-1] - cap
    n = 4  # rate settimanali nel mese
    idx = [min(len(close) - 1, i * 7 * 1440) for i in range(n)]
    q = sum(cap / n * (1 - FEE) / close[i] for i in idx)
    return q * close[-1] - cap


def main(n: int):
    fng = fng_regimes()
    rows = []
    for base, label in WINDOWS:
        px0 = pd.read_csv(os.path.join(D.DATA, f"{base}_1m_{label}.csv"), parse_dates=["dt"])[["dt", "close"]]
        pf = params_for(px0, base, fng, fixed=False)
        pfc = params_for(px0, base, fng, fixed=True)
        mix = pf.regime.value_counts(normalize=True).mul(100).round().astype(int).to_dict()
        chg = (px0.close.iloc[-1] / px0.close.iloc[0] - 1) * 100
        for seed in range(n):
            px = px0.copy()
            if seed:
                px["close"] = px0.close * (1 + np.random.default_rng(seed).normal(0, SIGMA, len(px0)))
            res = {"A": passive(base, px, "A"), "B": passive(base, px, "B")}
            for name in VARS:
                res[name] = run_one(base, px, pfc if name == "C" else pf, name)
            for k, v in res.items():
                rows.append((base, label, round(chg, 1), json.dumps(mix), seed, k, v))
        print(f"done {base} {label} ({chg:+.1f}%, regimi {mix})", flush=True)
    df = pd.DataFrame(rows, columns=["coin", "finestra", "prezzo_%", "regimi_%", "seed", "variante", "guadagno"])
    df.to_csv(os.path.join(D.A1, f"a1_history_n{n}.csv"), index=False)
    base = df[df.variante == "BASE"].set_index(["finestra", "seed"]).guadagno
    out = []
    for (fin, var), g in df.groupby(["finestra", "variante"], sort=False):
        gg = g.set_index(["finestra", "seed"]).guadagno
        diff = gg - base.loc[gg.index]
        out.append({"finestra": fin, "prezzo_%": g["prezzo_%"].iloc[0], "variante": var,
                    "guadagno_mediano": round(gg.median(), 2),
                    "diff_vs_BASE": round(diff.median(), 2),
                    "batte_BASE_%": round((diff > 0).mean() * 100) if var != "BASE" else None})
    res = pd.DataFrame(out)
    res.to_csv(os.path.join(D.A1, f"a1_history_summary_n{n}.csv"), index=False)
    piv = res.pivot(index="finestra", columns="variante", values="guadagno_mediano")
    win = res.pivot(index="finestra", columns="variante", values="batte_BASE_%")
    pd.set_option("display.width", 220)
    print("\n--- guadagno mediano ($) per finestra")
    print(piv[["A", "B", "BASE", "C", "D", "D2", "E1", "E2", "E3", "F", "G"]].to_string())
    print("\n--- % dei disturbi in cui la variante batte BASE")
    print(win[["C", "D", "D2", "E1", "E2", "E3", "F", "G"]].to_string())


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
