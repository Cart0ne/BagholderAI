"""BagHolderAI - Sherpa (Sprint 1, parameter writer).

Sherpa reads the latest sentinel_scores row, translates risk_score into
proposed Grid parameters (buy_pct / sell_pct / idle_reentry_hours), and
either writes them to bot_config (LIVE) or logs the would-be change to
sherpa_proposals (DRY_RUN, default).

Module layout:
    main.py             entry point (sync loop, every 120s)
    parameter_rules.py  base(regime) + delta(fast_signals) -> params
    config_writer.py    bot_config UPDATE + config_changes_log INSERT
    cooldown_manager.py 24h cooldown after a non-Sherpa change
"""
