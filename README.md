# tenders-sa

**SA Government Tender Intelligence** — Monitor, track, and act on South African government procurement opportunities automatically.

```
pip install -e .
tenders --help
```

## Quick Start

```bash
# First time — fetch active tenders (last 30 days)
tenders new --fetch --since 30

# Search what you've got
tenders search -k "information technology" -p "KwaZulu-Natal"

# Add keywords to watchlist
tenders watch -k "software" -p "Gauteng"
tenders watch -k "solar" -p "Eastern Cape"

# Check for new tenders since last fetch
tenders new --since 1

# Show cache stats
tenders stats

# Extract contacts from cached tenders
tenders contacts -d "RTMC"
```

## Commands

| Command | Description |
|---------|-------------|
| `tenders search` | Search cached tenders |
| `tenders new` | Show new tenders (use `--fetch` to pull from API) |
| `tenders contacts` | Extract contact info from tenders |
| `tenders history` | Historical tenders for a department |
| `tenders winners` | Past awarded contracts (competitive intel) |
| `tenders track` | Add a tender to your pipeline |
| `tenders pipeline` | View pipeline |
| `tenders watch` | Add keyword to watchlist |
| `tenders watch-list` | Show current watchlist |
| `tenders setup` | Verify configuration |
| `tenders stats` | Show cache statistics |

## Setup

```bash
cp .env.example .env
# Edit .env if needed

pip install -e .
```

## Cron — Daily Digest

Add to crontab (`crontab -e`):

```
0 7 * * * cd /path/to/tenders-sa && python scripts/daily_monitor.py >> /tmp/tenders-monitor.log 2>&1
```

Runs every day at 7am SAST. Fetches new tenders, filters by watchlist, sends WhatsApp digest.

## Architecture

- **API Client** (`tenders/client.py`) — httpx with retries, rate limiting
- **Cache** (`tenders/cache.py`) — SQLite, write-once, read-many
- **Models** (`tenders/models.py`) — Tender, Contact dataclasses
- **CLI** (`tenders/cli/`) — Click subcommands

## License

MIT