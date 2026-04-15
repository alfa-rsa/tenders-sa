"""tenders watch commands."""

import os
import sys

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tenders.cache import Cache


@click.command("watch")
@click.option("-k", "--keyword", required=True, help="Keyword to watch")
@click.option("-p", "--province", default="", help="Province filter")
@click.option("-c", "--category", default="", help="Category filter")
@click.option("--min-value", type=float, default=0, help="Minimum value filter")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"))
def watch(keyword, province, category, min_value, cache_db):
    """Add a keyword to your watchlist."""
    cache = Cache(cache_db)
    cache.add_watch(keyword, province, category, min_value)
    click.echo(f"[OK] Watching: {keyword}")
    if province:
        click.echo(f"  Province: {province}")
    if category:
        click.echo(f"  Category: {category}")
    if min_value:
        click.echo(f"  Min value: R{min_value:,.0f}")


@click.command("watch-list")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"))
def watch_list(cache_db):
    """Show current watchlist."""
    cache = Cache(cache_db)
    items = cache.list_watch()

    if not items:
        click.echo("Watchlist is empty. Add keywords with:")
        click.echo("  tenders watch -k <keyword>")
        return

    click.echo(f"Watching {len(items)} keyword(s):\n")
    for item in items:
        click.echo(f"  [{item['id']}] {item['keyword']}")
        if item["province"]:
            click.echo(f"      Province: {item['province']}")
        if item["min_value"]:
            click.echo(f"      Min value: R{item['min_value']:,.0f}")


@click.command("watch-remove")
@click.option("--id", "watch_id", required=True, type=int, help="Watchlist entry ID to remove")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"))
def watch_remove(watch_id, cache_db):
    """Remove a keyword from the watchlist."""
    cache = Cache(cache_db)
    cache.remove_watch(watch_id)
    click.echo(f"[OK] Removed watch entry {watch_id}")