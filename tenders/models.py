"""Data models for tenders-sa."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Contact:
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    tender_ocid: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "email": self.email or "",
            "phone": self.phone or "",
            "fax": self.fax or "",
            "tender_ocid": self.tender_ocid,
        }


@dataclass
class Tender:
    ocid: str
    title: str
    status: str
    province: str = ""
    department: str = ""
    category: str = ""           # mainProcurementCategory (goods/services/works)
    category_detail: str = ""   # detailed category (e.g. "Supplies: General")
    description: str = ""
    value_amount: float = 0.0
    value_currency: str = "ZAR"
    close_date: str = ""
    tender_period_start: str = ""
    tender_period_end: str = ""
    tender_id: str = ""          # government's internal reference number
    documents_url: str = ""     # first document URL
    documents: list[dict] = field(default_factory=list)   # all documents with title/url/date
    source_url: str = ""
    procurement_method: str = ""          # open, limited, etc.
    procurement_method_details: str = ""   # full method description
    delivery_location: str = ""            # delivery address
    special_conditions: str = ""          # special conditions text
    briefing_session: bool = False         # is there a briefing session
    briefing_date: str = ""                # briefing session date/time
    briefing_venue: str = ""               # briefing session venue
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    contacts: list[Contact] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict) -> "Tender":
        t = data.get("tender", {})
        period = t.get("tenderPeriod", {})
        value = t.get("value", {})
        planning = data.get("planning", {})
        budget = planning.get("budget", {})

        # Extract contact from tender.contactPerson
        contacts = []
        cp = t.get("contactPerson", {})
        if cp.get("name"):
            contacts.append(Contact(
                name=cp["name"],
                email=cp.get("email"),
                phone=cp.get("telephoneNumber"),
                fax=cp.get("faxNumber"),
                tender_ocid=data.get("ocid", ""),
            ))

        # Pull first document URL + all documents with metadata
        docs_url = ""
        all_docs = []
        docs = t.get("documents", [])
        if docs and isinstance(docs, list):
            for doc in docs:
                if isinstance(doc, dict) and doc.get("url"):
                    if not docs_url:
                        docs_url = doc["url"]
                    all_docs.append({
                        "title": doc.get("title", ""),
                        "url": doc.get("url", ""),
                        "date": doc.get("datePublished", ""),
                    })

        # Briefing session details
        bs = t.get("briefingSession", {})
        has_briefing = bool(bs.get("isSession", False)) if bs else False
        briefing_date = ""
        briefing_venue = ""
        if has_briefing:
            raw_date = bs.get("date", "")
            if raw_date and raw_date != "0001-01-01T00:00:00Z":
                briefing_date = raw_date[:16]
            venue = bs.get("venue", "")
            if venue and venue != "N/A":
                briefing_venue = venue

        return cls(
            ocid=data.get("ocid", ""),
            title=t.get("title", "N/A"),
            description=t.get("description", ""),
            status=t.get("status", "unknown"),
            province=t.get("province", ""),
            department=data.get("buyer", {}).get("name", ""),
            category=t.get("mainProcurementCategory", ""),
            category_detail=t.get("category", ""),
            value_amount=float(value.get("amount", 0) or 0),
            value_currency=value.get("currency", "ZAR"),
            close_date=period.get("endDate", "")[:10] if period.get("endDate") else "",
            tender_period_start=period.get("startDate", "")[:10] if period.get("startDate") else "",
            tender_period_end=period.get("endDate", "")[:10] if period.get("endDate") else "",
            tender_id=t.get("id", ""),
            documents_url=docs_url,
            documents=all_docs,
            source_url="https://www.etenders.gov.za",
            procurement_method=t.get("procurementMethod", ""),
            procurement_method_details=t.get("procurementMethodDetails", ""),
            delivery_location=t.get("deliveryLocation", ""),
            special_conditions=t.get("specialConditions", ""),
            briefing_session=has_briefing,
            briefing_date=briefing_date,
            briefing_venue=briefing_venue,
            contacts=contacts,
        )

    def to_dict(self) -> dict:
        return {
            "ocid": self.ocid,
            "title": self.title,
            "status": self.status,
            "province": self.province,
            "department": self.department,
            "category": self.category,
            "category_detail": self.category_detail,
            "description": self.description,
            "value_amount": self.value_amount,
            "value_currency": self.value_currency,
            "close_date": self.close_date,
            "tender_period_start": self.tender_period_start,
            "tender_id": self.tender_id,
            "documents_url": self.documents_url,
            "documents": self.documents,
            "source_url": self.source_url,
            "procurement_method": self.procurement_method,
            "procurement_method_details": self.procurement_method_details,
            "delivery_location": self.delivery_location,
            "special_conditions": self.special_conditions,
            "briefing_session": self.briefing_session,
            "briefing_date": self.briefing_date,
            "briefing_venue": self.briefing_venue,
            "fetched_at": self.fetched_at,
        }

    def to_row(self) -> list:
        return [
            self.ocid,
            self.title,
            self.status,
            self.province,
            self.department,
            self.category or self.category_detail,
            f"R{self.value_amount:,.0f}" if self.value_amount else "R0",
            self.close_date,
            self.contacts[0].email if self.contacts else "",
            self.contacts[0].name if self.contacts else "",
            self.source_url,
        ]

    @staticmethod
    def headers() -> list:
        return [
            "OCID", "Title", "Status", "Province", "Department",
            "Category", "Value", "Close Date", "Contact Email",
            "Contact Name", "Link",
        ]
