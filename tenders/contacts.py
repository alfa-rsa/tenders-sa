"""Contact extraction utilities."""

import csv
import io
from typing import Optional

from .cache import Cache
from .models import Contact, Tender


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
            lines.append(f"   [E] {c.email}")
        if c.phone:
            lines.append(f"   [P] {c.phone}")
        lines.append("")

    return "\n".join(lines).strip()


def format_tender_detail(t: Tender) -> str:
    """Format a single tender with full detail for the search/detail view."""
    lines = []

    # Title + status
    lines.append(f"[T] [{t.status.upper()}] {t.title}")
    lines.append(f"   OCID: {t.ocid}")

    # Reference number if available
    if t.tender_id:
        lines.append(f"   Ref: {t.tender_id}")

    # Department / buyer
    if t.department:
        lines.append(f"   [D] {t.department}")

    # Province
    if t.province:
        lines.append(f"   [L] {t.province}")

    # Category
    if t.category_detail:
        lines.append(f"   [Cat] {t.category_detail} ({t.category})")
    elif t.category:
        lines.append(f"   [Cat] {t.category}")

    # Value
    if t.value_amount > 0:
        lines.append(f"   R{t.value_amount:,.0f} {t.value_currency}")
    else:
        lines.append(f"   Value: not specified")

    # Dates
    if t.tender_period_start:
        lines.append(f"   [Start] {t.tender_period_start}")
    if t.close_date:
        lines.append(f"   [C] Closes: {t.close_date}")

    # Procurement method
    if t.procurement_method:
        lines.append(f"   [Method] {t.procurement_method}")
        if t.procurement_method_details:
            lines.append(f"            {t.procurement_method_details}")

    # Briefing session
    if t.briefing_session:
        lines.append(f"   [B] COMPULSORY briefing: {t.briefing_venue}")
        if t.briefing_date:
            lines.append(f"       {t.briefing_date}")

    # Delivery location
    if t.delivery_location:
        lines.append(f"   [Loc] {t.delivery_location}")

    # Documents
    doc_count = len(t.documents)
    if doc_count > 0:
        lines.append(f"   [Docs] {doc_count} document(s)")
        for d in t.documents[:3]:  # show first 3
            if d.get("title"):
                lines.append(f"       - {d['title']}")
        if doc_count > 3:
            lines.append(f"       ...and {doc_count - 3} more")
    elif t.documents_url:
        lines.append(f"   [Docs] 1 document")

    # Description snippet
    if t.description and len(t.description) > 50:
        snippet = t.description[:200].replace("\n", " ").strip()
        lines.append(f"   Desc: {snippet}...")

    # Contact
    if t.contacts:
        c = t.contacts[0]
        lines.append(f"   [E] {c.email}")
        if c.name:
            lines.append(f"       Attn: {c.name}")
        if c.phone:
            lines.append(f"   [P] {c.phone}")

    # Link
    lines.append(f"   [LINK] https://www.etenders.gov.za")

    return "\n".join(lines)


def format_tenders_text(tenders) -> str:
    """Format a list of tenders for WhatsApp/message display."""
    if not tenders:
        return "No tenders found."

    lines = []
    for i, t in enumerate(tenders, 1):
        lines.append(f"[T] [{t.status.upper()}] {t.title[:70]}")
        if t.department:
            lines.append(f"   [D] {t.department}")
        if t.province:
            lines.append(f"   [L] {t.province}")
        if t.value_amount > 0:
            lines.append(f"   R{t.value_amount:,.0f}")
        if t.close_date:
            lines.append(f"   [C] Closes: {t.close_date}")
        if t.tender_id:
            lines.append(f"   Ref: {t.tender_id}")
        if t.briefing_session:
            lines.append(f"   [B] COMPULSORY briefing")
        if t.documents:
            lines.append(f"   [Docs] {len(t.documents)} files")
        if t.contacts and t.contacts[0].email:
            lines.append(f"   [E] {t.contacts[0].email}")
        lines.append(f"   [LINK] https://www.etenders.gov.za")
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
