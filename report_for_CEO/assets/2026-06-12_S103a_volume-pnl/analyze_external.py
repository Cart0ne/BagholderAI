"""S103a — Validazione esterna su dati Binance mainnet (API pubblica, no key).

Universo: i symbol visti dallo scanner TF nel backup (163 coppie /USDT).
Dati: klines 1d degli ultimi ~12 mesi da api.binance.com.

Test A (incondizionato): rank settimanale per volume -> ritorno forward 7g per fascia.
Test B (condizionato, proxy segnale TF): golden cross EMA20/EMA50 daily -> ritorno
forward +3g/+7g stratificato per fascia di volume al giorno del segnale.
NB: il TF reale opera su scan 30min con soglia strength>=15; il daily cross e' un
proxy direzionale, non una replica.

Uso:
    python analyze_external.py <data_dir_jsonl> <output_dir>
"""
import json
import sys
import time
import urllib.request
import urllib.error

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_DIR, OUT_DIR = sys.argv[1], sys.argv[2]
BASE = "https://api.binance.com/api/v3/klines"
START_MS = int(pd.Timestamp("2025-06-01", tz="UTC").timestamp() * 1000)
TIER_B_MIN, TIER_A_MIN = 20e6, 100e6  # soglie volume del TF (trend_config)

# ------------------------------------------------ universo dai nostri scan
scans = pd.read_json(f"{DATA_DIR}/trend_scans.jsonl", lines=True)
symbols = sorted(scans.symbol.unique())
print(f"## Universo: {len(symbols)} symbol dai trend_scans")

def fetch_klines(pair):
    url = f"{BASE}?symbol={pair}&interval=1d&startTime={START_MS}&limit=1000"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None  # symbol non esiste (delistato / mai listato spot)
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return "error"

frames, dead, errors = {}, [], []
for i, sym in enumerate(symbols):
    pair = sym.replace("/", "")
    res = fetch_klines(pair)
    if res is None or res == []:
        dead.append(sym)
    elif res == "error":
        errors.append(sym)
    else:
        k = pd.DataFrame(res, columns=["open_time", "open", "high", "low", "close",
                                       "vol_base", "close_time", "quote_vol", "n_trades",
                                       "taker_base", "taker_quote", "ignore"])
        k = k[["open_time", "close", "quote_vol"]].astype(float)
        k["date"] = pd.to_datetime(k.open_time, unit="ms", utc=True)
        frames[sym] = k[["date", "close", "quote_vol"]]
    time.sleep(0.12)
    if (i + 1) % 40 == 0:
        print(f"  ... {i+1}/{len(symbols)} scaricati")

print(f"- scaricati: {len(frames)} | non disponibili su Binance spot oggi: {len(dead)} | errori rete: {len(errors)}")
if dead:
    print(f"- symbol senza dati (survivorship!): {', '.join(d.replace('/USDT','') for d in dead)}")

# panel: close + quote_vol per (date, symbol)
panel = pd.concat([f.assign(symbol=s) for s, f in frames.items()])
px = panel.pivot(index="date", columns="symbol", values="close").sort_index()
qv = panel.pivot(index="date", columns="symbol", values="quote_vol").sort_index()
print(f"- pannello: {px.shape[0]} giorni x {px.shape[1]} symbol "
      f"({px.index.min():%Y-%m-%d} -> {px.index.max():%Y-%m-%d})")
hist_days = px.notna().sum()
print(f"- storia media per symbol: {hist_days.mean():.0f} giorni; symbol con >=300 giorni: {(hist_days>=300).sum()}")

# ------------------------------------------------ BTC mainnet check periodo interno
btc = px["BTC/USDT"].dropna()
in_period = btc.loc["2026-04-24":"2026-05-08"]
if len(in_period) > 2:
    print(f"\n## BTC mainnet 24 apr - 8 mag 2026 (cross-check feed testnet)")
    print(f"- {in_period.iloc[0]:,.0f} -> {in_period.iloc[-1]:,.0f} "
          f"({(in_period.iloc[-1]/in_period.iloc[0]-1)*100:+.1f}%), "
          f"min {in_period.min():,.0f} / max {in_period.max():,.0f}")

