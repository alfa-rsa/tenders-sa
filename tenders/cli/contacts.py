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
@click.option("--export", "fmt", type=click.Choice(["csv"]), default=None, help="Export format")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"))
def contacts(keyword, province, department, fmt, cache_db):
    """Extract contact information from tenders."""
    cache = Cache(cache_db)
    contact_list = extract_contacts(
        cache,
        keyword=keyword,
        province=province,
        department=department,
    )

    if fmt == "csv":
        click.echo(contacts_to_csv(contact_list))
    else:
        click.echo(format_contacts_text(contact_list))
        click.echo(f"\n--- {len(contact_list)} contacts ---")