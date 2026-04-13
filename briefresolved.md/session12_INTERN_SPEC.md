# Session 12 — Intern Spec: Telegram Report Redesign

## Overview

Quattro bug da fixare, un redesign del report giornaliero.

**Cosa cambia:**
1. `_build_portfolio_summary()` in `grid_runner.py` — calcola P&L sbagliato ($+270 invece di $-13)
2. `DailyPnLTracker` in `db/client.py` — nuovo schema `daily_pnl` (già migrato su Supabase)
3. `telegram_notifier.py` — nuovi formati report (privato + pubblico)
4. `config/settings.py` — aggiungere config per bot Telegram pubblico
5. `grid_runner.py` daily report logic — un solo report al giorno, non 3

**⚠️ La migrazione della tabella `daily_pnl` su Supabase è GIÀ stata fatta. NON creare/modificare la tabella.**

---

## File 1: `config/settings.py`

Aggiungere le variabili per il bot Telegram pubblico nella classe `TelegramConfig`:

```python
class TelegramConfig:
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    # Public bot (read-only daily reports for followers)
    PUBLIC_BOT_TOKEN = os.getenv("TELEGRAM_PUBLIC_BOT_TOKEN", "")
    PUBLIC_CHAT_ID = os.getenv("TELEGRAM_PUBLIC_CHAT_ID", "")
```

---

## File 2: `db/client.py`

### 2a. Riscrivere `DailyPnLTracker` completamente

Sostituire l'intera classe `DailyPnLTracker` con:

```python
class DailyPnLTracker:
    """Tracks daily performance snapshots for dashboard."""
    
    def __init__(self):
        self.client = get_client()
    
    def record_daily(
        self,
        total_value: float,
        cash_remaining: float,
        holdings_value: float,
        initial_capital: float,
        total_pnl: float,
        realized_pnl_today: float = 0,
        total_fees_today: float = 0,
        trades_count: int = 0,
        buys_count: int = 0,
        sells_count: int = 0,
        positions: list = None,
    ) -> dict:
        """Record end-of-day portfolio snapshot."""
        import json
        data = {
            "date": date.today().isoformat(),
            "total_value": round(total_value, 8),
            "cash_remaining": round(cash_remaining, 8),
            "holdings_value": round(holdings_value, 8),
            "initial_capital": round(initial_capital, 8),
            "total_pnl": round(total_pnl, 8),
            "realized_pnl_today": round(realized_pnl_today, 8),
            "total_fees_today": round(total_fees_today, 8),
            "trades_count": trades_count,
            "buys_count": buys_count,
            "sells_count": sells_count,
            "positions": json.dumps(positions or []),
        }
        
        result = (
            self.client.table("daily_pnl")
            .upsert(data, on_conflict="date")
            .execute()
        )
        return result.data[0] if result.data else {}
    
    def has_today_snapshot(self) -> bool:
        """Check if today's snapshot already exists (for single-report coordination)."""
        today = date.today().isoformat()
        result = (
            self.client.table("daily_pnl")
            .select("id")
            .eq("date", today)
            .execute()
        )
        return bool(result.data)
    
    def get_daily_pnl_today(self) -> float:
        """Get today's P&L (for daily loss limit check)."""
        today = date.today().isoformat()
        result = (
            self.client.table("daily_pnl")
            .select("total_pnl")
            .eq("date", today)
            .execute()
        )
        if result.data:
            return float(result.data[0].get("total_pnl", 0))
        return 0.0
```

---

## File 3: `grid_runner.py`

### 3a. Riscrivere `_build_portfolio_summary()`

Sostituire l'intera funzione con:

```python
def _build_portfolio_summary(trade_logger, exchange, current_bot, current_symbol: str) -> dict:
    """
    Build a consolidated portfolio summary across all grid instances.
    Queries DB positions + live prices to calculate total portfolio value.
    
    FIX Session 12:
    - initial_capital uses MAX_CAPITAL ($500), not sum of grid allocations ($180)
    - Cash calculated globally, not per-instance (which clamped to $0)
    """
    initial_capital = HardcodedRules.MAX_CAPITAL
    
    total_invested_all = 0.0
    total_received_all = 0.0
    holdings_value = 0.0
    positions = []

    for inst in GRID_INSTANCES:
        pos = trade_logger.get_open_position(inst.symbol)
        h = pos["holdings"]
        total_invested_all += pos["total_invested"]
        total_received_all += pos["total_received"]

        if h > 0:
            # Use current bot's price if same symbol, otherwise fetch
            if inst.symbol == current_symbol:
                live_price = current_bot.state.last_price if current_bot.state else 0
            else:
                try:
                    ticker = exchange.fetch_ticker(inst.symbol)
                    live_price = ticker["last"]
                except Exception:
                    live_price = pos["avg_buy_price"]  # fallback

            value = h * live_price
            unrealized = (live_price - pos["avg_buy_price"]) * h if pos["avg_buy_price"] > 0 else 0
            unrealized_pct = ((live_price / pos["avg_buy_price"]) - 1) * 100 if pos["avg_buy_price"] > 0 else 0
            holdings_value += value
            positions.append({
                "symbol": inst.symbol,
                "holdings": h,
                "value": value,
                "avg_buy_price": pos["avg_buy_price"],
                "unrealized_pnl": unrealized,
                "unrealized_pnl_pct": unrealized_pct,
                "realized_pnl": pos["realized_pnl"],
                "live_price": live_price,
            })

    # Global cash: what's left from the real initial investment
    cash = max(0.0, initial_capital - total_invested_all + total_received_all)
    total_value = cash + holdings_value
    total_pnl = total_value - initial_capital

    return {
        "total_value": total_value,
        "cash": cash,
        "holdings_value": holdings_value,
        "initial_capital": initial_capital,
        "total_pnl": total_pnl,
        "positions": positions,
    }
```

### 3b. Riscrivere il blocco daily report (dentro il `while True` loop)

Sostituire tutto il blocco `# Daily report at 21:00` con:

```python
            # Daily report at 21:00 — only first bot to trigger sends
            now = datetime.now()
            if now.hour >= REPORT_HOUR and daily_report_sent != date.today():
                try:
                    # Check if another bot already sent today's report
                    if pnl_tracker and pnl_tracker.has_today_snapshot():
                        daily_report_sent = date.today()
                        logger.info("Daily snapshot already exists. Skipping report.")
                    else:
                        # Build consolidated portfolio from DB + live prices
                        portfolio_summary = _build_portfolio_summary(
                            trade_logger, exchange, bot, cfg.symbol
                        )

                        # Get today's trades for ALL symbols
                        today_all_trades = trade_logger.get_today_trades() if trade_logger else []
                        today_buys = sum(1 for t in today_all_trades if t.get("side") == "buy")
                        today_sells = sum(1 for t in today_all_trades if t.get("side") == "sell")
                        day_fees = sum(float(t.get("fee", 0)) for t in today_all_trades)
                        day_realized = sum(
                            float(t.get("realized_pnl", 0))
                            for t in today_all_trades if t.get("realized_pnl")
                        )

                        # Enrich positions with today's trade counts + grid info
                        for p in portfolio_summary.get("positions", []):
                            sym_trades = [t for t in today_all_trades if t.get("symbol") == p["symbol"]]
                            p["trades_today"] = len(sym_trades)
                            p["buys_today"] = sum(1 for t in sym_trades if t.get("side") == "buy")
                            p["sells_today"] = sum(1 for t in sym_trades if t.get("side") == "sell")
                            # Grid info only available for this bot's symbol
                            if p["symbol"] == cfg.symbol:
                                status = bot.get_status()
                                p["grid_range"] = status.get("range", "N/A")
                                p["grid_active_buys"] = status.get("levels", {}).get("active_buys", 0)
                                p["grid_active_sells"] = status.get("levels", {}).get("active_sells", 0)

                        # Calculate trading day number
                        day_number = 1
                        try:
                            first_trade_result = trade_logger.client.table("trades").select("created_at").order("created_at", desc=False).limit(1).execute()
                            if first_trade_result.data:
                                first_date_str = first_trade_result.data[0]["created_at"]
                                first_date = datetime.fromisoformat(first_date_str.replace("Z", "+00:00")).date()
                                day_number = (date.today() - first_date).days + 1
                        except Exception:
                            pass

                        # Bundle all report data
                        report_data = {
                            **portfolio_summary,
                            "day_number": day_number,
                            "today_trades_count": len(today_all_trades),
                            "today_buys": today_buys,
                            "today_sells": today_sells,
                            "today_fees": day_fees,
                            "today_realized": day_realized,
                        }

                        # Send reports
                        notifier.send_private_daily_report(report_data)
                        notifier.send_public_daily_report(report_data)

                        # Save snapshot to daily_pnl
                        if pnl_tracker:
                            # Prepare positions for JSON storage
                            snapshot_positions = []
                            for p in portfolio_summary.get("positions", []):
                                snapshot_positions.append({
                                    "symbol": p["symbol"],
                                    "holdings": p["holdings"],
                                    "value": round(p["value"], 4),
                                    "avg_buy_price": p["avg_buy_price"],
                                    "unrealized_pnl": round(p["unrealized_pnl"], 4),
                                    "unrealized_pnl_pct": round(p.get("unrealized_pnl_pct", 0), 2),
                                })
                            pnl_tracker.record_daily(
                                total_value=portfolio_summary["total_value"],
                                cash_remaining=portfolio_summary["cash"],
                                holdings_value=portfolio_summary["holdings_value"],
                                initial_capital=portfolio_summary["initial_capital"],
                                total_pnl=portfolio_summary["total_pnl"],
                                realized_pnl_today=day_realized,
                                total_fees_today=day_fees,
                                trades_count=len(today_all_trades),
                                buys_count=today_buys,
                                sells_count=today_sells,
                                positions=snapshot_positions,
                            )
                            logger.info("Daily P&L snapshot saved to database.")

                        daily_report_sent = date.today()
                        logger.info("Daily report sent via Telegram.")
                except Exception as e:
                    logger.error(f"Failed to send daily report: {e}")
```