# ------------------------------------------------ TEST A: incondizionato
vol7 = qv.rolling(7, min_periods=5).mean()
fwd7 = px.shift(-7) / px - 1  # ritorno forward 7g

rows = []
mondays = [d for d in px.index if d.dayofweek == 0]
for d in mondays:
    v, f = vol7.loc[d], fwd7.loc[d]
    ok = v.notna() & f.notna() & (v > 0)
    if ok.sum() < 30:
        continue
    v, f = v[ok], f[ok]
    terz = pd.qcut(v.rank(method="first"), 3, labels=["basso", "medio", "alto"])
    for sym in v.index:
        rows.append({"date": d, "symbol": sym, "bucket": terz[sym], "fwd7": f[sym]})
ta = pd.DataFrame(rows)
print(f"\n## TEST A — incondizionato (rank settimanale volume 7g -> ritorno forward 7g)")
print(f"- osservazioni: {len(ta)} (coin-settimane), settimane: {ta.date.nunique()}")
ga = ta.groupby("bucket", observed=True).fwd7.agg(["size", "mean", "median"])
ga["wr"] = ta.groupby("bucket", observed=True).fwd7.apply(lambda s: (s > 0).mean())
print((ga.assign(mean=ga["mean"]*100, median=ga["median"]*100, wr=ga.wr*100)
        .rename(columns={"mean": "media_%", "median": "mediana_%", "wr": "wr_%"})
        .to_string(float_format=lambda v: f"{v:,.2f}")))

# differenza basso-alto per settimana (medie settimanali -> osservazioni ~indipendenti)
wk = ta.groupby(["date", "bucket"], observed=True).fwd7.mean().unstack()
diff = (wk["basso"] - wk["alto"]).dropna()
tt = stats.ttest_1samp(diff, 0)
print(f"- spread settimanale basso-alto: media {diff.mean()*100:+.2f} p.p./sett "
      f"(n={len(diff)} settimane, t={tt.statistic:+.2f}, p={tt.pvalue:.3f})")

# ------------------------------------------------ TEST B: golden cross EMA20/50
ema20 = px.ewm(span=20, adjust=False, min_periods=20).mean()
ema50 = px.ewm(span=50, adjust=False, min_periods=50).mean()
above = ema20 > ema50
cross_up = above & ~above.shift(1).fillna(False) & ema50.notna()

events = []
fwd3 = px.shift(-3) / px - 1
for sym in px.columns:
    cu = cross_up[sym]
    for d in cu.index[cu]:
        if px[sym].loc[:d].notna().sum() < 60:
            continue  # serve storia per EMA stabili
        v = vol7.at[d, sym]
        f3, f7 = fwd3.at[d, sym], fwd7.at[d, sym]
        if pd.isna(v) or pd.isna(f7):
            continue
        events.append({"symbol": sym, "date": d, "vol7": v, "fwd3": f3, "fwd7": f7})
ev = pd.DataFrame(events)
ev["fascia_tf"] = pd.cut(ev.vol7, [0, TIER_B_MIN, TIER_A_MIN, np.inf],
                         labels=["C (<$20M)", "B ($20-100M)", "A (>$100M)"])
ev["quart"] = pd.qcut(ev.vol7, 4, labels=["Q1 basso", "Q2", "Q3", "Q4 alto"])

print(f"\n## TEST B — condizionato: golden cross EMA20/50 daily (proxy segnale TF)")
print(f"- eventi: {len(ev)} su {ev.symbol.nunique()} symbol, "
      f"{ev.date.min():%Y-%m-%d} -> {ev.date.max():%Y-%m-%d}")

for col, lab in (("fascia_tf", "fasce volume TF (soglie reali scanner)"),
                 ("quart", "quartili di volume (come esplorazione CEO)")):
    g = ev.groupby(col, observed=True).agg(
        n=("fwd7", "size"),
        fwd3_medio=("fwd3", lambda s: s.mean() * 100),
        fwd7_medio=("fwd7", lambda s: s.mean() * 100),
        fwd7_mediano=("fwd7", lambda s: s.median() * 100),
        wr7=("fwd7", lambda s: (s > 0).mean() * 100),
    )
    print(f"\n### per {lab}")
    print(g.to_string(float_format=lambda v: f"{v:,.2f}"))

