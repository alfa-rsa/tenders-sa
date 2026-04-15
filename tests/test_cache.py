"""Tests for the SQLite cache layer."""

import json
import sqlite3

import pytest

from tenders.cache import Cache, normalize_province, PROVINCE_ALIASES
from tenders.models import Contact, Tender


@pytest.fixture
def cache(tmp_path):
    """Fresh cache with a temporary database."""
    db = str(tmp_path / "test_cache.db")
    return Cache(db)


@pytest.fixture
def sample_tender():
    """Minimal Tender object."""
    return Tender(
        ocid="ocds-test-001",
        title="Test Tender",
        status="active",
        province="Gauteng",
        department="Test Department",
        category="services",
        category_detail="Services: IT",
        description="A test tender description.",
        value_amount=50000.0,
        value_currency="ZAR",
        close_date="2026-05-01",
        tender_period_start="2026-04-01",
        documents_url="https://example.com/doc.pdf",
        documents=[{"title": "Tender Doc", "url": "https://example.com/doc.pdf", "date": "2026-04-01"}],
        tender_id="T001",
        procurement_method="open",
        procurement_method_details="Open Tender",
        delivery_location="123 Test St",
        special_conditions="None",
        briefing_session=True,
        briefing_date="2026-04-10T09:00",
        briefing_venue="Test Boardroom",
        contacts=[
            Contact(name="Test Contact", email="test@example.com", phone="0123456789", tender_ocid="ocds-test-001"),
        ],
    )


class TestProvinceAliases:
    def test_exact_match(self):
        assert normalize_province("Gauteng") == "Gauteng"
        assert normalize_province("KwaZulu-Natal") == "KwaZulu-Natal"

    def test_alias_expansion(self):
        assert normalize_province("KZN") == "KwaZulu-Natal"
        assert normalize_province("kzn") == "KwaZulu-Natal"
        assert normalize_province("EC") == "Eastern Cape"
        assert normalize_province("GP") == "Gauteng"
        assert normalize_province("LP") == "Limpopo"
        assert normalize_province("wc") == "Western Cape"

    def test_unknown_unchanged(self):
        assert normalize_province("Unknown Province") == "Unknown Province"

    def test_empty(self):
        assert normalize_province("") == ""
        assert normalize_province(None) == ""


