"""tenders search and tenders new commands."""

import os
import sys
import json

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tenders.client import TenderClient
from tenders.cache import Cache
from tenders.search import search_tenders, fetch_and_cache, new_tenders
from tenders.contacts import format_tenders_text


@click.command()
@click.option("-k", "--keyword", help="Search keyword (title/description/category)")
@click.option("-p", "--province", help="Province filter")
@click.option("-d", "--department", help="Department filter")
@click.option("-c", "--category", help="Category filter")
@click.option("-s", "--status", default="active", help="Status filter (default: active)")
@click.option("--min-value", type=float, help="Minimum tender value in ZAR")
@click.option("--limit", default=20, help="Max results to return")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"), help="Path to cache DB")
def search(keyword, province, department, category, status, min_value, limit, cache_db):
    """Search cached tenders with filters."""
    cache = Cache(cache_db)
    tenders = search_tenders(
        cache,
        keyword=keyword,
        province=province,
        department=department,
        category=category,
        status=status,
        min_value=min_value,
        limit=limit,
    )

    if not tenders:
        click.echo("No tenders found matching your criteria.")
        return

    click.echo(format_tenders_text(tenders))
    click.echo(f"\n--- {len(tenders)} results ---")


@click.command()
@click.option("-k", "--keyword", help="Filter by keyword (can be used multiple times)", multiple=True)
@click.option("-p", "--province", help="Filter by province")
@click.option("-s", "--since", default="1", help="Days since last fetch (default: 1)")
@click.option("--limit", default=50, help="Max results")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"), help="Path to cache DB")
@click.option("--fetch/--no-fetch", default=False, help="Also fetch new tenders from API before searching")
@click.option("--date-from", help="Fetch from date (YYYY-MM-DD)")
@click.option("--date-to", default=None, help="Fetch to date (YYYY-MM-DD, default: today)")
def new(keyword, province, since, limit, cache_db, fetch, date_from, date_to):
    """Show tenders new since last fetch (or fetch them first)."""
    import datetime
    cache = Cache(cache_db)

    if fetch:
        client = TenderClient()
        to_date = date_to or datetime.date.today().isoformat()
        from_date = date_from or (datetime.date.today() - datetime.timedelta(days=int(since))).isoformat()

        def progress(page, _):
            click.echo(f"  Fetching page {page}...", err=True)

        click.echo(f"Fetching tenders from {from_date} to {to_date}...", err=True)
        total, new_count = fetch_and_cache(
            from_date, to_date, client, cache,
            progress_callback=progress,
        )
        click.echo(f"Done — fetched {total} tenders, {new_count} new.\n", err=True)

    kws = " ".join(keyword) if keyword else None
    tenders = new_tenders(cache, days=int(since), keyword=kws, province=province)

    if keyword:
        # Re-filter by each keyword
        kws = [kw.lower() for kw in keyword]
        tenders = [t for t in tenders
                   if any(kw in (t.title + t.description + t.category).lower() for kw in kws)]

    tenders = sorted(tenders, key=lambda t: t.close_date or "9999")[:limit]

    if not tenders:
        click.echo("No new tenders found.")
        return

    click.echo(format_tenders_text(tenders))
    click.echo(f"\n--- {len(tenders)} new tenders ---")
