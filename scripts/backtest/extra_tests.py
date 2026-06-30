"""
Grid-regime-backtest — test addizionali (richiesti da Max, 2026-06-30):

  (1) VERO LATERALE: cerca tra più mesi 2023 (l'anno range-bound di BTC) quello
      davvero piatto+choppy (drift ~0, tante oscillazioni ≥ buy_pct) e verifica
      se lì il grid RIPARATO batte hold — è l'unico regime dove dovrebbe vincere.
  (2) MAKER vs TAKER: rigira gli scenari con fee maker Kraken 0.25% (ordini
      limite sulla scala) invece di taker 0.40% (market). Il grid "fatto bene"
      usa limiti. La fee più bassa abbassa anche il trigger di sell (più stretto)
      -> più raccolta. CAVEAT: assume che gli ordini limite si riempiano (nel
      sim close-only il sell scatta quando il close tocca il trigger).

Read-only. Output in audits/backtest/ (report_extra_tests.md + charts_extra/).
"""

from __future__ import annotations
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for p in (_REPO_ROOT, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
import params as P
from fetch_data import fetch_ohlcv
from grid_sim import GridSim
from hold_sim import run_hold
from metrics import grid_metrics, hold_metrics
from plots import price_chart, equity_chart

OUT_DIR = os.path.join(_REPO_ROOT, "audits", "backtest")
CHART_DIR = os.path.join(OUT_DIR, "charts_extra")

# candidati "vero laterale" — mesi BTC del range-year 2023 + un paio extra
LATERAL_BASKET = [
    ("feb_2023", "2023-02-01", "2023-03-01"),
    ("apr_2023", "2023-04-01", "2023-05-01"),
    ("jul_2023", "2023-07-01", "2023-08-01"),
    ("lat_2023_09", "2023-09-01", "2023-10-01"),  # già scaricato
    ("sep_2024", "2024-09-01", "2024-10-01"),
]

# tutti gli scenari per lo sweep maker/taker
ALL_SCENARIOS = [
    ("Bear gen-2022", "bear_2022_06", "2022-06-01", "2022-07-01"),
    ("Bull nov-2024", "bull_2024_11", "2024-11-01", "2024-12-01"),
    ("Laterale set-2023", "lat_2023_09", "2023-09-01", "2023-10-01"),
]


def count_swings(closes, thr=0.025) -> int:
    """Numero di inversioni di prezzo >= thr (zigzag): proxy di oscillazione.

    Pivot fisso finché il prezzo non rompe ±thr (stabilisce la prima direzione,
    NON conta come swing); poi traccia l'estremo nella direzione corrente e conta
    ogni inversione di thr dall'estremo."""
    sw, pivot, direction = 0, closes[0], 0
    for p in closes:
        ch = (p - pivot) / pivot
        if direction == 0:
            if ch >= thr:
                direction = 1; pivot = p
            elif ch <= -thr:
                direction = -1; pivot = p
        elif direction > 0:
            if p > pivot:
                pivot = p                       # estende il massimo
            elif (p - pivot) / pivot <= -thr:
                sw += 1; direction = -1; pivot = p
        else:  # direction < 0
            if p < pivot:
                pivot = p                       # estende il minimo
            elif (p - pivot) / pivot >= thr:
                sw += 1; direction = 1; pivot = p
    return sw


def diag(df) -> dict:
    o, c = float(df.iloc[0]["open"]), float(df.iloc[-1]["close"])
    hi, lo = float(df["high"].max()), float(df["low"].min())
    return {"open": o, "close": c, "drift": (c/o-1)*100,
            "range": (hi-lo)/lo*100, "swings": count_swings(df["close"].tolist())}


def run_grid(df, pr, fee, repaired):
    return GridSim(
        capital=pr["capital"], capital_per_trade=pr["capital_per_trade"],
        buy_pct=pr["buy_pct"], sell_pct=pr["sell_pct"], skim_pct=pr["skim_pct"],
        min_profit_pct=pr["min_profit_pct"], idle_reentry_hours=pr["idle_reentry_hours"],
        dead_zone_hours=pr["dead_zone_hours"], stop_buy_drawdown_pct=pr["stop_buy_drawdown_pct"],
        stop_buy_unlock_hours=pr["stop_buy_unlock_hours"], buy_cooldown_seconds=pr["buy_cooldown_seconds"],
        slippage_buffer_pct=pr["slippage_buffer_pct"], fee_rate=fee,
        min_last_shot_usd=pr["min_last_shot_usd"], daily_trade_limit=pr["daily_trade_limit"],
        min_notional_usd=pr["min_notional_usd"], strategy=pr["strategy"], repaired=repaired).run(df)


def fmt(x, d=2, p=False, s=False):
    return (f"{x:+,.{d}f}" if s else f"{x:,.{d}f}") + ("%" if p else "")


def main():
    os.makedirs(CHART_DIR, exist_ok=True)
    snap = P.load_frozen_params(); pr = snap["params"]
    L = ["# Grid-Regime Backtest — Test addizionali", "",
         "_Addendum a `report_grid_regime_backtest.md` (richiesta Max 2026-06-30): "
         "vero laterale + maker 0.25% vs taker 0.40%._", ""]

    # ---- (1) trova il vero laterale ----
    print("=== ricerca vero laterale ===")
    L += ["## (1) Cerca un VERO laterale (BTC, mesi candidati)", "",
          "| Mese | Drift | Range | Oscillazioni ≥2.5% |", "|---|---|---|---|"]
    cand = []
    for lab, s, e in LATERAL_BASKET:
        df = fetch_ohlcv(lab, s, e)
        d = diag(df); d.update({"lab": lab, "s": s, "e": e, "df": df})
        cand.append(d)
        print(f"{lab:12} drift {d['drift']:+6.2f}% range {d['range']:5.1f}% swings {d['swings']}")
        L.append(f"| {lab} | {d['drift']:+.2f}% | {d['range']:.1f}% | {d['swings']} |")
    # flattest con range >= 8% (deve oscillare)
    eligible = [c for c in cand if c["range"] >= 8.0] or cand
    best = min(eligible, key=lambda x: abs(x["drift"]))
    L += ["", f"**Scelto: `{best['lab']}`** — drift {best['drift']:+.2f}% (il più piatto "
          f"con oscillazione reale: range {best['range']:.1f}%, {best['swings']} swing ≥2.5%).", ""]
    print(f"-> scelto {best['lab']}")

    # ---- (2) run sul vero laterale: current/repaired/hold @ taker + repaired @ maker ----
    df = best["df"]
    cur_t = run_grid(df, pr, P.FEE_KRAKEN_TAKER, False)
    rep_t = run_grid(df, pr, P.FEE_KRAKEN_TAKER, True)
    rep_m = run_grid(df, pr, P.FEE_KRAKEN_MAKER, True)
    hold = run_hold(df, pr["capital"], P.FEE_KRAKEN_TAKER)
    mc, mrt, mrm = grid_metrics(cur_t, pr["capital"]), grid_metrics(rep_t, pr["capital"]), grid_metrics(rep_m, pr["capital"])
    mh = hold_metrics(hold, pr["capital"])

    pcr = os.path.join(CHART_DIR, f"{best['lab']}_price_repaired.png")
    ec = os.path.join(CHART_DIR, f"{best['lab']}_equity.png")
    price_chart(df, rep_t.trades_df(), f"VERO laterale {best['lab']} — bot RIPARATO (taker 0.40%)", pcr)
    equity_chart(cur_t.equity_df(), hold, pr["capital"],
                 f"VERO laterale {best['lab']} — Grid attuale vs riparato vs Hold (taker 0.40%)", ec,
                 repaired_eq=rep_t.equity_df())

    L += [f"## (2) Vero laterale `{best['lab']}` — il grid batte hold?", "",
          f"![prezzo riparato]({os.path.relpath(pcr, OUT_DIR)})", "",
          f"![equity]({os.path.relpath(ec, OUT_DIR)})", "",
          "| Metrica | Grid ATT. (taker) | Grid RIP. (taker) | Grid RIP. (maker) | Hold |",
          "|---|---|---|---|---|",
          f"| P&L (%) | {fmt(mc['pnl_pct'],2,True,True)} | {fmt(mrt['pnl_pct'],2,True,True)} | {fmt(mrm['pnl_pct'],2,True,True)} | {fmt(mh['pnl_pct'],2,True,True)} |",
          f"| P&L (USDT) | {fmt(mc['pnl_usdt'],2,s=True)} | {fmt(mrt['pnl_usdt'],2,s=True)} | {fmt(mrm['pnl_usdt'],2,s=True)} | {fmt(mh['pnl_usdt'],2,s=True)} |",
          f"| Max drawdown | {fmt(mc['max_drawdown_pct'],2,True)} | {fmt(mrt['max_drawdown_pct'],2,True)} | {fmt(mrm['max_drawdown_pct'],2,True)} | {fmt(mh['max_drawdown_pct'],2,True)} |",
          f"| Sell completati | {mc['completed_sells']} | {mrt['completed_sells']} | {mrm['completed_sells']} | 0 |",
          f"| Skim | {fmt(mc['skim_total'])} | {fmt(mrt['skim_total'])} | {fmt(mrm['skim_total'])} | 0.00 |",
          ""]
    verdict = ("**Il grid riparato BATTE hold** nel vero laterale ✅"
               if mrt["pnl_pct"] > mh["pnl_pct"]
               else "**Anche nel vero laterale il grid NON batte hold** ❌")
    L += [verdict + f" (riparato taker {mrt['pnl_pct']:+.2f}% vs hold {mh['pnl_pct']:+.2f}%; "
          f"con maker {mrm['pnl_pct']:+.2f}%).", ""]

    # ---- (3) sweep maker/taker su tutti gli scenari (grid riparato) ----
    print("\n=== sweep maker/taker ===")
    L += ["## (3) Maker 0.25% vs Taker 0.40% (grid RIPARATO)", "",
          "| Scenario | Drift | RIP. taker 0.40% | RIP. maker 0.25% | Hold | Δ maker | Maker ribalta vs hold? |",
          "|---|---|---|---|---|---|---|"]
    sweep = list(ALL_SCENARIOS) + [(f"VERO laterale {best['lab']}", best["lab"], best["s"], best["e"])]
    for name, lab, s, e in sweep:
        dfx = fetch_ohlcv(lab, s, e)
        dd = diag(dfx)
        rt = grid_metrics(run_grid(dfx, pr, P.FEE_KRAKEN_TAKER, True), pr["capital"])
        rm = grid_metrics(run_grid(dfx, pr, P.FEE_KRAKEN_MAKER, True), pr["capital"])
        hh = hold_metrics(run_hold(dfx, pr["capital"], P.FEE_KRAKEN_TAKER), pr["capital"])
        flip = "—"
        if rt["pnl_pct"] <= hh["pnl_pct"] < rm["pnl_pct"]:
            flip = "**SÌ** ✅"
        elif rm["pnl_pct"] > hh["pnl_pct"]:
            flip = "già batteva"
        else:
            flip = "no"
        print(f"{name:22} taker {rt['pnl_pct']:+7.2f}% maker {rm['pnl_pct']:+7.2f}% hold {hh['pnl_pct']:+7.2f}%")
        L.append(f"| {name} | {dd['drift']:+.1f}% | {rt['pnl_pct']:+.2f}% | "
                 f"**{rm['pnl_pct']:+.2f}%** | {hh['pnl_pct']:+.2f}% | "
                 f"{rm['pnl_pct']-rt['pnl_pct']:+.2f} p.p. | {flip} |")
    L += ["", "> Maker assume che gli ordini limite si riempiano (nel sim il sell scatta "
          "quando il close tocca il trigger). In mercati veloci un limite può non riempirsi "
          "o essere saltato → il beneficio maker è un **limite superiore**.", ""]

    rpath = os.path.join(OUT_DIR, "report_extra_tests.md")
    with open(rpath, "w") as f:
        f.write("\n".join(L))
    print(f"\n[report] -> {rpath}")


if __name__ == "__main__":
    main()
