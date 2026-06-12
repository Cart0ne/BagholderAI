"""S103a — Analisi correlazione Volume <-> PnL su dati paper trading TF.

Input:  JSONL archiviati (backup pre-reset S67, 24 apr - 8 mag 2026).
Output: pairs.csv + grafici PNG + statistiche su stdout (markdown-friendly).

Uso:
    python analyze_internal.py /Volumes/Archivio/bagholderai_backups/2026-05-08_pre-reset-s67 <output_dir>

Sola lettura sui JSONL. Nessuna scrittura su Supabase, nessun import dal codice bot.
"""
import json
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_DIR = sys.argv[1]
OUT_DIR = sys.argv[2]

MATCH_TOLERANCE = pd.Timedelta(hours=6)  # vincolo brief: scan stesso symbol, +/-6h max
TIER_COLORS = {"A": "#4C72B0", "B": "#DD8452", "C": "#55A868"}

# ---------------------------------------------------------------- load
dec = pd.read_json(f"{DATA_DIR}/trend_decisions_log.jsonl", lines=True)
scans = pd.read_json(f"{DATA_DIR}/trend_scans.jsonl", lines=True)
for df, col in ((dec, "scan_timestamp"), (scans, "scan_timestamp")):
    df[col] = pd.to_datetime(df[col], format="ISO8601", utc=True)
scans = scans.sort_values("scan_timestamp").reset_index(drop=True)
dec = dec.sort_values("scan_timestamp").reset_index(drop=True)

print("## Dati caricati")
print(f"- decisions: {len(dec)} righe, {dec.symbol.nunique()} symbol, "
      f"{dec.scan_timestamp.min():%Y-%m-%d %H:%M} -> {dec.scan_timestamp.max():%Y-%m-%d %H:%M} UTC")
print(f"- scans: {len(scans)} righe, {scans.symbol.nunique()} symbol")

# ------------------------------------------------- pairing ALLOCATE->DEALLOCATE
def parse_alloc_reason(reason):
    """'Tier 3 (vol $7.0M): strongest BULLISH — $17 (strength=15.3)' -> (3, 7.0e6, 17, 15.3)"""
    m = re.match(r"Tier (\d) \(vol \$([\d.]+)M\).*?\$(\d+) \(strength=([\d.]+)\)", str(reason))
    if not m:
        return None, None, None, None
    return int(m.group(1)), float(m.group(2)) * 1e6, float(m.group(3)), float(m.group(4))

def parse_dealloc_reason(reason):
    """Estrae motivo canonico + realized $ se presente."""
    r = str(reason)
    if "ORPHAN_PERIOD_CLOSE" in r:
        motive = "ORPHAN_PERIOD_CLOSE"
    elif "STOP-LOSS" in r:
        motive = "STOP-LOSS"
    elif "TRAILING-STOP" in r:
        motive = "TRAILING-STOP"
    elif "GAIN_SATURATION" in r:
        motive = "GAIN_SATURATION"
    else:
        motive = r.split("(")[0].strip()[:40] or "ALTRO"
    m = re.search(r"realized \$([+-][\d.]+)", r)
    realized = float(m.group(1)) if m else np.nan
    return motive, realized

pairs, anomalies = [], {"realloc_open": 0, "dealloc_no_open": 0, "open_at_end": 0}
for symbol, g in dec[dec.action_taken.isin(["ALLOCATE", "DEALLOCATE"])].groupby("symbol"):
    open_row = None
    for _, row in g.iterrows():
        if row.action_taken == "ALLOCATE":
            if open_row is not None:
                anomalies["realloc_open"] += 1  # ALLOCATE su ciclo già aperto: tengo il primo
                continue
            open_row = row
        else:  # DEALLOCATE
            if open_row is None:
                anomalies["dealloc_no_open"] += 1  # ciclo aperto prima del 24/4 o orphan iniziale
                continue
            motive, realized = parse_dealloc_reason(row.reason)
            tier_n, vol_reason, alloc_usd, strength_reason = parse_alloc_reason(open_row.reason)
            pairs.append({
                "symbol": symbol,
                "entry_ts": open_row.scan_timestamp, "exit_ts": row.scan_timestamp,
                "entry_signal_strength": open_row.signal_strength, "entry_rsi": open_row.rsi_value,
                "tier_n_reason": tier_n, "vol_reason": vol_reason, "alloc_usd": alloc_usd,
                "strength_reason": strength_reason,
                "exit_motive": motive, "realized_usd": realized,
            })
            open_row = None
    if open_row is not None:
        anomalies["open_at_end"] += 1

