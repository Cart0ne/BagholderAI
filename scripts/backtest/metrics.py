"""
Grid-regime-backtest — metriche per scenario (grid vs hold).

Le 7 metriche del brief:
  P&L finale (USDT) · P&L finale (%) · Max drawdown (%) · Numero trade
  completati · Skim totale accumulato (USDT) · Tempo attivo vs dormiente (%) ·
  Valore unrealized holdings fine periodo
"""

from __future__ import annotations
import pandas as pd


def max_drawdown_pct(equity: pd.Series) -> float:
    """Max peak-to-trough drawdown of an equity series, in %."""
    if len(equity) == 0:
        return 0.0
    running_peak = equity.cummax()
    dd = (equity - running_peak) / running_peak
    return float(dd.min() * 100)


def grid_metrics(sim, capital: float) -> dict:
    eq = sim.equity_df()
    tr = sim.trades_df()
    final_equity = float(eq.iloc[-1]["equity"]) if len(eq) else capital
    final_price = float(eq.iloc[-1]["price"]) if len(eq) else 0.0
    n_buys = int((tr["side"] == "buy").sum()) if len(tr) else 0
    n_sells = int((tr["side"] == "sell").sum()) if len(tr) else 0
    active_pct = float(eq["active"].mean() * 100) if len(eq) else 0.0
    return {
        "pnl_usdt": final_equity - capital,
        "pnl_pct": (final_equity / capital - 1) * 100,
        "max_drawdown_pct": max_drawdown_pct(eq["equity"]) if len(eq) else 0.0,
        "completed_sells": n_sells,
        "buys": n_buys,
        "total_fills": n_buys + n_sells,
        "skim_total": float(sim.reserve),
        "active_pct": active_pct,
        "dormant_pct": 100 - active_pct,
        "unrealized_holdings_value": float(sim.holdings) * final_price,
        "final_equity": final_equity,
        "realized": float(sim.realized),
        "final_holdings": float(sim.holdings),
        "final_avg": float(sim.avg),
        "final_cash": float(sim.cash),
    }


def hold_metrics(hdf: pd.DataFrame, capital: float) -> dict:
    final_equity = float(hdf.iloc[-1]["equity"])
    return {
        "pnl_usdt": final_equity - capital,
        "pnl_pct": (final_equity / capital - 1) * 100,
        "max_drawdown_pct": max_drawdown_pct(hdf["equity"]),
        "completed_sells": 0,
        "buys": 1,
        "total_fills": 1,
        "skim_total": 0.0,
        "active_pct": 100.0,
        "dormant_pct": 0.0,
        "unrealized_holdings_value": final_equity,
        "final_equity": final_equity,
    }
