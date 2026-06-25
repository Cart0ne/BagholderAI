"""
S109 — Breadth-signal analysis (brief tier-breadth-regime-signal _bis).

READ-ONLY. Tests the Board hypothesis: does an expansion of BULLISH Tier 3
coins lead the forward rebound of Tier 1/2 *before/better than F&G*, and is
the signal concentrated in T3-mid (volume > $2M)?

Method (CEO-confirmed, survivorship-safe):
  - Universe = the FULL set of Binance USDT spot pairs (not "top-N of today"),
    minus stablecoins / leveraged tokens.
  - 4h klines over ~6 months + a warmup buffer, via the PUBLIC Binance API
    (no key). Raw klines carry quote_asset_volume (USDT) per candle, so the
    24h volume — and therefore the tier — is computed PER DAY from the candles
    of that day. Delisted coins simply have no candles later; new coins none
    earlier. Both handled naturally.
  - Indicators reuse the LIVE bot classifier (EMA20/50, RSI14, ATR14,
    classify_signal) so "BULLISH" means exactly what the bot means.
  - Tier per day: vol24h >= 100M -> T1, >= 20M -> T2, else T3.
    T3 sub-segments: micro < $2M, mid $2M-$20M.

Outputs: report_for_CEO/assets/*.png + a JSON/STDOUT summary the report reads.

Run:  venv/bin/python3.13 scripts/breadth_analysis_s109.py
Cache: klines cached under the scratchpad so re-runs skip the download.
"""

from __future__ import annotations

import json
import os
import sys
import time
import pickle
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.trend_follower.classifier import classify_signal  # reuse live logic
from bot.trend_follower.scanner import STABLECOIN_SYMBOLS

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
BINANCE = "https://api.binance.com"
INTERVAL = "4h"
CANDLES_PER_DAY = 6                       # 24h / 4h
WINDOW_DAYS = 182                         # ~6 months of analysis
WARMUP_DAYS = 30                          # extra history for indicator warmup
FORWARD_HORIZONS = {"24h": 6, "3d": 18, "7d": 42}  # in 4h candles

TIER1_MIN = 100_000_000
TIER2_MIN = 20_000_000
T3_MICRO_MAX = 2_000_000                  # T3-micro < $2M, T3-mid $2M-$20M

# anchored "now" passed in / fixed (no Date.now in scripts elsewhere, but this
# is a standalone analysis run, so wall-clock is fine here)
NOW = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
END = NOW
START_ANALYSIS = END - timedelta(days=WINDOW_DAYS)
START_DOWNLOAD = START_ANALYSIS - timedelta(days=WARMUP_DAYS)

SCRATCH = os.environ.get("BREADTH_SCRATCH",
    "/private/tmp/claude-501/-Users-max-Desktop-BagHolderAI-Repository-bagholder/"
    "bcbc8510-020e-4e74-bfe9-8821c7d5deac/scratchpad")
CACHE_DIR = os.path.join(SCRATCH, "breadth_klines")
os.makedirs(CACHE_DIR, exist_ok=True)
ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "report_for_CEO", "assets")
os.makedirs(ASSETS, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "bagholderai-breadth-analysis/1.0"})


def log(msg):
    print(f"[breadth] {msg}", flush=True)


# ----------------------------------------------------------------------
# 1. Universe
# ----------------------------------------------------------------------
def is_leveraged(base: str) -> bool:
    return any(base.endswith(sfx) for sfx in ("UP", "DOWN", "BULL", "BEAR"))


def fetch_universe() -> list[str]:
    r = SESSION.get(f"{BINANCE}/api/v3/exchangeInfo", timeout=30)
    r.raise_for_status()
    syms = []
    for s in r.json()["symbols"]:
        if s.get("quoteAsset") != "USDT":
            continue
        if s.get("status") != "TRADING":
            continue
        pair = f"{s['baseAsset']}/USDT"
        if pair in STABLECOIN_SYMBOLS:
            continue
        if is_leveraged(s["baseAsset"]):
            continue
        syms.append(s["symbol"])      # raw "BTCUSDT" form for the klines API
    return sorted(set(syms))