pairs = pd.DataFrame(pairs)
print(f"\n## Pairing\n- coppie ALLOCATE->DEALLOCATE: **{len(pairs)}**")
print(f"- anomalie: {anomalies}")

# ------------------------------------------------- match prezzo da scans (±6h)
scan_cols = scans[["symbol", "scan_timestamp", "price", "volume_24h", "tier", "rsi", "signal_strength"]]

def nearest_scan(symbol, ts):
    s = scan_cols[scan_cols.symbol == symbol]
    if s.empty:
        return None
    idx = (s.scan_timestamp - ts).abs().idxmin()
    row = s.loc[idx]
    dist = abs(row.scan_timestamp - ts)
    if dist > MATCH_TOLERANCE:
        return None
    return row, dist

rows = []
for _, p in pairs.iterrows():
    e = nearest_scan(p.symbol, p.entry_ts)
    x = nearest_scan(p.symbol, p.exit_ts)
    rec = p.to_dict()
    rec.update({
        "entry_price": e[0].price if e else np.nan,
        "entry_volume": e[0].volume_24h if e else np.nan,
        "tier": e[0].tier if e else None,
        "entry_match_min": e[1].total_seconds() / 60 if e else np.nan,
        "exit_price": x[0].price if x else np.nan,
        "exit_match_min": x[1].total_seconds() / 60 if x else np.nan,
    })
    rows.append(rec)
df = pd.DataFrame(rows)
df["matched"] = df.entry_price.notna() & df.exit_price.notna()
n_unmatched = (~df.matched).sum()
df = df[df.matched].copy()
df["pnl_pct"] = (df.exit_price - df.entry_price) / df.entry_price * 100
df["duration_h"] = (df.exit_ts - df.entry_ts).dt.total_seconds() / 3600
df["win"] = df.pnl_pct > 0
df["log_vol"] = np.log10(df.entry_volume)
df["is_orphan"] = df.exit_motive == "ORPHAN_PERIOD_CLOSE"

print(f"\n## Match prezzi (tolleranza ±6h)")
print(f"- coppie matchate: {len(df)} (scartate per match mancante: {n_unmatched})")
print(f"- distanza match entry: mediana {df.entry_match_min.median():.1f} min, max {df.entry_match_min.max():.1f} min")
print(f"- distanza match exit:  mediana {df.exit_match_min.median():.1f} min, max {df.exit_match_min.max():.1f} min")

# cross-check: PnL teorico vs realized $ dichiarato nel reason
chk = df.dropna(subset=["realized_usd"])
if len(chk) > 3:
    agree = ((chk.pnl_pct > 0) == (chk.realized_usd > 0)).mean()
    rho_chk = stats.spearmanr(chk.pnl_pct, chk.realized_usd)
    print(f"- cross-check vs realized $ nel reason (n={len(chk)}): concordanza segno {agree:.0%}, "
          f"Spearman {rho_chk.statistic:.2f} (p={rho_chk.pvalue:.3f})")

# volume dal reason vs volume dallo scan matchato
vchk = df.dropna(subset=["vol_reason"])
if len(vchk) > 3:
    ratio = (vchk.entry_volume / vchk.vol_reason)
    print(f"- cross-check volume scan vs reason: ratio mediano {ratio.median():.2f} "
          f"(1.00 = match perfetto)")

df.to_csv(f"{OUT_DIR}/pairs.csv", index=False)

# ---------------------------------------------------------------- statistiche
def fmt_p(p):
    return f"p={p:.4f}" if p >= 0.0001 else "p<0.0001"

