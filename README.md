# Bills Online

A simple Flask + SQLite web app to split monthly bills among participants.

Rules implemented:
- Electricity: split by usage percentage based on meter readings difference (current - previous) per participant. If no previous reading, usage defaults to 0.
- Water: split evenly among all participants.
- Internet: split evenly only among participants marked as included in internet; excluded participants pay 0 for internet.

## Quick start

Prerequisites: Python 3.11+ recommended.

1. Create a virtual environment and install dependencies
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app
```
flask --app wsgi:app run --debug
```

Then open http://localhost:5000 in your browser.

## Usage
1. Add participants. Toggle whether each participant is included in the internet bill.
2. Create a month with total amounts for electricity, water, and internet.
3. Open the month and enter previous and current meter readings per participant.
4. View the computed contributions table; totals are rounded to 2 decimals.

All data is stored in a local SQLite database file `billsonline.db` in the project root by default. Configure via `DATABASE_URL` if desired.

### Extras
- CSRF protection is enabled for all POST forms via Flask-WTF.
- Month creation and edit use WTForms validation.
- Archive months to hide them from the main list; view via the Archived page.
- Pagination: months list is paginated (10 per page) for large histories.
- Exports:
	- Per-month CSV from a month’s page
	- All months: CSV and Excel from the Home page

## Tests
Run unit tests for the calculation service:
```
pytest -q
```

## Project structure
- `app/models.py`: SQLAlchemy models
- `app/repositories.py`: data access layer
- `app/services.py`: bill calculation logic
- `app/routes/`: Flask routes and views
- `app/templates/`: Jinja templates
- `wsgi.py`: app entry point

This structure aims to follow SOLID principles by separating concerns across layers.