# ----------------------------------------------------------------------
# 2. Klines download (paginated, cached, throttled)
# ----------------------------------------------------------------------
def _cache_path(symbol: str) -> str:
    return os.path.join(CACHE_DIR, f"{symbol}.pkl")


def fetch_klines(symbol: str, start_ms: int, end_ms: int) -> list[list]:
    out, cur = [], start_ms
    while cur < end_ms:
        for attempt in range(5):
            try:
                r = SESSION.get(f"{BINANCE}/api/v3/klines", params={
                    "symbol": symbol, "interval": INTERVAL,
                    "startTime": cur, "endTime": end_ms, "limit": 1000,
                }, timeout=30)
                if r.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                r.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 4:
                    raise
                time.sleep(1 + attempt)
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        last_open = batch[-1][0]
        if len(batch) < 1000:
            break
        cur = last_open + 1
        time.sleep(0.12)              # throttle
    return out


def download_all(universe: list[str]) -> dict[str, pd.DataFrame]:
    start_ms = int(START_DOWNLOAD.timestamp() * 1000)
    end_ms = int(END.timestamp() * 1000)
    data = {}
    for i, sym in enumerate(universe, 1):
        cp = _cache_path(sym)
        if os.path.exists(cp):
            with open(cp, "rb") as f:
                df = pickle.load(f)
        else:
            try:
                raw = fetch_klines(sym, start_ms, end_ms)
            except Exception as e:
                log(f"  {sym}: download failed ({e}); skipping")
                with open(cp, "wb") as f:
                    pickle.dump(None, f)
                continue
            if not raw:
                with open(cp, "wb") as f:
                    pickle.dump(None, f)
                continue
            df = pd.DataFrame(raw, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_vol", "trades", "tb_base", "tb_quote", "ignore",
            ])
            for c in ("open", "high", "low", "close", "quote_vol"):
                df[c] = df[c].astype(float)
            df["dt"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
            df = df[["dt", "open_time", "high", "low", "close", "quote_vol"]]
            with open(cp, "wb") as f:
                pickle.dump(df, f)
        if df is not None and len(df) >= 60:
            data[sym] = df
        if i % 50 == 0:
            log(f"  downloaded {i}/{len(universe)} ({len(data)} usable)")
    return data


# ----------------------------------------------------------------------
# 3. Per-symbol daily observations (indicators + vol24h + classify)
# ----------------------------------------------------------------------
def wilder_rsi(close: pd.Series, period=14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def compute_symbol_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized indicators on the full series, then sample once per UTC day
    (the 20:00 candle = last of the day) with that day's 24h quote volume."""
    df = df.sort_values("open_time").reset_index(drop=True)
    close = df["close"]
    ema_fast = close.ewm(span=20, adjust=False).mean()
    ema_slow = close.ewm(span=50, adjust=False).mean()
    rsi = wilder_rsi(close, 14)
    prev_c = close.shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - prev_c).abs(),
                    (df["low"] - prev_c).abs()], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean()
    atr_avg = atr.rolling(100, min_periods=50).mean()   # bot uses last-100 window

    df = df.assign(ema_fast=ema_fast, ema_slow=ema_slow, rsi=rsi,
                   atr=atr, atr_avg=atr_avg)
    df["date"] = df["dt"].dt.date
    df["hour"] = df["dt"].dt.hour
    # 24h quote volume per day = sum of that day's 6 candles
    vol24 = df.groupby("date")["quote_vol"].transform("sum")
    df["vol24h"] = vol24
    # one observation per day: the last candle of the UTC day (hour == 20)
    obs = df[df["hour"] == 20].copy()
    obs = obs.dropna(subset=["ema_fast", "ema_slow", "rsi", "atr", "atr_avg"])
    return obs


