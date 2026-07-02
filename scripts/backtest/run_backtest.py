"""
Grid-regime-backtest — orchestratore (Fase 1: solo BTC).

Brief: config/2026-06-28_S110_brief_grid-regime-backtest.md

Per ogni scenario (bear/bull/laterale):
  scarica OHLCV 1m -> simula grid (fee Kraken primario + fee Binance confronto)
  -> simula hold -> metriche -> grafici -> riga report.
Poi: tabella riepilogo 3 scenari + caveat.

Read-only: nessuna modifica a bot/, bot_config, DB. Output in audits/backtest/.

Uso:
  venv/bin/python3.13 scripts/backtest/run_backtest.py
  venv/bin/python3.13 scripts/backtest/run_backtest.py --force   # riscarica dati
"""

from __future__ import annotations

import os
import sys
import argparse

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

OUT_DIR = os.path.join(_REPO_ROOT, "audits", "backtest")
CHART_DIR = os.path.join(OUT_DIR, "charts")

# Soglia "trend nascosto": oltre questo |drift| open->close il mese NON è
# laterale (brief: fermarsi e proporre alternative a Max).
LATERAL_TREND_GATE_PCT = 10.0

SCENARIOS = [
    {"id": "bear_2022_06", "label": "Bearish", "start": "2022-06-01", "end": "2022-07-01",
     "desc": "Giugno 2022 — discesa post Terra/Luna",
     "prediction": "Il grid compra a scaglioni in caduta e **accumula bag** "
                   "(holdings in perdita non realizzata); lo stop-buy al -3% "
                   "dovrebbe congelare i buy dopo poco. Atteso: grid perde meno "
                   "di hold in % ma resta sotto al capitale, con poche/zero sell."},
    {"id": "bull_2024_11", "label": "Bullish", "start": "2024-11-01", "end": "2024-12-01",
     "desc": "Novembre 2024 — rally post-elezione USA",
     "prediction": "Hold (100% long dal giorno 1) **stravince**: il grid vende "
                   "presto i lotti (+~1.8% netto) e resta in gran parte liquido, "
                   "perdendo la parte alta del rally. Atteso: grid positivo ma "
                   "molto sotto hold."},
    # Laterale risolto a runtime tra Ago e Set 2023.
]

LATERAL_CANDIDATES = [
    {"id": "lat_2023_08", "label": "Agosto 2023", "start": "2023-08-01", "end": "2023-09-01"},
    {"id": "lat_2023_09", "label": "Settembre 2023", "start": "2023-09-01", "end": "2023-10-01"},
]
LATERAL_PREDICTION = (
    "**Campo di casa del grid**: senza trend, il prezzo oscilla e il grid "
    "compra-basso/vende-alto ripetutamente, accumulando skim. Atteso: grid "
    "batte hold (hold ~piatto, grid raccoglie le oscillazioni). MA a fee Kraken "
    "0.40%/lato (0.80%/giro) il margine si assottiglia — da verificare se "
    "l'edge sopravvive."
)


def _range_diag(df: pd.DataFrame) -> dict:
    o = float(df.iloc[0]["open"])
    c = float(df.iloc[-1]["close"])
    hi = float(df["high"].max())
    lo = float(df["low"].min())
    return {
        "open": o, "close": c,
        "drift_pct": (c / o - 1) * 100,
        "range_pct": (hi - lo) / lo * 100,
        "high": hi, "low": lo,
    }


def select_lateral(force: bool) -> dict:
    """Scegli il mese più laterale tra i candidati. Applica il gate del brief."""
    diags = []
    for cand in LATERAL_CANDIDATES:
        df = fetch_ohlcv(cand["id"], cand["start"], cand["end"], force=force)
        d = _range_diag(df)
        d.update(cand)
        diags.append(d)
        print(f"[lateral] {cand['label']}: open ${d['open']:.0f} -> close "
              f"${d['close']:.0f} | drift {d['drift_pct']:+.1f}% | range {d['range_pct']:.1f}%")
    # flattest = minore |drift|
    flattest = min(diags, key=lambda x: abs(x["drift_pct"]))
    flattest["gate_tripped"] = abs(flattest["drift_pct"]) > LATERAL_TREND_GATE_PCT
    flattest["all_diags"] = diags
    if flattest["gate_tripped"]:
        print(f"\n⚠️  GATE LATERALE: il mese più piatto ({flattest['label']}) ha "
              f"drift {flattest['drift_pct']:+.1f}% > {LATERAL_TREND_GATE_PCT}% "
              f"-> NESSUN mese è realmente laterale. Serve decisione di Max.\n")
    else:
        print(f"\n[lateral] Scelto {flattest['label']} (drift {flattest['drift_pct']:+.1f}%, "
              f"il più piatto, sotto la soglia {LATERAL_TREND_GATE_PCT}%).\n")
    return flattest


