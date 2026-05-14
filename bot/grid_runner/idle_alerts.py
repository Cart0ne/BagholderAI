"""Idle re-entry / recalibrate Telegram alerts.

The Grid bot exposes `bot.idle_reentry_alerts`: a per-tick list populated
by grid_bot when an idle threshold fires (re-entry → reset reference,
recalibrate → ladder reset). This module renders and sends those alerts.

Refactor S76 (2026-05-14): extracted from grid_runner.py main loop.
Target for the upcoming idle-suppression audit (post-75b): when the
stop-buy unlock timer is armed, these alerts become noise (bot is
blocked for a structural reason, not for lack of opportunity). The
suppression policy will live here, not in the dispatcher.
"""

from utils.formatting import fmt_price


def send_idle_alerts(notifier, alerts) -> None:
    """Render and send each idle alert via Telegram.

    Args:
        notifier: SyncTelegramNotifier instance (or stub with send_message).
        alerts: iterable from bot.idle_reentry_alerts. Each item is a dict
            with keys: symbol, elapsed_hours, reference_price, recalibrate.
    """
    for alert in alerts:
        sym = alert["symbol"]
        base = sym.split("/")[0] if "/" in sym else sym
        if alert.get("recalibrate"):
            notifier.send_message(
                f"🔄 <b>IDLE RECALIBRATE: {base}</b>\n"
                f"After {alert['elapsed_hours']:.1f}h idle, buy reference reset to "
                f"{fmt_price(alert['reference_price'])}\n"
                f"Holdings still open — waiting for next buy signal."
            )
        else:
            notifier.send_message(
                f"⏰ <b>IDLE RE-ENTRY: {base}</b>\n"
                f"After {alert['elapsed_hours']:.1f}h idle, new reference: "
                f"{fmt_price(alert['reference_price'])}"
            )
