"""S103a — Robustezza del finding esterno (test B).

Due minacce da escludere:
1. pump-contamination: vol7 al cross e' gonfiato dal rally che causa il cross
   -> ristratifica per volume STRUTTURALE (mediana 90g, shiftata di 10g) e per
      SURGE (vol7 / vol_strutturale).
2. dipendenza cross-sectional: gli eventi arrivano a grappoli
   -> spread Q1-Q4 calcolato per mese-evento, t-test sulle medie mensili.

Uso:
    python robustness_external.py <data_dir_jsonl> <output_dir>
"""
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_DIR, OUT_DIR = sys.argv[1], sys.argv[2]
CACHE = Path("/tmp/s103a_binance_panel.parquet")
BASE = "https://api.binance.com/api/v3/klines"
START_MS = int(pd.Timestamp("2025-06-01", tz="UTC").timestamp() * 1000)

if CACHE.exists():
    panel = pd.read_parquet(CACHE)
    print(f"## Panel da cache ({CACHE})")
else:
    scans = pd.read_json(f"{DATA_DIR}/trend_scans.jsonl", lines=True)
    symbols = sorted(scans.symbol.unique())
    frames = {}
    for i, sym in enumerate(symbols):
        url = f"{BASE}?symbol={sym.replace('/', '')}&interval=1d&startTime={START_MS}&limit=1000"
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=15) as r:
                    res = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code in (400, 404):
                    res = None
                    break
                time.sleep(2 * (attempt + 1))
            except Exception:
                res = None
                time.sleep(2 * (attempt + 1))
        if res:
            k = pd.DataFrame(res, columns=["open_time", "open", "high", "low", "close",
                                           "vol_base", "close_time", "quote_vol", "n_trades",
                                           "taker_base", "taker_quote", "ignore"])
            k = k[["open_time", "close", "quote_vol"]].astype(float)
            k["date"] = pd.to_datetime(k.open_time, unit="ms", utc=True)
            frames[sym] = k[["date", "close", "quote_vol"]]
        time.sleep(0.12)
    panel = pd.concat([f.assign(symbol=s) for s, f in frames.items()])
    panel.to_parquet(CACHE)
    print(f"## Panel scaricato e cachato ({len(frames)} symbol)")

px = panel.pivot(index="date", columns="symbol", values="close").sort_index()
qv = panel.pivot(index="date", columns="symbol", values="quote_vol").sort_index()

vol7 = qv.rolling(7, min_periods=5).mean()
vol_struct = qv.shift(10).rolling(90, min_periods=45).median()  # liquidita' strutturale
fwd7 = px.shift(-7) / px - 1

ema20 = px.ewm(span=20, adjust=False, min_periods=20).mean()
ema50 = px.ewm(span=50, adjust=False, min_periods=50).mean()
above = ema20 > ema50
cross_up = above & ~above.shift(1).astype("boolean").fillna(False).astype(bool) & ema50.notna()

events = []
for sym in px.columns:
    cu = cross_up[sym]
    for d in cu.index[cu]:
        if px[sym].loc[:d].notna().sum() < 60:
            continue
        v7, vs, f7 = vol7.at[d, sym], vol_struct.at[d, sym], fwd7.at[d, sym]
        if pd.isna(v7) or pd.isna(f7):
            continue
        events.append({"symbol": sym, "date": d, "vol7": v7, "vol_struct": vs,
                       "surge": v7 / vs if vs and vs > 0 else np.nan, "fwd7": f7})
ev = pd.DataFrame(events)
print(f"- eventi golden cross: {len(ev)} (con vol_struct valido: {ev.vol_struct.notna().sum()})")

