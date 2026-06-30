"""
Grid-regime-backtest — grafici (matplotlib, backend Agg, niente display).

Per scenario:
  1. price_chart  : prezzo + marker verdi (buy) / rossi (sell)
  2. equity_chart : equity grid vs hold, con incroci evidenziati
"""

from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd


def _style(ax):
    ax.grid(True, alpha=0.25, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))


def price_chart(df: pd.DataFrame, trades: pd.DataFrame, title: str, path: str):
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(df["dt"], df["close"], color="#3b6ea5", linewidth=0.8, label="BTC close (1m)")
    if trades is not None and len(trades):
        buys = trades[trades["side"] == "buy"]
        sells = trades[trades["side"] == "sell"]
        if len(buys):
            ax.scatter(buys["dt"], buys["price"], marker="^", s=46,
                       color="#1a9850", edgecolor="white", linewidth=0.4,
                       zorder=5, label=f"BUY ({len(buys)})")
        if len(sells):
            ax.scatter(sells["dt"], sells["price"], marker="v", s=46,
                       color="#d73027", edgecolor="white", linewidth=0.4,
                       zorder=5, label=f"SELL ({len(sells)})")
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_ylabel("Prezzo (USD)")
    _style(ax)
    ax.legend(loc="best", framealpha=0.9, fontsize=9)
    fig.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)


def equity_chart(grid_eq: pd.DataFrame, hold_eq: pd.DataFrame, capital: float,
                 title: str, path: str, repaired_eq: pd.DataFrame = None):
    fig, ax = plt.subplots(figsize=(13, 6))
    # align on grid timeline (same candles)
    g = grid_eq[["dt", "equity"]].rename(columns={"equity": "grid"})
    h = hold_eq[["dt", "equity"]].rename(columns={"equity": "hold"})
    m = pd.merge(g, h, on="dt", how="inner")

    ax.plot(m["dt"], m["grid"], color="#2c7fb8", linewidth=1.3, label="Grid (attuale)")
    if repaired_eq is not None:
        r = repaired_eq[["dt", "equity"]].rename(columns={"equity": "repaired"})
        m = pd.merge(m, r, on="dt", how="inner")
        ax.plot(m["dt"], m["repaired"], color="#1a9850", linewidth=1.5,
                label="Grid (riparato)")
    ax.plot(m["dt"], m["hold"], color="#e6794b", linewidth=1.3, label="Hold")
    ax.axhline(capital, color="#888888", linewidth=0.8, linestyle="--",
               label=f"Capitale (${capital:.0f})")

    # shade where grid > hold (green) and grid < hold (red)
    ax.fill_between(m["dt"], m["grid"], m["hold"],
                    where=(m["grid"] >= m["hold"]), interpolate=True,
                    color="#1a9850", alpha=0.10)
    ax.fill_between(m["dt"], m["grid"], m["hold"],
                    where=(m["grid"] < m["hold"]), interpolate=True,
                    color="#d73027", alpha=0.10)

    # crossover markers
    diff = (m["grid"] - m["hold"]).values
    sign = np.sign(diff)
    cross_idx = np.where(np.diff(sign) != 0)[0]
    if len(cross_idx):
        ax.scatter(m["dt"].values[cross_idx], m["grid"].values[cross_idx],
                   marker="o", s=28, color="#444444", zorder=6,
                   label=f"Incroci ({len(cross_idx)})")

    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_ylabel("Valore portafoglio (USD)")
    _style(ax)
    ax.legend(loc="best", framealpha=0.9, fontsize=9)
    fig.tight_layout()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)