def corr_block(d, label):
    if len(d) < 5:
        print(f"- {label}: n={len(d)} troppo piccolo, skip")
        return
    pe_raw = stats.pearsonr(d.entry_volume, d.pnl_pct)
    pe_log = stats.pearsonr(d.log_vol, d.pnl_pct)
    sp = stats.spearmanr(d.entry_volume, d.pnl_pct)
    print(f"- {label} (n={len(d)}): Pearson(vol) r={pe_raw.statistic:+.3f} ({fmt_p(pe_raw.pvalue)}) | "
          f"Pearson(log10 vol) r={pe_log.statistic:+.3f} ({fmt_p(pe_log.pvalue)}) | "
          f"Spearman rho={sp.statistic:+.3f} ({fmt_p(sp.pvalue)})")

print(f"\n## Risultati complessivi")
print(f"- trade: {len(df)} | win rate: {df.win.mean():.1%} | PnL medio: {df.pnl_pct.mean():+.2f}% | "
      f"PnL mediano: {df.pnl_pct.median():+.2f}%")
print(f"- per confronto esplorazione CEO: 56 coppie, WR 26.8%, PnL +0.68%")

print(f"\n## Correlazione volume <-> PnL")
corr_block(df, "TUTTI")
corr_block(df[~df.is_orphan], "SENZA orphan close")
for t in ["A", "B", "C"]:
    corr_block(df[df.tier == t], f"Tier {t}")

# OLS con dummies tier: il volume aggiunge qualcosa oltre il tier?
sub = df.dropna(subset=["log_vol", "pnl_pct"])
X = pd.get_dummies(sub.tier, prefix="tier", drop_first=True).astype(float)
X["log_vol"] = sub.log_vol
X.insert(0, "const", 1.0)
beta, res_, rank_, sv_ = np.linalg.lstsq(X.values, sub.pnl_pct.values, rcond=None)
resid = sub.pnl_pct.values - X.values @ beta
dof = len(sub) - X.shape[1]
sigma2 = (resid ** 2).sum() / dof
cov = sigma2 * np.linalg.inv(X.values.T @ X.values)
se = np.sqrt(np.diag(cov))
tstat = beta / se
pvals = 2 * (1 - stats.t.cdf(np.abs(tstat), dof))
print(f"\n## OLS: pnl_pct ~ log10(volume) + tier dummies (controllo confounding tier)")
for name, b, s_, t_, p_ in zip(X.columns, beta, se, tstat, pvals):
    print(f"- {name}: beta={b:+.3f} (se={s_:.3f}, t={t_:+.2f}, p={p_:.3f})")

# quartili di volume
df["vol_q"] = pd.qcut(df.entry_volume, 4, labels=["Q1 (basso)", "Q2", "Q3", "Q4 (alto)"])
qt = df.groupby("vol_q", observed=True).agg(
    n=("pnl_pct", "size"), pnl_medio=("pnl_pct", "mean"), pnl_mediano=("pnl_pct", "median"),
    wr=("win", "mean"), vol_min=("entry_volume", "min"), vol_max=("entry_volume", "max"),
)
print(f"\n## Quartili di volume (entry)")
print(qt.to_string(float_format=lambda v: f"{v:,.2f}"))

q1 = df[df.vol_q == "Q1 (basso)"].pnl_pct
q4 = df[df.vol_q == "Q4 (alto)"].pnl_pct
mw = stats.mannwhitneyu(q1, q4, alternative="two-sided")
diff_obs = q1.mean() - q4.mean()
rng = np.random.default_rng(103)
boot = [rng.choice(q1, len(q1)).mean() - rng.choice(q4, len(q4)).mean() for _ in range(10_000)]
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"\n- Q1 vs Q4: diff PnL medio {diff_obs:+.2f} p.p., bootstrap 95% CI [{lo:+.2f}, {hi:+.2f}], "
      f"Mann-Whitney U {fmt_p(mw.pvalue)}")

