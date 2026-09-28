"""S131a (Board S131, 2026-09-28): dead zone as an explicit rule.

- Sherpa table: dead_zone_hours 0 (= off) in neutral / greed / extreme_greed,
  1h fear, 2h extreme_fear; where it is on it must come due before the idle
  recalibrate, or it is inert again (the S129 bug).
- Grid: dead_zone_hours <= 0 never fires, not even after a restart with an old
  _last_trade_time; when it fires it clears the ladder but not the buy
  reference (D2).
- config_sync: "dead zone inert" warning logged once per change.
- Telegram: the dead-zone message no longer claims a buy-reference reset.
"""

import os
import sys
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.timeutils import utcnow
from test_accounting_avg_cost import make_bot


def _bot_stuck_above_avg(dead_zone_hours: float, idle_hours: float, hours_since_trade: float):
    """Position at avg $100, ladder anchored at $104, price $102 (between avg and ladder)."""
    bot = make_bot()
    bot.managed_by = "grid"
    bot.is_active = True
    bot.buy_pct = 99.0
    bot.sell_pct = 2.0
    bot.idle_reentry_hours = idle_hours
    bot.dead_zone_hours = dead_zone_hours
    bot._execute_percentage_buy(price=100.0)
    bot._last_sell_price = 104.0
    bot._last_trade_time = utcnow() - timedelta(hours=hours_since_trade)
    return bot


def test_board_table_dead_zone_by_regime():
    from bot.sherpa.board_parameter_rules import BOARD_TABLE
    expected = {"extreme_fear": 2, "fear": 1, "neutral": 0, "greed": 0, "extreme_greed": 0}
    for regime, dz in expected.items():
        for tier, row in BOARD_TABLE[regime].items():
            assert row["dead_zone_hours"] == dz, (regime, tier, row["dead_zone_hours"])


def test_enabled_dead_zone_comes_due_before_idle():
    """Where the dead zone is on, it must not be longer than the idle
    recalibrate of the same regime, or the idle resets the shared clock first."""
    from bot.sherpa.board_parameter_rules import BOARD_TABLE
    from bot.sherpa.parameter_rules import BASE_TABLE
    for regime, tiers in BOARD_TABLE.items():
        idle = BASE_TABLE[regime]["idle_reentry_hours"]
        for tier, row in tiers.items():
            dz = row["dead_zone_hours"]
            if dz > 0:
                assert dz <= idle, f"{regime}/{tier}: dead zone {dz}h > idle {idle}h → inert"


def test_zero_never_fires_even_after_restart():
    """Greed after a restart: _last_trade_time is 30 days old, ladder active,
    price above avg. With dead_zone_hours = 0 nothing happens (before S131a
    this was exactly the boot-time sale of 26-27 Sep)."""
    bot = _bot_stuck_above_avg(dead_zone_hours=0.0, idle_hours=24.0 * 60, hours_since_trade=24 * 30)
    ref_before = bot._pct_last_buy_price
    trades = bot.check_price_and_execute(current_price=102.0)
    assert trades == []
    assert bot._last_sell_price == 104.0, "ladder must stay active"
    assert bot._pct_last_buy_price == ref_before
    assert not [a for a in bot.idle_reentry_alerts if a.get("dead_zone")]
    assert bot._skip_next_decision is False


def test_positive_dead_zone_fires_and_keeps_buy_reference():
    """Fear: dead zone 1h, idle 2h, 1.5h without trades → reset fires,
    ladder cleared, buy reference unchanged (D2)."""
    bot = _bot_stuck_above_avg(dead_zone_hours=1.0, idle_hours=2.0, hours_since_trade=1.5)
    ref_before = bot._pct_last_buy_price
    with patch("bot.grid.grid_bot.log_event"):   # no TEST rows in the production events table
        trades = bot.check_price_and_execute(current_price=102.0)
    assert trades == []
    assert bot._last_sell_price == 0.0
    assert bot._pct_last_buy_price == ref_before
    alerts = [a for a in bot.idle_reentry_alerts if a.get("dead_zone")]
    assert len(alerts) == 1 and alerts[0]["reference_price"] == ref_before


def test_inert_warning_logged_once_per_change():
    from bot.grid_runner.config_sync import _check_dead_zone_inert
    bot = SimpleNamespace(dead_zone_hours=2.0, idle_reentry_hours=0.75)
    with patch("db.event_logger.log_event") as log_event:
        _check_dead_zone_inert(bot, "TEST/USD")
        _check_dead_zone_inert(bot, "TEST/USD")
        assert log_event.call_count == 1, "inert → one warning, not one per tick"
        bot.idle_reentry_hours = 2.0          # dead zone now comes first → fine
        _check_dead_zone_inert(bot, "TEST/USD")
        bot.dead_zone_hours, bot.idle_reentry_hours = 0.0, 0.75   # off by choice
        _check_dead_zone_inert(bot, "TEST/USD")
        assert log_event.call_count == 1
        bot.dead_zone_hours = 3.0             # inert again → new warning
        _check_dead_zone_inert(bot, "TEST/USD")
        assert log_event.call_count == 2
        assert log_event.call_args.kwargs["event"] == "dead_zone_inert"


def test_telegram_dead_zone_message_keeps_reference():
    from bot.grid_runner.idle_alerts import send_idle_alerts

    class Notifier:
        def __init__(self):
            self.sent = []

        def send_message(self, text):
            self.sent.append(text)

    n = Notifier()
    send_idle_alerts(n, [{"symbol": "BTC/USD", "elapsed_hours": 2.5, "reference_price": 76000.0,
                          "recalibrate": True, "dead_zone": True}])
    assert len(n.sent) == 1
    assert "DEAD ZONE" in n.sent[0] and "unchanged" in n.sent[0]
    assert "reset to" not in n.sent[0]
