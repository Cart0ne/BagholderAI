"""NewsKeeper v2 "Barometro" unit tests (offline, no network/DB).

Covers the pure layers (brief §6.4):
  - aggregator: relevance_weight, decay, event-key dedup, raw_score (incl. the
    confidence abstain net), hysteresis (target_instant + decide_state).
  - classifier.sanitize: architecture C — Haiku's polarity is preserved even
    when the Python lexicon disagrees (THE fix to the S100 review's #1 bug);
    Python disagreement is logged as direction_conflict, never an override.

Run:
    pytest tests/test_newskeeper_v2.py
"""

from datetime import datetime, timedelta, timezone

from bot.newskeeper_v2 import aggregator as agg
from bot.newskeeper_v2.aggregator import BarometerParams
from bot.newskeeper_v2.classifier import sanitize, _clean_event_key

P = agg.DEFAULT_PARAMS
NOW = datetime(2026, 6, 9, 12, 0, 0, tzinfo=timezone.utc)


def _vote(polarity, relevance="high", confidence=0.9, event_key=None, age_h=0.0):
    return {
        "polarity": polarity,
        "relevance": relevance,
        "confidence": confidence,
        "event_key": event_key,
        "created_at": NOW - timedelta(hours=age_h),
    }


# ----------------------------------------------------------------------
# primitives
# ----------------------------------------------------------------------

def test_relevance_weight():
    assert agg.relevance_weight("high", P) == 1.0
    assert agg.relevance_weight("medium", P) == 0.5
    assert agg.relevance_weight("discard", P) == 0.0
    assert agg.relevance_weight(None, P) == 0.0


def test_decay_factor():
    assert agg.decay_factor(0, 10) == 1.0
    assert abs(agg.decay_factor(10 * 3600, 10) - 0.5) < 1e-9   # one half-life
    assert agg.decay_factor(20 * 3600, 10) < agg.decay_factor(10 * 3600, 10)


# ----------------------------------------------------------------------
# event-level dedup (keystone of architecture C)
# ----------------------------------------------------------------------

def test_dedup_collapses_same_event_key_to_one_vote():
    votes = [
        _vote(-1, event_key="FED|rate_signal", age_h=0),
        _vote(-1, event_key="FED|rate_signal", age_h=1),
        _vote(-1, event_key="FED|rate_signal", age_h=2),
    ]
    assert len(agg.dedup_by_event_key(votes, NOW, P)) == 1


def test_dedup_keeps_higher_relevance_representative():
    votes = [
        _vote(0, relevance="medium", event_key="BTC|price_move"),
        _vote(-1, relevance="high", event_key="BTC|price_move"),
    ]
    kept = agg.dedup_by_event_key(votes, NOW, P)
    assert len(kept) == 1
    assert kept[0]["relevance"] == "high" and kept[0]["polarity"] == -1


def test_dedup_prefers_directional_over_neutral_on_tie():
    votes = [
        _vote(0, relevance="high", confidence=0.9, event_key="MACRO|inflation_print"),
        _vote(-1, relevance="high", confidence=0.9, event_key="MACRO|inflation_print"),
    ]
    kept = agg.dedup_by_event_key(votes, NOW, P)
    assert kept[0]["polarity"] == -1


def test_dedup_keeps_keyless_votes_separate():
    votes = [_vote(-1, event_key=None), _vote(1, event_key=None)]
    assert len(agg.dedup_by_event_key(votes, NOW, P)) == 2


def test_dedup_prefers_in_window_over_stale_rep_mode1_regression():
    # review finding mode 1: a just-out-of-window high-conf row must NOT win
    # the rep slot and get the event dropped while a fresh in-window read exists.
    votes = [
        _vote(-1, confidence=0.95, event_key="K", age_h=24.05),  # out of 24h window
        _vote(-1, confidence=0.40, event_key="K", age_h=2.0),    # fresh, in-window
    ]
    deduped = agg.dedup_by_event_key(votes, NOW, P)
    r = agg.raw_score(deduped, NOW, P)
    assert r.vote_count == 1 and r.raw_score == -1.0   # event counts, not lost


