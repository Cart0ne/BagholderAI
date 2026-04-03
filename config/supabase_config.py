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

logger = logging.getLogger("bagholderai.config")

CONFIG_REFRESH_INTERVAL = 300  # seconds between config refreshes


# Fields to read from bot_config
_CONFIG_FIELDS = (
    "symbol,capital_allocation,grid_levels,grid_lower,grid_upper,"
    "profit_target_pct,reserve_floor_pct,capital_per_trade,"
    "is_active,buy_pct,sell_pct,grid_mode"
)


class SupabaseConfigReader:
    """
    Reads and periodically refreshes bot configuration from Supabase.

    Usage:
        reader = SupabaseConfigReader()
        reader.load_initial()          # call once on startup
        reader.start_refresh_loop()    # starts background thread

        cfg = reader.get_config("BTC/USDT")  # returns dict or None
    """

    def __init__(self):
        self._configs: dict = {}   # symbol -> raw row dict from bot_config
        self._lock = threading.Lock()
        self._client = None
        self._stop_event = threading.Event()
        self._notifier = None      # lazy-loaded SyncTelegramNotifier

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

    def load_initial(self):
        """
        Load configuration from Supabase on startup.
        Raises if Supabase is unreachable (bot cannot start without config).
        """
        rows = self._fetch_from_supabase()
        with self._lock:
            self._configs = {row["symbol"]: row for row in rows}
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

    def _get_notifier(self):
        """Lazy-load SyncTelegramNotifier (avoids import at module level)."""
        if self._notifier is None:
            try:
                from utils.telegram_notifier import SyncTelegramNotifier
                self._notifier = SyncTelegramNotifier()
            except Exception as e:
                logger.warning(f"[bagholderai.config] Could not init Telegram notifier: {e}")
        return self._notifier

    def _send_config_alert(self, symbol: str, param: str, old_val, new_val):
        """Send a Telegram alert for a single changed config parameter."""
        notifier = self._get_notifier()
        if not notifier:
            return
        text = (
            f"⚙️ <b>CONFIG UPDATED — {symbol}</b>\n"
            f"Parameter: {param}\n"
            f"Old: {old_val}\n"
            f"New: {new_val}\n"
            f"Source: dashboard"
        )
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

        new_configs = {row["symbol"]: row for row in rows}
        changes = []  # collect before acquiring lock to send outside lock

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
                        changes.append((symbol, key, old_val, new_val))
            self._configs = new_configs

        # Send Telegram alerts outside the lock (network call)
        for symbol, key, old_val, new_val in changes:
            self._send_config_alert(symbol, key, old_val, new_val)

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
