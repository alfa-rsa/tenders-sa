"""tenders contacts command."""

import os
import sys

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tenders.cache import Cache
from tenders.contacts import extract_contacts, format_contacts_text, contacts_to_csv


@click.command()
@click.option("-k", "--keyword", help="Filter by keyword")
@click.option("-p", "--province", help="Filter by province")
@click.option("-d", "--department", help="Filter by department/buyer")
@click.option("--export", "fmt", flag_value="csv", help="Export as CSV")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"))
def contacts(keyword, province, department, fmt, cache_db):
    """Extract contact information from tenders."""
    cache = Cache(cache_db)
    contacts = extract_contacts(
        cache,
        keyword=keyword,
        province=province,
        department=department,
    )

    if fmt == "csv":
        click.echo(contacts_to_csv(contacts))
    else:
        click.echo(format_contacts_text(contacts))
        click.echo(f"\n--- {len(contacts)} contacts ---")
