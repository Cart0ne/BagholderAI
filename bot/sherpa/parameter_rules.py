"""Sherpa parameter rules (Sprint 1).

Two-layer architecture (per CEO brief, board-approved):
    final = base(regime) + sum(delta_i(fast_signals)), clamped to ranges.

In Sprint 1 only the adjustment layer is active: regime is hardcoded to
"neutral". The base table for the other regimes is present in this file
ready for Sprint 2 (slow loop / regime detection from F&G + CMC) — at
that point parameter_rules.calculate_parameters will simply receive a
regime != "neutral" and the same code path will work unchanged.

The risk_score is mapped to fast-signal flags via _signals_from_risk
so Sprint 1 stays read-from-DB (we only have sentinel_scores.risk_score
and a few raw_signals fields). When Sprint 2 wires the slow-loop tables,
this can be replaced with a signal-aware version.
"""

from __future__ import annotations

from typing import Optional

# Base layer — Sprint 1 uses NEUTRAL only. Other rows exist for Sprint 2.
BASE_TABLE: dict[str, dict[str, float]] = {
    "extreme_fear":   {"buy_pct": 2.5, "sell_pct": 1.0, "idle_reentry_hours": 4.0},
    "fear":           {"buy_pct": 1.8, "sell_pct": 1.2, "idle_reentry_hours": 2.0},
    "neutral":        {"buy_pct": 1.0, "sell_pct": 1.5, "idle_reentry_hours": 1.0},
    "greed":          {"buy_pct": 0.8, "sell_pct": 2.0, "idle_reentry_hours": 0.75},
    "extreme_greed":  {"buy_pct": 0.5, "sell_pct": 3.0, "idle_reentry_hours": 0.5},
}

# Adjustment layer — fast-signal deltas applied on top of the base.
# Each tuple is (rule_name, predicate_kwarg, d_buy, d_sell, d_idle).
# Drop ladder is mutually exclusive (only the strongest match fires);
# pump ladder likewise. Funding has its own pair of ladders. speed_of_fall
# is independent.
DROP_LADDER = [
    # threshold_pct, name, d_buy, d_sell, d_idle
    (-10, "btc_drop_10pct_1h", 1.5, -0.7, 3.0),
    (-5,  "btc_drop_5pct_1h",  1.0, -0.5, 2.0),
    (-3,  "btc_drop_3pct_1h",  0.5, -0.3, 1.0),
]
PUMP_LADDER = [
    (5, "btc_pump_5pct_1h", -0.5, 1.0, -0.5),
    (3, "btc_pump_3pct_1h", -0.3, 0.5, -0.3),
]
FUNDING_LONG_LADDER = [
    (0.0005, "funding_long_strong",  0.4, -0.2, 0.5),
    (0.0003, "funding_long",         0.2, -0.1, 0.3),
]
FUNDING_SHORT_LADDER = [
    (-0.0003, "funding_short_strong", -0.2, 0.3, -0.3),
    (-0.0001, "funding_short",        -0.1, 0.1, -0.2),
]
SPEED_OF_FALL_DELTA = (0.3, -0.2, 0.5)  # d_buy, d_sell, d_idle

# Absolute clamps. Hard limits regardless of regime + delta arithmetic.
RANGES = {
    "buy_pct":            (0.3, 3.0),
    "sell_pct":           (0.8, 4.0),
    "idle_reentry_hours": (0.5, 6.0),
}


def calculate_parameters(
    regime: str = "neutral",
    fast_signals: Optional[dict] = None,
) -> tuple[dict, dict]:
    """Apply base + delta and return (final_params, breakdown).

    final_params keys: buy_pct, sell_pct, idle_reentry_hours.
    breakdown lists which rules fired with their per-rule deltas, for
    logging in sherpa_proposals.cooldown_parameters / raw_signals.
    """
    if regime not in BASE_TABLE:
        regime = "neutral"
    base = BASE_TABLE[regime]
    fast_signals = fast_signals or {}

    breakdown: dict = {"regime": regime, "base": dict(base), "rules": []}
    d_buy = d_sell = d_idle = 0.0

    change_1h = fast_signals.get("btc_change_1h")
    if change_1h is not None:
        for threshold, name, db, ds, di in DROP_LADDER:
            if change_1h <= threshold:
                d_buy += db
                d_sell += ds
                d_idle += di
                breakdown["rules"].append({"name": name, "d_buy": db, "d_sell": ds, "d_idle": di})
                break
        else:
            for threshold, name, db, ds, di in PUMP_LADDER:
                if change_1h >= threshold:
                    d_buy += db
                    d_sell += ds
                    d_idle += di
                    breakdown["rules"].append({"name": name, "d_buy": db, "d_sell": ds, "d_idle": di})
                    break

    if fast_signals.get("speed_of_fall_accelerating"):
        db, ds, di = SPEED_OF_FALL_DELTA
        d_buy += db
        d_sell += ds
        d_idle += di
        breakdown["rules"].append(
            {"name": "speed_of_fall_accelerating", "d_buy": db, "d_sell": ds, "d_idle": di}
        )

    funding = fast_signals.get("funding_rate")
    if funding is not None:
        if funding > 0:
            for threshold, name, db, ds, di in FUNDING_LONG_LADDER:
                if funding > threshold:
                    d_buy += db
                    d_sell += ds
                    d_idle += di
                    breakdown["rules"].append(
                        {"name": name, "d_buy": db, "d_sell": ds, "d_idle": di}
                    )
                    break
        else:
            for threshold, name, db, ds, di in FUNDING_SHORT_LADDER:
                if funding < threshold:
                    d_buy += db
                    d_sell += ds
                    d_idle += di
                    breakdown["rules"].append(
                        {"name": name, "d_buy": db, "d_sell": ds, "d_idle": di}
                    )
                    break

    raw = {
        "buy_pct": base["buy_pct"] + d_buy,
        "sell_pct": base["sell_pct"] + d_sell,
        "idle_reentry_hours": base["idle_reentry_hours"] + d_idle,
    }
    final = {k: _clamp(k, v) for k, v in raw.items()}
    breakdown["delta_total"] = {"d_buy": d_buy, "d_sell": d_sell, "d_idle": d_idle}
    breakdown["final"] = dict(final)
    return final, breakdown


def _clamp(name: str, v: float) -> float:
    lo, hi = RANGES[name]
    return max(lo, min(hi, round(v, 4)))


def is_changed(current: Optional[float], proposed: float, tol: float = 0.01) -> bool:
    """Rule-of-thumb equality check used by the Sherpa loop. None means
    the parameter is missing in bot_config — treat as a change so it gets
    populated.
    """
    if current is None:
        return True
    return abs(float(current) - float(proposed)) > tol
