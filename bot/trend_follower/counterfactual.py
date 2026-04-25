"""
BagHolderAI - 47a Counterfactual Tracker for Distance Filter Skips

Records what would have happened if the entry distance filter (45e v2)
had NOT skipped a coin. For each `entry_distance_skip` event older than
24h, fetches the current price + 24h peak via ccxt and stores a delta
row in `counterfactual_log`. The data lets the CEO tune the threshold
with hard numbers instead of intuition ("does +15% above EMA20 actually
catch losers, or are we leaving money on the table?").

Run cadence: once per TF scan cycle (default 1h), invoked from the main
loop of trend_follower.py. Only processes skips that are >=24h old AND
not already recorded — robust to orchestrator downtime (a 6h outage
doesn't lose any skips, they just get processed at the next scan).

Contract:
- `run_counterfactual_check` MUST NOT raise. Failures degrade to local
  warnings; observability is best-effort. The TF main loop must not be
  blocked by a counterfactual write error.
- Coin delistings / fetch errors → row is still written with NULL
  check_price/delta/peak + `notes='fetch_failed: <reason>'` so the
  skip doesn't get re-processed forever.
"""

import logging
from datetime import datetime, timedelta, timezone

from db.client import get_client
from db.event_logger import log_event

_logger = logging.getLogger("bagholderai.counterfactual")

# Minimum skip age before we evaluate the counterfactual. The brief
# defaults to 24h (one full daily cycle) — long enough to see whether
# the filter saved us from a dump or made us miss a pump.
_MIN_AGE_HOURS = 24.0

# Cap how many events we process per scan to avoid blocking the TF loop
# if a backlog accumulates (e.g. after a long downtime). Surplus events
# are picked up at the next scan.
_BATCH_LIMIT = 100


def _already_recorded_event_ids(supabase, event_ids: list[str]) -> set[str]:
    """Return the subset of skip_event_ids that already have a counterfactual
    row, so we don't double-process. We match by (symbol, skip_timestamp)
    because counterfactual_log doesn't store the original event uuid —
    keeping the schema lean as the brief requested.
    """
    # Implementation note: matching by (symbol, skip_timestamp) is unique
    # in practice (one log_event call per skip per scan). We pull all
    # skip_timestamps already in the log for the candidate symbols and
    # filter in Python — simpler than a NOT EXISTS subquery via PostgREST.
    return set()  # placeholder — see _filter_unprocessed below


def _filter_unprocessed(supabase, candidates: list[dict]) -> list[dict]:
    """Drop candidates that already have a row in counterfactual_log
    (matched by symbol + skip_timestamp). Resilient to PostgREST quirks:
    on any error, returns the input unchanged so worst case we re-process,
    not lose data.
    """
    if not candidates:
        return []
    try:
        # Query existing counterfactual rows for the candidate symbols only
        # (much smaller result set than scanning the whole table).
        symbols = list({c["symbol"] for c in candidates})
        existing = (
            supabase.table("counterfactual_log")
            .select("symbol,skip_timestamp")
            .in_("symbol", symbols)
            .execute()
        )
        seen = {
            (r["symbol"], r["skip_timestamp"])
            for r in (existing.data or [])
        }
        out = []
        for c in candidates:
            key = (c["symbol"], c["skip_timestamp"])
            if key not in seen:
                out.append(c)
        return out
    except Exception as e:
        _logger.warning(f"counterfactual: dedupe query failed ({e}) — proceeding without dedupe")
        return candidates


def _fetch_current_and_peak(exchange, symbol: str, skip_dt: datetime
                            ) -> tuple[float | None, float | None, str | None]:
    """Return (current_price, peak_24h_price_after_skip, error_note).

    Uses 1h OHLCV candles to derive both values in a single call:
    - current_price = last candle's close
    - peak_24h = max(high) across candles whose close-time is >= skip_dt
                 and within 24h of skip_dt

    On failure (delisted coin, network error, empty candles), returns
    (None, None, "<reason>"). The caller writes the row with NULL deltas
    + notes so the skip is permanently recorded as "not evaluable".
    """
    try:
        # Fetch enough candles to cover the 24h window plus the current
        # tick. limit=30 leaves headroom for clock skew / late candles.
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=30)
        if not ohlcv:
            return None, None, "no_candles"

        # ccxt timestamps are ms since epoch (UTC).
        skip_ms = int(skip_dt.timestamp() * 1000)
        window_end_ms = skip_ms + 24 * 3600 * 1000

        post_skip = [c for c in ohlcv if skip_ms <= c[0] <= window_end_ms]
        if not post_skip:
            # Skip is too recent for the candle granularity, or candles
            # are missing. Use the last candle as fallback for current
            # price and skip the peak.
            current = float(ohlcv[-1][4])  # last close
            return current, None, "no_post_skip_candles"

        peak = max(float(c[2]) for c in post_skip)  # high
        current = float(ohlcv[-1][4])
        return current, peak, None
    except Exception as e:
        # Common case: coin delisted → exchange returns 4xx or empty list.
        return None, None, f"fetch_failed: {type(e).__name__}"


