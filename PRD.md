# tenders-sa — SA Government Tender Intelligence

> Monitor, track, and act on South African government procurement opportunities — automatically.

---

## 1. Problem

**Finding government tender opportunities in South Africa is manual, slow, and unreliable.**

- The eTenders API is slow (45-60s per request)
- Results aren't filtered intelligently — you get 500 results and filter manually
- No change detection — you can't tell what's *new* since your last check
- No contact extraction — even when you find relevant tenders, outreach is manual
- No monitoring — you have to remember to check

Government contracts are real business. A single panel contract (like the RTMC IT panel) can be worth R500k–R5M+ per year over 3-5 years. The opportunities are there. The problem is intelligence, not information.

---

## 2. Solution

**tenders-sa** is an autonomous tender intelligence system that:

1. **Fetches** — pulls from the SA Government eTenders OCDS API
2. **Caches** — stores all results in SQLite for instant queries
3. **Filters** — applies keyword, province, category, and value filters
4. **Detects** — identifies new tenders since the last check
5. **Extracts** — pulls clean contact information for outreach
6. **Alerts** — sends daily WhatsApp digests of new relevant tenders
7. **Exports** — pushes to Google Sheets for pipeline tracking

---

## 3. Product Vision

> A system that finds the right government tenders before your competitors do, extracts the right contacts, and tells you about them automatically — every morning.

The target user is a small tech business owner in South Africa who wants to bid on government contracts but doesn't have time to manually scan eTenders every day. The system does the scanning, filtering, and alerting. The human decides which tenders to pursue and does the outreach.

---

## 4. Target User

- Small/micro SA tech businesses (1-10 people)
- Freelancers and consultants targeting government
- Companies looking for B2B contract revenue in SA
- Anyone bidding on SA government procurement

---

## 5. Core Features

### 5.1 Tender Search
```
tenders search --keyword "information technology" --province "KwaZulu-Natal"
tenders search --keyword "software" --min-value 50000 --status active
tenders search --category "IT Services" --department "SARS"
```
- Filters: keyword, province, category, department, status, value range, closing date range
- Returns structured results with contacts, values, and links

### 5.2 New Tender Detection
```
tenders new --since 2026-04-01 --keywords IT,solar,building
```
- Compares against cached data
- Returns only tenders that are new since the given date
- Powers the daily monitor

### 5.3 Contact Extraction
- Pulls name, email, phone from tender data
- Returns a clean contact list ready for outreach
- Exportable to CSV / Google Sheets

### 5.4 Daily Monitor (Cron)
- Runs every morning at 7am SAST
- Fetches tenders new since last run
- Filters by user's keyword watchlist
- Sends WhatsApp digest with top opportunities

### 5.5 Google Sheets Pipeline
```
tenders export --tender-id XYZ --to sheets
tenders track --dept RTMC --pipeline-stage "Briefing Registered"
```
- Push tender leads to a Google Sheets pipeline tracker
- Stages: Identified → Briefing Registered → Proposal Submitted → Won/Lost

### 5.6 Competitive Intelligence
```
tenders history --dept RTMC --since 2024-01-01
tenders winners --category "IT Services" --since 2024-01-01
```
- Shows historical tenders for a department
- Shows which suppliers won past contracts
- Benchmark values before bidding

---

## 6. Three-Phase Build

### Phase A — Live Monitoring
- SQLite cache (current tenders only)
- CLI search + filters
- Contact extraction
- Daily WhatsApp digest
- Google Sheets export
- **Scope:** Active tenders from today onwards

### Phase B — 12-Month Backfill
- One-time backfill of 2024-2025 data in monthly batches
- Full historical queries work
- Competitive intelligence from past wins
- **Trigger:** Phase A is live and validated

### Phase C — 24-Month Backfill
- Extend archive to 2023-01-01
- Full 2-year budget cycle visible
- Seasonal patterns and long-term supplier tracking
- **Trigger:** Phase B done, additional context needed

---

## 7. Architecture

### Stack
- **Language:** Python 3 (data wrangling, SQLite, CLI)
- **Database:** SQLite (persistent cache, no external DB needed)
- **CLI Framework:** Click (Typer as alternative)
- **HTTP:** httpx (async-capable, retry logic)
- **Cache:** SQLite with write-once, read-many strategy
- **Notifications:** WhatsApp via OpenClaw gateway
- **Spreadsheets:** Google Workspace API (GWS)

### Data Model

