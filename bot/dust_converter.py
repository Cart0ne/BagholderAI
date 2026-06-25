"""Dust-to-BNB conversion — Binance `POST /sapi/v1/asset/dust`.

MAINNET-ONLY by nature: the Binance Spot **testnet** (testnet.binance.vision)
does not implement the dust-conversion endpoint, so on testnet/paper this is
a guarded no-op. Context (brief DUST, S109 scope "evento + stub"):

`dust_handler` writes a sub-minNotional residue off the bot's *books* (DB +
in-memory state) so the grid stops retrying an unsellable order — but on a
real wallet those coins stay put. Over time, with fee-in-base-coin on every
BUY, that residue accumulates and the wallet drifts from the DB. On mainnet
this converter batch-sweeps those residues into BNB so the drift closes.

Scope today (S109): the guard + the module + the extension point. The real
conversion call and the wallet<->DB reconciliation of the converted dust are
a go-live task (brief DUST point 3) — they need a live wallet to be testable,
so wiring them now would be code we'd rewrite. This stub makes that explicit
instead of pretending to convert.
"""

import logging

from config.settings import TradingMode, ExchangeConfig
from db.event_logger import log_event

logger = logging.getLogger("bagholderai.dust")


def is_mainnet_live() -> bool:
    """True only on a real mainnet live session (not paper, not testnet)."""
    return TradingMode.is_live() and not ExchangeConfig.TESTNET


def convert_dust_to_bnb(exchange, assets=None) -> dict:
    """Convert sub-minNotional dust balances to BNB on mainnet.

    Guarded: a no-op on paper or testnet (the endpoint is absent there).
    Returns a result dict so callers/tests can assert what happened without
    side effects:
        {"converted": bool, "reason": str}

    `assets`: optional list of base-coin tickers to convert; None => let the
    (future) mainnet implementation discover convertible dust from the wallet.
    """
    if not is_mainnet_live():
        logger.info(
            "[dust] convert_dust_to_bnb skipped (mainnet-only; "
            f"is_live={TradingMode.is_live()}, testnet={ExchangeConfig.TESTNET})."
        )
        return {"converted": False, "reason": "not-mainnet-live"}

    # MAINNET path. The real call —
    #   exchange.sapi_post_asset_dust({"asset": [...]})
    # plus reconciliation of the converted residue against the DB (brief DUST
    # point 3) — lands at go-live, when there is a live wallet to test against.
    logger.warning(
        "[dust] convert_dust_to_bnb invoked on mainnet, but the real "
        "conversion is not wired yet (go-live task, brief DUST point 3)."
    )
    log_event(
        severity="warn",
        category="trade",
        event="DUST_CONVERT_STUB",
        message="convert_dust_to_bnb called on mainnet — not yet implemented",
        details={"assets": assets},
    )
    return {"converted": False, "reason": "mainnet-not-implemented"}
