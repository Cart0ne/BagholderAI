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
        # Brief 70b (S70 2026-05-10): aggiunto step granulare -2/-1/-0.5
        # per granularità su mercati laterali (range BTC ±1% nel dataset
        # 6-8 maggio = vecchia ladder cieca → risk fisso a 20).
        if change_1h <= -10:
            _add(breakdown, "btc_drop_10pct_1h", risk_delta=80)
            risk += 80
        elif change_1h <= -5:
            _add(breakdown, "btc_drop_5pct_1h", risk_delta=50)
            risk += 50
        elif change_1h <= -3:
            _add(breakdown, "btc_drop_3pct_1h", risk_delta=30)
            risk += 30
        elif change_1h <= -2:
            _add(breakdown, "btc_drop_2pct_1h", risk_delta=20)
            risk += 20
        elif change_1h <= -1:
            _add(breakdown, "btc_drop_1pct_1h", risk_delta=12)
            risk += 12
        elif change_1h <= -0.5:
            _add(breakdown, "btc_drop_0_5pct_1h", risk_delta=6)
            risk += 6
        # Pump ladder, opportunity side (granularità simmetrica).
        elif change_1h >= 5:
            _add(breakdown, "btc_pump_5pct_1h", opp_delta=40)
            opp += 40
        elif change_1h >= 3:
            _add(breakdown, "btc_pump_3pct_1h", opp_delta=25)
            opp += 25
        elif change_1h >= 2:
            _add(breakdown, "btc_pump_2pct_1h", opp_delta=15)
            opp += 15
        elif change_1h >= 1:
            _add(breakdown, "btc_pump_1pct_1h", opp_delta=10)
            opp += 10
        elif change_1h >= 0.5:
            _add(breakdown, "btc_pump_0_5pct_1h", opp_delta=5)
            opp += 5

    if signals.get("speed_of_fall_accelerating"):
        _add(breakdown, "speed_of_fall_accelerating", risk_delta=20)
        risk += 20

    funding = signals.get("funding_rate")
    if funding is not None:
        # Brief 70b (S70): aggiunto step granulare per dataset testnet
        # con funding range osservato ±0.00007 (1 ordine di grandezza
        # sotto le soglie originali). Soglie 0.0003/0.0005 restano per
        # mainnet con funding tipico 0.01-0.03%.
        if funding > 0.0005:  # > 0.05%
            _add(breakdown, "funding_over_leveraged_long_strong", risk_delta=25)
            risk += 25
        elif funding > 0.0003:  # > 0.03%
            _add(breakdown, "funding_over_leveraged_long", risk_delta=15)
            risk += 15
        elif funding > 0.0002:  # > 0.02%
            _add(breakdown, "funding_long_mild", risk_delta=8)
            risk += 8
        elif funding > 0.0001:  # > 0.01%
            _add(breakdown, "funding_long_weak", risk_delta=4)
            risk += 4
        elif funding < -0.0003:  # < -0.03%
            _add(breakdown, "funding_short_squeeze_strong", opp_delta=25)
            opp += 25
        elif funding < -0.0001:  # < -0.01%
            _add(breakdown, "funding_short_squeeze", opp_delta=15)
            opp += 15
        elif funding < -0.00005:  # < -0.005%
            _add(breakdown, "funding_short_mild", opp_delta=8)
            opp += 8
        elif funding < -0.00002:  # < -0.002%
            _add(breakdown, "funding_short_weak", opp_delta=4)
            opp += 4

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
