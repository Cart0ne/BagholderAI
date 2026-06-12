"""Sherpa Board-parameter table (Brief S103a, S103 2026-06-12).

The four protective parameters
    stop_buy_drawdown_pct, stop_buy_unlock_hours, dead_zone_hours,
    profit_target_pct
moved from Board-only/static to Sherpa-managed (decision Board S103, the
ownership principle "Board = money, Sherpa = everything else"). Unlike the
three strategy params (buy_pct/sell_pct/idle_reentry_hours), these are
discrete integers and do not scale continuously with volatility — so instead
of base x multiplier they use a discrete (regime x volatility-tier) lookup.

A coin's tier comes from its volatility multiplier (BTC anchor = 1.0, the same
number computed by bot/sherpa/volatility.py):
    LOW  : mult < BOARD_TIER_LOW_MAX             (BTC-like, ~1.0)
    MID  : LOW_MAX <= mult < BOARD_TIER_HIGH_MIN (SOL-like, ~1.53)
    HIGH : mult >= BOARD_TIER_HIGH_MIN           (BONK-like, ~1.75)

No amplitude cap and no clamp here: the values are already small integers in a
sensible range, and a +/-30% cap on an integer would be noise (brief). The
cliff at a tier boundary is smoothed instead by a *debounce* on the resolved
(regime, tier) — see bot/sherpa/board_debounce.py — a safeguard the Board
added on top of the brief so a boundary-hugging coin doesn't rewrite its
safety params as its multiplier wiggles hour to hour.

profit_target_pct is 0 in every cell: today sell_pct is the sole profit
threshold. The column is kept for completeness and for future activation
without a refactor (brief).
"""

from __future__ import annotations

from config.settings import HardcodedRules

# Column names match bot_config exactly so the values can be written through
# config_writer without translation.
BOARD_PARAM_KEYS = (
    "stop_buy_drawdown_pct",
    "stop_buy_unlock_hours",
    "dead_zone_hours",
    "profit_target_pct",
)

TIERS = ("LOW", "MID", "HIGH")
DEFAULT_REGIME = "neutral"
DEFAULT_TIER = "MID"


def _row(dd: float, unlock: float, dz: float, mp: float) -> dict[str, float]:
    """Brief BOARD_TABLE cell, in brief order:
    stop_buy_dd / stop_buy_unlock_h / dead_zone_h / min_profit."""
    return {
        "stop_buy_drawdown_pct": dd,
        "stop_buy_unlock_hours": unlock,
        "dead_zone_hours": dz,
        "profit_target_pct": mp,
    }


# (regime, tier) -> {4 params}. Source: Brief S103a BOARD_TABLE.
BOARD_TABLE: dict[str, dict[str, dict[str, float]]] = {
    "extreme_fear":  {"LOW": _row(3, 12, 2, 0), "MID": _row(4, 12, 2, 0), "HIGH": _row(5, 12, 2, 0)},
    "fear":          {"LOW": _row(4, 6, 1, 0),  "MID": _row(5, 6, 1, 0),  "HIGH": _row(6, 6, 1, 0)},
    "neutral":       {"LOW": _row(1, 2, 2, 0),  "MID": _row(2, 2, 2, 0),  "HIGH": _row(2, 1, 2, 0)},
    "greed":         {"LOW": _row(1, 2, 2, 0),  "MID": _row(1, 2, 2, 0),  "HIGH": _row(1, 1, 2, 0)},
    "extreme_greed": {"LOW": _row(1, 2, 3, 0),  "MID": _row(1, 2, 3, 0),  "HIGH": _row(1, 1, 3, 0)},
}


def classify_tier(volatility_multiplier: float) -> str:
    """Map a per-coin volatility multiplier to LOW/MID/HIGH using the
    boundaries in settings (midpoints between the three live coins)."""
    m = float(volatility_multiplier)
    if m < HardcodedRules.BOARD_TIER_LOW_MAX:
        return "LOW"
    if m < HardcodedRules.BOARD_TIER_HIGH_MIN:
        return "MID"
    return "HIGH"


def board_values_for(regime: str, tier: str) -> dict[str, float]:
    """Lookup the 4 protective params for a resolved (regime, tier).
    Unknown regime falls back to neutral; unknown tier falls back to MID."""
    r = regime if regime in BOARD_TABLE else DEFAULT_REGIME
    t = tier if tier in TIERS else DEFAULT_TIER
    return dict(BOARD_TABLE[r][t])


def calculate_board_parameters(
    regime: str, volatility_multiplier: float
) -> tuple[dict[str, float], str]:
    """Instantaneous lookup: classify the multiplier into a tier, then read
    the table. Returns (values, tier). No debounce here — the debounce gates
    the LIVE write (board_debounce.py + the Sherpa loop), not the table read.
    """
    tier = classify_tier(volatility_multiplier)
    return board_values_for(regime, tier), tier
