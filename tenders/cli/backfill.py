"""tenders backfill command — fetch historical tenders in monthly steps."""

import datetime
import os
import sys

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tenders.client import TenderClient
from tenders.cache import Cache
from tenders.search import fetch_and_cache


@click.command("backfill")
@click.option("--months", default=3, type=int, help="How many months back to fetch (default: 3)")
@click.option("--step-days", default=30, type=int, help="Days per fetch step (default: 30)")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"), help="Path to cache DB")
def backfill(months, step_days, cache_db):
    """Fetch historical tenders going back N months.

    The API only serves ~90 days of data at a time. This command
    steps backward month-by-month to build a historical dataset.
    """
    cache = Cache(cache_db)
    client = TenderClient()

    today = datetime.date.today()
    total_fetched = 0
    total_new = 0
    errors = 0

    click.echo(f"Backfilling last {months} months ({step_days}-day steps)...\n")

    # Walk backward in steps
    current_to = today
    for i in range(months):
        # Each step covers step_days before current_to
        current_from = current_to - datetime.timedelta(days=step_days)
        from_str = current_from.isoformat()
        to_str = current_to.isoformat()

        # Last step: don't overshoot today
        if i == months - 1:
            to_str = today.isoformat()

        click.echo(f"[{i+1}/{months}] {from_str} -> {to_str}...", err=True)

        try:
            fetched, new_count = fetch_and_cache(
                from_str, to_str, client, cache,
            )
            total_fetched += fetched
            total_new += new_count
            click.echo(f"  +{fetched} fetched ({new_count} new)", err=True)
        except Exception as e:
            errors += 1
            click.echo(f"  ERROR: {e}", err=True)

        # Move the window back
        current_to = current_from - datetime.timedelta(days=1)

    click.echo(f"\nBackfill complete:")
    click.echo(f"  Total fetched: {total_fetched}")
    click.echo(f"  New entries:  {total_new}")
    if errors:
        click.echo(f"  Errors:       {errors}")
