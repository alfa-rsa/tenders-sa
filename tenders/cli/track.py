"""tenders track and pipeline commands."""

import os
import sys

import click

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from tenders.cache import Cache


STAGES = ["Identified", "Briefing Registered", "Proposal Submitted", "Won", "Lost"]


@click.command()
@click.option("--tender-id", required=True, help="Tender OCID")
@click.option("--stage", type=click.Choice(STAGES), required=True, help="Pipeline stage")
@click.option("--notes", default="", help="Notes")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"))
def track(tender_id, stage, notes, cache_db):
    """Track a tender in the pipeline."""
    cache = Cache(cache_db)
    tender = cache.get_tender(tender_id)
    if not tender:
        click.echo(f"Tender {tender_id} not found in cache. Fetch it first.", err=True)
        raise click.exit(1)
    cache.set_pipeline_stage(tender_id, stage, notes)
    click.echo(f"✓ {tender.title[:60]}")
    click.echo(f"  Stage: {stage}")


@click.command("pipeline")
@click.option("--dept", "department", help="Filter by department")
@click.option("--cache-db", default=os.getenv("TENDERS_DB_PATH", "./cache.db"))
def pipeline(department, cache_db):
    """Show the current pipeline."""
    cache = Cache(cache_db)
    entries = cache.get_pipeline(department=department)

    if not entries:
        click.echo("Pipeline is empty. Use: tenders track --tender-id <ocid> --stage <stage>")
        return

    for e in entries:
        stage_emoji = {
            "Identified": "🔵",
            "Briefing Registered": "🟡",
            "Proposal Submitted": "🟠",
            "Won": "🟢",
            "Lost": "🔴",
        }.get(e["stage"], "⚪")

        click.echo(f"{stage_emoji} [{e['stage']}] {e.get('title', 'N/A')[:60]}")
        click.echo(f"   🏛️  {e.get('department', 'N/A')}")
        if e.get("close_date"):
            click.echo(f"   ⏰ Closes: {e['close_date']}")
        click.echo(f"   OCID: {e['tender_ocid']}")
        click.echo("")
