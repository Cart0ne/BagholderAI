"""
BagHolderAI - Supabase Config Reader
Reads bot configuration from the bot_config table in Supabase on startup
and refreshes it every CONFIG_REFRESH_INTERVAL seconds in a background thread.

If Supabase is unreachable during a refresh, the last known config is kept
and a warning is logged. The bot never crashes due to a config refresh failure.
"""

import threading
import logging
import time

from db.event_logger import log_event

logger = logging.getLogger("bagholderai.config")

CONFIG_REFRESH_INTERVAL = 300  # seconds between config refreshes


# Fields to read from bot_config
_CONFIG_FIELDS = (
    "symbol,capital_allocation,grid_levels,grid_lower,grid_upper,"
    "profit_target_pct,reserve_floor_pct,capital_per_trade,"
    "is_active,buy_pct,sell_pct,grid_mode,skim_pct,idle_reentry_hours,"
    "pending_liquidation,managed_by,stop_buy_drawdown_pct,"
    # 42a: multi-lot entry + greed decay anchor
    "initial_lots,allocated_at"
)

# 39j: global TF params polled from trend_config alongside bot_config.
# Kept minimal to avoid side effects with other trend_config fields that
# are consumed only by the TF scanner (e.g. scan_interval_hours).
_TREND_CONFIG_FIELDS = "tf_stop_loss_pct,tf_take_profit_pct,greed_decay_tiers"


