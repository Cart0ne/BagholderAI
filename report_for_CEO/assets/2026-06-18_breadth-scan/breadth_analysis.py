"""
Breadth analysis on trend_scans — exploratory, read-only.

Idea (Max, pitched to CEO): after days of ~0 BULLISH, the scanner suddenly
flags a burst of low-cap (tier 3) coins. Is that breadth-shift itself a
regime signal for NewsKeeper -> Sentinel?

This script measures BULLISH breadth per volume tier over time.

CAVEATS (read before trusting numbers):
- Source = trend_scans, fed by the TF scanner running on Binance TESTNET
  (create_exchange() sandbox). Testnet volumes are artificial -> the A/B/C
  tier split is distorted (BTC can land in B). Testnet klines drive the
  EMA/RSI/ATR that classify BULLISH, so for thin tier-C coins the signal
  is testnet noise, not the real altcoin market.
- tier labels: A = vol >= tier1_min (blue chip / tier1),
               B = vol >= tier2_min (mid / tier2),
               C = small cap (tier3).  (scanner.py:193)
- signal in {BULLISH, BEARISH, SIDEWAYS, NO_SIGNAL} (classifier.py)
- retention: trend_scans pruned to ~14d, currently ~7d of history.

Run on the Mac Mini (has .env + venv):
    cd /Volumes/Archivio/bagholderai && venv/bin/python3.13 - < breadth_analysis.py
"""
from db.client import get_client
from collections import defaultdict

TIER_NAME = {"A": "T1 (blue)", "B": "T2 (mid)", "C": "T3 (small)"}
TIERS = ["A", "B", "C"]

c = get_client()

# ---- pull all rows (paginated) --------------------------------------------
rows = []
PAGE = 1000
off = 0
while True:
    r = (c.table("trend_scans")
         .select("scan_timestamp,symbol,tier,signal,price")
         .order("scan_timestamp")
         .range(off, off + PAGE - 1)
         .execute())
    if not r.data:
        break
    rows.extend(r.data)
    if len(r.data) < PAGE:
        break
    off += PAGE

print(f"rows: {len(rows)}")
print(f"span: {rows[0]['scan_timestamp']}  ->  {rows[-1]['scan_timestamp']}")

# ---- group by scan, count per tier ----------------------------------------
# scan[ts][tier] = {'total': n, 'bull': n, 'bear': n}
scan = defaultdict(lambda: defaultdict(lambda: {"total": 0, "bull": 0, "bear": 0}))
btc_price_by_scan = {}
for row in rows:
    ts = row["scan_timestamp"]
    t = str(row.get("tier"))
    sig = str(row.get("signal"))
    if t not in TIERS:
        t = "?"
    d = scan[ts][t]
    d["total"] += 1
    if sig == "BULLISH":
        d["bull"] += 1
    elif sig == "BEARISH":
        d["bear"] += 1
    if row.get("symbol") == "BTC/USDT":
        btc_price_by_scan[ts] = row.get("price")

scans_sorted = sorted(scan.keys())
print(f"distinct scans: {len(scans_sorted)}")

# ---- daily aggregation ----------------------------------------------------
# per day: avg bull count + avg total per tier, plus max bull (burst), plus
# fraction of scans in the day with >=1 bullish in tier C.
def day_of(ts):
    return ts[:10]

days = defaultdict(list)
for ts in scans_sorted:
    days[day_of(ts)].append(ts)

print("\n=== DAILY BULLISH BREADTH PER TIER (avg bull / avg total per scan) ===")
hdr = f"{'day':<11} {'scans':>5} | " + " | ".join(f"{TIER_NAME[t]:>11}" for t in TIERS) + f" | {'BTC~':>8}"
print(hdr)
print("-" * len(hdr))
daily_csv = ["day,scans,A_bull,A_tot,B_bull,B_tot,C_bull,C_tot,C_scans_with_bull,C_max_bull,btc"]
for day in sorted(days.keys()):
    tss = days[day]
    n = len(tss)
    cells = []
    rowvals = {"day": day, "scans": n}
    for t in TIERS:
        bull = sum(scan[ts][t]["bull"] for ts in tss) / n
        tot = sum(scan[ts][t]["total"] for ts in tss) / n
        cells.append(f"{bull:>4.1f}/{tot:>4.1f}")
        rowvals[f"{t}_bull"] = round(bull, 2)
        rowvals[f"{t}_tot"] = round(tot, 2)
    c_with_bull = sum(1 for ts in tss if scan[ts]["C"]["bull"] >= 1)
    c_max_bull = max((scan[ts]["C"]["bull"] for ts in tss), default=0)
    btc_vals = [btc_price_by_scan[ts] for ts in tss if btc_price_by_scan.get(ts)]
    btc = sum(btc_vals) / len(btc_vals) if btc_vals else 0
    print(f"{day:<11} {n:>5} | " + " | ".join(f"{cc:>11}" for cc in cells)
          + f" | {btc:>8.0f}   (T3: {c_with_bull}/{n} scans w/ bull, max {c_max_bull})")
    daily_csv.append(
        f"{day},{n},{rowvals['A_bull']},{rowvals['A_tot']},{rowvals['B_bull']},"
        f"{rowvals['B_tot']},{rowvals['C_bull']},{rowvals['C_tot']},"
        f"{c_with_bull},{c_max_bull},{btc:.0f}")

# ---- per-scan tier-C bullish series (spot the burst) ----------------------
print("\n=== TIER 3 (C) BULLISH COUNT, per scan (chronological) — spot bursts ===")
line = []
for ts in scans_sorted:
    line.append(str(scan[ts]["C"]["bull"]))
print(" ".join(line))

print("\n=== TIER 2 (B) BULLISH COUNT, per scan ===")
print(" ".join(str(scan[ts]["B"]["bull"]) for ts in scans_sorted))
print("\n=== TIER 1 (A) BULLISH COUNT, per scan ===")
print(" ".join(str(scan[ts]["A"]["bull"]) for ts in scans_sorted))

# write CSV next to wherever cwd is
try:
    with open("breadth_daily.csv", "w") as f:
        f.write("\n".join(daily_csv))
    print("\nwrote breadth_daily.csv")
except Exception as e:
    print(f"(csv write skipped: {e})")
