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
        """Send a single trade notification with verification."""
        emoji = "🟢" if trade["side"] == "buy" else "🔴"
        pnl_line = ""
        if trade["side"] == "sell":
            if trade.get("realized_pnl") is not None:
                pnl = trade["realized_pnl"]
                pct = trade.get("trade_pnl_pct", 0)
                sign = "+" if pnl >= 0 else ""
                pnl_line = f"\n💰 Trade P&L: {sign}${pnl:.4f} ({sign}{pct:.2f}%)"
            if trade.get("portfolio_realized_pnl") is not None:
                port_pnl = trade["portfolio_realized_pnl"]
                port_pct = trade.get("portfolio_pnl_pct", 0)
                sign = "+" if port_pnl >= 0 else ""
                pnl_line += f"\n📊 Portfolio P&L: {sign}${port_pnl:.4f} ({sign}{port_pct:.2f}%)"
        elif trade.get("realized_pnl") is not None:
            pnl_line = f"\n💰 P&L: ${trade['realized_pnl']:.4f}"

        cost_label = "Revenue" if trade["side"] == "sell" else "Cost"

        # Verification line
        verify_line = ""
        TOLERANCE = 0.01  # 1% tolerance for rounding
        base = trade["symbol"].split("/")[0] if "/" in trade["symbol"] else trade["symbol"]
        if trade["side"] == "buy" and "cash_before" in trade:
            cash = trade["cash_before"]
            spend = trade["cost"]
            ok = cash >= spend * (1 - TOLERANCE)
            icon = "✅" if ok else "⚠️"
            verify_line = f"\n💵 Cash {base}: ${cash:.2f} → Spend ${spend:.2f} {icon}"
        elif trade["side"] == "sell" and "holdings_value_before" in trade:
            have = trade["holdings_value_before"]
            sell_val = trade["cost"]
            ok = have >= sell_val * (1 - TOLERANCE)
            icon = "✅" if ok else "⚠️"
            verify_line = f"\n🦺 Have {base}: ${have:.2f} → Sell ${sell_val:.2f} {icon}"

        skim_line = ""
        if trade["side"] == "sell" and trade.get("skim_amount") is not None:
            skim_amount = trade["skim_amount"]
            reserve_total = trade.get("reserve_total", 0)
            skim_line = f"\n🏦 {base} Reserve: +${skim_amount:.4f} (→ total ${reserve_total:.2f})"

        # 42a: greed-decay tier info on TF sells. Only present when the sell
        # was driven by greed decay (not by stop-loss / take-profit / bearish).
        greed_line = ""
        if (trade["side"] == "sell"
                and trade.get("greed_tier_age_min") is not None
                and trade.get("greed_tier_tp_pct") is not None):
            greed_line = (
                f"\n⏳ Greed tier: {trade['greed_tier_age_min']:.0f}min "
                f"→ TP {trade['greed_tier_tp_pct']}%"
            )

        text = (
            f"{emoji} <b>{trade['side'].upper()}</b> {trade['symbol']}\n"
            f"Amount: {trade['amount']:.6f}\n"
            f"Price: {fmt_price(trade['price'])}\n"
            f"{cost_label}: ${trade['cost']:.2f}\n"
            f"Fee: ${trade['fee']:.4f}\n"
            f"Brain: {trade['brain']} | Mode: {trade['mode']}"
            f"{pnl_line}"
            f"{skim_line}"
            f"{greed_line}"
            f"{verify_line}"
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
            f"{'─' * 15}\n"
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
                f"\n{'─' * 15}\n"
                f"💼 <b>Total Portfolio</b>\n"
                f"  Cash: ${cash:.2f}\n"
                f"  Holdings: ${holdings_val:.2f}\n"
                f"  <b>Total value: ${total_val:.2f}</b>\n"
                f"  Initial capital: ${initial:.2f}\n"
                f"  P&L: ${total_pnl:+.2f} ({pnl_pct:+.1f}%)\n"
            )

            positions = ps.get('positions', [])
            if positions:
                text += "\n  <b>Positions:</b>\n"
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

        47e/v2: layout aggregato. Cima = Total Portfolio (Grid + TF combinati).
        Sotto = sezioni separate Grid e TF, ciascuna con il proprio P&L vs il
        proprio capitale di partenza ($500 + $100 = $600 in paper mode).
        """
        today = date.today().strftime("%d/%m/%Y")
        day_num = data.get("day_number", "?")

        # Grid numbers
        grid_val = data.get("total_value", 0)
        grid_initial = data.get("initial_capital", 0)
        grid_pnl = data.get("total_pnl", 0)
        grid_pnl_pct = (grid_pnl / grid_initial * 100) if grid_initial > 0 else 0
        grid_pnl_emoji = "🟢" if grid_pnl >= 0 else "🔴"
        cash = data.get("cash", 0)
        holdings_val = data.get("holdings_value", 0)

        # TF numbers (may be empty if get_tf_state failed)
        tf = data.get("tf") or {}
        tf_val = float(tf.get("total_value") or 0)
        tf_budget = float(tf.get("tf_budget") or 0)
        tf_pnl = float(tf.get("total_pnl") or 0)
        tf_pnl_pct = (tf_pnl / tf_budget * 100) if tf_budget > 0 else 0
        tf_pnl_emoji = "🟢" if tf_pnl >= 0 else "🔴"

        # Aggregated (Grid + TF)
        total_val = grid_val + tf_val
        total_initial = grid_initial + tf_budget
        total_pnl = grid_pnl + tf_pnl
        total_pnl_pct = (total_pnl / total_initial * 100) if total_initial > 0 else 0
        total_pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"

        text = (
            f"📊 <b>BagHolderAI — Daily Report</b>\n"
            f"📅 {today} · Day {day_num} · Paper mode\n"
            f"\n"
            f"💼 <b>Total Portfolio: ${total_val:.2f}</b>\n"
            f"Started with ${total_initial:.0f} · P&L: {total_pnl_emoji} ${total_pnl:+.2f} ({total_pnl_pct:+.1f}%)\n"
        )

        # Today (Grid + TF combined)
        tc = data.get("today_trades_count", 0)
        tb = data.get("today_buys", 0)
        ts = data.get("today_sells", 0)
        tr_grid = data.get("today_realized", 0)
        fees = data.get("today_fees", 0)
        tf_trades_today = int(tf.get("trades_today") or 0)
        tf_buys_today = int(tf.get("buys_today") or 0)
        tf_sells_today = int(tf.get("sells_today") or 0)
        tr_tf = float(tf.get("realized_today") or 0)
        tr_combined = tr_grid + tr_tf
        tc_combined = tc + tf_trades_today
        tb_combined = tb + tf_buys_today
        ts_combined = ts + tf_sells_today
        realized_emoji = "🟢" if tr_combined >= 0 else "🔴"
        text += (
            f"\n📅 <b>Today (combined):</b> {tc_combined} trades "
            f"({tb_combined}B {ts_combined}S)\n"
            f"Realized: {realized_emoji} ${tr_combined:+.2f} · Fees: ${fees:.2f}\n"
        )

        # === GRID section ===
        # Same shape as the TF block below: header line with total + P&L,
        # second line with the cumulative breakdown (realized / skim / fees)
        # so the user sees the same metrics on both bots without scrolling.
        grid_realized_total = float(data.get("realized_total") or 0)
        grid_skim_total = float(data.get("skim_total") or 0)
        grid_fees_total = float(data.get("fees_total") or 0)
        text += (
            f"\n{'─' * 15}\n"
            f"🟢 <b>Grid: ${grid_val:.2f}</b> / ${grid_initial:.0f} · "
            f"P&L: {grid_pnl_emoji} ${grid_pnl:+.2f} ({grid_pnl_pct:+.1f}%)\n"
            f"Cash: ${cash:.2f} · Holdings: ${holdings_val:.2f}\n"
            f"Realized total: ${grid_realized_total:+.2f} · "
            f"Skim: ${grid_skim_total:.2f} · Fees: ${grid_fees_total:.2f}\n"
        )

        positions = data.get("positions", [])
        if positions:
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

        # === TF section ===
        # tf_val/budget/pnl already computed at the top for the aggregated header.
        # Same single source of truth as tf.html (commentary.get_tf_state).
        # Per-coin breakdown mirrors Grid section above so the eye scans both
        # the same way: one block per coin, holdings + avg_buy + realized
        # cumul + today's activity.
        if tf:
            tf_realized_total = float(tf.get("realized_total") or 0)
            tf_skim = float(tf.get("skim_total") or 0)
            tf_fees = float(tf.get("fees_total") or 0)

            text += (
                f"\n{'─' * 15}\n"
                f"📈 <b>Trend Follower: ${tf_val:.2f}</b> / ${tf_budget:.0f} · "
                f"P&L: {tf_pnl_emoji} ${tf_pnl:+.2f} ({tf_pnl_pct:+.1f}%)\n"
                f"Realized total: ${tf_realized_total:+.2f} · "
                f"Skim: ${tf_skim:.2f} · Fees: ${tf_fees:.2f}\n"
            )

            tf_positions = tf.get("active_positions") or []
            if tf_positions:
                for p in tf_positions:
                    sym = p.get("symbol", "?")
                    base = sym.split("/")[0] if "/" in sym else sym
                    val = float(p.get("value_usd") or 0)
                    upnl = float(p.get("unrealized_pnl") or 0)
                    upnl_pct = float(p.get("unrealized_pnl_pct") or 0)
                    holdings = float(p.get("holdings") or 0)
                    avg_buy = float(p.get("avg_buy_price") or 0)
                    realized_cumul = float(p.get("realized_pnl") or 0)
                    realized_today_coin = float(p.get("realized_today") or 0)
                    trades_today_coin = int(p.get("trades_today") or 0)
                    buys_today_coin = int(p.get("buys_today") or 0)
                    sells_today_coin = int(p.get("sells_today") or 0)
                    closed = bool(p.get("position_closed"))
                    arrow = "▲" if upnl >= 0 else "▼"
                    sign = "+" if upnl >= 0 else ""

                    text += f"\n<b>{sym}</b>  ${val:.2f} {arrow} {sign}{upnl_pct:.1f}%\n"
                    if closed:
                        text += "  Status: closed — awaiting re-entry\n"
                    else:
                        text += f"  Holdings: {holdings:.6f} {base}\n"
                        text += f"  Avg buy: {fmt_price(avg_buy)}\n"
                    text += f"  Realized: ${realized_cumul:+.4f}\n"
                    if trades_today_coin > 0:
                        coin_today_emoji = "🟢" if realized_today_coin >= 0 else "🔴"
                        text += (
                            f"  Today: {trades_today_coin} trades "
                            f"({buys_today_coin}B {sells_today_coin}S) · "
                            f"{coin_today_emoji} ${realized_today_coin:+.2f}\n"
                        )
                    else:
                        text += "  Today: no trades\n"
            else:
                text += "  No active TF positions.\n"

        # Reserve summary (Grid only — TF skim is shown above in TF section)
        # Prefer skim_by_sym from get_grid_state (always present).
        # Fall back to the legacy reserves dict for callers that don't pass it.
        reserves = data.get("skim_by_sym") or data.get("reserves") or {}
        if reserves and any(v > 0 for v in reserves.values()):
            total_reserve = sum(reserves.values())
            text += f"\n{'─' * 15}\n🏦 <b>Grid Reserve</b>\n"
            for sym, amt in reserves.items():
                if amt > 0:
                    base = sym.split("/")[0] if "/" in sym else sym
                    text += f"  💰 {base}: ${amt:.2f}\n"
            text += f"  📊 Total: ${total_reserve:.2f}\n"

        text += f"\n🤖 <i>Grid bot v3 · bagholderai.lol</i>"
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

        # Grid numbers
        grid_val = data.get("total_value", 0)
        grid_initial = data.get("initial_capital", 0)
        grid_pnl = data.get("total_pnl", 0)
        grid_pnl_pct = (grid_pnl / grid_initial * 100) if grid_initial > 0 else 0
        grid_pnl_emoji = "🟢" if grid_pnl >= 0 else "🔴"
        cash = data.get("cash", 0)

        # TF numbers
        tf = data.get("tf") or {}
        tf_val = float(tf.get("total_value") or 0)
        tf_budget = float(tf.get("tf_budget") or 0)
        tf_pnl = float(tf.get("total_pnl") or 0)
        tf_pnl_pct = (tf_pnl / tf_budget * 100) if tf_budget > 0 else 0
        tf_pnl_emoji = "🟢" if tf_pnl >= 0 else "🔴"

        # Aggregated
        total_val = grid_val + tf_val
        total_initial = grid_initial + tf_budget
        total_pnl = grid_pnl + tf_pnl
        total_pnl_pct = (total_pnl / total_initial * 100) if total_initial > 0 else 0
        total_pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"

        # Today combined
        tc = data.get("today_trades_count", 0)
        tr_grid = data.get("today_realized", 0)
        tf_trades_today = int(tf.get("trades_today") or 0)
        tr_tf = float(tf.get("realized_today") or 0)
        tc_combined = tc + tf_trades_today
        tr_combined = tr_grid + tr_tf
        realized_emoji = "🟢" if tr_combined >= 0 else "🔴"

        text = (
            f"📊 <b>BagHolderAI — Daily Report</b>\n"
            f"📅 {today} · Day {day_num} of paper trading\n"
            f"\n"
            f"<b>Total Portfolio: ${total_val:.2f}</b>\n"
            f"Started with ${total_initial:.0f} · P&L: {total_pnl_emoji} "
            f"${total_pnl:+.2f} ({total_pnl_pct:+.1f}%)\n"
            f"\n"
            f"Today: {tc_combined} trades · Realized: {realized_emoji} ${tr_combined:+.2f}\n"
        )

        # === GRID compact ===
        # Per-coin: value + arrow + today's trade count (or "idle" if 0).
        # No $ figures for today realized — public stays sober.
        text += (
            f"\n🟢 <b>Grid: ${grid_val:.2f}</b> / ${grid_initial:.0f} · "
            f"{grid_pnl_emoji} ${grid_pnl:+.2f} ({grid_pnl_pct:+.1f}%)\n"
        )
        positions = data.get("positions", [])
        if positions:
            for p in positions:
                sym = p.get("symbol", "?")
                base = sym.split("/")[0] if "/" in sym else sym
                val = p.get("value", 0)
                upnl_pct = p.get("unrealized_pnl_pct", 0)
                arrow = "▲" if upnl_pct >= 0 else "▼"
                pnl_sign = "+" if upnl_pct >= 0 else ""
                pt = int(p.get("trades_today", 0) or 0)
                today_tag = (
                    f"{pt} trade{'s' if pt != 1 else ''} today" if pt > 0 else "idle"
                )
                text += (
                    f"  {base}: ${val:.2f} {arrow} {pnl_sign}{upnl_pct:.1f}% "
                    f"· {today_tag}\n"
                )
            text += f"  Cash: ${cash:.2f}\n"

        # === TF compact ===
        if tf:
            text += (
                f"\n📈 <b>Trend Follower: ${tf_val:.2f}</b> / ${tf_budget:.0f} · "
                f"{tf_pnl_emoji} ${tf_pnl:+.2f} ({tf_pnl_pct:+.1f}%)\n"
            )
            tf_positions = tf.get("active_positions") or []
            if tf_positions:
                for p in tf_positions:
                    sym = p.get("symbol", "?")
                    base = sym.split("/")[0] if "/" in sym else sym
                    val = float(p.get("value_usd") or 0)
                    upnl_pct = float(p.get("unrealized_pnl_pct") or 0)
                    closed = bool(p.get("position_closed"))
                    pt = int(p.get("trades_today", 0) or 0)
                    arrow = "▲" if upnl_pct >= 0 else "▼"
                    sign = "+" if upnl_pct >= 0 else ""
                    if closed:
                        # holdings=0 idle: skip the value (it's $0 anyway)
                        # and just show the status. Today count if any.
                        suffix = (
                            f" · {pt} trade{'s' if pt != 1 else ''} today"
                            if pt > 0 else ""
                        )
                        text += f"  {base}: closed — awaiting re-entry{suffix}\n"
                    else:
                        today_tag = (
                    f"{pt} trade{'s' if pt != 1 else ''} today" if pt > 0 else "idle"
                )
                        text += (
                            f"  {base}: ${val:.2f} {arrow} {sign}{upnl_pct:.1f}% "
                            f"· {today_tag}\n"
                        )
            else:
                text += f"  No active positions.\n"

        text += f"\n🤖 <i>PAPER MODE · bagholderai.lol</i>"

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

    async def send_public_commentary(self, commentary_text: str) -> bool:
        """
        Post the daily Haiku commentary as a follow-up message on the public
        channel, right after the daily report. Same text that lands on
        bagholderai.lol/dashboard#ceo-log.
        Skips silently if commentary is empty or the public bot isn't configured.
        """
        if not commentary_text:
            return False

        public_token = TelegramConfig.PUBLIC_BOT_TOKEN
        public_chat = TelegramConfig.PUBLIC_CHAT_ID
        if not public_token or not public_chat:
            return False

        # Header keeps the message clearly tagged as Haiku's voice; the body
        # is the commentary verbatim — same content that ends up on the site.
        text = (
            f"💬 <b>CEO's Log</b>\n"
            f"\n"
            f"{commentary_text}\n"
            f"\n"
            f"🤖 <i>Generated by Haiku · Same as bagholderai.lol/dashboard</i>"
        )

        try:
            public_bot = Bot(token=public_token)
            await public_bot.send_message(
                chat_id=public_chat,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send public commentary: {e}")
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
        try:
            result = _run_async(self._async.send_message(text))
            if not result:
                logger.warning("Telegram send_message failed silently")
            return result
        except Exception as e:
            logger.warning(f"Telegram send_message exception: {e}")
            return False

    def send_trade_alert(self, trade: dict) -> bool:
        try:
            result = _run_async(self._async.send_trade_alert(trade))
            if not result:
                logger.warning(f"Telegram trade alert failed silently for {trade.get('symbol', '?')}")
            return result
        except Exception as e:
            logger.warning(f"Telegram trade alert exception: {e}")
            return False

    def send_daily_report(self, trades: list, status: dict, portfolio_summary: dict = None) -> bool:
        try:
            result = _run_async(self._async.send_daily_report(trades, status, portfolio_summary))
            if not result:
                logger.warning(f"Telegram daily report failed silently for {status.get('symbol', '?')}")
            return result
        except Exception as e:
            logger.warning(f"Telegram daily report exception: {e}")
            return False

    def send_bot_started(self, status: dict) -> bool:
        try:
            result = _run_async(self._async.send_bot_started(status))
            if not result:
                logger.warning(f"Telegram bot_started failed silently for {status.get('symbol', '?')}")
            return result
        except Exception as e:
            logger.warning(f"Telegram bot_started exception: {e}")
            return False

    def send_bot_stopped(self, status: dict, reason: str = "manual") -> bool:
        try:
            result = _run_async(self._async.send_bot_stopped(status, reason))
            if not result:
                logger.warning(f"Telegram bot_stopped failed silently for {status.get('symbol', '?')}")
            return result
        except Exception as e:
            logger.warning(f"Telegram bot_stopped exception: {e}")
            return False

    def send_grid_reset(self, old_range: str, new_range: str, price: float) -> bool:
        try:
            result = _run_async(self._async.send_grid_reset(old_range, new_range, price))
            if not result:
                logger.warning(f"Telegram grid_reset failed silently (price={price})")
            return result
        except Exception as e:
            logger.warning(f"Telegram grid_reset exception: {e}")
            return False

    def send_private_daily_report(self, data: dict) -> bool:
        try:
            result = _run_async(self._async.send_private_daily_report(data))
            if not result:
                logger.warning("Telegram private daily report failed silently")
            return result
        except Exception as e:
            logger.warning(f"Telegram private daily report exception: {e}")
            return False

    def send_public_daily_report(self, data: dict) -> bool:
        try:
            result = _run_async(self._async.send_public_daily_report(data))
            if not result:
                logger.warning("Telegram public daily report failed silently")
            return result
        except Exception as e:
            logger.warning(f"Telegram public daily report exception: {e}")
            return False

    def send_public_commentary(self, commentary_text: str) -> bool:
        try:
            result = _run_async(self._async.send_public_commentary(commentary_text))
            if not result:
                logger.warning("Telegram public commentary failed silently")
            return result
        except Exception as e:
            logger.warning(f"Telegram public commentary exception: {e}")
            return False

    def send_tf_error(self, error_msg: str) -> bool:
        """Send a Trend Follower error alert."""
        text = f"🚨 <b>TREND FOLLOWER ERROR</b>\n<code>{error_msg[:300]}</code>"
        return self.send_message(text)
