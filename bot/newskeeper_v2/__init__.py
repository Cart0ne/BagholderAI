"""NewsKeeper v2 — "Barometro" (S100, brief newskeeper-v2-barometro).

NewsKeeper stops being a per-item news classifier and becomes a slow,
bidirectional **market-climate barometer**: one state (bearish / neutral /
bullish) aggregated from the last 24h of news, published with hysteresis so
the output is slow even though the input is nervous.

Runs STANDALONE on the Mac Mini, IN SHADOW, alongside v1 (`bot.newskeeper`):
it never feeds Sentinel and never stops v1. It earns a place in Sentinel only
if ~2 weeks of shadow data show its flips lead the *price* (not the Fear &
Greed, which would be circular). See the brief for the falsifiable gate.

Design decisions baked in (Board, S100):
  - Architecture "C": Haiku reads the MEANING and decides polarity. The Python
    lexicon (preprocessor) has NO veto — it survives only as a logged
    `direction_conflict` audit sensor.
  - Confidence-weighted vote: a low-confidence read abstains (weight 0) rather
    than voting full. The safety net, without re-coupling Python<->Haiku.
  - Event-level dedup: the same story across feeds/days = one vote, not N.
    The keystone that makes "C" safe (errors can't be amplified by repetition).
"""
