"""Tests for search module functions."""

import pytest

from tenders.search import (
    get_tender_by_ocid,
    new_tenders,
)


class TestNewTenders:
    def test_uses_since_filter(self, tmp_path):
        from tenders.cache import Cache
        from tenders.models import Tender, Contact
        import datetime

        cache = Cache(str(tmp_path / "cache.db"))

        # Insert a tender with a recent fetched_at
        t = Tender(
            ocid="ocds-recent",
            title="Recent Tender",
            status="active",
            province="Gauteng",
            department="Test",
            contacts=[],
        )
        cache.upsert_tender(t)

        # Should find it when looking for tenders new in last 30 days
        results = new_tenders(cache, days=30)
        assert len(results) == 1

        # Should not find it when looking for tenders new in last 0 days
        results = new_tenders(cache, days=0)
        assert len(results) == 0


class TestGetTenderByOcid:
    def test_returns_tender(self, tmp_path):
        from tenders.cache import Cache
        from tenders.models import Tender

        cache = Cache(str(tmp_path / "cache.db"))
        t = Tender(ocid="ocds-find-me", title="Find Me", status="active", contacts=[])
        cache.upsert_tender(t)

        result = get_tender_by_ocid(cache, "ocds-find-me")
        assert result is not None
        assert result.title == "Find Me"

    def test_returns_none_for_missing(self, tmp_path):
        from tenders.cache import Cache
        cache = Cache(str(tmp_path / "cache.db"))
        result = get_tender_by_ocid(cache, "ocds-does-not-exist")
        assert result is None
