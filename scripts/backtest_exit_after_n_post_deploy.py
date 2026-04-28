"""
Replica del backtest exit_after_n filtrando SOLO i managed periods che
hanno coperto del tempo dopo il deploy 49a+49b (27/04/2026 20:00 UTC).

Definizione: un period è "post-deploy" se il suo opened_at >= cutoff,
oppure se opened_at < cutoff ma closed_at > cutoff (period a cavallo).
Per il confronto con il backtest pre-deploy esistente, runniamo entrambe
le segmentazioni e stampiamo i delta.

Output: scripts/output/exit_after_n_post_deploy_summary.csv
        scripts/output/exit_after_n_post_deploy_per_period.csv
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.backtest_exit_after_n_positive_sells import (
    fetch_all_tf_trades,
    build_managed_periods,
    summarize,
    write_per_period_csv,
    OUT_DIR,
    N_VALUES,
)


DEPLOY_CUTOFF = datetime(2026, 4, 27, 20, 0, 0, tzinfo=timezone.utc)


def parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def split_by_deploy(periods, cutoff=DEPLOY_CUTOFF):
    """
    Returns (pre, post, straddling).
    - pre: closed_at <= cutoff (entirely before deploy)
    - post: opened_at >= cutoff (entirely after deploy)
    - straddling: opened_at < cutoff < closed_at (crosses deploy)
    Open periods (closed=False) go in pre/post by opened_at only.
    """
    pre, post, straddling = [], [], []
    for p in periods:
        opened = parse_dt(p["opened_at"])
        closed = parse_dt(p["closed_at"]) if p["closed_at"] else None
        if opened >= cutoff:
            post.append(p)
        elif closed is not None and closed <= cutoff:
            pre.append(p)
        elif closed is None:
            # Still open, started before cutoff — treat as straddling
            straddling.append(p)
        else:
            straddling.append(p)
    return pre, post, straddling


def print_summary_table(label, summary):
    print(f"\n=== {label} ===")
    print(f"{'N':>3} {'trig':>5} {'beat':>5} {'worse':>6} {'tied':>5} "
          f"{'avgΔ$':>8} {'totΔ$':>9}")
    for row in summary:
        print(f"{row['N']:>3} {row['rule_triggered']:>5} "
              f"{row['rule_beat_actual']:>5} "
              f"{row['rule_worse_than_actual']:>6} {row['rule_tied']:>5} "
              f"{row['avg_delta_when_triggered_usd']:>8.2f} "
              f"{row['delta_total_usd']:>9.2f}")


def main():
    print("Fetching TF trades from Supabase...")
    trades = fetch_all_tf_trades()
    print(f"  fetched {len(trades)} trades")

    periods = build_managed_periods(trades)
    pre, post, straddling = split_by_deploy(periods)

    pre_closed = [p for p in pre if p["closed"]]
    post_closed = [p for p in post if p["closed"]]
    straddling_closed = [p for p in straddling if p["closed"]]
    straddling_open = [p for p in straddling if not p["closed"]]
    post_open = [p for p in post if not p["closed"]]

    print(f"\nDeploy cutoff: {DEPLOY_CUTOFF.isoformat()}")
    print(f"Total periods reconstructed: {len(periods)}")
    print(f"  PRE  (closed_at <= cutoff):     {len(pre)} ({len(pre_closed)} closed)")
    print(f"  POST (opened_at >= cutoff):     {len(post)} "
          f"({len(post_closed)} closed, {len(post_open)} still open)")
    print(f"  STRADDLING (crosses cutoff):    {len(straddling)} "
          f"({len(straddling_closed)} closed, {len(straddling_open)} still open)")

    print("\nPOST-deploy closed periods detail:")
    for p in sorted(post_closed, key=lambda x: x["opened_at"]):
        n_pos = sum(1 for t in p["trades"]
                    if t.get("side") == "sell"
                    and float(t.get("realized_pnl") or 0) > 0)
        print(f"  {p['symbol']:<14} opened={p['opened_at'][:19]} "
              f"closed={p['closed_at'][:19]} "
              f"trades={len(p['trades']):>3} pos_sells={n_pos:>2}")

    if post_open:
        print("\nPOST-deploy still-open periods:")
        for p in sorted(post_open, key=lambda x: x["opened_at"]):
            n_pos = sum(1 for t in p["trades"]
                        if t.get("side") == "sell"
                        and float(t.get("realized_pnl") or 0) > 0)
            print(f"  {p['symbol']:<14} opened={p['opened_at'][:19]} "
                  f"trades={len(p['trades']):>3} pos_sells={n_pos:>2} "
                  f"(STILL HOLDING)")

    if straddling_closed:
        print("\nSTRADDLING (opened pre-deploy, closed post-deploy):")
        for p in sorted(straddling_closed, key=lambda x: x["opened_at"]):
            n_pos = sum(1 for t in p["trades"]
                        if t.get("side") == "sell"
                        and float(t.get("realized_pnl") or 0) > 0)
            print(f"  {p['symbol']:<14} opened={p['opened_at'][:19]} "
                  f"closed={p['closed_at'][:19]} "
                  f"trades={len(p['trades']):>3} pos_sells={n_pos:>2}")

    pre_summary = summarize(pre_closed) if pre_closed else []
    post_summary = summarize(post_closed) if post_closed else []
    strad_summary = summarize(straddling_closed) if straddling_closed else []

    if pre_summary:
        print_summary_table(f"PRE-DEPLOY backtest ({len(pre_closed)} closed periods)", pre_summary)
    if post_summary:
        print_summary_table(f"POST-DEPLOY backtest ({len(post_closed)} closed periods)", post_summary)
    if strad_summary:
        print_summary_table(f"STRADDLING ({len(straddling_closed)} closed periods)", strad_summary)

    if pre_summary and post_summary:
        print("\n=== DELTA POST vs PRE (per-N edge totΔ$) ===")
        print(f"{'N':>3} {'pre_totΔ':>10} {'post_totΔ':>10} {'shift':>8}")
        for pre_row, post_row in zip(pre_summary, post_summary):
            pre_d = pre_row["delta_total_usd"]
            post_d = post_row["delta_total_usd"]
            print(f"{pre_row['N']:>3} {pre_d:>10.2f} {post_d:>10.2f} "
                  f"{post_d - pre_d:>+8.2f}")

    import csv
    sum_path = OUT_DIR / "exit_after_n_post_deploy_summary.csv"
    with open(sum_path, "w", newline="") as f:
        if post_summary:
            w = csv.DictWriter(f, fieldnames=list(post_summary[0].keys()))
            w.writeheader()
            w.writerows(post_summary)

    print(f"\nWritten:\n  {sum_path}")


if __name__ == "__main__":
    main()
