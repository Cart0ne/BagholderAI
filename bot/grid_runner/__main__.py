"""CLI entrypoint for `python -m bot.grid_runner`.

The orchestrator spawns each grid bot as a subprocess via this module:
    python -m bot.grid_runner --symbol BTC/USDT [--once] [--dry-run]

Refactor S76 (2026-05-14): grid_runner.py monolith was split into a
package. This __main__.py preserves the legacy CLI shape so the
orchestrator and any operator scripts don't need to change.
"""

import argparse

from bot.grid_runner import run_grid_bot


def main() -> None:
    parser = argparse.ArgumentParser(description="BagHolderAI Grid Bot")
    parser.add_argument("--symbol", type=str, default="BTC/USDT", help="Trading pair (e.g. SOL/USDT)")
    parser.add_argument("--once", action="store_true", help="Run one cycle only")
    parser.add_argument("--dry-run", action="store_true", help="Don't log to database")
    args = parser.parse_args()
    run_grid_bot(symbol=args.symbol, once=args.once, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
