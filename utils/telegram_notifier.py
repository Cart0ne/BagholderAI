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
from utils.formatting import fmt_price

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

        cost_label = "Revenue" if trade["side"] == "sell" else "Cost"
        text = (
            f"{emoji} <b>{trade['side'].upper()}</b> {trade['symbol']}\n"
            f"Amount: {trade['amount']:.6f}\n"
            f"Price: {fmt_price(trade['price'])}\n"
            f"{cost_label}: ${trade['cost']:.2f}\n"
            f"Fee: ${trade['fee']:.4f}\n"
            f"Brain: {trade['brain']} | Mode: {trade['mode']}"
            f"{pnl_line}"
        )
        return await self.send_message(text)

    async def send_daily_report(
        self,
        trades: list,
        status: dict,
        portfolio_summary: Optional[dict] = None,
    ) -> bool:
        """
        Send end-of-day summary.

        Args:
            trades: list of today's trades from DB (already filtered by symbol)
            status: dict from bot.get_status()
            portfolio_summary: optional dict with consolidated portfolio data:
                {total_value, cash, holdings_value, initial_capital, total_pnl, positions: [{symbol, holdings, value, unrealized_pnl}]}
        """
        today = date.today().strftime("%d/%m/%Y")
        num_buys = sum(1 for t in trades if t.get("side") == "buy")
        num_sells = sum(1 for t in trades if t.get("side") == "sell")
        total_fees = sum(float(t.get("fee", 0)) for t in trades)
        realized = sum(float(t.get("realized_pnl", 0)) for t in trades if t.get("realized_pnl"))

        symbol = status.get('symbol', 'N/A')
        base = symbol.split("/")[0] if "/" in symbol else symbol

        # Capital line
        capital = status.get('capital', 0)
        available = status.get('available_capital', 0)
        deployed = capital - available
        active_buys = status.get('levels', {}).get('active_buys', 0)
        capital_line = (
            f"  Capital: {fmt_price(deployed)}/{fmt_price(capital)} deployed"
            f" | Available: {fmt_price(available)}"
            f" | Buy levels remaining: {active_buys}"
        )

        text = (
            f"📊 <b>BagHolderAI Daily Report — {symbol}</b>\n"
            f"📅 {today}\n"
            f"{'─' * 28}\n"
            f"\n"
            f"<b>Trades:</b> {len(trades)} ({num_buys} buys, {num_sells} sells)\n"
            f"<b>Realized P&L:</b> ${realized:+.4f}\n"
            f"<b>Fees:</b> ${total_fees:.4f}\n"
            f"\n"
            f"<b>Portfolio:</b>\n"
            f"  Holdings: {status.get('holdings', 0):.6f} {base}\n"
            f"  Avg buy: {fmt_price(status.get('avg_buy_price', 0))}\n"
            f"  Unrealized P&L: ${status.get('unrealized_pnl', 0):+.4f}\n"
            f"\n"
            f"<b>Capital:</b>\n"
            f"{capital_line}\n"
            f"\n"
            f"<b>Grid:</b>\n"
            f"  Range: {status.get('range', 'N/A')}\n"
            f"  Active buys: {active_buys}\n"
            f"  Active sells: {status.get('levels', {}).get('active_sells', 0)}\n"
        )

        # Consolidated portfolio summary (all assets)
        if portfolio_summary:
            ps = portfolio_summary
            total_val = ps.get('total_value', 0)
            cash = ps.get('cash', 0)
            holdings_val = ps.get('holdings_value', 0)
            initial = ps.get('initial_capital', 0)
            total_pnl = ps.get('total_pnl', 0)
            pnl_pct = (total_pnl / initial * 100) if initial > 0 else 0

            text += (
                f"\n{'─' * 28}\n"
                f"💼 <b>Portfolio Totale</b>\n"
                f"  Cash: ${cash:.2f}\n"
                f"  Holdings: ${holdings_val:.2f}\n"
                f"  <b>Valore totale: ${total_val:.2f}</b>\n"
                f"  Capitale iniziale: ${initial:.2f}\n"
                f"  P&L: ${total_pnl:+.2f} ({pnl_pct:+.1f}%)\n"
            )

            positions = ps.get('positions', [])
            if positions:
                text += "\n  <b>Posizioni:</b>\n"
                for p in positions:
                    psym = p.get('symbol', '?')
                    pval = p.get('value', 0)
                    ppnl = p.get('unrealized_pnl', 0)
                    text += f"    {psym}: ${pval:.2f} (P&L: ${ppnl:+.4f})\n"

        text += f"\n🤖 <i>Mode: {status.get('mode', 'paper').upper()}</i>"
        return await self.send_message(text)

    async def send_bot_started(self, status: dict) -> bool:
        """Notify that the bot has started."""
        text = (
            f"🚀 <b>BagHolderAI started</b>\n"
            f"Symbol: {status.get('symbol', 'N/A')}\n"
            f"Price: {fmt_price(status.get('last_price', 0))}\n"
            f"Range: {status.get('range', 'N/A')}\n"
            f"Mode: {status.get('mode', 'paper').upper()}\n"
            f"Levels: {status.get('levels', {}).get('total', 0)}"
        )
        return await self.send_message(text)

    async def send_bot_stopped(self, status: dict, reason: str = "manual") -> bool:
        """Notify that the bot has stopped."""
        symbol = status.get('symbol', 'N/A')
        base = symbol.split("/")[0] if "/" in symbol else symbol
        text = (
            f"🛑 <b>BagHolderAI stopped</b>\n"
            f"Symbol: {symbol}\n"
            f"Reason: {reason}\n"
            f"Holdings: {status.get('holdings', 0):.6f} {base}\n"
            f"Realized P&L: ${status.get('realized_pnl', 0):+.4f}\n"
            f"Trades today: {status.get('trades_today', 0)}"
        )
        return await self.send_message(text)

    async def send_grid_reset(self, old_range: str, new_range: str, price: float) -> bool:
        """Notify that the grid was reset due to price movement."""
        text = (
            f"🔄 <b>Grid Reset</b>\n"
            f"Price moved to {fmt_price(price)}\n"
            f"Old range: {old_range}\n"
            f"New range: {new_range}"
        )
        return await self.send_message(text)

    async def send_private_daily_report(self, data: dict) -> bool:
        """
        Send Max's private daily report — one consolidated message with all assets.
        Designed for the operator: full portfolio overview + per-asset technical detail.
        """
        today = date.today().strftime("%d/%m/%Y")
        day_num = data.get("day_number", "?")
        total_val = data.get("total_value", 0)
        initial = data.get("initial_capital", 0)
        total_pnl = data.get("total_pnl", 0)
        pnl_pct = (total_pnl / initial * 100) if initial > 0 else 0
        cash = data.get("cash", 0)
        holdings_val = data.get("holdings_value", 0)
        cash_pct = (cash / total_val * 100) if total_val > 0 else 0
        hold_pct = (holdings_val / total_val * 100) if total_val > 0 else 0

        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"

        text = (
            f"📊 <b>BagHolderAI — Daily Report</b>\n"
            f"📅 {today} · Day {day_num} · Paper mode\n"
            f"\n"
            f"💼 <b>Portfolio: ${total_val:.2f}</b>\n"
            f"Invested: ${initial:.2f} · P&L: {pnl_emoji} ${total_pnl:+.2f} ({pnl_pct:+.1f}%)\n"
            f"Cash: ${cash:.2f} ({cash_pct:.1f}%) · Holdings: ${holdings_val:.2f} ({hold_pct:.1f}%)\n"
        )

        # Today summary
        tc = data.get("today_trades_count", 0)
        tb = data.get("today_buys", 0)
        ts = data.get("today_sells", 0)
        tr = data.get("today_realized", 0)
        tf = data.get("today_fees", 0)
        realized_emoji = "🟢" if tr >= 0 else "🔴"
        text += (
            f"\n📅 <b>Today:</b> {tc} trades ({tb}B {ts}S)\n"
            f"Realized: {realized_emoji} ${tr:+.4f} · Fees: ${tf:.4f}\n"
        )

        # Per-asset cards
        positions = data.get("positions", [])
        if positions:
            text += f"\n{'─' * 28}\n📈 <b>Assets</b>\n"
            for p in positions:
                sym = p.get("symbol", "?")
                base = sym.split("/")[0] if "/" in sym else sym
                val = p.get("value", 0)
                upnl = p.get("unrealized_pnl", 0)
                upnl_pct = p.get("unrealized_pnl_pct", 0)
                arrow = "▲" if upnl >= 0 else "▼"
                pnl_sign = "+" if upnl >= 0 else ""

                text += f"\n<b>{sym}</b>  ${val:.2f} {arrow} {pnl_sign}{upnl_pct:.1f}%\n"
                text += f"  Holdings: {p.get('holdings', 0):.6f} {base}\n"
                text += f"  Avg buy: {fmt_price(p.get('avg_buy_price', 0))}\n"
                text += f"  Realized: ${p.get('realized_pnl', 0):+.4f}\n"

                # Grid info (only available for the reporter bot's own symbol)
                if "grid_range" in p:
                    text += f"  Grid: {p['grid_range']}\n"
                    text += f"  Levels: {p.get('grid_active_buys', 0)} buy · {p.get('grid_active_sells', 0)} sell\n"

                pt = p.get("trades_today", 0)
                pb = p.get("buys_today", 0)
                ps = p.get("sells_today", 0)
                if pt > 0:
                    text += f"  Today: {pt} trades ({pb}B {ps}S)\n"
                else:
                    text += f"  Today: no trades\n"

        text += f"\n🤖 <i>Grid bot v3 · bagholder.lol</i>"
        return await self.send_message(text)

    async def send_public_daily_report(self, data: dict) -> bool:
        """
        Send the public daily report — clean, no jargon, readable by anyone.
        Uses the public bot token/chat if configured, otherwise skips silently.
        """
        public_token = TelegramConfig.PUBLIC_BOT_TOKEN
        public_chat = TelegramConfig.PUBLIC_CHAT_ID
        if not public_token or not public_chat:
            return False  # Public bot not configured yet, skip silently

        today = date.today().strftime("%d/%m/%Y")
        day_num = data.get("day_number", "?")
        total_val = data.get("total_value", 0)
        initial = data.get("initial_capital", 0)
        total_pnl = data.get("total_pnl", 0)
        pnl_pct = (total_pnl / initial * 100) if initial > 0 else 0
        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"

        text = (
            f"📊 <b>BagHolderAI — Daily Report</b>\n"
            f"📅 {today} · Day {day_num} of paper trading\n"
            f"\n"
            f"<b>Portfolio: ${total_val:.2f}</b>\n"
            f"Started with ${initial:.2f} · P&L: {pnl_emoji} ${total_pnl:+.2f} ({pnl_pct:+.1f}%)\n"
        )

        # Per-asset one-liners
        positions = data.get("positions", [])
        if positions:
            text += f"\n<b>Holdings</b>\n"
            for p in positions:
                sym = p.get("symbol", "?")
                base = sym.split("/")[0] if "/" in sym else sym
                val = p.get("value", 0)
                upnl_pct = p.get("unrealized_pnl_pct", 0)
                arrow = "▲" if upnl_pct >= 0 else "▼"
                pnl_sign = "+" if upnl_pct >= 0 else ""
                text += f"  {base}: ${val:.2f} {arrow} {pnl_sign}{upnl_pct:.1f}%\n"

            cash = data.get("cash", 0)
            text += f"  Cash: ${cash:.2f}\n"

        # Today one-liner
        tc = data.get("today_trades_count", 0)
        tb = data.get("today_buys", 0)
        ts = data.get("today_sells", 0)
        tr = data.get("today_realized", 0)
        tf = data.get("today_fees", 0)
        realized_emoji = "🟢" if tr >= 0 else "🔴"
        text += (
            f"\n<b>Today:</b> {tc} trades ({tb} buys, {ts} sells)\n"
            f"Realized: {realized_emoji} ${tr:+.2f} · Fees: ${tf:.2f}\n"
        )

        text += f"\n🤖 <i>PAPER MODE · bagholder.lol</i>"

        # Send via public bot
        try:
            public_bot = Bot(token=public_token)
            await public_bot.send_message(
                chat_id=public_chat,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send public report: {e}")
            return False


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

    def send_daily_report(self, trades: list, status: dict, portfolio_summary: dict = None) -> bool:
        return _run_async(self._async.send_daily_report(trades, status, portfolio_summary))

    def send_bot_started(self, status: dict) -> bool:
        return _run_async(self._async.send_bot_started(status))

    def send_bot_stopped(self, status: dict, reason: str = "manual") -> bool:
        return _run_async(self._async.send_bot_stopped(status, reason))

    def send_grid_reset(self, old_range: str, new_range: str, price: float) -> bool:
        return _run_async(self._async.send_grid_reset(old_range, new_range, price))

    def send_private_daily_report(self, data: dict) -> bool:
        return _run_async(self._async.send_private_daily_report(data))

    def send_public_daily_report(self, data: dict) -> bool:
        return _run_async(self._async.send_public_daily_report(data))
