"""
Grid-regime-backtest — historical OHLCV downloader (Binance via ccxt).

Brief: config/2026-06-28_S110_brief_grid-regime-backtest.md

- Risoluzione 1m (BTC loop = 60s -> candele da 1 minuto, fedele al polling live).
- Sorgente = Binance: ha lo storico profondo (2022/2023/2024) che a Kraken via
  REST non è recuperabile (l'endpoint OHLC dà solo ~720 candele). I dati di
  PREZZO sono identici tra venue ai fini del comportamento; la FEE invece è
  modellata su Kraken nel simulatore (vedi grid_sim.py). Disaccoppiati.
- Cache locale in audits/backtest/data/ (gitignored da `audits/*`): se il CSV
  esiste già non riscarica.

I dati pubblici klines NON richiedono API key e NON sono toccati dal blocco
EU su ordini/depositi (quello riguarda il trading, non i market-data feed).
"""

from __future__ import annotations

import os
import time
import pandas as pd

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(_REPO_ROOT, "audits", "backtest", "data")

# Candidate exchanges, in order. Binance first (deep history); fallbacks in case
# the public endpoint is geo-blocked from the run location.
_EXCHANGE_CANDIDATES = ["binance", "binanceus", "kraken"]


def _ms(ts: str) -> int:
    """ISO date 'YYYY-MM-DD' -> epoch ms (UTC)."""
    return int(pd.Timestamp(ts, tz="UTC").timestamp() * 1000)


def _make_exchange(name: str):
    import ccxt
    klass = getattr(ccxt, name)
    return klass({"enableRateLimit": True})


def _symbol_for(exchange_name: str, base: str = "BTC") -> str:
    # Price series is what matters; quote currency is irrelevant to OHLC shape.
    if exchange_name == "kraken":
        return f"{base}/USD"
    if exchange_name == "binanceus":
        return f"{base}/USDT"
    return f"{base}/USDT"


def _download_range(exchange, symbol: str, since_ms: int, end_ms: int,
                    timeframe: str = "1m") -> pd.DataFrame:
    all_rows = []
    cursor = since_ms
    limit = 1000
    tf_ms = 60_000  # 1m
    while cursor < end_ms:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=limit)
        if not batch:
            break
        all_rows.extend(batch)
        last = batch[-1][0]
        nxt = last + tf_ms
        if nxt <= cursor:
            break
        cursor = nxt
        if len(batch) < limit:
            # reached the tip of available data for this window
            if cursor >= end_ms:
                break
        time.sleep(getattr(exchange, "rateLimit", 200) / 1000.0)
    df = pd.DataFrame(all_rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df[(df["ts"] >= since_ms) & (df["ts"] < end_ms)]
    df = df.drop_duplicates(subset="ts").sort_values("ts").reset_index(drop=True)
    df["dt"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df


def fetch_ohlcv(label: str, start: str, end: str, timeframe: str = "1m",
                force: bool = False, base: str = "BTC") -> pd.DataFrame:
    """Download (or load from cache) OHLCV for [start, end).

    label: short scenario id used as the cache filename (e.g. 'bear_2022_06').
    start/end: 'YYYY-MM-DD' (UTC, end exclusive).
    base: coin symbol base (e.g. 'BTC', 'SOL', 'BONK'). Cache is keyed by base
          so multi-coin runs don't collide; BTC keeps its original filename.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    cache = os.path.join(DATA_DIR, f"{base}_{timeframe}_{label}.csv")
    if os.path.exists(cache) and not force:
        df = pd.read_csv(cache, parse_dates=["dt"])
        return df

    since_ms, end_ms = _ms(start), _ms(end)
    last_err = None
    for name in _EXCHANGE_CANDIDATES:
        try:
            ex = _make_exchange(name)
            sym = _symbol_for(name, base)
            print(f"[fetch] {label}: {name} {sym} {start}->{end} ({timeframe}) ...")
            df = _download_range(ex, sym, since_ms, end_ms, timeframe)
            if len(df) == 0:
                raise RuntimeError("empty dataframe")
            df.attrs["exchange"] = name
            df.attrs["symbol"] = sym
            df.to_csv(cache, index=False)
            print(f"[fetch] {label}: {len(df)} candele da {name} -> {cache}")
            return df
        except Exception as e:  # try next exchange
            last_err = e
            print(f"[fetch] {name} failed: {e}")
            continue
    raise RuntimeError(f"All exchanges failed for {label}: {last_err}")


if __name__ == "__main__":
    # Smoke test: a couple of days only.
    d = fetch_ohlcv("smoke_2024_11", "2024-11-01", "2024-11-03")
    print(d.head())
    print(d.tail())
    print("rows:", len(d))