```sql
-- Core tender data (write-once, read-many)
CREATE TABLE tenders (
    ocid TEXT PRIMARY KEY,          -- OCDS identifier
    title TEXT,
    description TEXT,
    status TEXT,                    -- active, complete, cancelled, pending
    province TEXT,
    department TEXT,                -- procuring entity name
    category TEXT,
    value_amount REAL,
    value_currency TEXT DEFAULT 'ZAR',
    close_date TEXT,                -- ISO date
    tender_period_start TEXT,
    tender_period_end TEXT,
    documents_url TEXT,
    source_url TEXT,
    fetched_at TEXT                 -- when we first saw this tender
);

-- Contact persons per tender
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_ocid TEXT REFERENCES tenders(ocid),
    name TEXT,
    email TEXT,
    phone TEXT,
    fax TEXT,
    UNIQUE(tender_ocid, name, email)
);

-- Fetch log for change detection
CREATE TABLE fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at TEXT,
    tender_count INTEGER,
    new_count INTEGER,
    error TEXT
);

-- User watchlist (keywords, provinces to monitor)
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT,
    province TEXT,
    category TEXT,
    min_value REAL,
    enabled INTEGER DEFAULT 1
);

-- Outreach pipeline
CREATE TABLE pipeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_ocid TEXT REFERENCES tenders(ocid),
    stage TEXT DEFAULT 'Identified',  -- Identified | Briefing Registered | Proposal Submitted | Won | Lost
    notes TEXT,
    updated_at TEXT
);
```

### API: eTenders OCDS

Base URL: `https://ocds-api.etenders.gov.za/api/OCDSReleases`

Required params: `PageNumber`, `PageSize`, `dateFrom`, `dateTo`

Known issues:
- Response time: 45-60 seconds per request (rate limit accordingly)
- `dateFrom` and `dateTo` are required
- API may return HTTP 500 intermittently (retry logic needed)

---

## 8. CLI Reference

```bash
# Search
tenders search -k "information technology" -p "KwaZulu-Natal" --min-value 50000
tenders search -k "software" --category "IT Services" --status active

# New tenders since date
tenders new --since 2026-04-01 -k IT,solar,building
tenders new --since yesterday --keywords IT

# Contact extraction
tenders contacts --dept "RTMC"
tenders contacts --tender-id ocds-9t57fa-XXX --export csv

# Pipeline management
tenders track --tender-id ocds-9t57fa-XXX --stage "Proposal Submitted"
tenders pipeline --dept "RTMC"

# Competitive intelligence
tenders history --dept "SARS" --since 2024-01-01
tenders winners --category "IT Services" --since 2024-01-01

# Setup and config
tenders setup --whatsapp        # Enable WhatsApp digest
tenders watch --add -k "IT" -p "Gauteng"  # Add to watchlist
tenders watch --list             # Show current watchlist
tenders cache --stats           # Show cache statistics

# Admin
tenders backfill --start 2024-01-01 --end 2024-12-31  # Phase B
tenders cache --clear           # Reset cache
```

---

## 9. Daily Monitor Flow

```
7:00 AM SAST — Cron Triggered
        ↓
Fetch tenders new since last run
        ↓
Apply watchlist filters (keywords, provinces)
        ↓
No new tenders? → Done, no alert sent
        ↓
New tenders found?
        ↓
Format WhatsApp digest:
- Title + department
- Contact name + email
- Closing date
- Direct link to eTenders
        ↓
Send to WhatsApp via OpenClaw
        ↓
Also push to Google Sheets pipeline (optional)
        ↓
Update fetch_log with this run
```

---

## 10. Key Design Decisions

### 10.1 SQLite over PostgreSQL
SQLite is embedded in the process. No external database to provision, manage, or pay for. For a tool that caches API responses, SQLite is the right tool — fast reads, ACID compliant, zero ops overhead.

### 10.2 Python over TypeScript/JavaScript
Python has better data wrangling libraries (pandas for future analytics), native SQLite support, and is the natural language for data-intensive CLI tools.

### 10.3 Write-Once Cache
Tenders are fetched once and stored. The `fetched_at` column tracks when we first saw a tender. `fetch_log` tracks when we last ran. New tenders = tenders with `fetched_at > last_run`. No re-fetching of old data.

### 10.4 No Full-Text Search (Yet)
SQLite FTS5 is available but adds complexity. Phase A uses simple `LIKE` queries on title/description. FTS5 can be added in Phase B if search performance degrades.

### 10.5 WhatsApp over Email
Government procurement people are on WhatsApp. Email alerts get buried. A WhatsApp digest at 7am SAST is the right channel — short, actionable, mobile-first.

---

## 11. Out of Scope (For Now)

- Email alerts (WhatsApp only for now)
- Bid document PDF downloading/parsing
- Supplier registration tracking
- Automated bid submission
- Mobile app
- Web UI

These can be added later if there's demand.

---

## 12. Success Metrics

Phase A is successful when:
- [ ] `tenders search` returns results in <1 second (from cache)
- [ ] `tenders new` correctly identifies tenders new since yesterday
- [ ] Daily WhatsApp digest is sent automatically at 7am SAST
- [ ] Contacts can be exported to Google Sheets
- [ ] Phase B backfill runs without errors

---

## 13. Repository

**GitHub:** github.com/alfa-rsa/tenders-sa

---

*Last updated: 2026-04-14*