def run_scenario(scn: dict, snap: dict, force: bool, base: str = "BTC") -> dict:
    pr = snap["params"]
    df = fetch_ohlcv(scn["id"], scn["start"], scn["end"], force=force, base=base)
    exch = "binance"  # sorgente dati (la fee è modellata su Kraken nel sim)

    # grid @ Kraken (primario), @ Binance (confronto), riparato @ Kraken
    def make_sim(fee, repaired=False):
        return GridSim(
            capital=pr["capital"], capital_per_trade=pr["capital_per_trade"],
            buy_pct=pr["buy_pct"], sell_pct=pr["sell_pct"], skim_pct=pr["skim_pct"],
            min_profit_pct=pr["min_profit_pct"], idle_reentry_hours=pr["idle_reentry_hours"],
            dead_zone_hours=pr["dead_zone_hours"], stop_buy_drawdown_pct=pr["stop_buy_drawdown_pct"],
            stop_buy_unlock_hours=pr["stop_buy_unlock_hours"],
            buy_cooldown_seconds=pr["buy_cooldown_seconds"],
            slippage_buffer_pct=pr["slippage_buffer_pct"], fee_rate=fee,
            min_last_shot_usd=pr["min_last_shot_usd"], daily_trade_limit=pr["daily_trade_limit"],
            min_notional_usd=pr["min_notional_usd"], strategy=pr["strategy"],
            repaired=repaired,
        ).run(df)

    sim_kraken = make_sim(P.FEE_KRAKEN_TAKER)
    sim_binance = make_sim(P.FEE_BINANCE)
    sim_repaired = make_sim(P.FEE_KRAKEN_TAKER, repaired=True)
    hold = run_hold(df, pr["capital"], P.FEE_KRAKEN_TAKER)

    gm = grid_metrics(sim_kraken, pr["capital"])
    gm_binance = grid_metrics(sim_binance, pr["capital"])
    gm_repaired = grid_metrics(sim_repaired, pr["capital"])
    hm = hold_metrics(hold, pr["capital"])

    # charts
    from plots import price_chart, equity_chart
    pc = os.path.join(CHART_DIR, f"{scn['id']}_price.png")
    pcr = os.path.join(CHART_DIR, f"{scn['id']}_price_repaired.png")
    ec = os.path.join(CHART_DIR, f"{scn['id']}_equity.png")
    price_chart(df, sim_kraken.trades_df(),
                f"{base} · {scn['label']} — {scn['desc']} · bot ATTUALE (fee Kraken 0.40%)", pc,
                coin_label=base)
    price_chart(df, sim_repaired.trades_df(),
                f"{base} · {scn['label']} — {scn['desc']} · bot RIPARATO (fee Kraken 0.40%)", pcr,
                coin_label=base)
    equity_chart(sim_kraken.equity_df(), hold, pr["capital"],
                 f"{scn['label']} — Grid vs Hold (fee Kraken 0.40%)", ec,
                 repaired_eq=sim_repaired.equity_df())

    # trade dump (locale, per ispezione)
    tr = sim_kraken.trades_df()
    if len(tr):
        tr.to_csv(os.path.join(OUT_DIR, f"trades_{scn['id']}.csv"), index=False)

    diag = _range_diag(df)
    return {
        "scn": scn, "diag": diag, "candles": len(df), "exchange": exch,
        "grid": gm, "grid_binance": gm_binance, "grid_repaired": gm_repaired, "hold": hm,
        "price_chart": os.path.relpath(pc, OUT_DIR),
        "price_chart_repaired": os.path.relpath(pcr, OUT_DIR),
        "equity_chart": os.path.relpath(ec, OUT_DIR),
    }


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def _fmt(x, dec=2, pct=False, sign=False):
    s = f"{x:+,.{dec}f}" if sign else f"{x:,.{dec}f}"
    return s + ("%" if pct else "")


