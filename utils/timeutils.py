"""Time helpers — single source for the project's UTC timestamp.

`datetime.utcnow()` is deprecated (Python 3.12+) and slated for removal.
The obvious replacement, `datetime.now(timezone.utc)`, returns a *tz-aware*
datetime — but this codebase is deliberately **naive-UTC**: bot timers
(`_last_trade_time`, `_stop_buy_activated_at`) are naive, and
`grid/state_manager.py` strips tzinfo off DB timestamps (`.replace(tzinfo=
None)`) precisely so subtractions/comparisons stay naive-vs-naive. Mixing a
tz-aware value into one of those subtractions raises TypeError.

So `utcnow()` here is a drop-in for the deprecated call: same naive-UTC
value, no deprecation warning. If the project ever migrates fully to
tz-aware datetimes, this is the one place to change (then fix the DB-replay
comparisons accordingly).
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC timestamp (tzinfo stripped). Drop-in for datetime.utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
