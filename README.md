# Bills Online

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
 - UI polish:
 	- Action icons (Edit, Archive, Delete, CSV, Back, View, Unarchive) for quick scanning
 	- Compact mode for dense tables: add `?compact=1` to the URL or toggle from the header

## Tests
Run unit tests for the calculation service:
```
pytest -q
```

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
- `wsgi.py`: app entry point
 - `asgi.py`: ASGI entry point for Uvicorn/Hypercorn

This structure aims to follow SOLID principles by separating concerns across layers.
