"""
A.1 (S130) — Quanto sono solide le differenze tra varianti?

Il grid è "caotico": un'operazione diversa all'inizio (per pochi centesimi di
prezzo) cambia tutta la storia dopo. Qui ogni variante gira N volte su prezzi
disturbati da un rumore minuto-per-minuto di sigma = 0,07% (metà dello scarto
medio misurato tra i nostri eseguiti Kraken e Binance, 0,14%) e si confronta
con BASE sullo STESSO disturbo (confronto appaiato).

Una variante "batte" BASE solo se vince nella grande maggioranza dei disturbi,
non se vince una volta.

Uso: python a1_robust.py [binance|coinbase] [N]
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

import a1_data as D
from a1_run import VARIANTS, run_variant, passive

SIGMA = 0.0007


def main(src: str, n: int):
    rows = []
    for symbol in D.COINS:
        px0 = D.prices(symbol, src)
        for seed in range(n):
            rng = np.random.default_rng(seed)
            px = px0.copy()
            if seed > 0:  # seed 0 = prezzi originali
                px["close"] = px0.close * (1 + rng.normal(0, SIGMA, len(px0)))
            for name in ["A", "B"]:
                eq = passive(symbol, px, name)
                rows.append((symbol, seed, name, eq.equity.iloc[-1] - eq.injected.iloc[-1]))
            for name in VARIANTS:
                g, eq, tr = run_variant(symbol, px, name)
                rows.append((symbol, seed, name, eq.equity.iloc[-1] - eq.injected.iloc[-1]))
    df = pd.DataFrame(rows, columns=["coin", "seed", "variante", "guadagno"])
    os.makedirs(D.A1, exist_ok=True)
    df.to_csv(os.path.join(D.A1, f"a1_robust_{src}_n{n}.csv"), index=False)
    base = df[df.variante == "BASE"].set_index(["coin", "seed"]).guadagno
    out = []
    for (coin, var), g in df.groupby(["coin", "variante"]):
        g = g.set_index(["coin", "seed"]).guadagno
        diff = g - base.loc[g.index]
        out.append({"coin": coin, "variante": var,
                    "guadagno_mediano": round(g.median(), 2),
                    "min": round(g.min(), 2), "max": round(g.max(), 2),
                    "diff_vs_BASE_mediana": round(diff.median(), 2),
                    "batte_BASE_%": round((diff > 0).mean() * 100) if var != "BASE" else None})
    res = pd.DataFrame(out)
    order = {v: i for i, v in enumerate(["A", "B", "BASE", "C", "D", "D2", "E1", "E2", "E3", "F", "G"])}
    res = res.sort_values(["coin", "variante"], key=lambda s: s.map(order) if s.name == "variante" else s)
    pd.set_option("display.width", 200)
    print(f"=== {src}, {n} disturbi (sigma {SIGMA*100:.2f}%)")
    print(res.to_string(index=False))
    res.to_csv(os.path.join(D.A1, f"a1_robust_summary_{src}_n{n}.csv"), index=False)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "binance", int(sys.argv[2]) if len(sys.argv) > 2 else 20)