def classify_row(r) -> str:
    coin = {"ema_fast": r.ema_fast, "ema_slow": r.ema_slow,
            "rsi": r.rsi, "atr": r.atr, "atr_avg": r.atr_avg}
    return classify_signal(coin, {})["signal"]


# ----------------------------------------------------------------------
# 4. Build the per-day panel
# ----------------------------------------------------------------------
def build_panel(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for sym, df in data.items():
        obs = compute_symbol_daily(df)
        if obs.empty:
            continue
        for r in obs.itertuples():
            vol = r.vol24h
            if vol >= TIER1_MIN:
                tier = "T1"
            elif vol >= TIER2_MIN:
                tier = "T2"
            else:
                tier = "T3"
            sig = classify_row(r)
            rows.append({
                "symbol": sym, "date": r.date, "close": r.close,
                "vol24h": vol, "tier": tier, "signal": sig,
                "open_time": r.open_time,
            })
    panel = pd.DataFrame(rows)
    panel = panel[(pd.to_datetime(panel["date"]) >= pd.Timestamp(START_ANALYSIS.date()))]
    return panel.sort_values(["date", "symbol"]).reset_index(drop=True)


# ----------------------------------------------------------------------
# 5. Breadth series + forward returns
# ----------------------------------------------------------------------
def breadth_series(panel: pd.DataFrame) -> pd.DataFrame:
    def pct_bull(g):
        return 100.0 * (g["signal"] == "BULLISH").sum() / max(len(g), 1)

    out = []
    for date, g in panel.groupby("date"):
        t1 = g[g.tier == "T1"]; t2 = g[g.tier == "T2"]; t3 = g[g.tier == "T3"]
        t3_micro = t3[t3.vol24h < T3_MICRO_MAX]
        t3_mid = t3[(t3.vol24h >= T3_MICRO_MAX) & (t3.vol24h < TIER2_MIN)]
        out.append({
            "date": date,
            "n_total": len(g), "n_t1": len(t1), "n_t2": len(t2), "n_t3": len(t3),
            "n_t3_micro": len(t3_micro), "n_t3_mid": len(t3_mid),
            "breadth_t1": pct_bull(t1), "breadth_t2": pct_bull(t2),
            "breadth_t3": pct_bull(t3),
            "breadth_t3_micro": pct_bull(t3_micro) if len(t3_micro) else np.nan,
            "breadth_t3_mid": pct_bull(t3_mid) if len(t3_mid) else np.nan,
        })
    return pd.DataFrame(out).sort_values("date").reset_index(drop=True)


def forward_returns(panel: pd.DataFrame) -> pd.DataFrame:
    """Vol-weighted forward return of the T1 and T2 baskets per day."""
    # price path per symbol keyed by open_time for horizon lookups
    px = {}
    for sym, g in panel.groupby("symbol"):
        gg = g.sort_values("open_time")
        px[sym] = dict(zip(gg["open_time"], gg["close"]))
    step_ms = 4 * 3600 * 1000
    out = []
    for date, g in panel.groupby("date"):
        row = {"date": date}
        for tier in ("T1", "T2"):
            sub = g[g.tier == tier]
            if sub.empty:
                for h in FORWARD_HORIZONS:
                    row[f"fwd_{tier.lower()}_{h}"] = np.nan
                continue
            w = sub["vol24h"].values
            wsum = w.sum()
            for h, ncandles in FORWARD_HORIZONS.items():
                rets = []
                wts = []
                for r, wi in zip(sub.itertuples(), w):
                    fut_t = r.open_time + ncandles * step_ms
                    fut = px.get(r.symbol, {}).get(fut_t)
                    if fut and r.close > 0:
                        rets.append((fut - r.close) / r.close)
                        wts.append(wi)
                if rets:
                    row[f"fwd_{tier.lower()}_{h}"] = float(np.average(rets, weights=wts) * 100)
                else:
                    row[f"fwd_{tier.lower()}_{h}"] = np.nan
        out.append(row)
    return pd.DataFrame(out).sort_values("date").reset_index(drop=True)


# ----------------------------------------------------------------------
# 6. Fear & Greed (alternative.me)
# ----------------------------------------------------------------------
def fetch_fng() -> pd.DataFrame:
    r = SESSION.get("https://api.alternative.me/fng/",
                    params={"limit": WINDOW_DAYS + WARMUP_DAYS + 10, "format": "json"},
                    timeout=30)
    r.raise_for_status()
    rows = [{"date": datetime.fromtimestamp(int(d["timestamp"]), tz=timezone.utc).date(),
             "fng": int(d["value"]), "fng_label": d["value_classification"]}
            for d in r.json()["data"]]
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


# ----------------------------------------------------------------------
# 7. Analysis
# ----------------------------------------------------------------------
def corr_lag(breadth: pd.Series, fwd: pd.Series) -> float:
    m = breadth.notna() & fwd.notna()
    if m.sum() < 10:
        return np.nan
    return float(np.corrcoef(breadth[m], fwd[m])[0, 1])


def analyze(bdf, fdf, fng) -> dict:
    df = bdf.merge(fdf, on="date", how="inner").merge(fng, on="date", how="left")
    df = df.sort_values("date").reset_index(drop=True)
    res = {"n_days": int(len(df)),
           "date_start": str(df["date"].min()), "date_end": str(df["date"].max())}

    # transition episodes: T3 breadth spikes after a quiet stretch
    df["t3_prev5"] = df["breadth_t3"].rolling(5).mean().shift(1)
    df["t3_spike"] = (df["breadth_t3"] >= 20) & (df["t3_prev5"] <= 10)
    res["n_t3_spike_days"] = int(df["t3_spike"].sum())
    res["t3_breadth_mean"] = round(float(df["breadth_t3"].mean()), 2)
    res["t3_breadth_max"] = round(float(df["breadth_t3"].max()), 2)
    res["t3_breadth_zero_frac"] = round(float((df["breadth_t3"] == 0).mean()), 3)

    # lead/lag correlations: breadth_T3[t] vs forward return T1/T2[t]
    for tier in ("t1", "t2"):
        for h in FORWARD_HORIZONS:
            res[f"corr_t3_breadth_vs_fwd_{tier}_{h}"] = round(
                corr_lag(df["breadth_t3"], df[f"fwd_{tier}_{h}"]), 3)
    # volume filter: mid vs micro
    for seg in ("breadth_t3_mid", "breadth_t3_micro"):
        for h in FORWARD_HORIZONS:
            res[f"corr_{seg}_vs_fwd_t1_{h}"] = round(
                corr_lag(df[seg], df[f"fwd_t1_{h}"]), 3)
    # F&G control
    for h in FORWARD_HORIZONS:
        res[f"corr_fng_vs_fwd_t1_{h}"] = round(corr_lag(df["fng"], df[f"fwd_t1_{h}"]), 3)

    # conditional forward returns: high vs low T3 breadth
    hi = df[df["breadth_t3"] >= df["breadth_t3"].quantile(0.8)]
    lo = df[df["breadth_t3"] <= df["breadth_t3"].quantile(0.2)]
    for tier in ("t1", "t2"):
        for h in FORWARD_HORIZONS:
            res[f"fwd_{tier}_{h}_when_t3_high"] = round(float(hi[f"fwd_{tier}_{h}"].mean()), 3)
            res[f"fwd_{tier}_{h}_when_t3_low"] = round(float(lo[f"fwd_{tier}_{h}"].mean()), 3)

    # false positives: spike days with NON-positive T1 7d forward
    sp = df[df["t3_spike"]]
    if len(sp):
        res["spike_fwd_t1_7d_mean"] = round(float(sp["fwd_t1_7d"].mean()), 3)
        res["spike_false_positive_frac"] = round(float((sp["fwd_t1_7d"] <= 0).mean()), 3)
    else:
        res["spike_fwd_t1_7d_mean"] = None
        res["spike_false_positive_frac"] = None

    return res, df


# ----------------------------------------------------------------------
# 8. Plots
# ----------------------------------------------------------------------
def make_plots(df: pd.DataFrame):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = pd.to_datetime(df["date"])

    fig, ax = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    ax[0].plot(d, df["breadth_t1"], label="T1", lw=1.4)
    ax[0].plot(d, df["breadth_t2"], label="T2", lw=1.4)
    ax[0].plot(d, df["breadth_t3"], label="T3", lw=1.6, color="crimson")
    ax[0].set_ylabel("% bullish (breadth)"); ax[0].legend(); ax[0].grid(alpha=.3)
    ax[0].set_title("Breadth per tier (% BULLISH, live classifier)")
    ax2 = ax[1]
    ax2.plot(d, df["breadth_t3_mid"], label="T3-mid (>$2M)", color="darkgreen", lw=1.4)
    ax2.plot(d, df["breadth_t3_micro"], label="T3-micro (<$2M)", color="orange", lw=1.2, alpha=.8)
    ax2.plot(d, df["fng"], label="F&G index", color="gray", lw=1.0, ls="--")
    ax2.set_ylabel("% bullish  /  F&G"); ax2.legend(); ax2.grid(alpha=.3)
    ax2.set_title("T3 sub-segments vs F&G")
    fig.tight_layout(); fig.savefig(os.path.join(ASSETS, "breadth_s109_series.png"), dpi=110)
    plt.close(fig)

    # scatter: T3 breadth vs forward T1 7d
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(df["breadth_t3"], df["fwd_t1_7d"], s=14, alpha=.5)
    ax.axhline(0, color="k", lw=.6); ax.set_xlabel("T3 breadth (% bullish)")
    ax.set_ylabel("T1 forward return 7d (%)")
    ax.set_title("T3 breadth vs T1 forward 7d return")
    ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(ASSETS, "breadth_s109_scatter.png"), dpi=110)
    plt.close(fig)


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main():
    log(f"window {START_ANALYSIS.date()} -> {END.date()} (download from {START_DOWNLOAD.date()})")
    universe = fetch_universe()
    log(f"universe: {len(universe)} USDT pairs (stablecoins + leveraged excluded)")
    limit = int(os.environ.get("BREADTH_LIMIT", "0") or 0)
    if limit:
        seed = [s for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"] if s in universe]
        rest = [s for s in universe if s not in seed]
        universe = (seed + rest)[:limit]
        log(f"SMOKE: limited to {len(universe)} symbols")
    data = download_all(universe)
    log(f"usable symbols with >=60 candles: {len(data)}")
    panel = build_panel(data)
    log(f"panel rows (coin-days in window): {len(panel)}")
    bdf = breadth_series(panel)
    fdf = forward_returns(panel)
    fng = fetch_fng()
    res, merged = analyze(bdf, fdf, fng)
    make_plots(merged)

    merged.to_csv(os.path.join(SCRATCH, "breadth_s109_merged.csv"), index=False)
    with open(os.path.join(SCRATCH, "breadth_s109_results.json"), "w") as f:
        json.dump(res, f, indent=2, default=str)
    log("=== RESULTS ===")
    print(json.dumps(res, indent=2, default=str), flush=True)
    log(f"avg coins/day: T1={bdf.n_t1.mean():.0f} T2={bdf.n_t2.mean():.0f} "
        f"T3={bdf.n_t3.mean():.0f} (micro={bdf.n_t3_micro.mean():.0f} mid={bdf.n_t3_mid.mean():.0f})")


if __name__ == "__main__":
    main()