def _fmt_price(x: float) -> str:
    """Coin-aware price: full dollars for BTC/SOL, sig-figs for sub-cent (BONK)."""
    if x >= 1:
        return f"${x:,.2f}"
    return f"${x:.6g}"


def metric_table(res: dict) -> str:
    g, r, h = res["grid"], res["grid_repaired"], res["hold"]
    gb = res["grid_binance"]
    rows = [
        ("P&L finale (USDT)", _fmt(g["pnl_usdt"], 2, sign=True), _fmt(r["pnl_usdt"], 2, sign=True), _fmt(h["pnl_usdt"], 2, sign=True)),
        ("P&L finale (%)", _fmt(g["pnl_pct"], 2, pct=True, sign=True), _fmt(r["pnl_pct"], 2, pct=True, sign=True), _fmt(h["pnl_pct"], 2, pct=True, sign=True)),
        ("Max drawdown (%)", _fmt(g["max_drawdown_pct"], 2, pct=True), _fmt(r["max_drawdown_pct"], 2, pct=True), _fmt(h["max_drawdown_pct"], 2, pct=True)),
        ("Trade completati (sell)", str(g["completed_sells"]), str(r["completed_sells"]), str(h["completed_sells"])),
        ("Buy totali", str(g["buys"]), str(r["buys"]), str(h["buys"])),
        ("Skim accumulato (USDT)", _fmt(g["skim_total"], 2), _fmt(r["skim_total"], 2), _fmt(h["skim_total"], 2)),
        ("Tempo attivo (%)", _fmt(g["active_pct"], 1, pct=True), _fmt(r["active_pct"], 1, pct=True), _fmt(h["active_pct"], 1, pct=True)),
        ("Unrealized holdings fine (USDT)", _fmt(g["unrealized_holdings_value"], 2), _fmt(r["unrealized_holdings_value"], 2), _fmt(h["unrealized_holdings_value"], 2)),
    ]
    out = ["| Metrica | Grid ATTUALE (Kraken) | Grid RIPARATO (Kraken) | Hold |", "|---|---|---|---|"]
    for name, gv, rv, hv in rows:
        out.append(f"| {name} | {gv} | {rv} | {hv} |")
    out.append("")
    out.append(f"> Effetto fee sul bot ATTUALE: a 0.10% (Binance/testnet) avrebbe fatto "
               f"**{_fmt(gb['pnl_usdt'], 2, sign=True)} USDT ({_fmt(gb['pnl_pct'], 2, pct=True, sign=True)})** "
               f"vs {_fmt(g['pnl_usdt'], 2, sign=True)} a 0.40% — l'illusione testnet vale "
               f"**{_fmt(gb['pnl_usdt'] - g['pnl_usdt'], 2, sign=True)} USDT**. "
               f"Il fix vale **{_fmt(r['pnl_usdt'] - g['pnl_usdt'], 2, sign=True)} USDT** "
               f"(riparato − attuale, stessa fee Kraken).")
    return "\n".join(out)


