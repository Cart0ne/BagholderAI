"""NewsKeeper v2 barometer aggregator — PURE functions, NO I/O.

Turns ~109 per-item votes/day into ONE slow state. Everything here is a pure
function of its arguments so it is unit-testable without network or DB (brief
§6.4). The main loop pulls the last 24h of votes from Supabase and feeds them
in; nothing in this module touches Supabase, Anthropic, or the clock — `now`
is always passed in.

Pipeline (per tick):
  1. dedup_by_event_key   — same story = one vote (keystone of architecture C)
  2. raw_score            — confidence-weighted, decayed, normalized net tilt
                            in [-1, +1]; also reports abstain_frac (health)
  3. decide_state         — hysteresis state machine: the published state flips
                            only on a net+persistent imbalance, so the output
                            is slow despite a nervous input

Parameters are *initial guesses* (brief §5), frozen during shadow and tuned on
data only AFTER a regime change is observed (anti-assenso B: don't fit 3
interacting params to a mono-directional bear window).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# --------------------------------------------------------------------------
# Parameters (initial values — NOT tuned; see brief §5 + anti-assenso B)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class BarometerParams:
    # relevance -> weight in the climate vote. "discard" never votes.
    relevance_weights: dict = field(
        default_factory=lambda: {"high": 1.0, "medium": 0.5}
    )
    # a read below this confidence ABSTAINS (vote weight 0) — the safety net.
    min_confidence: float = 0.3
    # exponential decay: a vote loses half its weight every half_life_h hours.
    half_life_h: float = 10.0
    # rolling window: votes older than this don't count at all.
    window_h: float = 24.0
    # hysteresis bands on the normalized raw score (in [-1, +1]).
    # Asymmetry (recall-biased, brief §5): easier to ENTER bearish (-0.12 vs
    # +0.15) and stickier to LEAVE it (must climb back to -0.04 vs drop to
    # +0.05) — "enter the bear faster than you exit it".
    bull_enter: float = 0.15
    bull_exit: float = 0.05
    bear_enter: float = -0.12
    bear_exit: float = -0.04
    # the instantaneous target must persist this long before the published
    # state actually flips (the thermostat — no flip-flop). Entering bearish
    # uses a shorter persistence (recall bias): react to the mazzata sooner.
    persist_h: float = 6.0
    persist_bear_h: float = 4.0


DEFAULT_PARAMS = BarometerParams()

_STATES = ("bearish", "neutral", "bullish")


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------


def relevance_weight(relevance: Optional[str], params: BarometerParams) -> float:
    """Weight of an item's relevance bucket. 'discard'/unknown -> 0 (no vote)."""
    return float(params.relevance_weights.get(relevance or "", 0.0))


def decay_factor(age_seconds: float, half_life_h: float) -> float:
    """Exponential time decay in (0, 1]. age<=0 -> 1.0; older -> smaller."""
    if age_seconds <= 0:
        return 1.0
    if half_life_h <= 0:
        return 1.0
    age_h = age_seconds / 3600.0
    return 0.5 ** (age_h / half_life_h)


