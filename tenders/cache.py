"""SQLite cache layer for tenders-sa."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Contact, Tender

DEFAULT_DB_PATH = os.getenv("TENDERS_DB_PATH", "./cache.db")


def _row_to_tender(row: sqlite3.Row) -> Tender:
    """Convert a DB row to a Tender object."""
    t = Tender(
        ocid=row["ocid"],
        title=row["title"],
        description=row["description"],
        status=row["status"],
        province=row["province"],
        department=row["department"],
        category=row["category"],
        value_amount=row["value_amount"] or 0.0,
        value_currency=row["value_currency"] or "ZAR",
        close_date=row["close_date"] or "",
        tender_period_start=row["tender_period_start"] or "",
        documents_url=row["documents_url"] or "",
        source_url=row["source_url"] or "",
        fetched_at=row["fetched_at"] or "",
    )
    return t


class Cache:
    """SQLite-backed tender cache. Write-once, read-many."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    @contextmanager
    def _conn(self):
        """Context manager for DB connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tenders (
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
                );

                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tender_ocid TEXT REFERENCES tenders(ocid) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    email TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    fax TEXT DEFAULT '',
                    UNIQUE(tender_ocid, name, email)
                );

                CREATE TABLE IF NOT EXISTS fetch_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fetched_at TEXT NOT NULL,
                    date_from TEXT NOT NULL,
                    date_to TEXT NOT NULL,
                    tender_count INTEGER DEFAULT 0,
                    new_count INTEGER DEFAULT 0,
                    error TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    province TEXT DEFAULT '',
                    category TEXT DEFAULT '',
                    min_value REAL DEFAULT 0,
                    enabled INTEGER DEFAULT 1,
                    UNIQUE(keyword, province)
                );

                CREATE TABLE IF NOT EXISTS pipeline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tender_ocid TEXT UNIQUE REFERENCES tenders(ocid) ON DELETE CASCADE,
                    stage TEXT DEFAULT 'Identified',
                    notes TEXT DEFAULT '',
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tenders_status ON tenders(status);
                CREATE INDEX IF NOT EXISTS idx_tenders_province ON tenders(province);
                CREATE INDEX IF NOT EXISTS idx_tenders_department ON tenders(department);
                CREATE INDEX IF NOT EXISTS idx_tenders_fetched_at ON tenders(fetched_at);
                CREATE INDEX IF NOT EXISTS idx_contacts_tender ON contacts(tender_ocid);
            """)

    # ── Tender operations ──────────────────────────────────────────────

    def upsert_tender(self, tender: Tender) -> bool:
        """
        Insert or update a tender. Returns True if it was new (not already cached).
        """
        is_new = False
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT ocid FROM tenders WHERE ocid = ?", (tender.ocid,)
            )
            row = cur.fetchone()
            is_new = row is None

            conn.execute("""
                INSERT INTO tenders (ocid, title, description, status, province,
                    department, category, value_amount, value_currency, close_date,
                    tender_period_start, documents_url, source_url, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ocid) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    status=excluded.status,
                    province=excluded.province,
                    department=excluded.department,
                    category=excluded.category,
                    value_amount=excluded.value_amount,
                    close_date=excluded.close_date,
                    tender_period_start=excluded.tender_period_start,
                    documents_url=excluded.documents_url
            """, (
                tender.ocid, tender.title, tender.description, tender.status,
                tender.province, tender.department, tender.category,
                tender.value_amount, tender.value_currency, tender.close_date,
                tender.tender_period_start, tender.documents_url,
                tender.source_url, tender.fetched_at,
            ))

            for contact in tender.contacts:
                conn.execute("""
                    INSERT OR IGNORE INTO contacts
                        (tender_ocid, name, email, phone, fax)
                    VALUES (?, ?, ?, ?, ?)
                """, (tender.ocid, contact.name, contact.email or "",
                      contact.phone or "", contact.fax or ""))

        return is_new

    def upsert_tenders(self, tenders: list[Tender]) -> int:
        """
        Batch upsert tenders. Returns count of newly inserted tenders.
        """
        new_count = 0
        for t in tenders:
            if self.upsert_tender(t):
                new_count += 1
        return new_count

    def get_tender(self, ocid: str) -> Optional[Tender]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM tenders WHERE ocid = ?", (ocid,)
            ).fetchone()
            if not row:
                return None
            tender = _row_to_tender(row)
            contacts = conn.execute(
                "SELECT * FROM contacts WHERE tender_ocid = ?", (ocid,)
            ).fetchall()
            tender.contacts = [
                Contact(
                    name=r["name"],
                    email=r["email"],
                    phone=r["phone"],
                    fax=r["fax"],
                    tender_ocid=r["tender_ocid"],
                )
                for r in contacts
            ]
            return tender

    def search(
        self,
        keyword: Optional[str] = None,
        province: Optional[str] = None,
        department: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        min_value: Optional[float] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        since: Optional[str] = None,  # fetched_at > since
        limit: int = 50,
    ) -> list[Tender]:
        """
        Search tenders from the cache with filters.
        """
        conditions = []
        params = []

        if keyword:
            conditions.append("(title LIKE ? OR description LIKE ? OR category LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])

        if province:
            conditions.append("province LIKE ?")
            params.append(f"%{province}%")

        if department:
            conditions.append("department LIKE ?")
            params.append(f"%{department}%")

        if category:
            conditions.append("category LIKE ?")
            params.append(f"%{category}%")

        if status:
            conditions.append("status = ?")
            params.append(status)

        if min_value is not None:
            conditions.append("value_amount >= ?")
            params.append(min_value)

        if date_from:
            conditions.append("close_date >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("close_date <= ?")
            params.append(date_to)

        if since:
            conditions.append("fetched_at > ?")
            params.append(since)

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM tenders WHERE {where} ORDER BY fetched_at DESC LIMIT ?"
        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            tenders = [_row_to_tender(r) for r in rows]
            for t in tenders:
                contacts = conn.execute(
                    "SELECT * FROM contacts WHERE tender_ocid = ?", (t.ocid,)
                ).fetchall()
                t.contacts = [
                    Contact(
                        name=r["name"],
                        email=r["email"],
                        phone=r["phone"],
                        fax=r["fax"],
                        tender_ocid=r["tender_ocid"],
                    )
                    for r in contacts
                ]
            return tenders

    # ── Contacts ─────────────────────────────────────────────────────

    def get_contacts(
        self,
        keyword: Optional[str] = None,
        province: Optional[str] = None,
        department: Optional[str] = None,
    ) -> list[Contact]:
        """
        Get contacts from tenders matching criteria.
        """
        sql = """
            SELECT c.* FROM contacts c
            JOIN tenders t ON c.tender_ocid = t.ocid
            WHERE 1=1
        """
        params = []

        if keyword:
            sql += " AND (t.title LIKE ? OR t.description LIKE ?)"
            kw = f"%{keyword}%"
            params.extend([kw, kw])

        if province:
            sql += " AND t.province LIKE ?"
            params.append(f"%{province}%")

        if department:
            sql += " AND t.department LIKE ?"
            params.append(f"%{department}%")

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [
                Contact(
                    name=r["name"],
                    email=r["email"],
                    phone=r["phone"],
                    fax=r["fax"],
                    tender_ocid=r["tender_ocid"],
                )
                for r in rows
            ]

    # ── Pipeline ─────────────────────────────────────────────────────

    def set_pipeline_stage(
        self, ocid: str, stage: str, notes: str = ""
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO pipeline (tender_ocid, stage, notes, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tender_ocid) DO UPDATE SET
                    stage=excluded.stage,
                    notes=excluded.notes,
                    updated_at=excluded.updated_at
            """, (ocid, stage, notes, now))

    def get_pipeline(self, department: Optional[str] = None) -> list[dict]:
        sql = """
            SELECT p.*, t.title, t.department, t.province, t.close_date
            FROM pipeline p
            JOIN tenders t ON p.tender_ocid = t.ocid
            WHERE 1=1
        """
        params = []
        if department:
            sql += " AND t.department LIKE ?"
            params.append(f"%{department}%")
        sql += " ORDER BY p.updated_at DESC"

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    # ── Watchlist ────────────────────────────────────────────────────

    def add_watch(self, keyword: str, province: str = "",
                   category: str = "", min_value: float = 0) -> None:
        with self._conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO watchlist (keyword, province, category, min_value)
                VALUES (?, ?, ?, ?)
            """, (keyword, province, category, min_value))

    def list_watch(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM watchlist WHERE enabled = 1"
            ).fetchall()
            return [dict(r) for r in rows]

    def remove_watch(self, watch_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM watchlist WHERE id = ?", (watch_id,))

    # ── Fetch log ────────────────────────────────────────────────────

    def log_fetch(
        self, date_from: str, date_to: str,
        tender_count: int, new_count: int, error: str = ""
    ) -> None:
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO fetch_log (fetched_at, date_from, date_to, tender_count, new_count, error)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.utcnow().isoformat(), date_from, date_to,
                  tender_count, new_count, error))

    def last_fetch(self) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM fetch_log ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    # ── Stats ────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM tenders WHERE status = 'active'"
            ).fetchone()[0]
            contacts = conn.execute(
                "SELECT COUNT(*) FROM contacts"
            ).fetchone()[0]
            pipeline = conn.execute(
                "SELECT COUNT(*) FROM pipeline"
            ).fetchone()[0]
            last = self.last_fetch()
            return {
                "total_tenders": total,
                "active_tenders": active,
                "total_contacts": contacts,
                "pipeline_entries": pipeline,
                "last_fetch": last,
            }
