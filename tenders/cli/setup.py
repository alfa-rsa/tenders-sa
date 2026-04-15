"""tenders setup and stats commands."""

import os
import sys

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tenders.cache import Cache


@click.command("setup")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"))
def setup(cache_db):
    """Show setup instructions and verify configuration."""
    click.echo("=== tenders-sa Setup ===\n")

    db_path = os.path.abspath(os.path.expanduser(cache_db))
    click.echo(f"Cache DB: {db_path}")

    # Ensure DB is initialized
    cache = Cache(cache_db)
    click.echo("[OK] Cache DB initialized")

    click.echo("\n--- Environment Variables ---")
    for var in ["ETENDERS_BASE_URL", "ETENDERS_TIMEOUT", "TENDERS_DB_PATH"]:
        val = os.getenv(var, "(not set)")
        click.echo(f"  {var}={val}")

    click.echo("\n--- Quick Start ---")
    click.echo("1. Fetch active tenders:")
    click.echo("   tenders new --fetch --since 30")
    click.echo("")
    click.echo("2. Search cached tenders:")
    click.echo("   tenders search -k 'IT' -p 'Gauteng'")
    click.echo("")
    click.echo("3. Add to watchlist:")
    click.echo("   tenders watch -k 'software' -p 'KwaZulu-Natal'")
    click.echo("")
    click.echo("4. Set up daily cron (7am SAST):")
    click.echo("   tenders daily-monitor --setup-cron")


@click.command("stats")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"))
def stats(cache_db):
    """Show cache statistics."""
    cache = Cache(cache_db)
    s = cache.stats()

    click.echo(f"Total tenders:    {s['total_tenders']}")
    click.echo(f"Active tenders:   {s['active_tenders']}")
    click.echo(f"Total contacts:   {s['total_contacts']}")
    click.echo(f"Pipeline entries: {s['pipeline_entries']}")

    last = s.get("last_fetch")
    if last:
        click.echo(f"\nLast fetch:")
        click.echo(f"  At:      {last['fetched_at']}")
        click.echo(f"  Range:   {last['date_from']} -> {last['date_to']}")
        click.echo(f"  Fetched: {last['tender_count']} tenders ({last['new_count']} new)")
        if last.get("error"):
            click.echo(f"  Error:   {last['error']}")
    else:
        click.echo("\nNo fetches yet. Run:")
        click.echo("  tenders new --fetch --since 30")