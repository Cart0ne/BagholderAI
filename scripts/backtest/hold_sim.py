"""
Grid-regime-backtest — buy-and-hold benchmark.

Brief: stesso capitale, compra tutto al prezzo di APERTURA del giorno 1, poi
non fa nient'altro. Valore = holdings * prezzo a ogni candela.

Per un confronto equo paga UNA fee d'ingresso (taker Kraken), come il grid paga
le fee sui suoi buy. Le holdings finali sono marcate a mercato senza fee di
uscita — simmetrico al grid (le sue holdings residue sono unrealized).
"""

from __future__ import annotations
import pandas as pd


def run_hold(df: pd.DataFrame, capital: float, fee_rate: float) -> pd.DataFrame:
    open0 = float(df.iloc[0]["open"])
    spent = capital
    fee = spent * fee_rate
    coins = (spent - fee) / open0
    out = []
    for row in df.itertuples(index=False):
        price = float(row.close)
        out.append({
            "dt": row.dt,
            "price": price,
            "equity": coins * price,
            "coins": coins,
        })
    hdf = pd.DataFrame(out)
    hdf.attrs["entry_price"] = open0
    hdf.attrs["coins"] = coins
    hdf.attrs["entry_fee"] = fee
    return hdf
