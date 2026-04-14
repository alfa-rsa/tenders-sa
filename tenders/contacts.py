"""Contact extraction utilities."""

import csv
import io
from typing import Optional

from .cache import Cache
from .models import Contact


def extract_contacts(
    cache: Cache,
    keyword: Optional[str] = None,
    province: Optional[str] = None,
    department: Optional[str] = None,
) -> list[Contact]:
    """
    Extract contacts from tenders matching criteria.
    Deduplicated by (name, email).
    """
    contacts = cache.get_contacts(
        keyword=keyword,
        province=province,
        department=department,
    )

    # Deduplicate by name+email
    seen = set()
    unique = []
    for c in contacts:
        key = (c.name.lower().strip(), (c.email or "").lower().strip())
        if key[0] and key[0] not in ("n/a", "", "nan") and key not in seen:
            seen.add(key)
            unique.append(c)

    return unique


def format_contacts_text(contacts: list[Contact]) -> str:
    """Format contacts for WhatsApp/message display."""
    if not contacts:
        return "No contacts found."

    lines = []
    for i, c in enumerate(contacts, 1):
        lines.append(f"{i}. {c.name}")
        if c.email:
            lines.append(f"   📧 {c.email}")
        if c.phone:
            lines.append(f"   📞 {c.phone}")
        lines.append("")

    return "\n".join(lines).strip()


def format_tenders_text(tenders) -> str:
    """Format tender list for WhatsApp/message display."""
    if not tenders:
        return "No tenders found."

    lines = []
    for i, t in enumerate(tenders, 1):
        lines.append(f"📋 [{t.status.upper()}] {t.title[:70]}")
        if t.department:
            lines.append(f"   🏛️  {t.department}")
        if t.province:
            lines.append(f"   📍 {t.province}")
        if t.value_amount > 0:
            lines.append(f"   💰 R{t.value_amount:,.0f}")
        if t.close_date:
            lines.append(f"   ⏰ Closes: {t.close_date}")
        if t.contacts and t.contacts[0].email:
            lines.append(f"   📧 {t.contacts[0].email}")
        lines.append(f"   🔗 https://www.etenders.gov.za")
        lines.append("")

    return "\n".join(lines).strip()


def contacts_to_csv(contacts: list[Contact]) -> str:
    """Serialize contacts to CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Name", "Email", "Phone", "Tender OCID"])
    for c in contacts:
        writer.writerow([c.name, c.email or "", c.phone or "", c.tender_ocid])
    return buf.getvalue()
