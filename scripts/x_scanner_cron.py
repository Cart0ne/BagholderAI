"""
BagHolderAI — X Scanner Cron Wrapper
=====================================
Lancia lo scan settimanale di @BagHolderAI e manda un riassunto Telegram
al bot privato di Max. Pensato per essere chiamato da cron (sabato 08:00).

Usage:
    python3.13 -m scripts.x_scanner_cron

Exit codes:
    0 = scan ok (anche se nessun post nuovo)
    1 = errore fatale (scan fallito o eccezione non gestita)
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.x_stats_refresh import main as run_scan
from utils.telegram_notifier import TelegramNotifier


def format_telegram_message(summary: dict) -> str:
    if summary["new_posts"] == 0:
        return (
            "📊 <b>X Scanner Weekly</b>\n"
            "Nessun post nuovo dall'ultimo scan."
        )

    lines = [
        "📊 <b>X Scanner Weekly</b>",
        f"Post nuovi: <b>{summary['new_posts']}</b> "
        f"({summary['originals']} originali · {summary['replies']} reply)",
        f"Impressions totali: <b>{summary['total_impressions']:,}</b>",
    ]

    top = summary.get("top_post")
    if top:
        excerpt = top["text"].replace("\n", " ").strip()
        if len(excerpt) > 120:
            excerpt = excerpt[:120] + "..."
        lines.append(
            f"\n🏆 Top post (<b>{top['impressions']:,}</b> impr):\n"
            f"<i>{excerpt}</i>\n"
            f"{top['url']}"
        )

    if summary.get("report_path"):
        report_name = Path(summary["report_path"]).name
        lines.append(f"\nReport: <code>{report_name}</code>")

    return "\n".join(lines)


async def send_telegram(text: str) -> None:
    notifier = TelegramNotifier()
    await notifier.send_message(text)


def main() -> int:
    try:
        # Simulate CLI invocation: x_stats_refresh.main() uses argparse
        # but we want default (incremental) mode — clear sys.argv to avoid
        # picking up unintended flags from the parent call.
        sys.argv = ["x_stats_refresh"]
        summary = run_scan()
    except SystemExit as e:
        # run_scan() may sys.exit(1) on auth/API errors
        code = e.code if isinstance(e.code, int) else 1
        try:
            asyncio.run(send_telegram(
                f"⚠️ <b>X Scanner Weekly</b>\nScan fallito (exit {code}). Vedi log."
            ))
        except Exception:
            pass
        return code or 1
    except Exception as e:
        err = traceback.format_exc()
        print(err, file=sys.stderr)
        try:
            asyncio.run(send_telegram(
                f"⚠️ <b>X Scanner Weekly</b>\nEccezione: <code>{type(e).__name__}: {e}</code>"
            ))
        except Exception:
            pass
        return 1

    msg = format_telegram_message(summary)
    asyncio.run(send_telegram(msg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
