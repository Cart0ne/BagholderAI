"""
Esperimento: grid con trend-gate (trailing-sell) vs grid puro vs hold.

Domanda (Max): un grid che in bull confermato smette di vendere e "cavalca"
con un trailing stop — quanto recupera di quel gap col hold? E quanto paga
nel laterale (whipsaw) e nel bear?

Onestà:
- Regime rilevato CAUSALMENTE (niente lookahead): uptrend = close > SMA(24h)
  E SMA in salita, calcolato solo sui dati passati (pandas rolling/shift).
- In più il "soffitto crystal-ball" = regime_up forzato True su tutta la finestra
  (trailing sempre acceso): il massimo teorico se la detection fosse perfetta.
  La distanza gated↔ceiling = il costo del ritardo/errore di detection.
- trail_pct = 4% dal picco (soglia delle nostre tf_grid, NON tarata sui dati).
- Grid puro = flag off = identico al backtest validato (regression check incluso).

Read-only. Usa la cache 1m già scaricata in audits/backtest/data/.
Uso: venv/bin/python3.13 scripts/backtest/trend_gate_experiment.py
"""

from __future__ import annotations
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for p in (_ROOT, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import json
import pandas as pd
import params as P
from grid_sim import GridSim
from hold_sim import run_hold
from metrics import grid_metrics, hold_metrics

OUT = os.path.join(_ROOT, "audits", "backtest")


def load_frozen(base: str) -> dict:
    """Parametri CONGELATI salvati (frozen_params_{BASE}.json) = riproducibili
    e coincidenti col report committato (load_frozen_params rileggerebbe live
    bot_config, che Sherpa muove -> non riproducibile)."""
    with open(os.path.join(OUT, f"frozen_params_{base}.json")) as f:
        return json.load(f)["params"]

DATA = os.path.join(_ROOT, "audits", "backtest", "data")
MA_WINDOW = 1440     # 24h di candele 1m
TRAIL_PCT = float(os.environ.get("TRAIL_PCT", "4.0"))

# coin -> regime -> (label, cache-file, drift atteso)
SCENARIOS = {
    "BTC/USDT": [
        ("Bear",     "BTC_1m_bear_2022_06.csv"),
        ("Bull",     "BTC_1m_bull_2024_11.csv"),
        ("Laterale", "BTC_1m_lat_2023_09.csv"),
    ],
    "SOL/USDT": [
        ("Bear",     "SOL_1m_sol_bearish_2022_11.csv"),
        ("Bull",     "SOL_1m_sol_bullish_2021_02.csv"),
        ("Laterale", "SOL_1m_sol_laterale_2026_04.csv"),
    ],
    "BONK/USDT": [
        ("Bear",     "BONK_1m_bonk_bearish_2025_02.csv"),
        ("Bull",     "BONK_1m_bonk_bullish_2024_11.csv"),
        ("Laterale", "BONK_1m_bonk_laterale_2026_03.csv"),
    ],
}


def add_regime(df: pd.DataFrame) -> pd.DataFrame:
    """Colonna regime_up CAUSALE: close > SMA(24h) e SMA in salita. No lookahead."""
    df = df.copy()
    sma = df["close"].rolling(MA_WINDOW, min_periods=MA_WINDOW).mean()
    sma_prev = sma.shift(MA_WINDOW)
    df["regime_up"] = ((df["close"] > sma) & (sma > sma_prev)).fillna(False)
    return df


def make_grid(pr, df, trend_gate=False):
    return GridSim(
        capital=pr["capital"], capital_per_trade=pr["capital_per_trade"],
        buy_pct=pr["buy_pct"], sell_pct=pr["sell_pct"], skim_pct=pr["skim_pct"],
        min_profit_pct=pr["min_profit_pct"], idle_reentry_hours=pr["idle_reentry_hours"],
        dead_zone_hours=pr["dead_zone_hours"], stop_buy_drawdown_pct=pr["stop_buy_drawdown_pct"],
        stop_buy_unlock_hours=pr["stop_buy_unlock_hours"], buy_cooldown_seconds=pr["buy_cooldown_seconds"],
        slippage_buffer_pct=pr["slippage_buffer_pct"], fee_rate=P.FEE_KRAKEN_TAKER,
        min_last_shot_usd=pr["min_last_shot_usd"], daily_trade_limit=pr["daily_trade_limit"],
        min_notional_usd=pr["min_notional_usd"], strategy=pr["strategy"],
        repaired=True, trend_gate=trend_gate, trail_pct=TRAIL_PCT,
    ).run(df)


def run_all():
    rows = []
    for symbol, scns in SCENARIOS.items():
        pr = load_frozen(symbol.split("/")[0])
        for label, fname in scns:
            path = os.path.join(DATA, fname)
            if not os.path.exists(path):
                print(f"[skip] {fname} assente"); continue
            df = pd.read_csv(path, parse_dates=["dt"])
            drift = (float(df.iloc[-1]["close"]) / float(df.iloc[0]["open"]) - 1) * 100

            # baseline grid puro (no regime column -> gate spento comunque)
            plain = make_grid(pr, df, trend_gate=False)
            # trend-gate causale
            dfr = add_regime(df)
            gated = make_grid(pr, dfr, trend_gate=True)
            # soffitto crystal-ball: regime_up = True ovunque
            dfc = df.copy(); dfc["regime_up"] = True
            ceil = make_grid(pr, dfc, trend_gate=True)
            hold = run_hold(df, pr["capital"], P.FEE_KRAKEN_TAKER)

            gm = grid_metrics(plain, pr["capital"])
            gg = grid_metrics(gated, pr["capital"])
            gc = grid_metrics(ceil, pr["capital"])
            hm = hold_metrics(hold, pr["capital"])
            up_pct = float(dfr["regime_up"].mean() * 100)
            rows.append({
                "coin": symbol.split("/")[0], "regime": label, "drift": drift,
                "plain": gm["pnl_pct"], "gated": gg["pnl_pct"], "ceil": gc["pnl_pct"],
                "hold": hm["pnl_pct"], "up_pct": up_pct,
                "plain_sells": gm["completed_sells"], "gated_sells": gg["completed_sells"],
            })
    return rows


def main():
    rows = run_all()
    print(f"\nTrend-gate experiment — trailing {TRAIL_PCT:.0f}% dal picco · "
          f"regime = close>SMA24h & SMA in salita (causale) · fee Kraken 0.40%\n")
    hdr = (f"{'Coin':5} {'Regime':9} {'drift':>7} | {'PLAIN':>8} {'GATED':>8} "
           f"{'CEIL(cb)':>8} {'HOLD':>8} | {'up%':>5} {'sell p→g':>9}")
    print(hdr); print("-" * len(hdr))
    for r in rows:
        print(f"{r['coin']:5} {r['regime']:9} {r['drift']:>+6.1f}% | "
              f"{r['plain']:>+7.2f}% {r['gated']:>+7.2f}% {r['ceil']:>+7.2f}% {r['hold']:>+7.2f}% | "
              f"{r['up_pct']:>4.0f}% {r['plain_sells']:>3d}→{r['gated_sells']:<3d}")
    print("\nLegenda: PLAIN=grid puro · GATED=trend-gate causale · CEIL=soffitto "
          "crystal-ball (detection perfetta) · up%=quota tempo in 'uptrend' rilevato.")
    # focus bull: quanto del hold cattura ciascuno
    print("\nCattura del rialzo nel BULL (P&L / hold):")
    for r in rows:
        if r["regime"] == "Bull" and r["hold"] != 0:
            print(f"  {r['coin']:5} plain {r['plain']/r['hold']*100:>4.0f}% · "
                  f"gated {r['gated']/r['hold']*100:>4.0f}% · ceiling {r['ceil']/r['hold']*100:>4.0f}%  (hold {r['hold']:+.0f}%)")


if __name__ == "__main__":
    main()
