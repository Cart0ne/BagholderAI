"""Idle re-entry / recalibrate Telegram alerts.

The Grid bot exposes `bot.idle_reentry_alerts`: a per-tick list populated
by grid_bot when an idle threshold fires (re-entry → reset reference,
recalibrate → ladder reset). This module renders and sends those alerts.

Refactor S76 (2026-05-14): extracted from grid_runner.py main loop.
Suppression policy (audit S76 post-75b): when the bot's `_stop_buy_active`
flag is set, these alerts are noise — the bot is blocked for a structural
reason (drawdown > stop_buy_drawdown_pct), not for lack of opportunity.
The recalibrate still executes in-memory (logger + log_event capture it
for audit); only the Telegram noise is suppressed. The unlock-timer flow
(brief 75b) or a profitable sell will re-emit a clear "buys re-enabled"
message via the stop-buy reset paths.
"""

from utils.formatting import fmt_price


def send_idle_alerts(notifier, alerts, stop_buy_active: bool = False) -> None:
    """Render and send each idle alert via Telegram.

    Args:
        notifier: SyncTelegramNotifier instance (or stub with send_message).
        alerts: iterable from bot.idle_reentry_alerts. Each item is a dict
            with keys: symbol, elapsed_hours, reference_price, recalibrate.
        stop_buy_active: if True, suppress all idle Telegram messages.
            Default False preserves the original verbose behavior (used by
            tests that don't pass the flag explicitly).
    """
    if stop_buy_active:
        # Suppression policy: structural block in place → idle alerts add
        # noise without informing the operator. The recalibrate's in-memory
        # effects (buy_reference reset, ladder reset) still run via grid_bot;
        # only the Telegram echo is silenced.
        return
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