---

## File 4: `utils/telegram_notifier.py`

### 4a. Aggiungere import per config pubblico

In cima al file, aggiungere:
```python
from config.settings import TelegramConfig
```

(Se `TelegramConfig` è già importato tramite altro percorso, assicurarsi che ci sia accesso a `PUBLIC_BOT_TOKEN` e `PUBLIC_CHAT_ID`.)

### 4b. Aggiungere `send_private_daily_report` alla classe `TelegramNotifier`

Aggiungere questo metodo DOPO `send_daily_report`:

```python
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

        text += f"\n🤖 <i>Grid bot v2 · bagholder.lol</i>"
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
```

### 4c. Aggiungere i sync wrappers in `SyncTelegramNotifier`

Aggiungere questi metodi alla classe `SyncTelegramNotifier`:

```python
    def send_private_daily_report(self, data: dict) -> bool:
        return _run_async(self._async.send_private_daily_report(data))

    def send_public_daily_report(self, data: dict) -> bool:
        return _run_async(self._async.send_public_daily_report(data))
```

### 4d. Il vecchio `send_daily_report()` — NON cancellare

Lasciare il vecchio `send_daily_report()` nel codice per retrocompatibilità ma non viene più chiamato dal grid_runner. Non serve modificarlo.

---

## File 5: `db/schema.sql` (solo documentazione)

Aggiornare lo schema SQL per riflettere la nuova struttura della tabella `daily_pnl`. Questo file è solo documentazione — la migrazione è già stata applicata su Supabase.

Sostituire la definizione `daily_pnl` esistente con:

```sql
-- Daily portfolio snapshots (dashboard-ready)
CREATE TABLE daily_pnl (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    date date NOT NULL UNIQUE,
    total_value numeric NOT NULL,
    cash_remaining numeric NOT NULL,
    holdings_value numeric NOT NULL,
    initial_capital numeric NOT NULL,
    total_pnl numeric NOT NULL,
    realized_pnl_today numeric DEFAULT 0,
    total_fees_today numeric DEFAULT 0,
    trades_count integer DEFAULT 0,
    buys_count integer DEFAULT 0,
    sells_count integer DEFAULT 0,
    positions jsonb DEFAULT '[]'::jsonb,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX idx_daily_pnl_date ON daily_pnl (date DESC);
```

---

## Checklist di test

Dopo aver applicato le modifiche:

1. **Verificare che il bot parta senza errori**: `python -m bot.grid_runner --symbol "BTC/USDT" --once`
2. **Verificare i numeri del report** controllando manualmente:
   - `initial_capital` deve essere $500 (non $180)
   - `cash` deve essere circa $22 (non $5)
   - `total_pnl` deve essere circa -$13 (non +$270)
3. **NON lanciare il bot** — solo testare con `--once --dry-run`
4. **NON modificare la tabella `daily_pnl` su Supabase** — è già stata migrata

---

## Riepilogo file modificati

| File | Azione |
|------|--------|
| `config/settings.py` | Aggiungere `PUBLIC_BOT_TOKEN` e `PUBLIC_CHAT_ID` |
| `db/client.py` | Riscrivere classe `DailyPnLTracker` |
| `bot/grid_runner.py` | Riscrivere `_build_portfolio_summary()` + blocco daily report |
| `utils/telegram_notifier.py` | Aggiungere `send_private_daily_report()` + `send_public_daily_report()` + sync wrappers |
| `db/schema.sql` | Aggiornare documentazione (solo commenti, no migrazione) |
