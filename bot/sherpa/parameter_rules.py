"""Sherpa parameter rules (Sprint 2, Brief 81a).

Three structural changes vs Sprint 1:

1. **Per-coin volatility scaling** — buy_pct and sell_pct from the base
   regime table are scaled by a per-symbol multiplier (BTC anchor = 1.0).
   A more volatile coin (e.g. BONK with ~3× BTC stdev) gets a wider
   sell_pct, so Sherpa stops proposing identical numbers for BTC/SOL/BONK.
   idle_reentry_hours is a time, not an amplitude — left unscaled.

2. **Slow-loop only** — the Sprint-1 fast-signal ladders
   (DROP_LADDER / PUMP_LADDER / FUNDING_*_LADDER / SPEED_OF_FALL_DELTA)
   are gone. Brain Analysis 2026-05-22 documented 449 fast-loop flips
   in 16 days driving a 6-minute proposal flicker. With Sprint 2 the
   only dynamic input is the slow-loop regime, which transitions every
   few hours. fast_signals is no longer a parameter of this function.

3. **Amplitude cap** — after base × multiplier and after absolute
   clamps, the final value is bounded to
       current * (1 - MAX_DELTA_PCT)  <=  proposed  <=  current * (1 + MAX_DELTA_PCT)
   so a single Sherpa tick cannot double or halve a parameter. The
   cap is skipped when current is None (parameter missing in
   bot_config — let the first proposal populate it).
"""

from __future__ import annotations

from typing import Optional

from config.settings import HardcodedRules

# Base layer — one row per regime, anchored on BTC volatility (multiplier=1.0).
# Other coins multiply the buy_pct/sell_pct entries by their volatility ratio.
BASE_TABLE: dict[str, dict[str, float]] = {
    "extreme_fear":   {"buy_pct": 2.5, "sell_pct": 1.0, "idle_reentry_hours": 4.0},
    "fear":           {"buy_pct": 1.8, "sell_pct": 1.2, "idle_reentry_hours": 2.0},
    "neutral":        {"buy_pct": 1.0, "sell_pct": 1.5, "idle_reentry_hours": 1.0},
    "greed":          {"buy_pct": 0.8, "sell_pct": 2.0, "idle_reentry_hours": 0.75},
    "extreme_greed":  {"buy_pct": 0.5, "sell_pct": 3.0, "idle_reentry_hours": 0.5},
}

# Absolute hard clamps. Final guard regardless of regime × multiplier.
# Kept identical to Sprint 1 — Brief 81a Block 3 instructs CC to start
# from the existing ranges and ask the Board if saturation appears.
RANGES = {
    "buy_pct":            (0.3, 3.0),
    "sell_pct":           (0.8, 4.0),
    "idle_reentry_hours": (0.5, 6.0),
}

# Parameters that scale with per-coin volatility. idle_reentry_hours is
# time (not amplitude) and is left unscaled.
VOLATILITY_SCALED = ("buy_pct", "sell_pct")


def calculate_parameters(
    regime: str,
    current_params: dict,
    volatility_multiplier: float = 1.0,
) -> tuple[dict, dict]:
    """Apply base(regime) × per-coin volatility, then absolute clamps,
    then amplitude cap relative to current_params. Returns (final, breakdown).

    Args:
        regime: one of BASE_TABLE keys; unknown values fall back to "neutral".
        current_params: {buy_pct, sell_pct, idle_reentry_hours} as currently
            stored in bot_config for this symbol. None values are allowed
            (e.g. first run) — the amplitude cap is skipped for those keys.
        volatility_multiplier: per-symbol scalar from volatility module.
            BTC anchor = 1.0. Coins with > 1.0 get wider amplitude params.

    breakdown logs the regime, base row, multiplier used, raw scaled
    values, clamp_applied flags, cap_applied flags, and the final dict —
    so sherpa_proposals.raw_signals stays auditable.
    """
    if regime not in BASE_TABLE:
        regime = "neutral"
    base = BASE_TABLE[regime]

    # Step 1: base × volatility (only for amplitude params).
    raw: dict[str, float] = {}
    for k in BASE_TABLE[regime]:
        if k in VOLATILITY_SCALED:
            raw[k] = base[k] * float(volatility_multiplier)
        else:
            raw[k] = base[k]

    # Step 2: absolute clamps.
    clamped: dict[str, float] = {}
    clamp_applied: dict[str, bool] = {}
    for k, v in raw.items():
        c = _clamp(k, v)
        clamped[k] = c
        clamp_applied[k] = c != round(v, 4)

    # Step 3: amplitude cap relative to current_params. Skipped where
    # current is missing (None) or zero (cap formula degenerate).
    final: dict[str, float] = {}
    cap_applied: dict[str, bool] = {}
    max_delta = HardcodedRules.MAX_DELTA_PCT
    for k, v in clamped.items():
        cur = current_params.get(k)
        if cur is None or float(cur) <= 0:
            final[k] = v
            cap_applied[k] = False
            continue
        cur_f = float(cur)
        up = cur_f * (1.0 + max_delta)
        down = cur_f * (1.0 - max_delta)
        capped = max(down, min(up, v))
        final[k] = round(capped, 4)
        cap_applied[k] = capped != v

    breakdown = {
        "regime": regime,
        "base": dict(base),
        "volatility_multiplier": round(float(volatility_multiplier), 4),
        "raw": {k: round(v, 4) for k, v in raw.items()},
        "clamped": dict(clamped),
        "clamp_applied": clamp_applied,
        "cap_applied": cap_applied,
        "max_delta_pct": max_delta,
        "final": dict(final),
    }
    return final, breakdown


def _clamp(name: str, v: float) -> float:
    lo, hi = RANGES[name]
    return max(lo, min(hi, round(v, 4)))


def is_changed(current: Optional[float], proposed: float, tol: float = 0.01) -> bool:
    """Rule-of-thumb equality check used by the Sherpa loop. None means
    the parameter is missing in bot_config — treat as a change so it gets
    populated."""
    if current is None:
        return True
    return abs(float(current) - float(proposed)) > tol