def bucket_table(d, col, label):
    d = d.dropna(subset=[col, "fwd7"]).copy()
    d["q"] = pd.qcut(d[col].rank(method="first"), 4, labels=["Q1 basso", "Q2", "Q3", "Q4 alto"])
    g = d.groupby("q", observed=True).fwd7.agg(["size", "mean", "median"])
    g[["mean", "median"]] *= 100
    g["wr%"] = d.groupby("q", observed=True).fwd7.apply(lambda s: (s > 0).mean() * 100)
    print(f"\n### fwd7 per quartili di {label} (n={len(d)})")
    print(g.to_string(float_format=lambda v: f"{v:,.2f}"))
    q1 = d[d.q == "Q1 basso"].fwd7
    q4 = d[d.q == "Q4 alto"].fwd7
    mw = stats.mannwhitneyu(q1, q4, alternative="two-sided")
    sp = stats.spearmanr(d[col], d.fwd7)
    print(f"- Q1-Q4: {q1.mean()*100-q4.mean()*100:+.2f} p.p. (MW p={mw.pvalue:.4f}) | "
          f"Spearman {col}-fwd7: {sp.statistic:+.3f} (p={sp.pvalue:.4f})")
    return d

print("\n## ROBUSTEZZA 1 — quale variabile porta il segnale?")
d_recent = bucket_table(ev, "vol7", "volume RECENTE 7g (test originale)")
d_struct = bucket_table(ev, "vol_struct", "volume STRUTTURALE (mediana 90g, shift 10g)")
d_surge = bucket_table(ev, "surge", "SURGE (vol7/vol_struct, intensita' pump)")

# doppio sort: struct controlla surge e viceversa (mediane split per n piccoli)
d2 = ev.dropna(subset=["vol_struct", "surge", "fwd7"]).copy()
d2["s_struct"] = np.where(d2.vol_struct <= d2.vol_struct.median(), "struct BASSO", "struct ALTO")
d2["s_surge"] = np.where(d2.surge <= d2.surge.median(), "surge basso", "surge alto")
print("\n### doppio sort (mediane): fwd7 medio % / n")
piv = d2.pivot_table(index="s_struct", columns="s_surge", values="fwd7",
                     aggfunc=["mean", "size"])
piv["mean"] *= 100
print(piv.to_string(float_format=lambda v: f"{v:,.2f}"))

print("\n## ROBUSTEZZA 2 — clustering temporale (volume strutturale)")
d_struct["mese"] = d_struct.date.dt.to_period("M")
sm = d_struct.groupby(["mese", "q"], observed=True).fwd7.mean().unstack()
spread_m = ((sm["Q1 basso"] - sm["Q4 alto"]) * 100).dropna()
tt = stats.ttest_1samp(spread_m, 0)
print(f"- spread mensile Q1-Q4 (struct): media {spread_m.mean():+.2f} p.p., "
      f"positivo in {(spread_m > 0).sum()}/{len(spread_m)} mesi, "
      f"t={tt.statistic:+.2f}, p={tt.pvalue:.4f}")
print(spread_m.round(2).to_string())

# grafico riassuntivo robustezza
fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), sharey=True)
for ax, (d, col, lab) in zip(axes, ((d_recent, "vol7", "volume recente 7g\n(contaminato dal pump)"),
                                    (d_struct, "vol_struct", "volume strutturale\n(mediana 90g, shift 10g)"),
                                    (d_surge, "surge", "surge = recente/strutturale\n(intensità pump)"))):
    g = d.groupby("q", observed=True).fwd7.mean() * 100
    n = d.groupby("q", observed=True).size()
    ax.bar(range(4), g.values, color=["#55A868", "#88B89A", "#C5BB7F", "#C44E52"])
    ax.set_xticks(range(4), ["Q1\nbasso", "Q2", "Q3", "Q4\nalto"], fontsize=8)
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_title(lab, fontsize=9)
    for i, (v, n_) in enumerate(zip(g.values, n.values)):
        ax.text(i, v + (0.3 if v >= 0 else -0.55), f"{v:+.1f}\nn={n_}", ha="center", fontsize=7.5)
axes[0].set_ylabel("ritorno medio +7g (%)")
fig.suptitle("Robustezza: il gradiente sta nel volume strutturale o nell'intensità del pump?",
             fontsize=11)
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/08_robustezza_esterna.png", bbox_inches="tight")
print(f"\nsalvato 08_robustezza_esterna.png")