def run_counterfactual_check(exchange, supabase=None) -> int:
    """Process pending entry_distance_skip events and write counterfactual
    rows. Returns the number of rows written. Never raises.

    Called once per TF scan cycle (after decisions are logged, before
    apply_allocations). Cheap when there are no pending skips: one
    SELECT, no inserts, no exchange calls.
    """
    if supabase is None:
        supabase = get_client()

    written = 0
    try:
        # 1) Pull recent entry_distance_skip events older than 24h. We
        # query a wide window (last 14 days) so catch-up after long
        # downtime works; dedupe filters out the already-recorded ones.
        cutoff_max = datetime.now(timezone.utc) - timedelta(hours=_MIN_AGE_HOURS)
        cutoff_min = datetime.now(timezone.utc) - timedelta(days=14)

        events_q = (
            supabase.table("bot_events_log")
            .select("id,created_at,symbol,details")
            .eq("event", "entry_distance_skip")
            .gte("created_at", cutoff_min.isoformat())
            .lte("created_at", cutoff_max.isoformat())
            .order("created_at", desc=False)
            .limit(_BATCH_LIMIT)
            .execute()
        )
        events = events_q.data or []
        if not events:
            return 0

        # 2) Build candidate list with the fields we need downstream.
        candidates = []
        for e in events:
            details = e.get("details") or {}
            skip_price = details.get("skip_price")
            skip_ema20 = details.get("skip_ema20")
            distance_pct = details.get("distance_pct")
            symbol = e.get("symbol")
            skip_ts = e.get("created_at")
            if not symbol or not skip_ts:
                continue
            # Skip events from BEFORE 47a deploy don't have skip_price/ema —
            # we can still write a row but with NULL pre-state. Mark it.
            missing_pre = skip_price is None or skip_ema20 is None
            candidates.append({
                "symbol": symbol,
                "skip_timestamp": skip_ts,
                "skip_price": float(skip_price) if skip_price is not None else None,
                "skip_ema20": float(skip_ema20) if skip_ema20 is not None else None,
                "skip_distance_pct": float(distance_pct) if distance_pct is not None else 0.0,
                "_missing_pre": missing_pre,
            })

        # 3) Drop already-processed.
        candidates = _filter_unprocessed(supabase, candidates)
        if not candidates:
            return 0

        _logger.info(f"counterfactual: {len(candidates)} skip(s) ready for evaluation")

        # 4) For each candidate, fetch current + peak and insert.
        for c in candidates:
            try:
                skip_dt = datetime.fromisoformat(
                    str(c["skip_timestamp"]).replace("Z", "+00:00")
                )
            except Exception as e:
                _logger.warning(
                    f"counterfactual: bad skip_timestamp on {c['symbol']}: {e}"
                )
                continue

            # 47a: pre-deploy skips lack skip_price/ema — we can't compute
            # delta_pct without the baseline, so write a stub row with
            # notes='no_baseline' to mark them as processed and move on.
            if c["_missing_pre"]:
                _insert_counterfactual_stub(supabase, c, notes="no_baseline")
                written += 1
                continue

            current_price, peak_price, err = _fetch_current_and_peak(
                exchange, c["symbol"], skip_dt
            )
            now_dt = datetime.now(timezone.utc)
            hours_elapsed = (now_dt - skip_dt).total_seconds() / 3600.0

            row = {
                "symbol": c["symbol"],
                "skip_timestamp": c["skip_timestamp"],
                "skip_price": c["skip_price"],
                "skip_ema20": c["skip_ema20"],
                "skip_distance_pct": c["skip_distance_pct"],
                "hours_elapsed": round(hours_elapsed, 2),
                "check_price": None,
                "delta_24h_pct": None,
                "peak_24h_pct": None,
                "notes": err,  # NULL on success
            }

            if current_price is not None and c["skip_price"]:
                row["check_price"] = current_price
                row["delta_24h_pct"] = round(
                    ((current_price - c["skip_price"]) / c["skip_price"]) * 100, 2
                )
            if peak_price is not None and c["skip_price"]:
                row["peak_24h_pct"] = round(
                    ((peak_price - c["skip_price"]) / c["skip_price"]) * 100, 2
                )

            try:
                supabase.table("counterfactual_log").insert(row).execute()
                written += 1
            except Exception as e:
                _logger.warning(
                    f"counterfactual: insert failed for {c['symbol']} @ {c['skip_timestamp']}: {e}"
                )

        if written > 0:
            _logger.info(f"counterfactual: wrote {written} row(s)")
            log_event(
                severity="info",
                category="tf",
                event="counterfactual_batch",
                symbol=None,
                message=f"Counterfactual check wrote {written} row(s) for distance skips",
                details={"rows": written, "candidates": len(candidates)},
            )
        return written
    except Exception as e:
        _logger.warning(f"counterfactual: unexpected error ({e}) — skipping cycle")
        return written


def _insert_counterfactual_stub(supabase, candidate: dict, notes: str) -> None:
    """Insert a row with the symbol+timestamp only, marking the skip as
    processed. Used when we lack the baseline price/EMA (events from
    before 47a deploy) so we don't keep re-checking them.
    """
    try:
        supabase.table("counterfactual_log").insert({
            "symbol": candidate["symbol"],
            "skip_timestamp": candidate["skip_timestamp"],
            "skip_price": candidate["skip_price"] or 0,
            "skip_ema20": candidate["skip_ema20"] or 0,
            "skip_distance_pct": candidate["skip_distance_pct"],
            "hours_elapsed": 0,
            "check_price": None,
            "delta_24h_pct": None,
            "peak_24h_pct": None,
            "notes": notes,
        }).execute()
    except Exception as e:
        _logger.warning(
            f"counterfactual stub insert failed for {candidate['symbol']}: {e}"
        )
