"""tenders history and winners commands."""

import os
import sys

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tenders.cache import Cache
from tenders.search import tender_history, winning_suppliers
from tenders.contacts import format_tenders_text


@click.command("history")
@click.option("--dept", "department", help="Department to search")
@click.option("--category", help="Category to search")
@click.option("--since", default="2024-01-01", help="Start date (YYYY-MM-DD)")
@click.option("--limit", default=20)
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"))
def history(department, category, since, limit, cache_db):
    """Show historical tenders for a department or category."""
    cache = Cache(cache_db)
    tenders = tender_history(
        cache,
        department=department,
        category=category,
        since=since,
        limit=limit,
    )

    if not tenders:
        click.echo("No historical tenders found.")
        return

    click.echo(format_tenders_text(tenders))
    click.echo(f"\n--- {len(tenders)} historical tenders since {since} ---")


@click.command("winners")
@click.option("--dept", "department", help="Filter by department")
@click.option("--category", help="Filter by category")
@click.option("--since", default="2024-01-01", help="Start date (YYYY-MM-DD)")
@click.option("--limit", default=20)
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"))
def winners(department, category, since, limit, cache_db):
    """Show past awarded tenders (for competitive intelligence)."""
    cache = Cache(cache_db)
    past = winning_suppliers(
        cache,
        department=department,
        category=category,
        since=since,
        limit=limit,
    )

    if not past:
        click.echo("No awarded tenders found.")
        return

    for i, t in enumerate(past, 1):
        click.echo(f"{i}. {t['title'][:65]}")
        click.echo(f"   [D] {t['department']}")
        click.echo(f"   R{t['value']:,.0f} | [D] {t['close_date']}")
        click.echo(f"   OCID: {t['ocid']}")
        click.echo("")