def test_dedup_fresh_beats_stale_higher_conf_mode2_regression():
    # review finding mode 2: a fresh read must beat a marginally-more-confident
    # stale one, so dedup can't defeat the half-life decay.
    votes = [
        _vote(-1, confidence=0.90, event_key="K", age_h=23.0),   # stale, slightly higher conf
        _vote(-1, confidence=0.85, event_key="K", age_h=0.5),    # fresh
    ]
    kept = [v for v in agg.dedup_by_event_key(votes, NOW, P) if v["event_key"] == "K"]
    assert len(kept) == 1 and kept[0]["confidence"] == 0.85      # the fresh one survives


# ----------------------------------------------------------------------
# raw_score + the confidence abstain net
# ----------------------------------------------------------------------

def test_raw_score_all_bearish_is_minus_one():
    votes = [_vote(-1, event_key=f"k{i}") for i in range(5)]
    r = agg.raw_score(votes, NOW, P)
    assert r.raw_score == -1.0 and r.vote_count == 5 and r.abstain_frac == 0.0


def test_raw_score_all_bullish_is_plus_one():
    votes = [_vote(1, event_key=f"k{i}") for i in range(4)]
    assert agg.raw_score(votes, NOW, P).raw_score == 1.0


def test_raw_score_balanced_is_zero():
    votes = [_vote(1, event_key="a"), _vote(-1, event_key="b")]
    assert agg.raw_score(votes, NOW, P).raw_score == 0.0


def test_low_confidence_abstains_and_is_counted_in_abstain_frac():
    votes = [
        _vote(-1, confidence=0.9, event_key="a"),   # counts
        _vote(-1, confidence=0.1, event_key="b"),   # abstains (conf < 0.3)
    ]
    r = agg.raw_score(votes, NOW, P)
    assert r.vote_count == 1                 # only the confident one scored
    assert r.raw_score == -1.0               # abstainer didn't dilute
    assert r.abstain_frac == 0.5             # but it IS in the health metric


def test_discard_and_neutral_do_not_vote():
    votes = [
        _vote(-1, relevance="discard", event_key="a"),  # discard -> no vote
        _vote(0, relevance="high", event_key="b"),       # neutral -> no vote
    ]
    r = agg.raw_score(votes, NOW, P)
    assert r.vote_count == 0 and r.raw_score == 0.0


def test_out_of_window_votes_excluded():
    votes = [_vote(-1, age_h=30, event_key="old")]   # window_h = 24
    assert agg.raw_score(votes, NOW, P).vote_count == 0


def test_decay_makes_recent_news_dominate():
    # recent bullish vs old bearish -> the fresh one wins
    votes = [
        _vote(1, age_h=0, event_key="fresh"),
        _vote(-1, age_h=20, event_key="stale"),
    ]
    assert agg.raw_score(votes, NOW, P).raw_score > 0


# ----------------------------------------------------------------------
# hysteresis: target_instant
# ----------------------------------------------------------------------

def test_target_instant_neutral_bands():
    assert agg.target_instant(0.20, "neutral", P) == "bullish"    # >= +0.15
    assert agg.target_instant(-0.20, "neutral", P) == "bearish"   # <= -0.12
    assert agg.target_instant(0.05, "neutral", P) == "neutral"    # inside band


def test_target_instant_sticky_once_in_state():
    # in bullish, a small dip to +0.08 stays bullish (above bull_exit 0.05)
    assert agg.target_instant(0.08, "bullish", P) == "bullish"
    # drops below exit -> back to neutral
    assert agg.target_instant(0.02, "bullish", P) == "neutral"
    # in bearish, must climb past bear_exit (-0.04) to leave
    assert agg.target_instant(-0.06, "bearish", P) == "bearish"
    assert agg.target_instant(-0.02, "bearish", P) == "neutral"


