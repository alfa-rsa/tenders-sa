#!/usr/bin/env python3
"""
Daily monitor script — called by cron at 7am SAST.
Fetches tenders new since last run, filters by watchlist,
and sends a WhatsApp digest via OpenClaw.
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tenders.client import TenderClient
from tenders.cache import Cache
from tenders.search import fetch_and_cache, new_tenders
from tenders.contacts import format_tenders_text


CACHE_DB = os.getenv("TENDERS_DB_PATH", "./cache.db")
OPENCLAW_SESSION = os.getenv("OPENCLAW_SESSION", "main")


def build_digest(tenders: list, watch_items: list) -> str:
    """Build WhatsApp digest text."""
    if not tenders:
        return "📋 *tenders-sa Daily*\n\nNo new tenders matching your watchlist today. ✅"

    lines = [f"📋 *tenders-sa Daily Digest*\n{len(tenders)} new tender(s) found:\n"]

    for t in tenders[:10]:  # cap at 10
        lines.append(f"📌 {t.title[:65]}")
        if t.department:
            lines.append(f"   🏛️ {t.department}")
        if t.province:
            lines.append(f"   📍 {t.province}")
        if t.value_amount > 0:
            lines.append(f"   💰 R{t.value_amount:,.0f}")
        if t.close_date:
            days_left = ""
            try:
                close = datetime.date.fromisoformat(t.close_date)
                delta = (close - datetime.date.today()).days
                if delta > 0:
                    days_left = f" (closes in {delta} days)"
            except Exception:
                pass
            lines.append(f"   ⏰ {t.close_date}{days_left}")
        if t.contacts and t.contacts[0].email:
            c = t.contacts[0]
            lines.append(f"   📧 {c.email}")
        lines.append("")

    if len(tenders) > 10:
        lines.append(f"...and {len(tenders) - 10} more. Run `tenders search` for full list.")

    return "\n".join(lines)


def run():
    """Main daily monitor entry point."""
    cache = Cache(CACHE_DB)

    # Determine date range
    last = cache.last_fetch()
    if last:
        # Start from the last fetch date
        date_from = last["date_from"]
        date_to = datetime.date.today().isoformat()
        click.echo(f"Fetching since last run: {date_from}")
    else:
        # First run — default to last 7 days
        date_from = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        date_to = datetime.date.today().isoformat()
        click.echo(f"First run — fetching last 7 days: {date_from} → {date_to}")

    # Fetch from API
    client = TenderClient()
    total, new_count = fetch_and_cache(date_from, date_to, client, cache)
    click.echo(f"Fetched {total} total, {new_count} new tenders.")

    # Get watchlist
    watch_items = cache.list_watch()
    if not watch_items:
        click.echo("No watchlist set. Add keywords: tenders watch -k <keyword>")
        return

    # Filter new tenders by watchlist
    all_new = new_tenders(cache, days=30)  # last 30 days of fetched tenders
    matched = []
    for t in all_new:
        for w in watch_items:
            kw = w["keyword"].lower()
            if (kw in t.title.lower() or kw in t.description.lower() or
                    kw in t.category.lower()):
                if w["province"] and w["province"].lower() not in t.province.lower():
                    continue
                matched.append(t)
                break

    # Build and send digest
    digest = build_digest(matched, watch_items)
    click.echo(digest)

    # TODO: send via OpenClaw sessions_send when WhatsApp target is configured
    click.echo("\n[Digest would be sent to WhatsApp here]")


if __name__ == "__main__":
    import click
    run()