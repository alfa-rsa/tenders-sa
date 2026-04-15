"""Search logic for tenders-sa."""

from datetime import datetime, timedelta
from typing import Optional

from .cache import Cache
from .client import TenderClient
from .models import Tender


def fetch_and_cache(
    date_from: str,
    date_to: str,
    client: TenderClient,
    cache: Cache,
    page_size: int = 50,
    progress_callback=None,
) -> tuple[int, int]:
    """
    Fetch all pages for a date range and store in cache.

    Returns (total_fetched, new_count).
    """
    releases = client.fetch_all_pages(
        date_from=date_from,
        date_to=date_to,
        page_size=page_size,
        progress_callback=progress_callback,
    )

    tenders = [Tender.from_api(r) for r in releases]
    new_count = cache.upsert_tenders(tenders)

    cache.log_fetch(
        date_from=date_from,
        date_to=date_to,
        tender_count=len(tenders),
        new_count=new_count,
    )

    return len(tenders), new_count


def search_tenders(
    cache: Cache,
    keyword: Optional[str] = None,
    province: Optional[str] = None,
    department: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = "active",
    min_value: Optional[float] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
) -> list[Tender]:
    """Search cached tenders with filters."""
    return cache.search(
        keyword=keyword,
        province=province,
        department=department,
        category=category,
        status=status,
        min_value=min_value,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


def get_tender_by_ocid(cache: Cache, ocid: str) -> Optional[Tender]:
    """Get a single tender by OCID from the cache."""
    return cache.get_tender(ocid)


def new_tenders(
    cache: Cache,
    days: int = 1,
    keyword: Optional[str] = None,
    province: Optional[str] = None,
) -> list[Tender]:
    """
    Find tenders that are new since N days ago.

    Uses fetched_at to detect new arrivals.
    """
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    return cache.search(
        keyword=keyword,
        province=province,
        since=since,
        limit=100,
    )


def tender_history(
    cache: Cache,
    department: Optional[str] = None,
    category: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 50,
) -> list[Tender]:
    """Get historical tenders for a department/category."""
    return cache.search(
        keyword=None,
        province=None,
        department=department,
        category=category,
        status=None,
        since=since,
        limit=limit,
    )


def winning_suppliers(
    cache: Cache,
    category: Optional[str] = None,
    department: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """
    Get historical awarded tenders — useful for competitive intelligence.
    Shows which suppliers won past contracts.
    """
    tenders = cache.search(
        department=department,
        category=category,
        status="complete",
        date_from=since,
        limit=limit,
    )
    return [
        {
            "title": t.title,
            "department": t.department,
            "category": t.category,
            "value": t.value_amount,
            "close_date": t.close_date,
            "ocid": t.ocid,
        }
        for t in tenders
        if t.value_amount > 0
    ]
