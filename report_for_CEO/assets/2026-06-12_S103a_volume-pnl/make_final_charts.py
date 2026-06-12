"""S103a — Grafici finali analisi interna (distinguono orphan sintetici da trade reali).

Riusa pairs.csv prodotto da analyze_internal.py.
"""
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
TIER_COLORS = {"A": "#4C72B0", "B": "#DD8452", "C": "#55A868"}

df = pd.read_csv(f"{OUT}/pairs.csv", parse_dates=["entry_ts", "exit_ts"])
clean = df[~df.is_orphan]

plt.rcParams.update({"figure.dpi": 130, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})

# 1. scatter: orphan in grigio, trade reali colorati, OLS sui reali
fig, ax = plt.subplots(figsize=(8.5, 5.5))
orph = df[df.is_orphan]
ax.scatter(orph.entry_volume, orph.pnl_pct, marker="x", color="#AAAAAA", s=42,
           label=f"ORPHAN_PERIOD_CLOSE sintetici (n={len(orph)}, 29 con PnL=0 forzato)")
for t in ["A", "B", "C"]:
    d = clean[clean.tier == t]
    if len(d):
        ax.scatter(d.entry_volume, d.pnl_pct, label=f"Tier {t} reali (n={len(d)})",
                   color=TIER_COLORS[t], alpha=0.85, s=52, edgecolor="white", linewidth=0.5)
lv = np.log10(clean.entry_volume)
b1, b0 = np.polyfit(lv, clean.pnl_pct, 1)
xs = np.linspace(lv.min(), lv.max(), 100)
ax.plot(10 ** xs, b0 + b1 * xs, "k--", linewidth=1.4,
        label=f"OLS sui reali: slope {b1:+.2f} (n.s.)")
ax.set_xscale("log")
ax.axhline(0, color="gray", linewidth=0.8)
ax.set_xlabel("Volume 24h all'entry (USD, scala log)")
ax.set_ylabel("PnL teorico entry→exit (%)")
ax.set_title("Volume vs PnL — 51 coppie TF (24 apr–8 mag 2026)\n"
             "le chiusure sintetiche hanno PnL≈0 per costruzione e diluiscono tutto")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(f"{OUT}/01_scatter_volume_pnl.png")

# 2. confronto: quartili campione completo vs terzili trade reali
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
df["vol_q"] = pd.qcut(df.entry_volume, 4, labels=["Q1\nbasso", "Q2", "Q3", "Q4\nalto"])
qt = df.groupby("vol_q", observed=True).agg(n=("pnl_pct", "size"), pnl=("pnl_pct", "mean"),
                                            orph=("is_orphan", "sum"))
axes[0].bar(range(4), qt.pnl, color=["#55A868", "#88B89A", "#C5BB7F", "#C44E52"])
axes[0].set_xticks(range(4), qt.index, fontsize=8)
for i, (v, n, o) in enumerate(zip(qt.pnl, qt.n, qt.orph)):
    axes[0].text(i, v + (0.06 if v >= 0 else -0.18),
                 f"{v:+.2f}%\nn={n} ({o} orph.)", ha="center", fontsize=8)
axes[0].axhline(0, color="gray", linewidth=0.8)
axes[0].set_title("CAMPIONE COMPLETO (51, come esplorazione CEO)\nquartili di volume — pattern NON monotono")
axes[0].set_ylabel("PnL medio %")

c = clean.copy()
c["vol_t"] = pd.qcut(c.entry_volume, 3, labels=["T1\nbasso", "T2", "T3\nalto"])
ct = c.groupby("vol_t", observed=True).agg(n=("pnl_pct", "size"), pnl=("pnl_pct", "mean"),
                                           wr=("win", "mean"))
axes[1].bar(range(3), ct.pnl, color=["#55A868", "#C5BB7F", "#C44E52"])
axes[1].set_xticks(range(3), ct.index, fontsize=8)
for i, (v, n, w) in enumerate(zip(ct.pnl, ct.n, ct.wr)):
    axes[1].text(i, v + 0.06, f"{v:+.2f}%\nn={n}, WR {w:.0%}", ha="center", fontsize=8)
axes[1].axhline(0, color="gray", linewidth=0.8)
axes[1].set_title("SOLO TRADE REALI (19, chiusi da mercato)\nterzili di volume — il vantaggio low-volume sparisce")
fig.tight_layout()
fig.savefig(f"{OUT}/02_quartili_pnl_wr.png")

# 5. predittori entry, solo trade reali
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
for ax, col, lab in ((axes[0], "entry_signal_strength", "signal_strength all'ALLOCATE"),
                     (axes[1], "entry_rsi", "RSI all'ALLOCATE")):
    ax.scatter(clean[col], clean.pnl_pct, alpha=0.8, s=46,
               c=[TIER_COLORS.get(t, "gray") for t in clean.tier])
    b1, b0 = np.polyfit(clean[col], clean.pnl_pct, 1)
    xs = np.linspace(clean[col].min(), clean[col].max(), 50)
    ax.plot(xs, b0 + b1 * xs, "k--", linewidth=1.2)
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_xlabel(lab)
axes[0].set_ylabel("PnL %")
fig.suptitle("Trade reali (n=19): segnali più 'tirati' all'entry → esiti peggiori (colore = tier)",
             fontsize=10)
fig.tight_layout()
fig.savefig(f"{OUT}/05_predittori_entry.png")

print("grafici 01/02/05 rigenerati (versione finale, orphan distinti)")
