"""
Grid-regime-backtest — regime scanner (fase 2: SOL, BONK).

Trova, sulla storia REALE di prezzo di ciascun coin, le finestre di 30 giorni
(mese di calendario) che rappresentano i tre regimi. Per ogni mese con dati
completi calcola:

  drift% = (close_ultimo_giorno / open_primo_giorno - 1) * 100   (trend netto)
  range% = (max_high - min_low) / min_low * 100                  (oscillazione)

Selezione (stessa filosofia del gate BTC del brief S110):
  bear    = mese con drift più NEGATIVO
  bull    = mese con drift più POSITIVO
  laterale= mese con |drift| minimo, MA deve passare il gate |drift| < 10%.
            Se lo supera -> "quasi-laterale", flaggato (un memecoin raramente
            va davvero piatto: onestà > forzare un'etichetta).

Sorgente = Binance daily (storico profondo, no API key). Read-only.
Cache in audits/backtest/data/{BASE}_1d_history.csv (gitignored).

Uso:
  venv/bin/python3.13 scripts/backtest/scan_regimes.py SOL/USDT
  venv/bin/python3.13 scripts/backtest/scan_regimes.py BONK/USDT --force
"""

from __future__ import annotations

import os
import sys
import time
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in (_REPO_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pandas as pd

DATA_DIR = os.path.join(_REPO_ROOT, "audits", "backtest", "data")

LATERAL_GATE_PCT = 10.0     # oltre questo |drift| il mese NON è laterale
MIN_DAYS_IN_MONTH = 26      # scarta mesi parziali (es. mese di listing)
MIN_LATERAL_RANGE_PCT = 8.0  # "laterale" = piatto MA con oscillazione da raccogliere

# Da dove iniziare a scaricare la storia daily (ccxt taglia comunque al listing).
_HISTORY_START = {
    "BTC": "2020-01-01",
    "SOL": "2020-08-01",
    "BONK": "2023-12-01",
}


def _ms(ts: str) -> int:
    return int(pd.Timestamp(ts, tz="UTC").timestamp() * 1000)


def fetch_daily_history(base: str, force: bool = False) -> pd.DataFrame:
    """Scarica (o carica da cache) l'intero storico daily del coin su Binance."""
    os.makedirs(DATA_DIR, exist_ok=True)
    cache = os.path.join(DATA_DIR, f"{base}_1d_history.csv")
    if os.path.exists(cache) and not force:
        return pd.read_csv(cache, parse_dates=["dt"])

    import ccxt
    ex = ccxt.binance({"enableRateLimit": True})
    sym = f"{base}/USDT"
    since = _ms(_HISTORY_START.get(base, "2020-01-01"))
    now_ms = ex.milliseconds()
    rows, cursor = [], since
    day_ms = 86_400_000
    while cursor < now_ms:
        batch = ex.fetch_ohlcv(sym, timeframe="1d", since=cursor, limit=1000)
        if not batch:
            break
        rows.extend(batch)
        nxt = batch[-1][0] + day_ms
        if nxt <= cursor:
            break
        cursor = nxt
        if len(batch) < 1000:
            break
        time.sleep(getattr(ex, "rateLimit", 200) / 1000.0)
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates(subset="ts").sort_values("ts").reset_index(drop=True)
    df["dt"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df.to_csv(cache, index=False)
    print(f"[scan] {base}: {len(df)} giorni {df['dt'].iloc[0].date()} -> "
          f"{df['dt'].iloc[-1].date()} -> {cache}")
    return df


def month_diagnostics(daily: pd.DataFrame) -> pd.DataFrame:
    """Un record per mese di calendario: drift%, range%, open/close/hi/lo."""
    d = daily.copy()
    d["ym"] = d["dt"].dt.strftime("%Y-%m")
    recs = []
    for ym, g in d.groupby("ym"):
        g = g.sort_values("dt")
        if len(g) < MIN_DAYS_IN_MONTH:
            continue  # mese parziale (listing o mese corrente incompleto)
        o = float(g.iloc[0]["open"])
        c = float(g.iloc[-1]["close"])
        hi = float(g["high"].max())
        lo = float(g["low"].min())
        y, m = ym.split("-")
        start = f"{ym}-01"
        end = f"{int(y)+1}-01-01" if m == "12" else f"{y}-{int(m)+1:02d}-01"
        recs.append({
            "ym": ym, "label": pd.Timestamp(start).strftime("%B %Y"),
            "start": start, "end": end, "days": len(g),
            "open": o, "close": c, "high": hi, "low": lo,
            "drift_pct": (c / o - 1) * 100,
            "range_pct": (hi - lo) / lo * 100,
        })
    return pd.DataFrame(recs).sort_values("ym").reset_index(drop=True)


def select_regimes(md: pd.DataFrame) -> dict:
    """bear = min drift, bull = max drift, laterale = |drift| minimo con range."""
    bear = md.loc[md["drift_pct"].idxmin()].to_dict()
    bull = md.loc[md["drift_pct"].idxmax()].to_dict()

    # laterale: fra i mesi con oscillazione reale, il più piatto.
    osc = md[md["range_pct"] >= MIN_LATERAL_RANGE_PCT]
    pool = osc if len(osc) else md
    lat = pool.loc[pool["drift_pct"].abs().idxmin()].to_dict()
    lat["gate_tripped"] = abs(lat["drift_pct"]) > LATERAL_GATE_PCT

    bear["regime"], bull["regime"], lat["regime"] = "Bearish", "Bullish", "Laterale"
    return {"bear": bear, "bull": bull, "lateral": lat}


def _rank_table(md: pd.DataFrame, by: str, ascending: bool, n: int = 5) -> str:
    top = md.sort_values(by, ascending=ascending).head(n)
    lines = ["| Mese | drift% | range% | open → close |", "|---|---|---|---|"]
    for _, r in top.iterrows():
        lines.append(f"| {r['label']} | {r['drift_pct']:+.1f}% | {r['range_pct']:.1f}% | "
                     f"{r['open']:.6g} → {r['close']:.6g} |")
    return "\n".join(lines)


def scan(symbol: str, force: bool = False, verbose: bool = True) -> dict:
    base = symbol.split("/")[0].upper()
    daily = fetch_daily_history(base, force=force)
    md = month_diagnostics(daily)
    sel = select_regimes(md)
    if verbose:
        print(f"\n===== {base}: {len(md)} mesi completi analizzati =====")
        for key, r in sel.items():
            gate = " ⚠️ GATE laterale superato (quasi-laterale)" if r.get("gate_tripped") else ""
            print(f"  {r['regime']:9} -> {r['label']:14} drift {r['drift_pct']:+6.1f}% "
                  f"range {r['range_pct']:5.1f}% [{r['start']} -> {r['end']}]{gate}")
        print(f"\n  Top-5 più ribassisti:\n{_rank_table(md, 'drift_pct', True)}")
        print(f"\n  Top-5 più rialzisti:\n{_rank_table(md, 'drift_pct', False)}")
    return {"base": base, "months": md, "selection": sel}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol", nargs="?", default="SOL/USDT")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    scan(args.symbol, force=args.force)