q1, q4 = ev[ev.quart == "Q1 basso"].fwd7, ev[ev.quart == "Q4 alto"].fwd7
mw = stats.mannwhitneyu(q1, q4, alternative="two-sided")
rng = np.random.default_rng(103)
boot = [rng.choice(q1, len(q1)).mean() - rng.choice(q4, len(q4)).mean() for _ in range(10_000)]
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"\n- Q1 vs Q4 (fwd7): diff {q1.mean()*100-q4.mean()*100:+.2f} p.p., "
      f"bootstrap 95% CI [{lo*100:+.2f}, {hi*100:+.2f}], Mann-Whitney p={mw.pvalue:.4f}")
sp = stats.spearmanr(ev.vol7, ev.fwd7)
print(f"- Spearman volume-fwd7 su eventi: rho={sp.statistic:+.3f} (p={sp.pvalue:.4f})")

# regime split: il pattern regge in entrambi i semestri?
ev["semestre"] = np.where(ev.date < pd.Timestamp("2025-12-01", tz="UTC"), "giu-nov 2025", "dic 2025-giu 2026")
gs = ev.groupby(["semestre", "quart"], observed=True).fwd7.agg(["size", "mean"])
gs["mean"] *= 100
print(f"\n### split temporale (regime check)")
print(gs.to_string(float_format=lambda v: f"{v:,.2f}"))

ev.to_csv(f"{OUT_DIR}/external_events.csv", index=False)

# ------------------------------------------------ grafici
plt.rcParams.update({"figure.dpi": 130, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})

fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
gq = ev.groupby("quart", observed=True)
x = np.arange(4)
labels = ["Q1 basso", "Q2", "Q3", "Q4 alto"]
m7 = [gq.fwd7.mean()[l] * 100 for l in labels]
w7 = [(gq.fwd7.apply(lambda s: (s > 0).mean())[l]) * 100 for l in labels]
n_ = [gq.size()[l] for l in labels]
axes[0].bar(x, m7, color=["#55A868", "#88B89A", "#C5BB7F", "#C44E52"])
axes[0].axhline(0, color="gray", linewidth=0.8)
axes[0].set_xticks(x, labels, fontsize=8)
axes[0].set_title("Ritorno medio +7g dopo golden cross")
axes[0].set_ylabel("%")
for i, (v, n) in enumerate(zip(m7, n_)):
    axes[0].text(i, v + (0.08 if v >= 0 else -0.2), f"{v:+.2f}%\n(n={n})", ha="center", fontsize=8)
axes[1].bar(x, w7, color=["#55A868", "#88B89A", "#C5BB7F", "#C44E52"])
axes[1].set_xticks(x, labels, fontsize=8)
axes[1].axhline(50, color="gray", linewidth=0.8, linestyle="--")
axes[1].set_title("WR +7g dopo golden cross")
axes[1].set_ylabel("%")
fig.suptitle(f"Validazione esterna Binance mainnet — {len(ev)} golden cross daily, "
             f"{ev.symbol.nunique()} coin, 12 mesi", fontsize=10)
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/06_esterno_eventi_quartili.png", bbox_inches="tight")

fig, ax = plt.subplots(figsize=(8, 4.6))
wk_plot = (wk * 100).rolling(4).mean()
for col, c in (("basso", "#55A868"), ("alto", "#C44E52")):
    ax.plot(wk_plot.index, wk_plot[col], label=f"terzile volume {col}", color=c, linewidth=1.4)
ax.axhline(0, color="gray", linewidth=0.8)
ax.set_title("TEST A incondizionato: ritorno forward 7g medio per terzile di volume\n(media mobile 4 settimane)")
ax.set_ylabel("% / settimana")
ax.legend()
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/07_esterno_incondizionato.png")

print(f"\n## Salvati external_events.csv + 2 PNG in {OUT_DIR}")