class TestUpsertTender:
    def test_insert_new_tender(self, cache, sample_tender):
        is_new = cache.upsert_tender(sample_tender)
        assert is_new is True

    def test_insert_twice_is_not_new(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        is_new = cache.upsert_tender(sample_tender)
        assert is_new is False

    def test_upsert_tenders_count(self, cache, sample_tender):
        t2 = Tender(
            ocid="ocds-test-002", title="Tender 2", status="active",
            contacts=[],
        )
        count = cache.upsert_tenders([sample_tender, t2])
        assert count == 2

    def test_roundtrip_fields(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        retrieved = cache.get_tender("ocds-test-001")

        assert retrieved is not None
        assert retrieved.ocid == "ocds-test-001"
        assert retrieved.title == "Test Tender"
        assert retrieved.province == "Gauteng"
        assert retrieved.category_detail == "Services: IT"
        assert retrieved.value_amount == 50000.0
        assert retrieved.tender_id == "T001"
        assert retrieved.procurement_method == "open"
        assert retrieved.briefing_session is True
        assert retrieved.briefing_venue == "Test Boardroom"
        assert retrieved.documents[0]["title"] == "Tender Doc"
        assert len(retrieved.contacts) == 1
        assert retrieved.contacts[0].email == "test@example.com"

    def test_get_nonexistent(self, cache):
        assert cache.get_tender("ocds-nonexistent") is None

    def test_briefing_session_false_stored_correctly(self, cache):
        t = Tender(ocid="ocds-no-briefing", title="No Briefing", status="active", contacts=[])
        cache.upsert_tender(t)
        retrieved = cache.get_tender("ocds-no-briefing")
        assert retrieved.briefing_session is False


class TestSearch:
    def test_search_empty(self, cache):
        results = cache.search(limit=10)
        assert results == []

    def test_search_by_province(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        results = cache.search(province="Gauteng")
        assert len(results) == 1
        assert results[0].ocid == "ocds-test-001"

    def test_search_by_province_alias(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        results = cache.search(province="GP")
        assert len(results) == 1

    def test_search_by_keyword(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        results = cache.search(keyword="Test Tender")
        assert len(results) == 1

    def test_search_by_category(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        results = cache.search(category="IT")
        assert len(results) == 1

    def test_search_by_category_detail(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        results = cache.search(category="Services")
        assert len(results) == 1

    def test_search_by_status(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        results = cache.search(status="active")
        assert len(results) == 1
        results = cache.search(status="cancelled")
        assert len(results) == 0

    def test_search_by_min_value(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        results = cache.search(min_value=10000.0)
        assert len(results) == 1
        results = cache.search(min_value=100000.0)
        assert len(results) == 0

    def test_search_by_date_range(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        results = cache.search(date_from="2026-04-01", date_to="2026-05-31")
        assert len(results) == 1
        results = cache.search(date_from="2026-06-01", date_to="2026-12-31")
        assert len(results) == 0

    def test_search_by_department(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        results = cache.search(department="Test Department")
        assert len(results) == 1

    def test_search_limit(self, cache, sample_tender):
        for i in range(5):
            t = Tender(ocid=f"ocds-test-{i:03d}", title=f"Tender {i}", status="active", contacts=[])
            cache.upsert_tender(t)
        results = cache.search(limit=2)
        assert len(results) == 2


class TestPipeline:
    def test_set_and_get_pipeline(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        cache.set_pipeline_stage("ocds-test-001", "Proposal Submitted", "Notes here")

        entries = cache.get_pipeline()
        assert len(entries) == 1
        assert entries[0]["stage"] == "Proposal Submitted"
        assert entries[0]["notes"] == "Notes here"
        assert entries[0]["tender_ocid"] == "ocds-test-001"

    def test_pipeline_filter_by_department(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        cache.set_pipeline_stage("ocds-test-001", "Won")

        results = cache.get_pipeline(department="Test Department")
        assert len(results) == 1

        results = cache.get_pipeline(department="Other Department")
        assert len(results) == 0


class TestWatchlist:
    def test_add_and_list_watch(self, cache):
        cache.add_watch("software", province="Gauteng", min_value=10000.0)
        items = cache.list_watch()
        assert len(items) == 1
        assert items[0]["keyword"] == "software"
        assert items[0]["province"] == "Gauteng"

    def test_remove_watch(self, cache):
        cache.add_watch("software")
        cache.add_watch("hardware")
        assert len(cache.list_watch()) == 2

        # Find ID of first watch
        items = cache.list_watch()
        first_id = items[0]["id"]

        cache.remove_watch(first_id)
        assert len(cache.list_watch()) == 1


class TestFetchLog:
    def test_log_fetch(self, cache):
        cache.log_fetch("2026-01-01", "2026-01-31", tender_count=100, new_count=50, error="")
        last = cache.last_fetch()
        assert last["tender_count"] == 100
        assert last["new_count"] == 50
        assert last["date_from"] == "2026-01-01"

    def test_last_fetch_empty(self, cache):
        assert cache.last_fetch() is None


class TestStats:
    def test_stats_empty(self, cache):
        s = cache.stats()
        assert s["total_tenders"] == 0
        assert s["active_tenders"] == 0
        assert s["total_contacts"] == 0
        assert s["pipeline_entries"] == 0

    def test_stats_after_insert(self, cache, sample_tender):
        cache.upsert_tender(sample_tender)
        cache.set_pipeline_stage("ocds-test-001", "Identified")
        s = cache.stats()
        assert s["total_tenders"] == 1
        assert s["active_tenders"] == 1
        assert s["total_contacts"] == 1
        assert s["pipeline_entries"] == 1


class TestSchemaMigration:
    """Test that old databases can be read with the new schema."""

    def test_old_database_still_readable(self, tmp_path):
        """Create a database with old schema (fewer columns) and verify it upgrades."""
        db_path = tmp_path / "old.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE tenders (
                ocid TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT '',
                province TEXT DEFAULT '',
                department TEXT DEFAULT '',
                category TEXT DEFAULT '',
                value_amount REAL DEFAULT 0,
                value_currency TEXT DEFAULT 'ZAR',
                close_date TEXT DEFAULT '',
                tender_period_start TEXT DEFAULT '',
                documents_url TEXT DEFAULT '',
                source_url TEXT DEFAULT '',
                fetched_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO tenders VALUES ('ocds-old-001', 'Old Tender', '', 'active', 'Gauteng', 'Old Dept', '', 0, 'ZAR', '2026-05-01', '2026-04-01', '', '', '2026-04-01')
        """)
        conn.commit()
        conn.close()

        # Open with new Cache class — should add new columns automatically
        cache = Cache(str(db_path))
        t = cache.get_tender("ocds-old-001")
        assert t is not None
        assert t.ocid == "ocds-old-001"
        assert t.title == "Old Tender"
        # New fields default to empty
        assert t.category_detail == ""
        assert t.briefing_session is False
