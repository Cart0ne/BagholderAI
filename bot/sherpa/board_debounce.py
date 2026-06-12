"""Sherpa Board-parameter debounce (Board decision 2026-06-12, on top of
Brief S103a).

The four protective params are written with no amplitude cap, so a
(regime, tier) that sits on a boundary and flips would rewrite them sharply.
This module adds a dwell/confirmation: a newly observed (regime, tier) must
persist continuously for BOARD_DEBOUNCE_HOURS before Sherpa adopts it as the
*effective* target. A coin's FIRST classification (no prior state) is adopted
immediately — the debounce only gates subsequent changes of a live coin.

Why dwell on the resolved (regime, tier) and not on each axis separately:
the flapping risk is on BOTH the tier axis (hourly volatility multiplier) and
the regime axis (a Fear&Greed value hugging a band boundary). Confirming the
combined pair covers both with one rule.

The state lives in the sherpa_board_state table (one row per symbol) so the
timer survives orchestrator restarts. decide() itself is pure: given the
current state row + the observed (regime, tier) + now, it returns the new
effective (regime, tier) and the next state row (or None when unchanged). The
Sherpa loop does the DB read/upsert around it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class BoardDecision:
    effective_regime: str
    effective_tier: str
    new_state: Optional[dict]   # row to upsert, or None when nothing changed
    state_changed: bool
    adopted_now: bool           # True when effective just moved (or first set)


def _parse_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _adopt(regime: str, tier: str) -> dict:
    return {
        "effective_regime": regime,
        "effective_tier": tier,
        "candidate_regime": None,
        "candidate_tier": None,
        "candidate_since": None,
    }


def decide(
    state_row: Optional[dict],
    observed_regime: str,
    observed_tier: str,
    now: datetime,
    debounce_hours: float,
) -> BoardDecision:
    """Pure debounce transition — see module docstring.

    state_row keys (all optional): effective_regime, effective_tier,
    candidate_regime, candidate_tier, candidate_since.
    """
    obs = (observed_regime, observed_tier)

    # First classification ever -> adopt immediately.
    if not state_row or not state_row.get("effective_regime"):
        return BoardDecision(
            observed_regime, observed_tier,
            _adopt(observed_regime, observed_tier), True, True,
        )

    eff = (state_row["effective_regime"], state_row["effective_tier"])

    # Observed matches what we already enforce -> in sync. Clear any pending
    # candidate (a flap that came back home before maturing).
    if obs == eff:
        if state_row.get("candidate_regime"):
            return BoardDecision(eff[0], eff[1], _adopt(eff[0], eff[1]), True, False)
        return BoardDecision(eff[0], eff[1], None, False, False)

    # Observed differs from effective. Is it the candidate we're already timing?
    cand = (
        (state_row.get("candidate_regime"), state_row.get("candidate_tier"))
        if state_row.get("candidate_regime") else None
    )
    if cand == obs:
        since = _parse_dt(state_row.get("candidate_since"))
        mature = since is not None and \
            (now - since).total_seconds() >= debounce_hours * 3600
        if mature:
            return BoardDecision(
                observed_regime, observed_tier,
                _adopt(observed_regime, observed_tier), True, True,
            )
        # Still waiting -> keep enforcing the old effective, no state change.
        return BoardDecision(eff[0], eff[1], None, False, False)

    # A fresh candidate (different from both effective and the previous
    # candidate) -> start its timer, keep enforcing the old effective.
    new = {
        "effective_regime": eff[0],
        "effective_tier": eff[1],
        "candidate_regime": observed_regime,
        "candidate_tier": observed_tier,
        "candidate_since": now.isoformat(),
    }
    return BoardDecision(eff[0], eff[1], new, True, False)