def _parse_ts(value) -> Optional[datetime]:
    """Accept a datetime or an ISO string (DB rows arrive as strings)."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _polarity(v: dict) -> int:
    """Read polarity as a clean int in {-1, 0, 1}; anything else -> 0."""
    try:
        p = int(v.get("polarity"))
    except (TypeError, ValueError):
        return 0
    return p if p in (-1, 0, 1) else 0


def _confidence(v: dict) -> float:
    try:
        c = float(v.get("confidence"))
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, c))


# --------------------------------------------------------------------------
# 1. Event-level dedup (keystone of architecture C)
# --------------------------------------------------------------------------


def dedup_by_event_key(
    votes: list[dict], now: datetime, params: BarometerParams = DEFAULT_PARAMS
) -> list[dict]:
    """Collapse votes that share an event_key to ONE representative vote.

    The same climate event (a Fed decision covered by 5 outlets across 3 days)
    must count once, not N times — otherwise a single mis-read story repeated
    by the feed could swing the aggregate (the risk CC flagged on architecture
    C). Votes with no event_key are kept as-is (each is its own event).

    The representative is the row that would contribute MOST to the current
    climate, ranked by `(in_window, directional, effective_weight)` where
    `effective_weight = relevance * confidence * decay(age)`. This is
    window/decay-aware ON PURPOSE: an in-window row always beats an
    out-of-window one (so a fresh read is never discarded in favour of a stale
    rep that raw_score then drops), and among in-window rows a fresh directional
    read beats a marginally-more-confident stale one (so dedup can't defeat the
    half-life decay). Direction outranks weight so a weak directional read still
    lets the event vote (recall bias) rather than being shadowed by a confident
    "neutral".
    """
    best: dict[str, dict] = {}
    best_rank: dict[str, tuple] = {}
    passthrough: list[dict] = []
    for v in votes:
        key = v.get("event_key")
        if not key:
            passthrough.append(v)
            continue
        rank = _dedup_rank(v, now, params)
        if key not in best or rank > best_rank[key]:
            best[key] = v
            best_rank[key] = rank
    return passthrough + list(best.values())


def _dedup_rank(v: dict, now: datetime, params: BarometerParams) -> tuple:
    """Sort key for picking the representative of an event_key collision.

    `in_window` mirrors raw_score's own filter (-1s tolerance .. horizon), so a
    representative chosen here can't be silently dropped there while a usable
    in-window row existed.
    """
    ts = _parse_ts(v.get("created_at"))
    if ts is None:
        return (0, 0, -1.0)  # unparseable timestamp -> lowest priority
    age = (now - ts).total_seconds()
    horizon = params.window_h * 3600.0
    in_window = 1 if (-1.0 <= age <= horizon) else 0
    directional = 1 if _polarity(v) != 0 else 0
    eff_weight = (
        relevance_weight(v.get("relevance"), params)
        * _confidence(v)
        * decay_factor(age, params.half_life_h)
    )
    return (in_window, directional, eff_weight)


# --------------------------------------------------------------------------
# 2. Raw score (confidence-weighted, decayed, normalized) + health metric
# --------------------------------------------------------------------------


@dataclass
class ScoreResult:
    raw_score: float          # net tilt in [-1, +1]
    vote_count: int           # directional votes that actually counted
    abstain_frac: float       # would-be directional reads silenced by low conf
    total_weight: float       # denominator (0 -> no directional info)


def raw_score(
    votes: list[dict], now: datetime, params: BarometerParams = DEFAULT_PARAMS
) -> ScoreResult:
    """Normalized net climate tilt from already-deduped votes.

    A vote counts toward direction only if: relevance is high/medium (not
    discard), polarity is +/-1 (not neutral), and confidence >= min_confidence
    (else it ABSTAINS — weight 0, the safety net). Each counting vote's weight
    is relevance_weight * confidence * decay(age). The score is the
    weight-normalized sum of (weight * polarity), so it stays in [-1, +1]
    regardless of news volume.

    `abstain_frac` is the share of would-be directional reads (relevant +
    non-neutral) that were silenced by low confidence — the health metric for
    "is the barometer slow, or mute?" (anti-assenso A).
    """
    num = 0.0
    den = 0.0
    counted = 0
    would_vote = 0
    abstained = 0
    horizon = params.window_h * 3600.0

    for v in votes:
        w_rel = relevance_weight(v.get("relevance"), params)
        if w_rel <= 0:
            continue  # discard / unknown relevance never votes
        pol = _polarity(v)
        if pol == 0:
            continue  # neutral reads don't move direction
        ts = _parse_ts(v.get("created_at"))
        if ts is None:
            continue
        age = (now - ts).total_seconds()
        if age > horizon or age < -1.0:
            continue  # outside the window (small negative tolerated for clock skew)

        would_vote += 1
        conf = _confidence(v)
        if conf < params.min_confidence:
            abstained += 1
            continue  # ABSTAIN: counts toward abstain_frac, not toward score

        w = w_rel * conf * decay_factor(age, params.half_life_h)
        if w <= 0:
            continue
        num += w * pol
        den += w
        counted += 1

    score = (num / den) if den > 0 else 0.0
    abstain_frac = (abstained / would_vote) if would_vote else 0.0
    return ScoreResult(
        raw_score=round(score, 4),
        vote_count=counted,
        abstain_frac=round(abstain_frac, 3),
        total_weight=round(den, 4),
    )


# --------------------------------------------------------------------------
# 3. Hysteresis state machine
# --------------------------------------------------------------------------


def target_instant(raw: float, current: str, params: BarometerParams) -> str:
    """Which state the raw score argues for RIGHT NOW, given hysteresis.

    Enter/exit thresholds differ (that IS the hysteresis): once in a state you
    stay until the score crosses back past the (closer-to-zero) exit band, so
    a value wobbling around a single threshold doesn't flip-flop.
    """
    if current == "bullish":
        if raw <= params.bear_enter:
            return "bearish"
        if raw < params.bull_exit:
            return "neutral"
        return "bullish"
    if current == "bearish":
        if raw >= params.bull_enter:
            return "bullish"
        if raw > params.bear_exit:
            return "neutral"
        return "bearish"
    # neutral
    if raw >= params.bull_enter:
        return "bullish"
    if raw <= params.bear_enter:
        return "bearish"
    return "neutral"


def _persist_seconds(target: str, params: BarometerParams) -> float:
    """Persistence required before committing a flip TO `target`."""
    h = params.persist_bear_h if target == "bearish" else params.persist_h
    return h * 3600.0


@dataclass
class StateDecision:
    state: str                      # the (possibly new) PUBLISHED state
    pending: Optional[str]          # a flip waiting to clear persistence
    pending_since: Optional[datetime]
    flipped: bool                   # True iff `state` changed this tick


def decide_state(
    current: str,
    pending: Optional[str],
    pending_since: Optional[datetime],
    raw: float,
    now: datetime,
    params: BarometerParams = DEFAULT_PARAMS,
) -> StateDecision:
    """Advance the hysteresis machine by one tick. Pure: the caller persists
    (state, pending, pending_since) across ticks and reloads them at boot.

    A flip to a new state requires the instantaneous target to differ from the
    published state AND hold continuously for the target's persistence window.
    The moment the target stops differing (score falls back), the pending flip
    is cancelled — so a brief spike never commits.
    """
    if current not in _STATES:
        current = "neutral"
    inst = target_instant(raw, current, params)

    if inst == current:
        return StateDecision(current, None, None, False)  # nothing pending

    # inst differs from the published state -> a flip is being considered.
    if pending == inst and pending_since is not None:
        if (now - pending_since).total_seconds() >= _persist_seconds(inst, params):
            return StateDecision(inst, None, None, True)  # committed flip
        return StateDecision(current, pending, pending_since, False)  # still waiting

    # a new (or changed) pending target: (re)start the persistence clock.
    return StateDecision(current, inst, now, False)


# --------------------------------------------------------------------------
# Orchestration (still pure: all inputs passed in)
# --------------------------------------------------------------------------


@dataclass
class BarometerResult:
    score: ScoreResult
    decision: StateDecision


def compute(
    votes: list[dict],
    now: datetime,
    current: str,
    pending: Optional[str],
    pending_since: Optional[datetime],
    params: BarometerParams = DEFAULT_PARAMS,
) -> BarometerResult:
    """Full barometer tick: dedup -> score -> hysteresis. Pure."""
    deduped = dedup_by_event_key(votes, now, params)
    score = raw_score(deduped, now, params)
    decision = decide_state(current, pending, pending_since, score.raw_score, now, params)
    return BarometerResult(score=score, decision=decision)
