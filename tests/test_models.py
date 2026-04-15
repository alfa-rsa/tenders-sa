"""Tests for Tender and Contact models."""

import pytest

from tenders.models import Contact, Tender


class TestContact:
    def test_contact_creation(self):
        c = Contact(name="John Doe", email="john@example.com", phone="0123456789")
        assert c.name == "John Doe"
        assert c.email == "john@example.com"
        assert c.phone == "0123456789"
        assert c.fax is None
        assert c.tender_ocid == ""

    def test_contact_to_dict(self):
        c = Contact(name="Jane Doe", email="jane@example.com", tender_ocid="ocds-abc123")
        d = c.to_dict()
        assert d["name"] == "Jane Doe"
        assert d["email"] == "jane@example.com"
        assert d["tender_ocid"] == "ocds-abc123"


class TestTenderFromAPI:
    def _sample_release(self, **overrides):
        """Minimal valid API release dict with optional overrides."""
        base = {
            "ocid": "ocds-9t57fa-999999",
            "tender": {
                "id": "999999",
                "title": "Test Tender Title",
                "status": "active",
                "category": "Services: IT",
                "mainProcurementCategory": "services",
                "province": "Gauteng",
                "description": "Description of the tender.",
                "value": {"amount": 150000.0, "currency": "ZAR"},
                "tenderPeriod": {
                    "startDate": "2026-04-01T00:00:00Z",
                    "endDate": "2026-04-30T12:00:00Z",
                },
                "contactPerson": {
                    "name": "John Contact",
                    "email": "john@example.com",
                    "telephoneNumber": "0111234567",
                },
                "documents": [
                    {
                        "id": "doc1",
                        "title": "Tender Document.pdf",
                        "url": "https://example.com/doc.pdf",
                        "datePublished": "2026-04-01T10:00:00Z",
                    }
                ],
                "procurementMethod": "open",
                "procurementMethodDetails": "Request for Bid (Open-Tender)",
                "deliveryLocation": "123 Main St, Johannesburg",
                "specialConditions": "N/A",
                "briefingSession": {
                    "isSession": True,
                    "date": "2026-04-10T09:00:00Z",
                    "venue": "Boardroom A",
                },
            },
            "buyer": {"name": "Test Department"},
            "planning": {"budget": {"description": "Budget line item"}},
        }

        # Apply overrides using dot-notation keys (e.g. "tender.documents")
        for dotted_key, value in overrides.items():
            parts = dotted_key.split(".", 1)
            if len(parts) == 1:
                base[dotted_key] = value
            else:
                d = base
                for part in parts[:-1]:
                    d = d.setdefault(part, {})
                d[parts[-1]] = value

        return base

    def test_basic_extraction(self):
        release = self._sample_release()
        t = Tender.from_api(release)

        assert t.ocid == "ocds-9t57fa-999999"
        assert t.title == "Test Tender Title"
        assert t.status == "active"
        assert t.province == "Gauteng"
        assert t.department == "Test Department"
        assert t.category == "services"
        assert t.category_detail == "Services: IT"
        assert t.value_amount == 150000.0
        assert t.value_currency == "ZAR"
        assert t.close_date == "2026-04-30"
        assert t.tender_period_start == "2026-04-01"
        assert t.tender_id == "999999"

    def test_procurement_method(self):
        release = self._sample_release()
        t = Tender.from_api(release)
        assert t.procurement_method == "open"
        assert t.procurement_method_details == "Request for Bid (Open-Tender)"
        assert t.delivery_location == "123 Main St, Johannesburg"
        assert t.special_conditions == "N/A"

    def test_briefing_session_extracted(self):
        release = self._sample_release()
        t = Tender.from_api(release)
        assert t.briefing_session is True
        assert t.briefing_date == "2026-04-10T09:00"
        assert t.briefing_venue == "Boardroom A"

    def test_briefing_session_not_present(self):
        release = self._sample_release(
            **{"tender.briefingSession": {"isSession": False, "date": "0001-01-01T00:00:00Z", "venue": "N/A"}}
        )
        t = Tender.from_api(release)
        assert t.briefing_session is False
        assert t.briefing_date == ""
        assert t.briefing_venue == ""

    def test_contact_extracted(self):
        release = self._sample_release()
        t = Tender.from_api(release)
        assert len(t.contacts) == 1
        c = t.contacts[0]
        assert c.name == "John Contact"
        assert c.email == "john@example.com"
        assert c.phone == "0111234567"
        assert c.tender_ocid == "ocds-9t57fa-999999"

    def test_documents_all_extracted(self):
        release = self._sample_release(
            **{
                "tender.documents": [
                    {"id": "d1", "title": "Doc 1", "url": "https://e.com/1", "datePublished": "2026-04-01T10:00:00Z"},
                    {"id": "d2", "title": "Doc 2", "url": "https://e.com/2", "datePublished": "2026-04-02T10:00:00Z"},
                ]
            }
        )
        t = Tender.from_api(release)
        assert len(t.documents) == 2
        assert t.documents_url == "https://e.com/1"
        assert t.documents[1]["title"] == "Doc 2"

    def test_documents_url_falls_back_to_second(self):
        release = self._sample_release(
            **{
                "tender.documents": [
                    {"id": "d1", "title": "No URL doc", "datePublished": "2026-04-01T10:00:00Z"},
                    {"id": "d2", "title": "Has URL", "url": "https://e.com/2", "datePublished": "2026-04-02T10:00:00Z"},
                ]
            }
        )
        t = Tender.from_api(release)
        assert t.documents_url == "https://e.com/2"

    def test_no_contact_person(self):
        release = self._sample_release(**{"tender.contactPerson": {}})
        t = Tender.from_api(release)
        assert len(t.contacts) == 0

    def test_empty_documents(self):
        release = self._sample_release(**{"tender.documents": []})
        t = Tender.from_api(release)
        assert t.documents == []
        assert t.documents_url == ""

    def test_to_dict_roundtrip(self):
        release = self._sample_release()
        t = Tender.from_api(release)
        d = t.to_dict()
        assert d["ocid"] == "ocds-9t57fa-999999"
        assert d["category_detail"] == "Services: IT"
        assert d["procurement_method"] == "open"
        assert d["briefing_session"] is True
        assert d["documents"][0]["title"] == "Tender Document.pdf"

    def test_to_row(self):
        release = self._sample_release()
        t = Tender.from_api(release)
        row = t.to_row()
        # row: [ocid, title, status, province, department, category, value, close_date, contact_email, contact_name, link]
        assert row[0] == "ocds-9t57fa-999999"
        assert row[1] == "Test Tender Title"
        assert row[5] == "services"  # category (mainProcurementCategory)

    def test_headers(self):
        headers = Tender.headers()
        assert "OCID" in headers
        assert "Title" in headers
        assert "Link" in headers
