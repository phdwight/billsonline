# Bills Online

[![Docker Build](https://github.com/phdwight/billsonline/actions/workflows/docker-build.yml/badge.svg)](https://github.com/phdwight/billsonline/actions/workflows/docker-build.yml)
[![Test Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen)](tests/)
[![Tests](https://img.shields.io/badge/tests-296%20passing-brightgreen)](tests/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**Bills Online** is a Flask web application for splitting monthly household utility bills among housemates or roommates. It handles the common scenario where multiple people share a living space and need to fairly divide costs for electricity, water, internet, and other recurring expenses.

## The Problem It Solves

Splitting bills in a shared household is often complicated:
- Some bills should be split equally (internet, rent)
- Other bills need to be split by usage (electricity based on meter readings)
- Sometimes a person should be excluded from certain bills (e.g., traveling that month)
- When someone is excluded, their share needs to be redistributed to others
- Tracking all this monthly becomes tedious and error-prone

**Bills Online** automates all of this with a simple web interface.

## Key Concepts

### Participants
The people sharing the bills (e.g., Alice, Bob, Charlie). Add them once — in **Settings → People Directory** or on the Manage page — and they're available for all months. When creating a new month you choose which participants to include; only those appear in that month's readings, adjustments, and contributions.

### Monthly Bills
Each month gets its own billing period containing components, meter readings, and per-participant results. The home page shows periods as cards with their grand total and status (Active/Archived).

### Bill Components
Individual line items within a monthly bill. Each component has:
- **Name**: e.g., "Electricity", "Water", "Internet", "Rent"
- **Amount**: The total cost
- **Split Method**: How to divide the cost among participants
- **Bill photos** (optional): up to two snapshots of the physical bill, stored compressed

### Split Methods
- **Equal**: Everyone pays the same amount (total ÷ number of participants)
- **Usage**: Split proportionally based on meter reading differences
- **Percentage**: Custom percentages per participant (must sum to 100%)
- **Fixed Amount**: Specific amounts per participant

### Meter Readings
For usage-based bills like electricity, enter each person's meter readings:
- **Previous Reading**: Where the meter was at the start of the period (pre-filled from last month)
- **Current Reading**: Where the meter is now
- **Usage** = (Current − Previous) ÷ 10 — the meters register tenths of a kWh (calculated live as you type)
- **Base cost** = each person's usage share of the usage-split bill, shown alongside the effective ₱/kWh rate — the raw computation *before* any adjustments

### Adjustments & Redistribution
When someone shouldn't pay (part of) a component — e.g., they were away — a redistribution rule shifts their share to specific participants by percentage or fixed amounts, with optional notes. Archived months show a read-only summary of every rule that was applied, including the derived peso amounts.

---

## Features

### Bill Management
- **Billing period cards**: Home lists all months with grand total, participant count, and Active/Archived status
- **Archive / Unarchive**: Archived months become read-only but remain fully viewable and exportable
- **PDF Export**: A printable month summary — meter consumption with base costs and ₱/kWh rate, components with custom shares, redistribution rules with derived amounts, the final per-participant computation, and all attached photos in a captioned appendix

### Dynamic Bill Components
- **Custom Components**: Any number of components (Electricity, Water, Internet, Rent, Gas, …)
- **Four split methods** with live sum validation for custom amounts/percentages (✓ when balanced, red when not) and derived peso amounts beside percentage inputs
- **Bill photos**: Attach up to two optional photos per component. Uploads are EXIF-rotated upright, stripped of metadata, downscaled to 1600 px, and re-encoded as JPEG (a typical phone photo stores at ~100–300 KB). Stored in the database, so backups include them.
- **Positioning**: Manual position control determines column order everywhere

### Meter Readings
- **Grid and Ledger layouts**: A table view or per-participant cards, switchable per preference (persisted locally)
- **Live recalculation**: Usage, base costs, and the ₱/kWh rate update as you type
- **Pre-fill Support**: Previous readings pre-filled from the prior month
- **Meter photo**: One optional photo of the meter per month (add/replace/remove)

### Adjustments & Redistribution
- **Custom Redistribution**: Shift a participant's component share to others by percentage or fixed amounts
- **Redistribution Notes**: Optional description per rule
- **Computed Amounts**: Derived peso values shown next to percentage inputs in real time
- **Archived summary**: Read-only table of applied rules (with derived amounts) on archived months

### Reports
- **Participant Contribution Share**: Pie chart of each participant's share of total contributions over a selectable month range, with a summary table (total, share %, average, min, max)
- **Total Consumption Trend**: Total monthly kWh and the effective cost per kWh on one chart (separate axes)
- **Electricity Consumption**: Stacked monthly kWh bars per participant with a usage summary table
- **Stable, colorblind-safe colors**: Each participant keeps the same color across charts and ranges

### Participant Management
- **People Directory** in Settings: add and delete people
- **Manage page**: rename or delete participants
- **Per-Month Selection**: Choose who's included when creating a month; link/unlink participants on existing months

### Settings & Backup
- **Database Backup**: Download a timestamped copy of the SQLite database (photos included)
- **Database Restore**: Upload a backup; its schema (and any legacy photo storage) is automatically upgraded on the spot
- **Version Display**: Application version shown in the footer

### User Interface
- **"Industry" design system**: a steel-blue aesthetic — soft-rounded hairline cards, condensed headings, Lucide icons
- **Responsive**: Works on desktop and mobile (photo upload opens the camera on phones)
- **CSRF Protection**: All forms protected via Flask-WTF

---

## Quick Start

### Option 1: Run with Docker (Recommended)

```bash
# Pull the published image
docker run -d -p 8000:8000 \
  -e SECRET_KEY="change-me" \
  -e DATABASE_URL="sqlite:////app/instance/billsonline.db" \
  -v billsonline-data:/app/instance \
  --name billsonline \
  ghcr.io/phdwight/billsonline:latest

# Or build locally
git clone https://github.com/phdwight/billsonline.git
cd billsonline
docker build -t billsonline:local .
docker run -d -p 8000:8000 \
  -e SECRET_KEY="change-me" \
  -e DATABASE_URL="sqlite:////app/instance/billsonline.db" \
  -v billsonline-data:/app/instance \
  --name billsonline billsonline:local
```

Open **http://localhost:8000** in your browser. The schema is created automatically on first start; the named volume keeps your data across upgrades.

#### Docker Compose

```bash
docker compose up -d       # Start (pulls ghcr.io/phdwight/billsonline:latest)
docker compose logs -f     # View logs
docker compose pull && docker compose up -d   # Upgrade to the latest image
docker compose down        # Stop
```

Set `SECRET_KEY` in your environment (or a `.env` next to the compose file) for production.

---

### Option 2: Run Directly with Python

**Prerequisites**: Python 3.12

```bash
# Clone the repository
git clone https://github.com/phdwight/billsonline.git
cd billsonline

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run with the Flask development server (schema auto-creates on first start)
flask --app wsgi run --debug --port 5000
```

Open **http://localhost:5000** in your browser.

> **Note**: `flask run` auto-loads any `.env` it finds in the directory tree. If a parent
> directory has a `.env` with a conflicting `DATABASE_URL`, either remove it or set
> `DATABASE_URL` explicitly.

#### Run with Uvicorn (ASGI — how the Docker image runs)

```bash
# Development with auto-reload
uvicorn asgi:app --host 127.0.0.1 --port 8000 --reload

# Production
uvicorn asgi:app --host 0.0.0.0 --port 8000 --workers 2
```

The ASGI wrapper ([asgi.py](asgi.py)) buffers request bodies and declares them terminated, so form posts work behind proxies that forward chunked bodies without a `Content-Length` (e.g. Cloudflare Tunnel).

---

## Usage Guide

### Getting Started

1. **Add People**: Go to **Settings → People Directory** and add participants
2. **Create a Month**: Click **New month** on the home page, pick the year/month, amounts, and which participants to include
3. **Enter Readings**: Open the month and fill in previous/current meter readings — usage and base costs compute live
4. **Adjust Splits**: In Per-Component Adjustments, set each component's bill total and split method; add custom shares or redistribution rules as needed
5. **Attach Photos** (optional): Add a photo of each physical bill to its component
6. **Review**: The Contributions section shows the final per-participant matrix; export it as a printable PDF

### Redistribution Example

To make Bob cover Alice's Internet share for January:
1. Open the January month
2. Expand **Advanced redistribution** in Per-Component Adjustments
3. Under Internet, set Alice's rule to **Percent** with `Bob: 100`
4. Save — Alice pays ₱0 for Internet, Bob pays her share; the note field records why

### Participant Selection Example

To create a month with only Alice and Bob (excluding Charlie): on the New month form, uncheck Charlie in **Select Participants for this Month** (or use Select All / Deselect All), then submit. Only Alice and Bob appear in that month's calculations. You can also link/unlink participants later from the month's **Month Participants** section.

### Reports

Open **Reports** to pick a From/To month range. The contribution pie shows each person's share of the total for the range; the consumption chart shows monthly kWh per participant. Both come with summary tables.

---

## Tests

The project includes **296 tests** (~88% code coverage): 277 backend tests (most BDD-style with Gherkin feature files) plus 19 Playwright browser tests.

### Run All Tests

```bash
# Backend tests
pytest --ignore=tests/ui

# Everything, with coverage
pytest --cov=app --cov-report=term-missing tests/

# UI tests need a Playwright browser once:
playwright install chromium
pytest tests/ui/ -v
```

### Test Layout

Backend BDD suites live in `tests/bdd/` with Gherkin feature files in `tests/features/`:

| Feature File | Scenarios | Description |
|--------------|-----------|-------------|
| `routes.feature` | 47 | Flask route handlers |
| `repositories.feature` | 31 | Data access layer (CRUD operations) |
| `routes_complex.feature` | 26 | Complex multi-step route scenarios |
| `extended_routes.feature` | 24 | Extended route coverage |
| `calculator.feature` | 23 | Bill calculation logic (splitting, redistribution) |
| `adjustment_service.feature` | 19 | Adjustment service business logic |
| `month_service.feature` | 18 | Month service operations |
| `models.feature` | 10 | SQLAlchemy models and relationships |
| `reports.feature` | 9 | Reports data aggregation |
| `forms.feature` | 7 | WTForms validation rules |
| `monthly_bills.feature` | 7 | Bill CRUD operations |
| `bill_components.feature` | 6 | Component splitting methods |
| `adjustments.feature` | 6 | Cost redistribution |
| `participants.feature` | 5 | Participant management |
| `meter_readings.feature` | 5 | Meter reading tracking |
| `version.feature` | 5 | Version utility tests |

Plain pytest suites cover the newer features: bill photo compression/upload/serving (`test_component_images.py`), PDF export content (`test_pdf_export.py`), the archived redistribution summary (`test_archived_redistribution.py`), base usage cost display (`test_usage_base_cost.py`), and backup-restore schema upgrades (`test_database_restore_schema.py`).

**Example BDD Scenario:**

```gherkin
Scenario: Add an equally split component
  Given participants "Alice, Bob, Charlie" exist
  And a bill for January 2025 exists
  When I add a component "Water" with amount 300.00 split "equal"
  Then each participant should pay 100.00 for "Water"
```

### UI Tests (Playwright)

Located in `tests/ui/` with Gherkin feature files in `tests/ui/features/`:

| Feature File | Scenarios | Description |
|--------------|-----------|-------------|
| `ui_participants.feature` | 5 | Participant UI flows |
| `ui_navigation.feature` | 4 | Page navigation |
| `ui_months.feature` | 3 | Monthly bill creation/archiving |
| `ui_components.feature` | 3 | Adding/editing components |
| `ui_meter_readings.feature` | 2 | Meter reading entry |
| `ui_settings.feature` | 2 | Settings page flows |

```bash
pytest tests/ui/ -v                     # headless
pytest tests/ui/ -v --headed            # visible browser
pytest tests/ui/ -v --headed --slowmo=500
PWDEBUG=1 pytest tests/ui/ -v           # Playwright Inspector
pytest tests/ui/ -v --browser=firefox   # chromium (default) / firefox / webkit
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLAlchemy database URI | `sqlite:///<cwd>/billsonline.db` (Docker: set to `sqlite:////app/instance/billsonline.db`) |
| `SECRET_KEY` | Flask secret key (sessions + CSRF) | `dev-secret` — **always set your own in production** |
| `FLASK_ENV` | Environment mode | `development` |

Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Project Structure

```
billsonline/
├── app/
│   ├── __init__.py          # Package exports (create_app, get_version)
│   ├── factory.py           # Flask application factory
│   ├── version.py           # Version utility
│   ├── config.py            # Configuration classes
│   ├── extensions.py        # Flask extensions (db, migrate, csrf)
│   ├── models.py            # SQLAlchemy models (7 models)
│   ├── repositories.py      # Data access layer
│   ├── forms.py             # WTForms definitions
│   ├── routes/              # Blueprint routes
│   │   ├── registration.py  # Blueprint registration
│   │   ├── home.py          # Billing-period cards (home)
│   │   ├── admin.py         # Management page
│   │   ├── months.py        # Month CRUD, readings, PDF export
│   │   ├── participants.py  # Participant management
│   │   ├── components.py    # Components + bill photos
│   │   ├── adjustments.py   # Redistribution rules
│   │   ├── reports.py       # Reports data API
│   │   └── settings.py      # People directory, backup/restore
│   ├── services/            # Business logic (SOLID)
│   │   ├── bill_calculator.py   # Core calculation engine
│   │   ├── month_service.py     # Month orchestration
│   │   ├── adjustment_service.py# Adjustment logic
│   │   ├── image_service.py     # Bill photo compression (Pillow)
│   │   └── pdf_service.py       # Printable month summary (reportlab)
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS (Industry design system), JS, bundled fonts
├── tests/
│   ├── bdd/                 # Backend tests (277)
│   ├── features/            # Gherkin feature files (16)
│   └── ui/                  # Playwright UI tests (19)
├── migrations/              # Alembic database migrations
├── main.py / asgi.py        # ASGI entrypoints (uvicorn)
├── wsgi.py                  # WSGI entrypoint
├── Dockerfile               # Container build
├── docker-compose.yml       # Docker Compose config
├── requirements.txt         # Python dependencies
└── VERSION                  # App version number
```

### Architecture

This project follows **SOLID principles** with clean separation:

- **Models** (`models.py`): Data structures and relationships only
- **Repositories** (`repositories.py`): Database access, no business logic
- **Services** (`services/`): Business logic with dependency injection
- **Routes** (`routes/`): HTTP handling, delegates to services
- **Factory** (`factory.py`): Application composition root

---

## Deployment Notes

- Merges to `main` trigger CI, which runs the full test suite and publishes a multi-arch image to `ghcr.io/phdwight/billsonline` (`latest`, branch, SHA, and semver tags). Upgrade a server with `docker compose pull && docker compose up -d`.
- Restoring an old database backup through Settings automatically upgrades its schema — no restart needed.
- PDF exports send `Cache-Control: no-store`. If you front the app with a CDN that caches by file extension (Cloudflare does for `.pdf`), this keeps exports fresh; purge any copies cached before this header existed.

## Troubleshooting

**Port already in use:**

```bash
flask --app wsgi run --debug --port 5001
# or
uvicorn asgi:app --port 8001
```

**App starts against the wrong database:** `flask run` picks up `.env` files from parent directories — set `DATABASE_URL` explicitly.

**CSRF 400 error on form submit:**
- Ensure the page was loaded in the same browser session
- If behind a proxy, run via `asgi.py` (uvicorn) or a server that handles chunked request bodies

**Docker container won't start:**

```bash
docker logs billsonline  # Check logs
docker rm billsonline    # Remove and recreate
```

---

## CI/CD

GitHub Actions automatically:
- Runs all tests on PRs to `main` (minimum 80% coverage required) and builds the image without pushing
- On merge to `main`: builds and pushes multi-arch images (`linux/amd64`, `linux/arm64`) to GitHub Container Registry (`ghcr.io/phdwight/billsonline`)
- Tags with `latest`, branch name, git SHA, and semantic versions
- Bumps the patch version after each merge

## Contributing

1. Branch from `develop`, make your changes, and keep the test suite green (`pytest --ignore=tests/ui` for a quick pass)
2. For anything touching runtime behavior, verify against the Docker image (`docker build -t billsonline:local .`) — it matches how production runs
3. Open a PR from `develop` to `main`; CI must pass before merge

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