class SupabaseConfigReader:
    """
    Reads and periodically refreshes bot configuration from Supabase.

    Usage:
        reader = SupabaseConfigReader()
        reader.load_initial()          # call once on startup
        reader.start_refresh_loop()    # starts background thread

        cfg = reader.get_config("BTC/USDT")  # returns dict or None
    """

    def __init__(self, own_symbol: str = None):
        self._configs: dict = {}   # symbol -> raw row dict from bot_config
        self._trend_config: dict = {}  # 39j: key -> value from trend_config
        self._lock = threading.Lock()
        self._client = None
        self._stop_event = threading.Event()
        self._notifier = None      # lazy-loaded SyncTelegramNotifier
        self._own_symbol = own_symbol  # only alert for this symbol (Bug 2)

    def _get_client(self):
        if self._client is None:
            from db.client import get_client
            self._client = get_client()
        return self._client

    def _fetch_from_supabase(self) -> list:
        """Fetch all rows from bot_config. Raises on error."""
        client = self._get_client()
        result = (
            client.table("bot_config")
            .select(_CONFIG_FIELDS)
            .execute()
        )
        return result.data or []

    def _fetch_trend_config(self) -> dict:
        """39j: fetch the (single) trend_config row. Returns {} on empty table.
        Raises on error so the caller can keep last known values."""
        client = self._get_client()
        result = (
            client.table("trend_config")
            .select(_TREND_CONFIG_FIELDS)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return dict(rows[0]) if rows else {}

    def load_initial(self):
        """
        Load configuration from Supabase on startup.
        Raises if Supabase is unreachable (bot cannot start without config).
        """
        rows = self._fetch_from_supabase()
        trend_cfg = self._fetch_trend_config()
        with self._lock:
            self._configs = {row["symbol"]: row for row in rows}
            self._trend_config = trend_cfg
        logger.info(
            f"[bagholderai.config] Loaded config for {list(self._configs.keys())} from Supabase"
        )

    def get_config(self, symbol: str) -> dict:
        """Return current config dict for a symbol, or empty dict if not found."""
        with self._lock:
            return dict(self._configs.get(symbol, {}))

    def get_all_configs(self) -> dict:
        """Return a copy of all current configs keyed by symbol."""
        with self._lock:
            return {s: dict(c) for s, c in self._configs.items()}

    def get_trend_config_value(self, key: str):
        """39j: return the latest polled value for a trend_config field,
        or None if not present / not yet loaded. Callers must handle None."""
        with self._lock:
            return self._trend_config.get(key)

    def _get_notifier(self):
        """Lazy-load SyncTelegramNotifier (avoids import at module level)."""
        if self._notifier is None:
            try:
                from utils.telegram_notifier import SyncTelegramNotifier
                self._notifier = SyncTelegramNotifier()
            except Exception as e:
                logger.warning(f"[bagholderai.config] Could not init Telegram notifier: {e}")
        return self._notifier

    def _send_config_changes(self, symbol: str, changes: list):
        """Send a consolidated Telegram alert for all changed params of a symbol.

        changes: list of (key, old_val, new_val)
        """
        notifier = self._get_notifier()
        if not notifier:
            return
        lines = [f"⚙️ <b>CONFIG CHANGE DETECTED — {symbol}</b>"]
        for key, old_val, new_val in changes:
            lines.append(f"{key}: {old_val} → {new_val}")
        text = "\n".join(lines)
        try:
            notifier.send_message(text)
        except Exception as e:
            logger.warning(f"[bagholderai.config] Telegram alert failed: {e}")

    def refresh(self):
        """
        Re-read config from Supabase. Log any changed values and send Telegram alerts.
        On error: log warning and keep last known config.
        """
        try:
            rows = self._fetch_from_supabase()
        except Exception as e:
            logger.warning(
                f"[bagholderai.config] Supabase unreachable during refresh, "
                f"keeping last known config. Error: {e}"
            )
            return

        # 39j: trend_config polling is best-effort — failure must not drop the
        # fresh bot_config values we just fetched. Keep last known trend_config
        # on error, same pattern as bot_config above.
        try:
            new_trend_cfg = self._fetch_trend_config()
            trend_cfg_ok = True
        except Exception as e:
            logger.warning(
                f"[bagholderai.config] trend_config unreachable during refresh, "
                f"keeping last known values. Error: {e}"
            )
            new_trend_cfg = None
            trend_cfg_ok = False

        new_configs = {row["symbol"]: row for row in rows}
        # by_symbol: symbol -> [(key, old_val, new_val), ...]
        by_symbol: dict = {}
        # 43a: collect trend_config diffs under the lock, emit events outside.
        trend_diffs: list = []

        with self._lock:
            for symbol, new_cfg in new_configs.items():
                old_cfg = self._configs.get(symbol, {})
                for key, new_val in new_cfg.items():
                    old_val = old_cfg.get(key)
                    if old_val is not None and old_val != new_val:
                        logger.info(
                            f"[bagholderai.config] Config updated for {symbol}: "
                            f"{key} {old_val} → {new_val}"
                        )
                        # Only alert for own symbol (Bug 2)
                        if self._own_symbol is None or symbol == self._own_symbol:
                            by_symbol.setdefault(symbol, []).append((key, old_val, new_val))
            self._configs = new_configs

            # 39j: log trend_config diffs at INFO (no Telegram — the TF scan
            # loop already sends a consolidated alert on trend_config edits,
            # see brief 39g). Swapping the dict under the same lock as bot_config
            # keeps get_trend_config_value consistent with get_config.
            if trend_cfg_ok:
                old_trend = self._trend_config
                for key, new_val in new_trend_cfg.items():
                    old_val = old_trend.get(key)
                    if old_val is not None and old_val != new_val:
                        logger.info(
                            f"[bagholderai.config] trend_config updated: "
                            f"{key} {old_val} → {new_val}"
                        )
                        trend_diffs.append((key, old_val, new_val))
                self._trend_config = new_trend_cfg

        # Send one consolidated Telegram alert per symbol (Bug 3), outside lock
        for symbol, param_changes in by_symbol.items():
            self._send_config_changes(symbol, param_changes)
            # 43a: one structured event per symbol, grouping all diffs. Avoids
            # per-field event spam when the CEO edits several params in one save.
            log_event(
                severity="info",
                category="config",
                event="config_changed_bot_config",
                symbol=symbol,
                message=f"bot_config changed for {symbol}: {len(param_changes)} field(s)",
                details={
                    "changes": [
                        {"key": k, "old": str(o), "new": str(n)}
                        for k, o, n in param_changes
                    ],
                },
            )

        # 43a: NOTE — we intentionally do NOT emit config_changed_trend_config
        # here. This reader runs in every grid_runner process, so emitting
        # would produce N duplicate events per change. The trend_follower
        # loop is the single source of truth for trend_config diffs (it
        # already does the diff for Telegram alerts in 39g; the event is
        # added there in this same commit).
        _ = trend_diffs  # intentionally unused, kept for clarity

    def _refresh_loop(self):
        """Background thread: refresh config every CONFIG_REFRESH_INTERVAL seconds."""
        while not self._stop_event.wait(CONFIG_REFRESH_INTERVAL):
            self.refresh()

    def start_refresh_loop(self):
        """Start the background refresh thread (daemon so it dies with the main process)."""
        t = threading.Thread(target=self._refresh_loop, name="config-refresher", daemon=True)
        t.start()
        logger.info(
            f"[bagholderai.config] Config refresh loop started "
            f"(every {CONFIG_REFRESH_INTERVAL}s)"
        )

    def stop(self):
        """Signal the refresh loop to stop."""
        self._stop_event.set()
