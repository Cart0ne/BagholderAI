"""
BagHolderAI — 47d Distance Filter Backtest
==========================================
Historical sweep over 90 days of 1h candles to find the optimal threshold for
`tf_entry_max_distance_pct`. Complementary to the forward counterfactual
tracker (47a): backtest answers "what would have happened?", tracker answers
"what is happening?".

Logic per (coin, threshold):
  - Walk 1h candles. At each candle compute distance_pct = (close - ema20) / ema20 * 100
  - Bullish gate (simplified vs full classifier): close > ema20 AND ema20 > ema50
  - If flat AND bullish AND 0 < distance_pct <= threshold → BUY at close
  - If holding:
      unrealized = (close - entry) / entry * 100
      if unrealized >= +5%  → SELL (profit_lock)
      if unrealized <= -3%  → SELL (stop_loss)
  - 1 position per coin at a time. Fee 0.075% per side.

Deviations from the brief (discussed with Max, approved):
  1. Coin universe = Top 100 USDT pairs by 24h volume *today* (deterministic
     and reproducible vs "what scanner evaluates today" which changes hourly).
  2. Bullish = close > ema20 AND ema20 > ema50 (closer to real classifier).
  3. Distance-band table is the headline output, not a "bonus".

Usage:
  python scripts/backtest_distance_filter.py --days 90 --lot-size 30
  python scripts/backtest_distance_filter.py --days 7 --thresholds 12,17,20  # quick test
  python scripts/backtest_distance_filter.py --cache  # reuse cached OHLCV

Outputs in scripts/output/:
  backtest_by_distance_band.csv  ← THE table to read
  backtest_summary.csv
  backtest_by_coin.csv
  backtest_trades.csv  (every simulated trade, for audit)

Read-only. No DB writes. No live bot impact.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from bot.exchange import create_exchange

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [backtest] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backtest")

# Output directory (relative to repo root, like scripts/cash_audit.py)
REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "scripts" / "output"
CACHE_DIR = REPO_ROOT / "scripts" / "output" / ".ohlcv_cache"

# Backtest parameters
FEE_RATE = 0.00075         # 0.075% per side, matches grid_bot.FEE_RATE
PROFIT_LOCK_PCT = 5.0      # match tf_profit_lock_pct (live default)
STOP_LOSS_PCT = -3.0       # match tf_stop_loss_pct (live)
DEFAULT_THRESHOLDS = [10, 12, 15, 17, 20, 25]
DEFAULT_LOT_SIZE = 30.0
DEFAULT_DAYS = 90
DISTANCE_BANDS = [
    ("0-5%",   0.0,  5.0),
    ("5-10%",  5.0,  10.0),
    ("10-15%", 10.0, 15.0),
    ("15-20%", 15.0, 20.0),
    ("20-25%", 20.0, 25.0),
    ("25%+",   25.0, float("inf")),
]


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_top_usdt_pairs(exchange, top_n: int = 100) -> list[str]:
    """Return up to top_n /USDT pairs by 24h quote volume, descending."""
    logger.info(f"Fetching top {top_n} USDT pairs by 24h volume...")
    tickers = exchange.fetch_tickers()
    rows = []
    for sym, t in tickers.items():
        if not sym.endswith("/USDT"):
            continue
        # Skip stablecoins and obvious leveraged tokens
        base = sym.split("/")[0]
        if base in {"USDT", "USDC", "BUSD", "TUSD", "DAI", "FDUSD", "PYUSD"}:
            continue
        if base.endswith("UP") or base.endswith("DOWN") or base.endswith("BULL") or base.endswith("BEAR"):
            continue
        vol = t.get("quoteVolume") or 0
        if vol > 0:
            rows.append((sym, float(vol)))
    rows.sort(key=lambda x: x[1], reverse=True)
    pairs = [s for s, _ in rows[:top_n]]
    logger.info(f"Selected {len(pairs)} pairs (volumes ${rows[0][1]/1e6:.0f}M ↘ ${rows[len(pairs)-1][1]/1e6:.1f}M)")
    return pairs


def fetch_ohlcv_cached(exchange, symbol: str, days: int, use_cache: bool) -> pd.DataFrame | None:
    """Fetch 1h OHLCV for `days` days. Returns DataFrame or None on failure.

    Cache key includes days so changing the window invalidates correctly.
    """
    safe = symbol.replace("/", "_")
    cache_path = CACHE_DIR / f"{safe}_{days}d.csv"
    if use_cache and cache_path.exists():
        try:
            df = pd.read_csv(cache_path)
            if len(df) > 50:  # sanity: not corrupted
                df["ts"] = pd.to_datetime(df["ts"], utc=True)
                return df
        except Exception:
            pass  # fall through to refetch

    needed = days * 24
    # Binance limit per call is 1000 candles. For 90 days * 24h = 2160 we need
    # multiple calls paged via the `since` param. Compute oldest start.
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - needed * 3600 * 1000

    all_rows: list[list] = []
    current = start_ms
    while True:
        try:
            batch = exchange.fetch_ohlcv(symbol, "1h", since=current, limit=1000)
        except Exception as e:
            logger.warning(f"  {symbol}: fetch_ohlcv error ({type(e).__name__}: {e}) — skipping")
            return None
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = batch[-1][0]
        if len(batch) < 1000 or last_ts >= end_ms:
            break
        current = last_ts + 3600 * 1000  # next hour
        time.sleep(0.15)  # gentle rate-limit; ccxt also throttles internally

    if not all_rows:
        return None

    df = pd.DataFrame(all_rows, columns=["ts_ms", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df = df.drop_duplicates(subset=["ts_ms"]).sort_values("ts_ms").reset_index(drop=True)

    if use_cache:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            df[["ts", "open", "high", "low", "close", "volume"]].to_csv(
                cache_path, index=False
            )
        except Exception as e:
            logger.warning(f"  cache write failed for {symbol}: {e}")

    return df


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

def add_emas(df: pd.DataFrame) -> pd.DataFrame:
    """Add ema20 + ema50 columns. Uses pandas' standard EWM (alpha = 2/(N+1))
    which matches ccxt/TradingView EMA.
    """
    df = df.copy()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["distance_pct"] = (df["close"] - df["ema20"]) / df["ema20"] * 100
    return df


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    symbol: str
    threshold: float
    entry_idx: int
    entry_ts: pd.Timestamp
    entry_price: float
    entry_distance_pct: float
    exit_idx: int
    exit_ts: pd.Timestamp
    exit_price: float
    exit_reason: str  # 'profit_lock' | 'stop_loss' | 'end_of_data'
    gross_pnl: float
    net_pnl: float
    holding_hours: float


def simulate(df: pd.DataFrame, symbol: str, threshold: float,
             lot_size: float) -> list[Trade]:
    """Walk the candle dataframe and produce a list of simulated trades."""
    trades: list[Trade] = []
    in_pos = False
    entry_idx = entry_price = entry_distance = 0.0
    entry_ts: pd.Timestamp | None = None

    closes = df["close"].values
    ema20 = df["ema20"].values
    ema50 = df["ema50"].values
    dist = df["distance_pct"].values
    ts = df["ts"].values

    n = len(df)
    # First 50 rows: EMAs not yet stable
    start = 50

    for i in range(start, n):
        c = closes[i]
        if not in_pos:
            bullish = (c > ema20[i]) and (ema20[i] > ema50[i])
            d = dist[i]
            if bullish and 0.0 < d <= threshold and not np.isnan(d):
                in_pos = True
                entry_idx = i
                entry_price = c
                entry_distance = d
                entry_ts = ts[i]
            continue

        # In position: check exits
        unreal = (c - entry_price) / entry_price * 100
        if unreal >= PROFIT_LOCK_PCT:
            reason = "profit_lock"
        elif unreal <= STOP_LOSS_PCT:
            reason = "stop_loss"
        else:
            continue

        # Close trade
        gross = (c - entry_price) * (lot_size / entry_price)  # ≈ lot_size * unreal/100
        fees = lot_size * FEE_RATE + (lot_size + gross) * FEE_RATE
        net = gross - fees
        holding = (ts[i] - entry_ts) / np.timedelta64(1, "h")
        trades.append(Trade(
            symbol=symbol, threshold=threshold,
            entry_idx=entry_idx, entry_ts=pd.Timestamp(entry_ts),
            entry_price=entry_price, entry_distance_pct=entry_distance,
            exit_idx=i, exit_ts=pd.Timestamp(ts[i]),
            exit_price=c, exit_reason=reason,
            gross_pnl=gross, net_pnl=net, holding_hours=float(holding),
        ))
        in_pos = False

    # Tail: still open at end of data
    if in_pos:
        i = n - 1
        c = closes[i]
        gross = (c - entry_price) * (lot_size / entry_price)
        fees = lot_size * FEE_RATE + (lot_size + gross) * FEE_RATE
        net = gross - fees
        holding = (ts[i] - entry_ts) / np.timedelta64(1, "h")
        trades.append(Trade(
            symbol=symbol, threshold=threshold,
            entry_idx=entry_idx, entry_ts=pd.Timestamp(entry_ts),
            entry_price=entry_price, entry_distance_pct=entry_distance,
            exit_idx=i, exit_ts=pd.Timestamp(ts[i]),
            exit_price=c, exit_reason="end_of_data",
            gross_pnl=gross, net_pnl=net, holding_hours=float(holding),
        ))

    return trades


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def trades_to_df(trades: list[Trade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    return pd.DataFrame([asdict(t) for t in trades])


def summarize_by_threshold(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for thr, g in df.groupby("threshold"):
        wins = (g["net_pnl"] > 0).sum()
        n = len(g)
        rows.append({
            "threshold_pct": thr,
            "trades": n,
            "win_rate_pct": round(wins / n * 100, 1) if n else 0.0,
            "avg_net_pnl": round(g["net_pnl"].mean(), 4),
            "total_net_pnl": round(g["net_pnl"].sum(), 2),
            "avg_holding_hours": round(g["holding_hours"].mean(), 1),
            "max_loss": round(g["net_pnl"].min(), 2),
            "max_gain": round(g["net_pnl"].max(), 2),
            "profit_locks": int((g["exit_reason"] == "profit_lock").sum()),
            "stop_losses": int((g["exit_reason"] == "stop_loss").sum()),
            "still_open": int((g["exit_reason"] == "end_of_data").sum()),
        })
    return pd.DataFrame(rows).sort_values("threshold_pct").reset_index(drop=True)


def summarize_by_distance_band(df: pd.DataFrame) -> pd.DataFrame:
    """Headline table: regardless of threshold filter, what was the actual
    win rate by entry distance band?"""
    if df.empty:
        return pd.DataFrame()
    rows = []
    for label, lo, hi in DISTANCE_BANDS:
        mask = (df["entry_distance_pct"] > lo) & (df["entry_distance_pct"] <= hi)
        g = df[mask]
        if len(g) == 0:
            rows.append({
                "distance_band": label, "trades": 0, "win_rate_pct": None,
                "avg_net_pnl": None, "total_net_pnl": None, "avg_holding_hours": None,
            })
            continue
        wins = (g["net_pnl"] > 0).sum()
        rows.append({
            "distance_band": label,
            "trades": int(len(g)),
            "win_rate_pct": round(wins / len(g) * 100, 1),
            "avg_net_pnl": round(g["net_pnl"].mean(), 4),
            "total_net_pnl": round(g["net_pnl"].sum(), 2),
            "avg_holding_hours": round(g["holding_hours"].mean(), 1),
        })
    return pd.DataFrame(rows)


def summarize_by_coin(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for (sym, thr), g in df.groupby(["symbol", "threshold"]):
        wins = (g["net_pnl"] > 0).sum()
        n = len(g)
        rows.append({
            "symbol": sym,
            "threshold_pct": thr,
            "trades": n,
            "win_rate_pct": round(wins / n * 100, 1) if n else 0.0,
            "total_net_pnl": round(g["net_pnl"].sum(), 2),
        })
    return pd.DataFrame(rows).sort_values(["symbol", "threshold_pct"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="47d distance filter backtest")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help=f"history window in days (default {DEFAULT_DAYS})")
    parser.add_argument("--lot-size", type=float, default=DEFAULT_LOT_SIZE,
                        help=f"USDT per simulated buy (default {DEFAULT_LOT_SIZE})")
    parser.add_argument("--thresholds", type=str,
                        default=",".join(map(str, DEFAULT_THRESHOLDS)),
                        help="comma-separated thresholds, e.g. 10,12,15,17,20,25")
    parser.add_argument("--top-n", type=int, default=100,
                        help="how many top USDT pairs to test (default 100)")
    parser.add_argument("--cache", action="store_true",
                        help="reuse cached OHLCV data when available")
    parser.add_argument("--symbols", type=str, default=None,
                        help="comma-separated explicit symbols (skips top-N)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    thresholds = [float(t) for t in args.thresholds.split(",") if t.strip()]
    logger.info(f"Backtest: days={args.days}, lot=${args.lot_size}, thresholds={thresholds}")

    exchange = create_exchange()
    exchange.load_markets()

    if args.symbols:
        pairs = [s.strip() for s in args.symbols.split(",") if s.strip()]
    else:
        pairs = fetch_top_usdt_pairs(exchange, top_n=args.top_n)

    all_trades: list[Trade] = []
    skipped = 0
    for idx, sym in enumerate(pairs, 1):
        logger.info(f"[{idx}/{len(pairs)}] {sym}")
        df = fetch_ohlcv_cached(exchange, sym, args.days, use_cache=args.cache)
        if df is None or len(df) < 60:
            skipped += 1
            continue
        df = add_emas(df)
        for thr in thresholds:
            trades = simulate(df, sym, thr, args.lot_size)
            all_trades.extend(trades)

    logger.info(f"Done: {len(pairs) - skipped}/{len(pairs)} symbols processed, "
                f"{skipped} skipped, {len(all_trades)} total trades")

    df_trades = trades_to_df(all_trades)
    if df_trades.empty:
        logger.warning("No trades produced. Check thresholds / time window / data.")
        return

    by_band = summarize_by_distance_band(df_trades)
    by_thr = summarize_by_threshold(df_trades)
    by_coin = summarize_by_coin(df_trades)

    # Save
    df_trades.to_csv(OUTPUT_DIR / "backtest_trades.csv", index=False)
    by_band.to_csv(OUTPUT_DIR / "backtest_by_distance_band.csv", index=False)
    by_thr.to_csv(OUTPUT_DIR / "backtest_summary.csv", index=False)
    by_coin.to_csv(OUTPUT_DIR / "backtest_by_coin.csv", index=False)

    # Console output (headline first)
    print()
    print("=" * 70)
    print("DISTANCE BAND TABLE — the headline answer")
    print("=" * 70)
    print(by_band.to_string(index=False))

    print()
    print("=" * 70)
    print("BY THRESHOLD — what we'd get setting tf_entry_max_distance_pct = X")
    print("=" * 70)
    print(by_thr.to_string(index=False))

    print()
    print(f"Files written in {OUTPUT_DIR.relative_to(REPO_ROOT)}/")
    for f in ["backtest_by_distance_band.csv", "backtest_summary.csv",
              "backtest_by_coin.csv", "backtest_trades.csv"]:
        size_kb = (OUTPUT_DIR / f).stat().st_size / 1024
        print(f"  {f}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
