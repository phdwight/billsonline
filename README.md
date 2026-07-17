# Bills Online

[![Docker Build](https://github.com/phdwight/billsonline/actions/workflows/docker-build.yml/badge.svg)](https://github.com/phdwight/billsonline/actions/workflows/docker-build.yml)
[![Test Coverage](https://img.shields.io/badge/coverage-86%25-brightgreen)](tests/)
[![Tests](https://img.shields.io/badge/tests-270%20passing-brightgreen)](tests/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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
The people sharing the bills (e.g., Alice, Bob, Charlie). Add them once and they're available for all months. When creating a new month, you can select which participants to include - only selected participants will appear in that month's readings, adjustments, and contributions.

### Monthly Bills
Each month gets its own bill entry containing multiple components and meter readings.

### Bill Components
Individual line items within a monthly bill. Each component has:
- **Name**: e.g., "Electricity", "Water", "Internet", "Rent"
- **Amount**: The total cost
- **Split Method**: How to divide the cost among participants

### Split Methods
- **Equal**: Everyone pays the same amount (total ÷ number of participants)
- **Usage**: Split proportionally based on meter reading differences
- **Percentage**: Custom percentages per participant (must sum to 100%)
- **Fixed Amount**: Specific amounts per participant

### Meter Readings
For usage-based bills like electricity, enter each person's meter readings:
- **Previous Reading**: Where the meter was at the start of the period
- **Current Reading**: Where the meter is now
- **Usage** = Current - Previous (calculated automatically)

### Adjustments
When someone shouldn't pay for a component (e.g., they were away):
1. "Zero out" their share for that component
2. Their portion gets redistributed to others
3. Redistribution can be equal, by percentage, or fixed amounts

---

## Features

### Bill Management
- **Monthly Bills**: Create and manage bills for each month with multiple cost components
- **Archive System**: Archive old bills to keep the main view clean; view archived bills separately
- **Pagination**: Bills list is paginated (10 per page) for large histories
- **CSV Export**: Download per-month contribution tables as CSV files

### Dynamic Bill Components
- **Custom Components**: Add any number of bill components (Electricity, Water, Internet, Rent, etc.)
- **Flexible Splitting Methods**:
  - **Equal**: Split evenly among all participants
  - **Usage-based**: Split by meter reading differences (current - previous)
  - **Percentage**: Assign custom percentages to each participant
  - **Fixed Amount**: Assign specific amounts to each participant
- **Component Ordering**: Drag-and-drop or manual position control

### Meter Readings
- **Track Usage**: Record previous and current meter readings per participant
- **Auto-calculation**: Usage automatically calculated as (current - previous)
- **Pre-fill Support**: Previous readings can be pre-filled from the last month

### Adjustments & Redistribution
- **Zero Out**: Exclude any participant from any component for a specific month
- **Custom Redistribution**: When zeroing out, redistribute to:
  - All remaining participants equally (default)
  - Specific participants by percentage
  - Specific participants by fixed amounts
- **Redistribution Notes**: Add optional notes to describe why a redistribution was made
- **Computed Amounts**: See calculated amounts next to percentage inputs in real-time
- **Multiple Adjustments**: Zero out multiple participants with cascading redistribution

### Participant Management
- **Add/Edit/Delete**: Manage household participants
- **Unique Names**: Prevents duplicate participant names
- **Per-Month Selection**: Choose which participants to include when creating a new month
- **Flexible Membership**: Add or remove participants from existing months as needed

### Settings & Backup
- **Database Backup**: Download timestamped database backups
- **Database Restore**: Upload and restore from backup files
- **Auto Schema Migration**: Uploading older database files automatically updates the schema
- **Version Display**: Application version shown in footer

### User Interface
- **Responsive Design**: Works on desktop and mobile
- **Theme Support**: Default and vibrant themes available
- **Compact Mode**: Dense table view (add `?compact=1` to URL)
- **Action Icons**: Quick-access icons for Edit, Archive, Delete, CSV, etc.
- **CSRF Protection**: All forms protected via Flask-WTF

---

## Quick Start

### Option 1: Run with Docker (Recommended)

```bash
# Pull and run the latest image
docker run -d -p 8000:8000 --name billsonline billsonline:latest

# Or build locally
git clone https://github.com/phdwight/billsonline.git
cd billsonline
docker build -t billsonline:latest .
docker run -d -p 8000:8000 --name billsonline billsonline:latest
```

Open **http://localhost:8000** in your browser.

#### Docker with Persistent Database

```bash
# Run with volume mount for data persistence
docker run -d -p 8000:8000 \
  -v billsonline-data:/app \
  --name billsonline \
  billsonline:latest

# Copy existing database into container
docker cp ./billsonline.db billsonline:/app/billsonline.db
docker restart billsonline

# Backup database from container
docker cp billsonline:/app/billsonline.db ./billsonline-backup.db
```

#### Docker Compose

```bash
docker compose up -d --build    # Build and start
docker compose logs -f          # View logs
docker compose down             # Stop
```

---

### Option 2: Run Directly with Python

**Prerequisites**: Python 3.11+ (3.12 recommended)

```bash
# Clone the repository
git clone https://github.com/phdwight/billsonline.git
cd billsonline

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask --app wsgi:app db upgrade

# Run with Flask development server
flask --app wsgi:app run --debug --port 5000
```

Open **http://localhost:5000** in your browser.

#### Run with Uvicorn (ASGI - Production)

```bash
# Development with auto-reload
uvicorn asgi:app --host 127.0.0.1 --port 8000 --reload

# Production
uvicorn asgi:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## Usage Guide

### Getting Started

1. **Add Participants**: Go to Admin and add participants (e.g., Alice, Bob, Charlie)
2. **Create a Month**: Create a new monthly bill entry and select which participants to include (all are selected by default)
3. **Add Components**: Add bill components with amounts and splitting methods
4. **Enter Readings**: For usage-based components, enter meter readings
5. **View Results**: See the calculated contributions table

### Adjustments Example

To exclude Alice from Internet for January:
1. Open the January bill
2. Go to Adjustments section
3. Zero out Alice's Internet component
4. Choose redistribution method (equal to others, or custom percentages)
5. Save - Alice pays $0, others pay her share

### Participant Selection Example

To create a month where only Alice and Bob are included (Charlie is excluded):
1. Go to Admin page
2. Click "Create New Month"
3. In the "Select Participants for this Month" section:
   - Uncheck Charlie's checkbox, OR
   - Click the "✕" remove button next to Charlie's name, OR
   - Use "Deselect All" and then manually select Alice and Bob
4. Fill in the month details and bill amounts
5. Submit - only Alice and Bob will appear in that month's calculations

**Tip:** You can use "Select All" / "Deselect All" buttons to quickly manage participant selection during month creation.

### Managing Participants

To manage (edit or delete) participants:
1. Go to Admin page
2. Click "👥 Participants" or "Manage" link in the Participants section
3. On the Manage Participants page:
   - **Edit**: Modify participant name in the text field and click "✓" to save
   - **Delete**: Click "✕" button to permanently remove a participant
   - **Warning**: Deleting a participant will remove them from all months and cannot be undone

---

## Tests

The project includes comprehensive test coverage with **279 tests** (87% code coverage) using **BDD-style Gherkin** feature files across all test categories.

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=term-missing tests/
```

### Test Categories

#### BDD Tests (251 tests)

All tests use **pytest-bdd** with Gherkin feature files for readable, behavior-driven specifications.

Located in `tests/bdd/` with Gherkin feature files in `tests/features/`:

| Feature File | Scenarios | Description |
|--------------|-----------|-------------|
| `calculator.feature` | 23 | Bill calculation logic (splitting, redistribution) |
| `models.feature` | 10 | SQLAlchemy models and relationships |
| `repositories.feature` | 31 | Data access layer (CRUD operations) |
| `routes.feature` | 47 | Flask route handlers |
| `routes_complex.feature` | 26 | Complex multi-step route scenarios |
| `forms.feature` | 7 | WTForms validation rules |
| `version.feature` | 5 | Version utility tests |
| `adjustment_service.feature` | 19 | Adjustment service business logic |
| `month_service.feature` | 18 | Month service operations |
| `extended_routes.feature` | 24 | Extended route coverage |
| `participants.feature` | 5 | Participant management |
| `monthly_bills.feature` | 7 | Bill CRUD operations |
| `bill_components.feature` | 6 | Component splitting methods |
| `adjustments.feature` | 6 | Cost redistribution |
| `meter_readings.feature` | 5 | Meter reading tracking |

**Example BDD Scenario:**

```gherkin
Scenario: Add an equally split component
  Given participants "Alice, Bob, Charlie" exist
  And a bill for January 2025 exists
  When I add a component "Water" with amount 300.00 split "equal"
  Then each participant should pay 100.00 for "Water"

Scenario Outline: Validate redistribution rules
  Given a component "<component>" with amount <amount>
  When I validate a <mode> rule with targets summing to <sum>
  Then the validation should <result>

  Examples:
    | component   | amount | mode    | sum   | result |
    | Electricity | 100.0  | percent | 100.0 | pass   |
    | Water       | 150.0  | percent | 90.0  | fail   |
    | Internet    | 100.0  | amount  | 50.0  | pass   |
```

### Run Specific Test Categories

```bash
# Run all BDD tests
pytest tests/bdd/

# Run specific feature file tests
pytest tests/bdd/test_bdd_calculator.py -v

# Run tests matching a pattern
pytest -k "adjustment" -v
```

### UI Tests (Playwright)

Located in `tests/ui/` with Gherkin feature files in `tests/ui/features/`. These tests use **pytest-bdd** with **Playwright** for browser automation.

| Feature File | Scenarios | Description |
|--------------|-----------|-------------|
| `ui_participants.feature` | 5 | Participant UI flows |
| `ui_months.feature` | 3 | Monthly bill creation/archiving |
| `ui_components.feature` | 3 | Adding/editing components |
| `ui_meter_readings.feature` | 2 | Meter reading entry |
| `ui_navigation.feature` | 4 | Page navigation |

#### Run UI Tests

```bash
# Run all UI tests (headless by default)
pytest tests/ui/ -v

# Run with visible browser (headed mode)
pytest tests/ui/ -v --headed

# Slow down execution to visually follow the test (in ms)
pytest tests/ui/ -v --headed --slowmo=500

# Run a specific UI test file
pytest tests/ui/steps/test_navigation_steps.py -v --headed

# Run with browser debug mode (pauses on failure)
PWDEBUG=1 pytest tests/ui/ -v

# Run specific browser (default is chromium)
pytest tests/ui/ -v --browser=firefox
pytest tests/ui/ -v --browser=webkit
```

#### Playwright Options Reference

| Option | Description |
|--------|-------------|
| `--headed` | Run with visible browser window |
| `--slowmo=<ms>` | Slow down operations by specified milliseconds |
| `--browser=<name>` | Browser to use: `chromium`, `firefox`, or `webkit` |
| `--browser-channel=<channel>` | Use specific browser channel (e.g., `chrome`, `msedge`) |
| `--tracing=on` | Enable Playwright tracing for debugging |
| `PWDEBUG=1` | Environment variable to enable Playwright Inspector |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database path | `sqlite:///billsonline.db` |
| `SECRET_KEY` | Flask secret key | Auto-generated (set for production) |
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
│   ├── models.py            # SQLAlchemy models (6 models)
│   ├── repositories.py      # Data access layer
│   ├── forms.py             # WTForms definitions
│   ├── routes/              # Blueprint routes
│   │   ├── __init__.py      # Re-exports register_blueprints
│   │   ├── registration.py  # Blueprint registration function
│   │   ├── admin.py         # Admin dashboard
│   │   ├── home.py          # Home page routes
│   │   ├── months.py        # Monthly bill CRUD
│   │   ├── participants.py  # Participant management
│   │   ├── components.py    # Bill component management
│   │   ├── adjustments.py   # Adjustment/redistribution
│   │   └── settings.py      # Settings and backup
│   ├── services/            # Business logic (SOLID)
│   │   ├── __init__.py      # Re-exports services
│   │   ├── bill_calculator.py  # Core calculation engine
│   │   ├── month_service.py    # Month orchestration
│   │   └── adjustment_service.py  # Adjustment logic
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS, JS, themes
├── tests/
│   ├── bdd/                 # BDD step definitions (251 tests)
│   │   ├── conftest.py      # Fixtures and mocks
│   │   └── test_bdd_*.py    # Step implementations (15 files)
│   ├── features/            # Gherkin feature files (15 features)
│   └── ui/                  # Playwright UI tests (19 tests)
├── migrations/              # Alembic database migrations
├── docs/                    # Documentation assets
├── main.py                  # ASGI entrypoint
├── asgi.py                  # ASGI app wrapper
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

## Troubleshooting

### Common Issues

**Port already in use:**

```bash
# Use a different port
flask --app wsgi:app run --debug --port 5001
# Or for uvicorn
uvicorn asgi:app --port 8001
```

**Database migration errors:**

```bash
flask --app wsgi:app db upgrade
# If out of sync, recreate (dev only):
rm billsonline.db && flask --app wsgi:app db upgrade
```

**CSRF 400 error on form submit:**
- Ensure the page was loaded in the same browser session
- Check that CSRF token field is present in forms

**Docker container won't start:**

```bash
docker logs billsonline  # Check logs
docker rm billsonline    # Remove and recreate
```

---

## CI/CD

GitHub Actions automatically:
- Runs all tests (minimum 80% coverage required)
- Builds Docker images on push to `main`
- Pushes to GitHub Container Registry (`ghcr.io/phdwight/billsonline`)
- Tags with `latest`, branch name, git SHA, and semantic versions
- Builds for `linux/amd64` and `linux/arm64` platforms

---

## License

MIT License - see [LICENSE](LICENSE) file.
