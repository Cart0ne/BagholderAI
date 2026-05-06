"""Sentinel score engine (Sprint 1, fast signals only).

Translates a dict of raw signals from price_monitor + funding_monitor
into a (risk_score, opportunity_score) pair, both 0-100.

The contribution table below is the Sprint 1 proposal from the CEO
brief. Weights are intentionally exposed as module-level constants so
they can be retuned with live data without touching engine logic.

Contract:
    score(signals: dict) -> (risk: int, opportunity: int, breakdown: dict)
The breakdown dict lists which rules fired with their per-rule contribution,
making post-hoc analysis on sentinel_scores.raw_signals straightforward.
"""

from __future__ import annotations

from typing import Optional

# (label, predicate description, risk_delta, opp_delta).
# The predicate is enforced in code; the description is for the breakdown
# log only.
_BASE_RISK = 20
_BASE_OPP = 20


def score(signals: dict) -> tuple[int, int, dict]:
    """Compute risk and opportunity scores from a Sentinel signal dict.

    Expected keys (all optional — missing values are treated as no-signal):
        btc_change_1h: float | None  (% change last hour)
        speed_of_fall_accelerating: bool
        funding_rate: float | None  (decimal, e.g. 0.0003 = 0.03%)

    Returns (risk_score, opportunity_score, breakdown). Both scores are
    clamped to 0-100. breakdown is a dict {rule_name: {"risk": x, "opp": y}}.
    """
    risk = _BASE_RISK
    opp = _BASE_OPP
    breakdown: dict = {"base": {"risk": _BASE_RISK, "opp": _BASE_OPP}}

    change_1h = signals.get("btc_change_1h")
    if change_1h is not None:
        # Drop ladder: only the strongest matching rule contributes.
        if change_1h <= -10:
            _add(breakdown, "btc_drop_10pct_1h", risk_delta=80)
            risk += 80
        elif change_1h <= -5:
            _add(breakdown, "btc_drop_5pct_1h", risk_delta=50)
            risk += 50
        elif change_1h <= -3:
            _add(breakdown, "btc_drop_3pct_1h", risk_delta=30)
            risk += 30
        # Pump ladder, opportunity side.
        elif change_1h >= 5:
            _add(breakdown, "btc_pump_5pct_1h", opp_delta=40)
            opp += 40
        elif change_1h >= 3:
            _add(breakdown, "btc_pump_3pct_1h", opp_delta=25)
            opp += 25

    if signals.get("speed_of_fall_accelerating"):
        _add(breakdown, "speed_of_fall_accelerating", risk_delta=20)
        risk += 20

    funding = signals.get("funding_rate")
    if funding is not None:
        if funding > 0.0005:  # > 0.05%
            _add(breakdown, "funding_over_leveraged_long_strong", risk_delta=25)
            risk += 25
        elif funding > 0.0003:  # > 0.03%
            _add(breakdown, "funding_over_leveraged_long", risk_delta=15)
            risk += 15
        elif funding < -0.0003:  # < -0.03%
            _add(breakdown, "funding_short_squeeze_strong", opp_delta=25)
            opp += 25
        elif funding < -0.0001:  # < -0.01%
            _add(breakdown, "funding_short_squeeze", opp_delta=15)
            opp += 15

    risk = _clamp(risk)
    opp = _clamp(opp)
    return risk, opp, breakdown


def _add(breakdown: dict, name: str, risk_delta: int = 0, opp_delta: int = 0) -> None:
    breakdown[name] = {"risk": risk_delta, "opp": opp_delta}


def _clamp(v: int) -> int:
    if v < 0:
        return 0
    if v > 100:
        return 100
    return int(v)
