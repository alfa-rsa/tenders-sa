"""Data models for tenders-sa."""

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
    category: str = ""
    description: str = ""
    value_amount: float = 0.0
    value_currency: str = "ZAR"
    close_date: str = ""
    tender_period_start: str = ""
    tender_period_end: str = ""
    documents_url: str = ""
    source_url: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    contacts: list[Contact] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict) -> "Tender":
        t = data.get("tender", {})
        buyer = t.get("buyer", {})
        period = t.get("tenderPeriod", {})
        value = t.get("value", {})
        cp = t.get("contactPerson", {})

        contacts = []
        if cp.get("name"):
            contacts.append(Contact(
                name=cp["name"],
                email=cp.get("email"),
                phone=cp.get("telephone"),
                fax=cp.get("fax"),
                tender_ocid=data.get("ocid", ""),
            ))

        return cls(
            ocid=data.get("ocid", ""),
            title=t.get("title", "N/A"),
            description=t.get("description", ""),
            status=t.get("status", "unknown"),
            province=t.get("province", ""),
            department=buyer.get("name", ""),
            category=t.get("category", ""),
            value_amount=float(value.get("amount", 0) or 0),
            value_currency=value.get("currency", "ZAR"),
            close_date=period.get("endDate", "")[:10] if period.get("endDate") else "",
            tender_period_start=period.get("startDate", "")[:10] if period.get("startDate") else "",
            documents_url=data.get("documentsUrl", ""),
            source_url=f"https://www.etenders.gov.za",
            contacts=contacts,
        )

    def to_dict(self) -> dict:
        return {
            "ocid": self.ocid,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "province": self.province,
            "department": self.department,
            "category": self.category,
            "value_amount": self.value_amount,
            "value_currency": self.value_currency,
            "close_date": self.close_date,
            "tender_period_start": self.tender_period_start,
            "documents_url": self.documents_url,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at,
        }

    def to_row(self) -> list:
        return [
            self.ocid,
            self.title,
            self.status,
            self.province,
            self.department,
            self.category,
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