# ----------------------------------------------------------------------
# hysteresis: decide_state (persistence)
# ----------------------------------------------------------------------

def test_no_flip_when_target_equals_current():
    d = agg.decide_state("neutral", None, None, 0.01, NOW, P)
    assert d.state == "neutral" and d.flipped is False and d.pending is None


def test_pending_starts_then_commits_after_persistence():
    # tick 1: raw argues bearish -> pending starts (persist_bear_h = 4h)
    d1 = agg.decide_state("neutral", None, None, -0.20, NOW, P)
    assert d1.flipped is False and d1.pending == "bearish"
    # tick 2: still bearish but only 3h later -> not yet
    d2 = agg.decide_state(
        "neutral", d1.pending, d1.pending_since, -0.20, NOW + timedelta(hours=3), P
    )
    assert d2.flipped is False and d2.state == "neutral"
    # tick 3: 4h+ -> commit
    d3 = agg.decide_state(
        "neutral", d2.pending, d2.pending_since, -0.20, NOW + timedelta(hours=4), P
    )
    assert d3.flipped is True and d3.state == "bearish"


def test_brief_spike_does_not_commit():
    d1 = agg.decide_state("neutral", None, None, -0.20, NOW, P)        # pending bear
    # next tick the score recovered into the neutral band -> pending cancelled
    d2 = agg.decide_state(
        "neutral", d1.pending, d1.pending_since, 0.00, NOW + timedelta(hours=1), P
    )
    assert d2.pending is None and d2.flipped is False


def test_bear_persistence_shorter_than_bull():
    # entering bear commits at 4h; entering bull would still be pending at 4h
    db = agg.decide_state("neutral", "bearish", NOW, -0.20, NOW + timedelta(hours=4), P)
    dbull = agg.decide_state("neutral", "bullish", NOW, 0.20, NOW + timedelta(hours=4), P)
    assert db.flipped is True
    assert dbull.flipped is False  # persist_h = 6h for bull


# ----------------------------------------------------------------------
# classifier.sanitize — architecture C (THE S100 fix)
# ----------------------------------------------------------------------

def _env(direction="mixed", content_type="article"):
    return {"direction": direction, "content_type": content_type,
            "title": "t", "entities": ["BTC"]}


def test_sanitize_preserves_haiku_polarity_against_lexicon_S100_regression():
    # The lexicon said "up" (e.g. "inflation JUMPS 6%"); Haiku correctly read
    # it as bearish (-1). Architecture C: Haiku wins, lexicon does NOT override.
    haiku = {"relevance": "high", "polarity": -1, "event_key": "MACRO|inflation_print",
             "confidence": 0.9, "reasoning": "rising inflation is bearish for risk"}
    out = sanitize(_env(direction="up"), haiku)
    assert out["polarity"] == -1                  # NOT flipped to +1
    assert out["direction_conflict"] is True      # disagreement logged, not acted on
    assert out["classifier_version"] == "barometro_v1"


def test_sanitize_clamps_and_defaults():
    out = sanitize(_env(), {"relevance": "banana", "polarity": 7,
                            "confidence": "x", "event_key": "nope"})
    assert out["relevance"] == "discard"
    assert out["polarity"] == 0
    assert out["confidence"] == 0.0
    assert out["event_key"] == "MISC|misc"


def test_sanitize_video_forced_to_discard():
    haiku = {"relevance": "high", "polarity": -1, "event_key": "BTC|price_move",
             "confidence": 0.9}
    out = sanitize(_env(content_type="video"), haiku)
    assert out["relevance"] == "discard"          # structural guardrail
    assert out["polarity"] == -1                  # but polarity untouched


def test_clean_event_key():
    assert _clean_event_key("FED|rate_signal") == "FED|rate_signal"
    assert _clean_event_key("btc|ETF_FLOW") == "BTC|etf_flow"
    assert _clean_event_key("garbage") == "MISC|misc"
    assert _clean_event_key("XXX|yyy") == "MISC|misc"
    assert _clean_event_key(None) == "MISC|misc"