def build_report(snap: dict, results: list, lateral_info: dict,
                 scenarios: list, base: str = "BTC") -> str:
    pr, src, meta = snap["params"], snap["sources"], snap["meta"]
    phase = {"BTC": "Fase 1", "SOL": "Fase 2", "BONK": "Fase 3"}.get(base, "")
    L = []
    L.append(f"# Grid-Regime Backtest — {phase} ({base})")
    L.append("")
    L.append(f"_Generato: {meta['snapshot_utc']} · scenari selezionati sul prezzo "
             f"reale di {base} (scan_regimes.py) · brief "
             "`config/2026-06-28_S110_brief_grid-regime-backtest.md`_")
    L.append("")
    L.append("## Cos'è (e cosa NON è)")
    L.append("")
    _window_src = ("Le finestre di 30 giorni sono ancorate a regimi storici reali di "
                   f"{base}." if base == "BTC" else
                   "Le finestre di 30 giorni NON sono scelte a mano ma trovate "
                   f"algoritmicamente sul prezzo di {base} (`scan_regimes.py`: drift "
                   "open→close + gate laterale |drift|<10%).")
    L.append(f"Mappa **comportamentale** del nostro grid bot su **{base}** — a "
             "**parametri congelati** — in tre regimi storici (bear / bull / laterale), "
             "confrontato con un semplice **hold**. **Non è un'ottimizzazione**: i "
             f"parametri si congelano, si gira, si guarda. {_window_src} I numeri "
             "saranno poi confrontati con il mainnet reale (Kraken).")
    L.append("")
    L.append("**Metodo & caveat (leggere prima dei numeri):**")
    L.append("")
    L.append(f"- **Fee = Kraken taker 0.40%** (i market order del grid sono taker). "
             "È il costo reale del venue mainnet (S112b). La colonna di confronto a "
             "0.10% mostra quanto il testnet Binance ci *gonfiava* il risultato.")
    _chk = int(pr.get("check_interval_seconds", 60))
    _gran_extra = ("" if _chk >= 60 else
                   f" ⚠️ **{base} in LIVE checka ogni {_chk}s** (< 1m): la candela 1m "
                   "sotto-campiona ancora di più le sue oscillazioni → i numeri del "
                   "**laterale sono un floor pessimistico** (skim reale probabilmente maggiore).")
    L.append(f"- **Risoluzione = candele 1m**, fill sul **close** (il bot live fa polling "
             f"ogni {_chk}s su un prezzo istantaneo, non vede high/low del minuto). Sotto-conta "
             f"i micro-rimbalzi inframinuto → possibile **sottostima** di skim/sell nel laterale.{_gran_extra}")
    L.append(f"- **Parametri congelati** = snapshot `bot_config` {base} del {meta['snapshot_utc']} "
             "(inclusi i valori già mossi da Sherpa). In LIVE Sherpa li muoverebbe per "
             "regime: questo è il **caso a freno fisso**.")
    L.append(f"- **Capitale = ${pr['capital']:.0f}** (target mainnet go-live, Master Task List 1.3; "
             f"allocazione testnet live: ${meta.get('capital_allocation_live')}). "
             f"Densità griglia = capitale/lotto = **~{pr['capital']/pr['capital_per_trade']:.0f} gradini** "
             f"(lotto ${pr['capital_per_trade']:.2f}).")
    L.append("- **Un mese per regime NON è statisticamente significativo.** Vale il "
             "**pattern**, non il centesimo. Benchmark orientativo, non paper accademico.")
    L.append("- **Sorgente prezzi = Binance** (storico profondo; Kraken via REST non lo dà). "
             "Il prezzo è equivalente tra venue; la *fee* è ciò che modelliamo su Kraken.")
    L.append("- **Niente TF/Sentinel/Sherpa/NewsKeeper**: solo grid puro.")
    L.append("")

    # parametri
    L.append("## Parametri congelati (snapshot)")
    L.append("")
    L.append("| Parametro | Valore | Fonte |")
    L.append("|---|---|---|")
    order = ["capital", "capital_per_trade", "buy_pct", "sell_pct", "skim_pct",
             "min_profit_pct", "idle_reentry_hours", "dead_zone_hours",
             "stop_buy_drawdown_pct", "stop_buy_unlock_hours", "buy_cooldown_seconds",
             "slippage_buffer_pct", "fee_rate", "check_interval_seconds"]
    for k in order:
        L.append(f"| {k} | {pr[k]} | {src.get(k, '-')} |")
    L.append("")

    # previsioni
    L.append("## Previsioni qualitative (dichiarate PRIMA dei numeri)")
    L.append("")
    for scn in scenarios:
        L.append(f"- **{scn['label']}** — {scn['prediction']}")
    L.append("")

    # per scenario
    for res in results:
        scn, d = res["scn"], res["diag"]
        L.append(f"## {scn['label']} — {scn['desc']}")
        L.append("")
        L.append(f"Periodo {scn['start']} → {scn['end']} · {res['candles']:,} candele 1m · "
                 f"open {_fmt_price(d['open'])} → close {_fmt_price(d['close'])} "
                 f"(**{d['drift_pct']:+.1f}%**) · range intramese **{d['range_pct']:.1f}%**.")
        if scn.get("lateral_note"):
            L.append("")
            L.append(scn["lateral_note"])
        L.append("")
        L.append("**Operazioni — bot ATTUALE (churn da polvere):**")
        L.append("")
        L.append(f"![prezzo attuale]({res['price_chart']})")
        L.append("")
        L.append("**Operazioni — bot RIPARATO (solo trade reali):**")
        L.append("")
        L.append(f"![prezzo riparato]({res['price_chart_repaired']})")
        L.append("")
        L.append("**Equity: Grid attuale vs Grid riparato vs Hold:**")
        L.append("")
        L.append(f"![equity]({res['equity_chart']})")
        L.append("")
        L.append(metric_table(res))
        L.append("")

    # finding churn
    L.append("## ⚠️ Il finding: churn da polvere (perché il grid attuale perde ovunque)")
    L.append("")
    L.append("Il backtest ha scoperto — e i **trade veri** del bot testnet lo confermano — "
             "che il grid degenera in un **round-trip a vuoto ogni ~4h**:")
    L.append("")
    L.append("1. Il grid svende fino alla **polvere**, azzera il prezzo medio ma **tiene** le "
             "monetine (finding S111, `realized_pnl_avg_cost_fixB`).")
    L.append("2. La polvere accumulata **diluisce l'avg verso il basso** al re-entry successivo.")
    L.append("3. Con l'avg falsato, il trigger di vendita risulta **già superato** → il bot "
             "**vende ~1 minuto dopo aver comprato, allo stesso prezzo**.")
    L.append("4. Non guadagna nulla, **paga solo le fee**. Su Binance (0.10%) è quasi invisibile "
             "e mascherato da un *realized fantasma*; su **Kraken (0.40%, 4×)** brucia soldi veri, "
             "**peggio nei trend** (il grid è fermo → re-entry continuo).")
    L.append("")
    L.append("**Riparato** = l'avg \"operativo\" non si azzera sulla polvere (la trattiene al "
             "costo vero) → niente diluizione → il sell richiede un movimento reale → niente churn. "
             "È **più del Fix B parcheggiato** (che sistemava solo il *numero* realized): qui si "
             "sistema l'avg che guida le **decisioni di trading**.")
    L.append("")

    # riepilogo
    L.append("## Riepilogo — 3 scenari (fee Kraken 0.40%): attuale vs riparato vs hold")
    L.append("")
    L.append(f"| Scenario | Drift {base} | Grid ATTUALE | Grid RIPARATO | Hold | Δ fix (rip−att) | Esito (riparato vs hold) |")
    L.append("|---|---|---|---|---|---|---|")
    for res in results:
        g, r, h, d = res["grid"], res["grid_repaired"], res["hold"], res["diag"]
        delta_fix = r["pnl_pct"] - g["pnl_pct"]
        delta_vs_hold = r["pnl_pct"] - h["pnl_pct"]
        esito = "Grid batte hold" if delta_vs_hold > 0 else "Hold batte grid"
        L.append(f"| {res['scn']['label']} | {d['drift_pct']:+.1f}% | "
                 f"{g['pnl_pct']:+.2f}% | **{r['pnl_pct']:+.2f}%** | {h['pnl_pct']:+.2f}% | "
                 f"**{delta_fix:+.2f} p.p.** | {esito} |")
    L.append("")
    L.append("**Lettura per regime (sul bot RIPARATO = comportamento onesto):**")
    L.append("")
    if base == "BTC":
        L.append("- **Bull**: il grid prende tanti micro-profitti (+1.8%/giro) e **si perde il trend** "
                 "→ positivo ma molto sotto hold. È la debolezza strutturale del grid in salita, non un bug.")
        L.append("- **Laterale(ish)**: quasi pari a hold. Settembre 2023 ha comunque un drift +3.9% "
                 "che hold cattura e il grid no (vende presto).")
        L.append("- **Bear**: il grid compra i dip e **tiene i bag** (99% in mercato, stop-buy a −3% "
                 "ferma gli acquisti) → finisce sotto, ma **batte hold** (esposizione parziale + cash). "
                 "⚠️ **Nota**: qui il bot ATTUALE sembra *meglio* (−19% vs −28%), ma è un **effetto "
                 "collaterale del churn** che lo svuota in cash il 60% del tempo (de-risk involontario), "
                 "non una virtù. Il riparato mostra l'esposizione reale.")
    else:
        # data-driven, una riga per scenario dai numeri reali
        for res in results:
            scn, r, h, d = res["scn"], res["grid_repaired"], res["hold"], res["diag"]
            delta = r["pnl_pct"] - h["pnl_pct"]
            verdict = "**batte hold**" if delta > 0 else "sotto hold"
            L.append(f"- **{scn['label']}** (drift {d['drift_pct']:+.1f}%): grid riparato "
                     f"**{r['pnl_pct']:+.2f}%** vs hold {h['pnl_pct']:+.2f}% → {verdict} "
                     f"({delta:+.2f} p.p.) · {r['completed_sells']} sell · "
                     f"{r['active_pct']:.0f}% del tempo in mercato.")
    L.append("")

    # gate laterale
    if lateral_info.get("gate_tripped"):
        L.append("## ⚠️ Nota sul laterale (gate del brief)")
        L.append("")
        L.append(f"Il mese più piatto tra i candidati ({lateral_info['label']}) ha un drift "
                 f"open→close di **{lateral_info['drift_pct']:+.1f}%**, oltre la soglia "
                 f"{LATERAL_TREND_GATE_PCT}%: **nessuno dei due mesi è realmente laterale**. "
                 "Per il brief questo richiede una decisione di Max (proporre alternative). "
                 "Lo scenario è incluso comunque, ma va letto come *quasi-laterale*.")
        L.append("")

    L.append("## Limiti dichiarati")
    L.append("")
    L.append("1. **Fedeltà del simulatore**: replica il loop reale (stop-buy, dead-zone, "
             "idle re-entry, ladder sell net-of-fee, skim, Strategy A) ma resta una "
             "semplificazione (no slippage reale di book, no spike-guard, fill su close 1m). "
             "Divergenze grid-sim ↔ live possibili per ragioni strutturali, non di mercato.")
    L.append("2. **Un mese ≠ tutti i bear/bull/laterali**: campione singolo per regime.")
    L.append("3. **Granularità 1m**: i micro-rimbalzi inframinuto persi possono sottostimare "
             "gli skim nel laterale.")
    L.append("4. **available_cash**: il sim sottrae la fee dal cash reale (modello Kraken "
             "fee-in-quote); il bot live ha una formula fee-blind (artefatto Binance "
             "fee-in-base) → differenza ≤0.4% che tocca solo il sizing last-shot.")
    L.append("")
    return "\n".join(L)