# tier breakdown
tb = df.groupby("tier").agg(
    n=("pnl_pct", "size"), pnl_medio=("pnl_pct", "mean"), wr=("win", "mean"),
    vol_mediano=("entry_volume", "median"), durata_med_h=("duration_h", "median"),
)
print(f"\n## Breakdown per tier")
print(tb.to_string(float_format=lambda v: f"{v:,.2f}"))

# durata per esito
print(f"\n## Durata trade (ore)")
print(df.groupby(df.win.map({True: "win", False: "loss"})).duration_h
        .describe()[["count", "mean", "50%", "max"]].to_string(float_format=lambda v: f"{v:.1f}"))
print("\nper tier:")
print(df.groupby("tier").duration_h.describe()[["count", "mean", "50%", "max"]]
        .to_string(float_format=lambda v: f"{v:.1f}"))

# signal strength / RSI all'entry vs PnL
print(f"\n## Predittori all'ALLOCATE")
for col, label in (("entry_signal_strength", "signal_strength"), ("entry_rsi", "RSI")):
    d = df.dropna(subset=[col])
    sp = stats.spearmanr(d[col], d.pnl_pct)
    pe = stats.pearsonr(d[col], d.pnl_pct)
    print(f"- {label} (n={len(d)}): Spearman {sp.statistic:+.3f} ({fmt_p(sp.pvalue)}), "
          f"Pearson {pe.statistic:+.3f} ({fmt_p(pe.pvalue)})")
    med = d[col].median()
    lo_, hi_ = d[d[col] <= med], d[d[col] > med]
    print(f"    <=mediana ({med:.1f}): PnL {lo_.pnl_pct.mean():+.2f}% WR {lo_.win.mean():.0%} | "
          f">mediana: PnL {hi_.pnl_pct.mean():+.2f}% WR {hi_.win.mean():.0%}")

# motivi DEALLOCATE
print(f"\n## Motivi DEALLOCATE")
mb = df.groupby("exit_motive").agg(
    n=("pnl_pct", "size"), pnl_medio=("pnl_pct", "mean"), pnl_min=("pnl_pct", "min"),
    wr=("win", "mean"), durata_med_h=("duration_h", "median"),
)
print(mb.sort_values("n", ascending=False).to_string(float_format=lambda v: f"{v:,.2f}"))

# ---------------------------------------------------------------- BTC contesto
btc = scans[scans.symbol == "BTC/USDT"].sort_values("scan_timestamp")
btc_ret = (btc.price.iloc[-1] / btc.price.iloc[0] - 1) * 100
roll_max = btc.price.cummax()
max_dd = ((btc.price / roll_max) - 1).min() * 100
daily = btc.set_index("scan_timestamp").price.resample("1D").last().dropna()
daily_vol = daily.pct_change().std() * 100
print(f"\n## Contesto BTC ({btc.scan_timestamp.min():%d %b} -> {btc.scan_timestamp.max():%d %b})")
print(f"- start {btc.price.iloc[0]:,.0f} -> end {btc.price.iloc[-1]:,.0f} ({btc_ret:+.1f}%)")
print(f"- min {btc.price.min():,.0f} / max {btc.price.max():,.0f} "
      f"(range {(btc.price.max()/btc.price.min()-1)*100:.1f}%)")
print(f"- max drawdown nel periodo: {max_dd:.1f}% | vol giornaliera (std ret 1d): {daily_vol:.2f}%")

# ---------------------------------------------------------------- grafici
plt.rcParams.update({"figure.dpi": 130, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})

# 1. scatter log-volume vs PnL + OLS
fig, ax = plt.subplots(figsize=(8, 5.5))
for t in ["A", "B", "C"]:
    d = df[df.tier == t]
    ax.scatter(d.entry_volume, d.pnl_pct, label=f"Tier {t} (n={len(d)})",
               color=TIER_COLORS[t], alpha=0.75, s=46, edgecolor="white", linewidth=0.5)
xs = np.linspace(df.log_vol.min(), df.log_vol.max(), 100)
b1, b0 = np.polyfit(df.log_vol, df.pnl_pct, 1)
ax.plot(10 ** xs, b0 + b1 * xs, "k--", linewidth=1.4,
        label=f"OLS su log10(vol): slope {b1:+.2f}")
