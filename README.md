# Bills Online

[![Docker Build](https://github.com/phdwight/billsonline/actions/workflows/docker-build.yml/badge.svg)](https://github.com/phdwight/billsonline/actions/workflows/docker-build.yml)
[![Test Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen)](tests/)

A simple Flask + SQLite web app to split monthly bills among participants.

Rules implemented:
- Electricity: split by usage percentage based on meter readings difference (current - previous) per participant. If no previous reading, usage defaults to 0.
- Water: split evenly among all participants.
- Internet: split evenly among all participants by default. If you need to exclude someone for a month, zero their Internet in Adjustments.

Adjustments and redistribution:
- You can zero any participant’s Electricity/Water/Internet for a month.
- The zeroed amount is redistributed equally among the remaining eligible participants for that component.
- Eligible means “had a non-zero base share for that component” (e.g., for Electricity, non-zero usage; for Water/Internet, all participants).

## Quick start

Prerequisites: Python 3.11+ recommended.

1. Create a virtual environment and install dependencies
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Initialize the database (first run and after schema changes)
```
flask --app wsgi:app db upgrade
```

3. Run the app (Flask dev server)
```
flask --app wsgi:app run --debug
```

Then open http://localhost:5000 in your browser.

## Usage
1. Add participants.
2. Create a month with total amounts for electricity, water, and internet.
3. Open the month and enter previous and current meter readings per participant.
4. Use the Adjustments section to zero any component (e.g., exclude someone from Internet this month).
5. View the computed contributions table; totals are rounded to 2 decimals and badges indicate zeroed components (E/W/I).

All data is stored in a local SQLite database file `billsonline.db` in the project root by default. Configure via `DATABASE_URL` if desired.

## Screenshots / GIF
Add your own screenshots or a short GIF to quickly show the main flows. Place files under `docs/screenshots/` and update the paths below. You can use the helper script `scripts/record_gif.sh` (macOS + ffmpeg) to capture a GIF.

- Home (months list and create month)

	![Home](docs/screenshots/home.png)

- Month detail (readings, adjustments, contributions)

	![Month detail](docs/screenshots/month_detail.png)

- Adjustments in action (GIF recommended)

	![Adjustments flow](docs/screenshots/flow.gif)

### Extras
- CSRF protection is enabled for all POST forms via Flask-WTF.
- Month creation and edit use WTForms validation.
- Archive months to hide them from the main list; view via the Archived page.
- Pagination: months list is paginated (10 per page) for large histories.
- Exports:
	- Per-month CSV download of the Contributions table from a month’s page
- Settings page:
	- Download database backup with timestamped filename
	- Upload and replace database (with automatic backup and confirmation)
	- Version number display in footer (auto-incremented on push)
- UI polish:
	- Action icons (Edit, Archive, Delete, CSV, Back, View, Unarchive) for quick scanning
	- Compact mode for dense tables: add `?compact=1` to the URL or toggle from the header

## Tests
Run unit tests for the calculation service:
```
pytest -q
```

Run tests with coverage report:
```
pytest --cov=app --cov-report=term-missing tests/
```

Current test coverage: **86%** (148 tests)

## Run with Docker

The easiest way to run the application is with Docker.

### Using Pre-built Image (Recommended)

Pull and run the latest image from GitHub Container Registry:

```bash
# Pull the latest image
docker pull ghcr.io/phdwight/billsonline:latest

# Run with docker-compose (recommended)
curl -O https://raw.githubusercontent.com/phdwight/billsonline/main/docker-compose.yml
docker compose up -d

# Or run directly
docker run -d -p 1982:8000 --name billsonline ghcr.io/phdwight/billsonline:latest
```

The app will be available at **http://localhost:1982**

### Build Locally

```bash
# Clone the repository
git clone https://github.com/phdwight/billsonline.git
cd billsonline

# Build and start the container
docker compose up -d --build

# View logs
docker compose logs -f

# Stop the container
docker compose down
```

### Prerequisites
- Docker and Docker Compose installed

### Quick Start
```bash
# Build and start the container
docker compose up -d --build

# View logs
docker compose logs -f

# Stop the container
docker compose down
```

The app will be available at **http://localhost:1982**

### Database Persistence

The SQLite database is stored in a Docker volume at `/app/instance/billsonline.db` inside the container. Your data persists across container restarts.

#### Export database (backup)
```bash
# Copy from container to your local machine
docker compose cp app:/app/instance/billsonline.db ./billsonline-backup.db
```

#### Import database (restore)
```bash
# Copy from your local machine into the container
docker compose cp ./billsonline.db app:/app/instance/billsonline.db

# Restart to apply
docker compose restart
```

### Environment Variables

Create a `.env` file in the project root for custom configuration:
```
SECRET_KEY=your-secure-random-key-here
FLASK_ENV=production
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Deploy to Another Machine

1. Copy `docker-compose.yml` to the new machine (or download it):
   ```bash
   curl -O https://raw.githubusercontent.com/phdwight/billsonline/main/docker-compose.yml
   ```
2. Install Docker on the new machine
3. Create a `.env` file with your `SECRET_KEY`
4. Run `docker compose up -d`
5. (Optional) Import your database backup using the steps above

## Run with Uvicorn (ASGI)

You can run this Flask app with an ASGI server using a WSGI→ASGI adapter. The ASGI app is defined in `asgi.py` and wraps the Flask WSGI app via `asgiref.wsgi.WsgiToAsgi`.

1) Install (includes `uvicorn` and `asgiref`)
```
pip install -r requirements.txt
```

2) Dev run with auto-reload
```
uvicorn asgi:app --host 127.0.0.1 --port 8000 --reload
```

3) Production run (example)
```
uvicorn asgi:app --host 0.0.0.0 --port 8000 --workers 2
```

Env vars:
- DATABASE_URL (optional; defaults to local SQLite file `billsonline.db`)
- SECRET_KEY (set for production)

Reverse proxy:
- Put Nginx/Caddy in front for TLS and static file caching.

Example `systemd` unit (optional):
```
[Unit]
Description=BillsOnline (Uvicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/billsonline
Environment="DATABASE_URL=sqlite:////opt/billsonline/billsonline.db"
Environment="SECRET_KEY=change-me"
ExecStart=/opt/billsonline/.venv/bin/uvicorn asgi:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

## Troubleshooting
- Can’t reach the app or get 403 on 127.0.0.1:
	- Use the correct URL with the port: http://localhost:5000/ or http://127.0.0.1:5000/
	- If behind a VPN/proxy, try using localhost instead of 127.0.0.1, or disconnect the VPN.

- “Port 5000 is already in use” or browser shows another app:
	- Run on a different port:
		- `flask --app wsgi:app run --debug --port 5001`

- “flask: command not found”:
	- Use your virtualenv’s Python: `python -m flask --app wsgi:app run`
	- Or activate the venv: `source .venv/bin/activate`

- Database file issues (permission/path):
	- Default DB path is `<repo>/billsonline.db`. Ensure the folder is writable.
	- You can override with `DATABASE_URL` (e.g., `sqlite:////absolute/path/to/db.sqlite`).

- Migration errors (missing tables/columns):
	- Run migrations: `flask --app wsgi:app db upgrade`
	- If Alembic is out of sync, you can recreate the DB (development only): remove `billsonline.db` and run upgrade again.

- CSRF 400 on form submit:
	- Ensure the page was loaded in the same browser session and the CSRF token field is present in the form.

## Project structure
- `app/models.py`: SQLAlchemy models
- `app/repositories.py`: data access layer
- `app/services.py`: bill calculation logic
- `app/routes/`: Flask routes and views
- `app/templates/`: Jinja templates
- `tests/`: test suite (148 tests, 86% coverage)
- `wsgi.py`: app entry point
- `asgi.py`: ASGI entry point for Uvicorn/Hypercorn
- `Dockerfile`: container build configuration
- `VERSION`: application version (auto-incremented on push)
- `.github/workflows/`: CI/CD pipelines (including version bump)

This structure aims to follow SOLID principles by separating concerns across layers.

## CI/CD

This project uses GitHub Actions for continuous integration:

- **Tests**: All tests must pass before Docker build proceeds (minimum 80% coverage required)
- **Docker Build**: On every push to `main`/`master`, a Docker image is automatically built and pushed to GitHub Container Registry (`ghcr.io/phdwight/billsonline`)
- **Tags**: Images are tagged with `latest`, branch name, git SHA, and semantic versions (e.g., `v1.0.0`)
- **Multi-platform**: Images are built for both `linux/amd64` (Intel/AMD) and `linux/arm64` (Apple Silicon)

### Branch Protection (Recommended)

To enforce that tests pass before merging, configure branch protection in GitHub:

1. Go to **Settings** → **Branches** → **Add rule**
2. Set **Branch name pattern** to `main` (or `master`)
3. Enable **Require status checks to pass before merging**
4. Search and select **test** as a required status check
5. (Optional) Enable **Require branches to be up to date before merging**
6. Save changes
