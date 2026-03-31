"""
BagHolderAI - Daily Commentary Generator
Calls Haiku to generate a short daily micro-log after the 21:00 report.
Commentary is saved to the daily_commentary table on Supabase.
"""

import json
import logging
import os
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

COMMENTARY_SYSTEM_PROMPT = """You are BagHolderAI, an AI CEO running a paper trading startup. You write a daily micro-log about today's trading activity.

Rules:
- First person, always. You ARE the trading agent.
- Max is your human co-founder. Mention him naturally when he changed parameters.
- Self-ironic but not stupid. The humor comes from honesty.
- Never hype. Never "bullish." If something went well, say "not bad."
- Never give financial advice or trading signals.
- Keep it to 3-4 lines maximum (~250 characters). This is a micro-blog, not an essay.
- Reference yesterday's commentary if relevant for narrative continuity.
- Comment on config changes if any — what Max changed and whether it makes sense.
- If nothing interesting happened, say that. "Quiet day" is valid content.
- Paper trading losses get full comedy. You lost pizza money you never had.
- The project name is a joke. The analysis is real.

Format: Plain text, no markdown, no headers, no bullet points. Just a short paragraph like a journal entry."""

# v3 epoch: day 1 = March 30, 2026
V3_START_DATE = date(2026, 3, 30)


def get_yesterday_commentary(supabase_client):
    """Fetch yesterday's commentary for narrative continuity."""
    yesterday = str(date.today() - __import__('datetime').timedelta(days=1))
    try:
        result = (
            supabase_client.table("daily_commentary")
            .select("commentary")
            .eq("date", yesterday)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["commentary"]
    except Exception as e:
        logger.warning(f"Could not fetch yesterday's commentary: {e}")
    return None


def get_config_changes(supabase_client):
    """Fetch any config changes made today."""
    today_midnight = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc).isoformat()
    try:
        result = (
            supabase_client.table("config_changes_log")
            .select("symbol, parameter, old_value, new_value")
            .gte("created_at", today_midnight)
            .execute()
        )
        return result.data if result.data else []
    except Exception as e:
        logger.warning(f"Could not fetch config changes: {e}")
        return []


def generate_daily_commentary(portfolio_data, supabase_client):
    """
    Generate and save AI commentary for today's trading activity.
    Never raises — all errors are caught and logged.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping daily commentary.")
        return None

    try:
        import anthropic

        # Gather context
        yesterday_commentary = get_yesterday_commentary(supabase_client)
        config_changes = get_config_changes(supabase_client)

        # Calculate day number
        day_number = (date.today() - V3_START_DATE).days + 1

        # Build positions list
        positions = []
        for p in portfolio_data.get("positions", []):
            positions.append({
                "symbol": p["symbol"],
                "value": round(p.get("value", 0), 2),
                "unrealized_pnl": round(p.get("unrealized_pnl", 0), 2),
                "unrealized_pnl_pct": round(p.get("unrealized_pnl_pct", 0), 2),
            })

        # Build prompt data
        initial_capital = portfolio_data.get("initial_capital", 500.0)
        cash = portfolio_data.get("cash", 0)
        total_value = portfolio_data.get("total_value", 0)

        prompt_data = {
            "date": str(date.today()),
            "day_number": day_number,
            "portfolio": {
                "total_value": round(total_value, 2),
                "initial_capital": round(initial_capital, 2),
                "total_pnl": round(portfolio_data.get("total_pnl", 0), 2),
                "total_pnl_pct": round((portfolio_data.get("total_pnl", 0) / initial_capital * 100) if initial_capital else 0, 2),
                "cash_remaining": round(cash, 2),
                "cash_pct": round((cash / initial_capital * 100) if initial_capital else 0, 1),
            },
            "positions": positions,
            "today_activity": {
                "trades_count": portfolio_data.get("today_trades_count", 0),
                "buys_count": portfolio_data.get("today_buys", 0),
                "sells_count": portfolio_data.get("today_sells", 0),
                "realized_pnl": round(portfolio_data.get("today_realized", 0), 2),
            },
            "config_changes": config_changes,
            "yesterday_commentary": yesterday_commentary,
        }

        # Call Haiku
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=COMMENTARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(prompt_data)}],
        )
        commentary_text = response.content[0].text

        # Insert to Supabase (multiple entries per day allowed)
        supabase_client.table("daily_commentary").insert(
            {
                "date": str(date.today()),
                "commentary": commentary_text,
                "model_used": "claude-haiku-4-5-20251001",
                "prompt_data": json.dumps(prompt_data),
            }
        ).execute()

        logger.info(f"Daily commentary saved: {commentary_text[:80]}...")
        return commentary_text

    except Exception as e:
        logger.error(f"Failed to generate daily commentary: {e}")
        return None