ax.set_xscale("log")
ax.axhline(0, color="gray", linewidth=0.8)
ax.set_xlabel("Volume 24h all'entry (USD, scala log)")
ax.set_ylabel("PnL teorico entry→exit (%)")
ax.set_title(f"Volume vs PnL — {len(df)} trade TF, 24 apr–8 mag 2026")
ax.legend()
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/01_scatter_volume_pnl.png")

# 2. quartili: PnL e WR
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
qt_r = qt.reset_index()
axes[0].bar(qt_r.vol_q.astype(str), qt_r.pnl_medio,
            color=["#55A868", "#88B89A", "#C5BB7F", "#C44E52"])
axes[0].axhline(0, color="gray", linewidth=0.8)
axes[0].set_title("PnL medio per quartile di volume")
axes[0].set_ylabel("PnL %")
for i, (v, n) in enumerate(zip(qt_r.pnl_medio, qt_r.n)):
    axes[0].text(i, v + (0.06 if v >= 0 else -0.16), f"{v:+.2f}%\n(n={n})",
                 ha="center", fontsize=8)
axes[1].bar(qt_r.vol_q.astype(str), qt_r.wr * 100,
            color=["#55A868", "#88B89A", "#C5BB7F", "#C44E52"])
axes[1].set_title("Win rate per quartile di volume")
axes[1].set_ylabel("WR %")
for i, v in enumerate(qt_r.wr * 100):
    axes[1].text(i, v + 0.8, f"{v:.0f}%", ha="center", fontsize=9)
for ax in axes:
    ax.tick_params(axis="x", labelsize=8)
fig.suptitle("Q1 = volume più basso → Q4 = più alto", y=1.02, fontsize=9, color="dimgray")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/02_quartili_pnl_wr.png", bbox_inches="tight")

# 3. BTC nel periodo + entry marks
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(btc.scan_timestamp, btc.price, color="#4C72B0", linewidth=1.2)
for ts in df.entry_ts:
    ax.axvline(ts, color="#55A868", alpha=0.12, linewidth=1)
ax.set_title(f"BTC/USDT (testnet feed) 24 apr – 8 mag · {btc_ret:+.1f}% · "
             f"max DD {max_dd:.1f}% · barre verdi = ALLOCATE TF")
ax.set_ylabel("Prezzo USD")
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/03_btc_periodo.png")

# 4. motivi deallocate
fig, ax = plt.subplots(figsize=(8, 4.6))
mb_r = mb.sort_values("pnl_medio")
ax.barh(mb_r.index, mb_r.pnl_medio,
        color=["#C44E52" if v < 0 else "#55A868" for v in mb_r.pnl_medio])
ax.axvline(0, color="gray", linewidth=0.8)
for i, (v, n) in enumerate(zip(mb_r.pnl_medio, mb_r.n)):
    ax.text(v + (0.05 if v >= 0 else -0.05), i, f"{v:+.2f}% (n={n})",
            va="center", ha="left" if v >= 0 else "right", fontsize=9)
ax.set_xlabel("PnL teorico medio (%)")
ax.set_title("PnL medio per motivo di DEALLOCATE")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/04_deallocate_reasons.png")

# 5. predittori entry
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
axes[0].scatter(df.entry_signal_strength, df.pnl_pct, alpha=0.7, s=40,
                c=[TIER_COLORS.get(t, "gray") for t in df.tier])
axes[0].axhline(0, color="gray", linewidth=0.8)
axes[0].set_xlabel("signal_strength all'ALLOCATE")
axes[0].set_ylabel("PnL %")
axes[1].scatter(df.entry_rsi, df.pnl_pct, alpha=0.7, s=40,
                c=[TIER_COLORS.get(t, "gray") for t in df.tier])
axes[1].axhline(0, color="gray", linewidth=0.8)
axes[1].set_xlabel("RSI all'ALLOCATE")
fig.suptitle("Predittori al momento dell'ALLOCATE vs PnL (colore = tier)")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/05_predittori_entry.png")

print(f"\n## Grafici salvati in {OUT_DIR}")
