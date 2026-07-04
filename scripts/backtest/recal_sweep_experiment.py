"""
Counterfactual: quanto costa (o rende) l'IDLE RECALIBRATE in lateral?

Sweep di idle_reentry_hours a parametri altrimenti CONGELATI (stessi dei report
grid-regime). Bot = variante 'repaired' (fix Piano A), fee Kraken 0.40%.

idle=0    -> idle path OFF del tutto (niente recalibrate, niente re-entry)
idle=720  -> recalibrate mai (finestra > periodo mensile) ma path abilitato
idle=4    -> BASELINE (valore congelato dei report)

Extra: variante 'no-recal' = idle OFF + dead_zone OFF (nessun reference-chasing).
"""
import os
import sys
import json
import pandas as pd

REPO = "/Users/max/Desktop/BagHolderAI/Repository/bagholder"
BT = os.path.join(REPO, "scripts", "backtest")
for p in (REPO, BT):
    if p not in sys.path:
        sys.path.insert(0, p)

from grid_sim import GridSim          # noqa: E402
from fetch_data import fetch_ohlcv    # noqa: E402
from hold_sim import run_hold         # noqa: E402
from metrics import grid_metrics, hold_metrics  # noqa: E402
import params as P                    # noqa: E402

FROZEN_DIR = os.path.join(REPO, "audits", "backtest")


def load_params(base):
    with open(os.path.join(FROZEN_DIR, f"frozen_params_{base}.json")) as f:
        return json.load(f)["params"]


# (base, id, dummy_start, dummy_end, label, kind)  -- date ignorate (cache hit)
DATASETS = [
    ("BTC", "lat_2023_08", "2023-08-01", "2023-09-01", "BTC lat Ago23", "lateral"),
    ("BTC", "lat_2023_09", "2023-09-01", "2023-10-01", "BTC lat Set23", "lateral"),
    ("SOL", "sol_laterale_2026_04", "2026-04-01", "2026-05-01", "SOL laterale", "lateral"),
    ("BONK", "bonk_laterale_2026_03", "2026-03-01", "2026-04-01", "BONK laterale", "lateral"),
    ("BTC", "bear_2022_06", "2022-06-01", "2022-07-01", "BTC BEAR (ctrl)", "bear"),
    ("BTC", "bull_2024_11", "2024-11-01", "2024-12-01", "BTC BULL (ctrl)", "bull"),
]

IDLE_SWEEP = [0.0, 2.0, 4.0, 8.0, 24.0, 720.0]


def build_sim(pr, df, idle_h, dead_zone_h=None):
    return GridSim(
        capital=pr["capital"], capital_per_trade=pr["capital_per_trade"],
        buy_pct=pr["buy_pct"], sell_pct=pr["sell_pct"], skim_pct=pr["skim_pct"],
        min_profit_pct=pr["min_profit_pct"],
        idle_reentry_hours=idle_h,
        dead_zone_hours=pr["dead_zone_hours"] if dead_zone_h is None else dead_zone_h,
        stop_buy_drawdown_pct=pr["stop_buy_drawdown_pct"],
        stop_buy_unlock_hours=pr["stop_buy_unlock_hours"],
        buy_cooldown_seconds=pr["buy_cooldown_seconds"],
        slippage_buffer_pct=pr["slippage_buffer_pct"], fee_rate=P.FEE_KRAKEN_TAKER,
        min_last_shot_usd=pr["min_last_shot_usd"], daily_trade_limit=pr["daily_trade_limit"],
        min_notional_usd=pr["min_notional_usd"], strategy=pr["strategy"],
        repaired=True,
    ).run(df)


def rng(df):
    o = float(df.iloc[0]["open"]); c = float(df.iloc[-1]["close"])
    hi = float(df["high"].max()); lo = float(df["low"].min())
    return (c / o - 1) * 100, (hi - lo) / lo * 100


print("=" * 84)
print("IDLE RECALIBRATE SWEEP  —  bot RIPARATO, fee Kraken 0.40%  (idle=4 = baseline report)")
print("=" * 84)

for base, sid, s0, s1, label, kind in DATASETS:
    pr = load_params(base)
    df = fetch_ohlcv(sid, s0, s1, base=base)
    drift, span = rng(df)
    hold = hold_metrics(run_hold(df, pr["capital"], P.FEE_KRAKEN_TAKER), pr["capital"])

    print(f"\n### {label}  [{kind}]  drift {drift:+.1f}% · range {span:.0f}% · "
          f"buy_pct {pr['buy_pct']}% · sell_pct {pr['sell_pct']}% · cap ${pr['capital']:.0f}")
    print(f"    HOLD: {hold['pnl_pct']:+.2f}%  (${hold['pnl_usdt']:+.2f})")
    print(f"    {'idle_h':>7} | {'P&L%':>8} | {'P&L$':>9} | {'buys':>5} | {'sells':>5} | "
          f"{'skim$':>7} | {'vs hold':>8}")
    print("    " + "-" * 70)
    base_pnl = None
    for idle_h in IDLE_SWEEP:
        g = grid_metrics(build_sim(pr, df, idle_h), pr["capital"])
        if idle_h == 4.0:
            base_pnl = g["pnl_pct"]
        tag = "  <= baseline" if idle_h == 4.0 else ""
        print(f"    {idle_h:>7.0f} | {g['pnl_pct']:>+7.2f}% | {g['pnl_usdt']:>+8.2f} | "
              f"{g['buys']:>5} | {g['completed_sells']:>5} | {g['skim_total']:>7.2f} | "
              f"{g['pnl_pct']-hold['pnl_pct']:>+7.2f}%{tag}")
    # extra: no-recal (idle off + dead_zone off)
    gnr = grid_metrics(build_sim(pr, df, 0.0, dead_zone_h=1e9), pr["capital"])
    d = gnr["pnl_pct"] - base_pnl if base_pnl is not None else 0.0
    print(f"    {'NO-RECAL':>7} | {gnr['pnl_pct']:>+7.2f}% | {gnr['pnl_usdt']:>+8.2f} | "
          f"{gnr['buys']:>5} | {gnr['completed_sells']:>5} | {gnr['skim_total']:>7.2f} | "
          f"{gnr['pnl_pct']-hold['pnl_pct']:>+7.2f}%   (Δ vs baseline {d:+.2f} pt)")

print("\n" + "=" * 84)
print("Δ vs baseline > 0  =>  spegnere/allungare il recalibrate AVREBBE reso di più.")
print("=" * 84)
