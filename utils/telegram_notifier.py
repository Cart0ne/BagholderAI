"""
BagHolderAI - Telegram Notifier
Sends trade alerts and daily reports to Max via Telegram.

Usage:
    from utils.telegram_notifier import TelegramNotifier
    notifier = TelegramNotifier()
    await notifier.send_message("Hello from BagHolderAI!")
    await notifier.send_daily_report()
"""

import asyncio
import logging
import threading
from datetime import date, datetime
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode

from config.settings import TelegramConfig

logger = logging.getLogger("bagholderai.telegram")


class TelegramNotifier:
    """Sends notifications to Max via Telegram."""

    def __init__(self):
        self.bot = Bot(token=TelegramConfig.BOT_TOKEN)
        self.chat_id = TelegramConfig.CHAT_ID

    async def send_message(self, text: str, parse_mode: str = ParseMode.HTML) -> bool:
        """Send a message to the configured chat. Returns True if sent."""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode,
            )
            logger.info("Telegram message sent.")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def send_trade_alert(self, trade: dict) -> bool:
        """Send a single trade notification."""
        emoji = "🟢" if trade["side"] == "buy" else "🔴"
        pnl_line = ""
        if trade.get("realized_pnl") is not None:
            pnl_line = f"\n💰 P&L: ${trade['realized_pnl']:.4f}"

        text = (
            f"{emoji} <b>{trade['side'].upper()}</b> {trade['symbol']}\n"
            f"Amount: {trade['amount']:.6f}\n"
            f"Price: ${trade['price']:,.2f}\n"
            f"Cost: ${trade['cost']:.2f}\n"
            f"Fee: ${trade['fee']:.4f}\n"
            f"Brain: {trade['brain']} | Mode: {trade['mode']}"
            f"{pnl_line}"
        )
        return await self.send_message(text)

    async def send_daily_report(self, trades: list, status: dict) -> bool:
        """
        Send end-of-day summary.
        
        Args:
            trades: list of today's trades from DB
            status: dict from bot.get_status()
        """
        today = date.today().strftime("%d/%m/%Y")
        num_buys = sum(1 for t in trades if t.get("side") == "buy")
        num_sells = sum(1 for t in trades if t.get("side") == "sell")
        total_fees = sum(float(t.get("fee", 0)) for t in trades)
        realized = sum(float(t.get("realized_pnl", 0)) for t in trades if t.get("realized_pnl"))

        text = (
            f"📊 <b>BagHolderAI Daily Report</b>\n"
            f"📅 {today}\n"
            f"{'─' * 28}\n"
            f"\n"
            f"<b>Trades:</b> {len(trades)} ({num_buys} buys, {num_sells} sells)\n"
            f"<b>Realized P&L:</b> ${realized:+.4f}\n"
            f"<b>Fees:</b> ${total_fees:.4f}\n"
            f"\n"
            f"<b>Portfolio:</b>\n"
            f"  Holdings: {status.get('holdings', 0):.6f} BTC\n"
            f"  Avg buy: ${status.get('avg_buy_price', 0):,.2f}\n"
            f"  Unrealized P&L: ${status.get('unrealized_pnl', 0):+.4f}\n"
            f"\n"
            f"<b>Grid:</b>\n"
            f"  Range: {status.get('range', 'N/A')}\n"
            f"  Active buys: {status.get('levels', {}).get('active_buys', 0)}\n"
            f"  Active sells: {status.get('levels', {}).get('active_sells', 0)}\n"
            f"\n"
            f"🤖 <i>Mode: {status.get('mode', 'paper').upper()}</i>"
        )
        return await self.send_message(text)

    async def send_bot_started(self, status: dict) -> bool:
        """Notify that the bot has started."""
        price = status.get("last_price", 0)
        text = (
            f"🚀 <b>BagHolderAI started</b>\n"
            f"Symbol: {status.get('symbol', 'N/A')}\n"
            f"Price: ${price:,.2f}\n"
            f"Range: {status.get('range', 'N/A')}\n"
            f"Mode: {status.get('mode', 'paper').upper()}\n"
            f"Levels: {status.get('levels', {}).get('total', 0)}"
        )
        return await self.send_message(text)

    async def send_bot_stopped(self, status: dict, reason: str = "manual") -> bool:
        """Notify that the bot has stopped."""
        text = (
            f"🛑 <b>BagHolderAI stopped</b>\n"
            f"Reason: {reason}\n"
            f"Holdings: {status.get('holdings', 0):.6f} BTC\n"
            f"Realized P&L: ${status.get('realized_pnl', 0):+.4f}\n"
            f"Trades today: {status.get('trades_today', 0)}"
        )
        return await self.send_message(text)

    async def send_grid_reset(self, old_range: str, new_range: str, price: float) -> bool:
        """Notify that the grid was reset due to price movement."""
        text = (
            f"🔄 <b>Grid Reset</b>\n"
            f"Price moved to ${price:,.2f}\n"
            f"Old range: {old_range}\n"
            f"New range: {new_range}"
        )
        return await self.send_message(text)


# === Sync wrappers for use in non-async code ===

_loop = None
_thread = None


def _get_loop():
    """Get or create a persistent event loop in a background thread."""
    global _loop, _thread
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        _thread = threading.Thread(target=_loop.run_forever, daemon=True)
        _thread.start()
    return _loop


def _run_async(coro):
    """Run an async function from sync code using a persistent loop."""
    loop = _get_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=10)


class SyncTelegramNotifier:
    """
    Synchronous wrapper around TelegramNotifier.
    Use this in the grid_runner main loop (which is sync).
    """

    def __init__(self):
        self._async = TelegramNotifier()

    def send_message(self, text: str) -> bool:
        return _run_async(self._async.send_message(text))

    def send_trade_alert(self, trade: dict) -> bool:
        return _run_async(self._async.send_trade_alert(trade))

    def send_daily_report(self, trades: list, status: dict) -> bool:
        return _run_async(self._async.send_daily_report(trades, status))

    def send_bot_started(self, status: dict) -> bool:
        return _run_async(self._async.send_bot_started(status))

    def send_bot_stopped(self, status: dict, reason: str = "manual") -> bool:
        return _run_async(self._async.send_bot_stopped(status, reason))

    def send_grid_reset(self, old_range: str, new_range: str, price: float) -> bool:
        return _run_async(self._async.send_grid_reset(old_range, new_range, price))
