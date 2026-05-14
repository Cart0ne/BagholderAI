"""Hot-reload of Supabase bot_config / trend_config values onto the live bot.

Read once per tick from `run_grid_bot`'s main loop. The bot's safety params
(stop_buy_drawdown_pct, dead_zone_hours, TF stops, profit-lock, trailing-stop,
greed-decay tiers, allocated_at) all flow through here. Logs at INFO when a
value actually changes; silent on no-op.

Refactor S76 (2026-05-14): extracted from grid_runner.py monolith.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.supabase_config import SupabaseConfigReader
    from bot.grid.grid_bot import GridBot

logger = logging.getLogger("bagholderai.runner")


def _sync_config_to_bot(reader: "SupabaseConfigReader", bot: "GridBot", symbol: str):
    """
    Apply the latest Supabase config values to the running bot.
    Only updates fields that are safe to change mid-run without a restart.
    """
    sb_cfg = reader.get_config(symbol)
    if not sb_cfg:
        return
    if "buy_pct" in sb_cfg and sb_cfg["buy_pct"] is not None:
        bot.buy_pct = float(sb_cfg["buy_pct"])
    if "sell_pct" in sb_cfg and sb_cfg["sell_pct"] is not None:
        bot.sell_pct = float(sb_cfg["sell_pct"])
    if "capital_per_trade" in sb_cfg and sb_cfg["capital_per_trade"] is not None:
        bot.capital_per_trade = float(sb_cfg["capital_per_trade"])
    # Brief s70 FASE 2: grid_mode rimosso dallo schema bot_config.
    # Avg-cost only — niente più switching dinamico fixed↔percentage.
    if "skim_pct" in sb_cfg and sb_cfg["skim_pct"] is not None:
        bot.skim_pct = float(sb_cfg["skim_pct"])
    if "idle_reentry_hours" in sb_cfg and sb_cfg["idle_reentry_hours"] is not None:
        bot.idle_reentry_hours = float(sb_cfg["idle_reentry_hours"])
    if "profit_target_pct" in sb_cfg and sb_cfg["profit_target_pct"] is not None:
        bot.min_profit_pct = float(sb_cfg["profit_target_pct"])
    if "stop_buy_drawdown_pct" in sb_cfg and sb_cfg["stop_buy_drawdown_pct"] is not None:
        # 39b: per-coin manual stop-buy threshold (hot-reload via config refresh).
        # Changing the value does NOT reset _stop_buy_active — the flag clears
        # only on a profitable sell (event-based hysteresis).
        bot.stop_buy_drawdown_pct = float(sb_cfg["stop_buy_drawdown_pct"])
    if "stop_buy_unlock_hours" in sb_cfg and sb_cfg["stop_buy_unlock_hours"] is not None:
        # 75b: per-coin unlock timer for the stop-buy guard. Hot-reload like
        # the other safety params. 0 disables the timer; the existing event-
        # based reset (profitable sell) still applies.
        bot.stop_buy_unlock_hours = float(sb_cfg["stop_buy_unlock_hours"])
    if "dead_zone_hours" in sb_cfg and sb_cfg["dead_zone_hours"] is not None:
        # 74b (S74b): per-coin dead-zone recalibrate threshold (hot-reload).
        # Read fresh on every tick via self.dead_zone_hours.
        bot.dead_zone_hours = float(sb_cfg["dead_zone_hours"])
    if "is_active" in sb_cfg:
        bot.is_active = bool(sb_cfg["is_active"])
    if "pending_liquidation" in sb_cfg:
        # pending_liquidation is monotonic-sticky: once the bot flags itself
        # for cleanup (e.g. 39a stop-loss), don't let a DB poll overwrite it
        # back to False. Clearing happens via the grid_runner UPDATE after the
        # liquidation branch runs + bot exit + fresh start.
        db_flag = bool(sb_cfg.get("pending_liquidation", False))
        if db_flag and not bot.pending_liquidation:
            bot.pending_liquidation = True
    if "managed_by" in sb_cfg and sb_cfg.get("managed_by"):
        bot.managed_by = sb_cfg["managed_by"]

    # 39j: hot-reload of TF safety params from trend_config. Only TF bots use
    # these thresholds (grid_bot gates the checks on managed_by); manual bots
    # keep their own stop_buy_drawdown_pct (39b). Log at INFO on change —
    # Telegram notification is owned by the TF scan loop (39g), not here.
    if bot.managed_by in ("tf", "tf_grid"):
        tf_slp = reader.get_trend_config_value("tf_stop_loss_pct")
        if tf_slp is not None:
            new_slp = float(tf_slp)
            if new_slp != bot.tf_stop_loss_pct:
                logger.info(
                    f"[{symbol}] tf_stop_loss_pct updated: "
                    f"{bot.tf_stop_loss_pct} → {new_slp}"
                )
                bot.tf_stop_loss_pct = new_slp

        tf_tpp = reader.get_trend_config_value("tf_take_profit_pct")
        if tf_tpp is not None:
            new_tpp = float(tf_tpp)
            if new_tpp != bot.tf_take_profit_pct:
                logger.info(
                    f"[{symbol}] tf_take_profit_pct updated: "
                    f"{bot.tf_take_profit_pct} → {new_tpp}"
                )
                bot.tf_take_profit_pct = new_tpp

        # 45f: profit lock enable + threshold — hot-reloaded so the CEO can
        # flip the switch from the dashboard without restarting the bot.
        tf_ple = reader.get_trend_config_value("tf_profit_lock_enabled")
        if tf_ple is not None:
            new_ple = bool(tf_ple)
            if new_ple != bot.tf_profit_lock_enabled:
                logger.info(
                    f"[{symbol}] tf_profit_lock_enabled updated: "
                    f"{bot.tf_profit_lock_enabled} → {new_ple}"
                )
                bot.tf_profit_lock_enabled = new_ple

        tf_plp = reader.get_trend_config_value("tf_profit_lock_pct")
        if tf_plp is not None:
            new_plp = float(tf_plp)
            if new_plp != bot.tf_profit_lock_pct:
                logger.info(
                    f"[{symbol}] tf_profit_lock_pct updated: "
                    f"{bot.tf_profit_lock_pct} → {new_plp}"
                )
                bot.tf_profit_lock_pct = new_plp

        # 45g: hot-reload kill-switch and global N (so CEO can change either
        # from the dashboard / SQL without restarting the orchestrator).
        tf_xen = reader.get_trend_config_value("tf_exit_after_n_enabled")
        if tf_xen is not None:
            new_xen = bool(tf_xen)
            if new_xen != bot.tf_exit_after_n_enabled:
                logger.info(
                    f"[{symbol}] tf_exit_after_n_enabled updated: "
                    f"{bot.tf_exit_after_n_enabled} → {new_xen}"
                )
                bot.tf_exit_after_n_enabled = new_xen

        tf_xn = reader.get_trend_config_value("tf_exit_after_n_positive_sells")
        if tf_xn is not None:
            new_xn = int(tf_xn)
            if new_xn != bot.tf_exit_after_n_default:
                logger.info(
                    f"[{symbol}] tf_exit_after_n_positive_sells updated: "
                    f"{bot.tf_exit_after_n_default} → {new_xn}"
                )
                bot.tf_exit_after_n_default = new_xn

        # 45g: per-coin override lives on bot_config — re-read each tick so
        # CEO's SQL UPDATEs propagate without restart.
        new_override = sb_cfg.get("tf_exit_after_n_override")
        new_override_int = int(new_override) if new_override is not None else None
        if new_override_int != bot.tf_exit_after_n_override:
            logger.info(
                f"[{symbol}] tf_exit_after_n_override updated: "
                f"{bot.tf_exit_after_n_override} → {new_override_int}"
            )
            bot.tf_exit_after_n_override = new_override_int

        # 51b: hot-reload trailing-stop knobs (activation + trailing pct).
        # Same pattern as the other safety params — CEO changes the DB
        # value, the next tick picks it up. 0 disables the feature
        # immediately (peak tracking branch in grid_bot keys off it).
        tf_tsa = reader.get_trend_config_value("tf_trailing_stop_activation_pct")
        if tf_tsa is not None:
            new_tsa = float(tf_tsa)
            if new_tsa != bot.tf_trailing_stop_activation_pct:
                logger.info(
                    f"[{symbol}] tf_trailing_stop_activation_pct updated: "
                    f"{bot.tf_trailing_stop_activation_pct} → {new_tsa}"
                )
                bot.tf_trailing_stop_activation_pct = new_tsa

        tf_tsp = reader.get_trend_config_value("tf_trailing_stop_pct")
        if tf_tsp is not None:
            new_tsp = float(tf_tsp)
            if new_tsp != bot.tf_trailing_stop_pct:
                logger.info(
                    f"[{symbol}] tf_trailing_stop_pct updated: "
                    f"{bot.tf_trailing_stop_pct} → {new_tsp}"
                )
                bot.tf_trailing_stop_pct = new_tsp

        # 42a: greed_decay_tiers is global (trend_config); allocated_at is
        # per-bot (bot_config). Both are re-read each tick so UI edits and
        # SWAP re-allocations propagate without restart.
        new_tiers = reader.get_trend_config_value("greed_decay_tiers")
        if new_tiers is not None and new_tiers != bot.greed_decay_tiers:
            logger.info(
                f"[{symbol}] greed_decay_tiers updated: "
                f"{bot.greed_decay_tiers} → {new_tiers}"
            )
            bot.greed_decay_tiers = new_tiers

        raw_alloc = sb_cfg.get("allocated_at")
        if raw_alloc:
            try:
                new_alloc = datetime.fromisoformat(str(raw_alloc).replace("Z", "+00:00"))
                if new_alloc != bot.allocated_at:
                    logger.info(
                        f"[{symbol}] allocated_at updated: "
                        f"{bot.allocated_at} → {new_alloc}"
                    )
                    bot.allocated_at = new_alloc
            except Exception as e:
                logger.warning(f"[{symbol}] allocated_at parse error: {e}")