def build_coin_scenarios(base: str, force: bool):
    """SOL/BONK: scenari bear/bull/laterale trovati dallo scanner dei regimi."""
    from scan_regimes import scan
    sc = scan(f"{base}/USDT", force=force, verbose=True)
    sel = sc["selection"]

    def mk(r, label, pred):
        ym = r["ym"].replace("-", "_")
        s = {
            "id": f"{base.lower()}_{label.lower()}_{ym}",
            "label": label, "start": r["start"], "end": r["end"],
            "desc": f"{r['label']} — drift {r['drift_pct']:+.1f}%, range {r['range_pct']:.0f}%",
            "prediction": pred,
        }
        if r.get("gate_tripped"):
            s["lateral_note"] = (
                f"_⚠️ Il mese più piatto ({r['label']}) ha drift {r['drift_pct']:+.1f}% "
                "> soglia 10% → **quasi-laterale**, non piatto puro (un memecoin raramente "
                "va davvero flat: onestà > forzare l'etichetta)._")
        return s

    scenarios = [
        mk(sel["bear"], "Bearish",
           "Il grid compra a scaglioni in caduta e **accumula bag**; lo stop-buy congela "
           "i buy dopo il drawdown. Atteso: sotto al capitale ma **meno di hold**, poche sell."),
        mk(sel["bull"], "Bullish",
           "Hold (100% long dal giorno 1) **stravince**: il grid vende presto i lotti e "
           "resta liquido, perdendo il grosso del rally. Atteso: grid positivo ma molto sotto hold."),
        mk(sel["lateral"], "Laterale",
           "**Campo di casa del grid**: senza trend, compra-basso/vende-alto ripetutamente e "
           "accumula skim. MA a fee Kraken 0.40%/lato (0.80%/giro) il margine si assottiglia "
           "— da verificare se l'edge sopravvive."),
    ]
    lat = sel["lateral"]
    lateral_info = {"gate_tripped": lat.get("gate_tripped", False),
                    "label": lat["label"], "drift_pct": lat["drift_pct"]}
    return scenarios, lateral_info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTC/USDT",
                    help="BTC/USDT (default) | SOL/USDT | BONK/USDT")
    ap.add_argument("--force", action="store_true", help="riscarica gli OHLCV")
    args = ap.parse_args()
    base = args.symbol.split("/")[0].upper()

    os.makedirs(CHART_DIR, exist_ok=True)

    snap = P.load_frozen_params(args.symbol)
    P.save_snapshot(snap, os.path.join(OUT_DIR, f"frozen_params_{base}.json"))
    print("[params] snapshot:", snap["meta"])

    results = []
    if base == "BTC":
        # BTC: percorso originale (bear/bull hardcoded + laterale risolto a runtime).
        lateral = select_lateral(args.force)
        lat_scn = {
            "id": lateral["id"] + "_lat", "label": "Laterale", "start": lateral["start"],
            "end": lateral["end"],
            "desc": f"{lateral['label']} — range-bound (il più piatto tra Ago/Set 2023)",
            "prediction": LATERAL_PREDICTION,
            "lateral_note": (
                f"_Selezione: tra i candidati, **{lateral['label']}** è il più piatto "
                f"(drift {lateral['drift_pct']:+.1f}%). "
                + ("⚠️ supera la soglia 10% → vedi nota sul laterale._"
                   if lateral["gate_tripped"] else "Sotto la soglia 10%._")),
        }
        lat_scn_fetch_id = lateral["id"]
        scenarios = list(SCENARIOS) + [lat_scn]
        lateral_info = lateral
        for scn in scenarios:
            print(f"\n===== {scn['label']} =====")
            fid = lat_scn_fetch_id if scn is lat_scn else scn["id"]
            scn_run = dict(scn)
            scn_run["id"] = fid  # usa la cache già scaricata
            res = run_scenario(scn_run, snap, args.force, base=base)
            res["scn"] = scn  # ripristina metadati display (label/desc/note)
            results.append(res)
    else:
        # SOL/BONK: scenari dallo scanner dei regimi.
        scenarios, lateral_info = build_coin_scenarios(base, args.force)
        for scn in scenarios:
            print(f"\n===== {base} {scn['label']} ({scn['start']} → {scn['end']}) =====")
            res = run_scenario(scn, snap, args.force, base=base)
            res["scn"] = scn
            results.append(res)

    report = build_report(snap, results, lateral_info, scenarios, base=base)
    rname = ("report_grid_regime_backtest.md" if base == "BTC"
             else f"report_grid_regime_{base}.md")
    rpath = os.path.join(OUT_DIR, rname)
    with open(rpath, "w") as f:
        f.write(report)
    print(f"\n[report] -> {rpath}")
    print("[charts] ->", CHART_DIR)

    # console summary
    print(f"\n===== SOMMARIO {base} =====")
    for res in results:
        g, r, h = res["grid"], res["grid_repaired"], res["hold"]
        print(f"{res['scn']['label']:9} | grid_att {g['pnl_pct']:+7.2f}% | "
              f"grid_rip {r['pnl_pct']:+7.2f}% | hold {h['pnl_pct']:+7.2f}% "
              f"| sell {r['completed_sells']:3d} | skim ${r['skim_total']:.2f}")


if __name__ == "__main__":
    main()
