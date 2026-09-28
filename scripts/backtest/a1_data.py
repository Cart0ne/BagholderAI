"""
A.1 (S130) — dati condivisi: prezzi 1m, operazioni reali, parametri nel tempo,
regimi Sherpa, fermi e riavvii del bot. Input in audits/ (non versionati).
"""

from __future__ import annotations

import json
import os

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
A1 = os.path.join(ROOT, "audits", "backtest", "a1")
SNAP = os.path.join(ROOT, "audits", "a1_snapshot_20260926")
DATA = os.path.join(ROOT, "audits", "backtest", "data")

T = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731

# Ricostruiti dai log grid sul Mini (S130): riga "Grid Bot starting" + buchi nei log.
RESTARTS = [T("2026-08-07 11:00:45"), T("2026-08-07 18:10:43"), T("2026-08-09 07:36:59"),
            T("2026-09-16 18:16:35"), T("2026-09-26 19:07:30"), T("2026-09-27 18:48:22")]
DOWNTIME = [
    (T("2026-09-05 05:23"), T("2026-09-14 14:39")),  # Mini senza rete (Errno 8 continuo)
    (T("2026-09-14 14:43"), T("2026-09-16 18:16")),  # riavvio macOS, bot non rilanciati
    (T("2026-09-16 23:42"), T("2026-09-17 00:03")),  # blocchi Supabase: loop fermo
    (T("2026-09-17 01:50"), T("2026-09-17 02:16")),
    (T("2026-09-17 03:16"), T("2026-09-17 03:41")),
    (T("2026-09-26 12:01"), T("2026-09-26 19:07")),  # riavvio Mini, bot giù
    (T("2026-09-27 08:33"), T("2026-09-27 18:48")),  # riavvio Mini, bot giù
]

COINS = {
    "BTC/USD": dict(base="BTC", start=T("2026-07-22 19:14"), cpt=33.33, skim=30.0,
                    cooldown=1800, min_qty=5e-05,
                    capital=[(T("2026-07-22 19:14"), 100.0), (T("2026-08-07 11:00:45"), 250.0)]),
    "SOL/USD": dict(base="SOL", start=T("2026-08-07 10:55"), cpt=20.0, skim=30.0,
                    cooldown=900, min_qty=0.06,
                    capital=[(T("2026-08-07 10:55"), 150.0)]),
}

PARAMS = {"buy_pct": "buy_pct", "sell_pct": "sell_pct", "idle_reentry_hours": "idle_h",
          "dead_zone_hours": "dz_h", "stop_buy_drawdown_pct": "sb_dd",
          "stop_buy_unlock_hours": "sb_unlock"}

# Valori a bot_config al 26-set per i parametri mai cambiati (fallback).
_CFG = {r["symbol"]: r for r in json.load(open(os.path.join(SNAP, "bot_config.json")))}


def prices(symbol: str, src: str = "binance") -> pd.DataFrame:
    """Candele 1m. src='binance' (BTC/USDT, SOL/USDT) o 'coinbase' (BTC-USD, SOL-USD)."""
    base = COINS[symbol]["base"]
    tag = "a1" if src == "binance" else "cb_a1"
    df = pd.read_csv(os.path.join(DATA, f"{base}_1m_{tag}_20260720_20260929.csv"), parse_dates=["dt"])
    df = df[df.dt >= COINS[symbol]["start"]].reset_index(drop=True)
    return df[["dt", "close", "high", "low"]]


def real_trades(symbol: str) -> pd.DataFrame:
    t = pd.DataFrame(json.load(open(os.path.join(A1, "trades.json"))))
    t = t[(t.symbol == symbol) & (t.cycle == "kraken_2b")].copy()
    t["dt"] = pd.to_datetime(t.created_at, utc=True, format="ISO8601")
    for c in ("price", "amount", "cost", "fee", "realized_pnl"):
        t[c] = pd.to_numeric(t[c])
    return t.sort_values("dt").reset_index(drop=True)


def config_changes(symbol: str) -> pd.DataFrame:
    c = pd.DataFrame(json.load(open(os.path.join(A1, "config_changes.json"))))
    c = c[(c.symbol == symbol) & (c.parameter.isin(PARAMS))].copy()
    c["dt"] = pd.to_datetime(c.created_at, utc=True, format="ISO8601")
    return c.sort_values("dt")


def regimes(symbol: str) -> pd.DataFrame:
    rows = json.load(open(os.path.join(SNAP, "sherpa_proposals.json")))
    rows += json.load(open(os.path.join(A1, "sherpa_proposals.json")))
    r = pd.DataFrame(rows)[["created_at", "symbol", "proposed_regime"]]
    r = r[r.symbol == symbol].copy()
    r["dt"] = pd.to_datetime(r.created_at, utc=True, format="ISO8601")
    return r.drop_duplicates("dt").sort_values("dt")[["dt", "proposed_regime"]]


def initial_params(symbol: str) -> dict:
    ch = config_changes(symbol)
    out = {}
    for p, col in PARAMS.items():
        first = ch[ch.parameter == p]
        out[col] = float(first.iloc[0].old_value) if len(first) else float(_CFG[symbol][p])
    return out


def param_frame(symbol: str, px: pd.DataFrame, fixed: bool = False) -> pd.DataFrame:
    """Parametri in vigore a ogni minuto (+ regime). fixed=True -> valori di partenza (C)."""
    init = initial_params(symbol)
    out = pd.DataFrame({"dt": px.dt})
    ch = config_changes(symbol)
    for p, col in PARAMS.items():
        if fixed:
            out[col] = init[col]
            continue
        s = ch[ch.parameter == p][["dt", "new_value"]].rename(columns={"new_value": col})
        s[col] = s[col].astype(float)
        m = pd.merge_asof(out[["dt"]], s, on="dt", direction="backward")
        out[col] = m[col].fillna(init[col]).values
    rg = pd.merge_asof(out[["dt"]], regimes(symbol), on="dt", direction="backward")
    out["regime"] = rg.proposed_regime.fillna("n/d").values
    return out[["buy_pct", "sell_pct", "idle_h", "dz_h", "sb_dd", "sb_unlock", "regime"]]
