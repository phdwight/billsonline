# Handoff — Bills Online

A guide for future LLM agents (and humans) to ramp up on this codebase in one read.

## 1. What this app is

Bills Online is a small Flask web application for splitting monthly household utility bills among a fixed set of housemates. A user defines participants, creates a `MonthlyBill` per calendar month, attaches arbitrary `BillComponent`s (e.g. Electricity, Water, Internet), enters meter readings for usage-based components, and optionally records per-component adjustments that zero out a participant's share and redistribute it to others. The app then renders a contributions table per month and supports CSV export and multi-month reports. See product description in [README.md#L9-L57](README.md#L9-L57).

Non-obvious key traits, derived from the code:

- Server-rendered Jinja2 monolith — no SPA, no client-side framework. Routes return HTML via [app/templates/](app/templates).
- Dual entrypoints: WSGI (`wsgi.py`) for `flask run`, and an ASGI wrapper (`asgi.py`, `main.py`) using `asgiref.WsgiToAsgi` so Uvicorn can serve it. Docker uses ASGI ([Dockerfile#L26-L27](Dockerfile#L26-L27)).
- SQLite-only persistence in practice. The settings page downloads and replaces the raw `.db` file, and the upload path runs ad-hoc `sqlite3` `ALTER TABLE` migrations directly ([app/routes/settings.py#L67-L95](app/routes/settings.py#L67-L95)).
- Two parallel data models live side by side: legacy fixed columns (`electricity_amount`, `water_amount`, `internet_amount` on `MonthlyBill`) and the newer dynamic `BillComponent` table. The services synthesise legacy components on the fly when no dynamic components exist ([app/services/month_service.py#L196-L218](app/services/month_service.py#L196-L218)).
- BDD-first testing: `pytest-bdd` with Gherkin feature files for every layer, plus Playwright UI tests ([pytest.ini](pytest.ini), [tests/features/](tests/features)).
- Pydantic is used only as a typed return shape for calculator output (`DynamicContribution`), not for request validation ([app/services/bill_calculator.py#L10-L20](app/services/bill_calculator.py#L10-L20)).
- All money-side currency strings are formatted with the literal `₱` (Philippine peso) in error messages — there is no locale or formatting helper ([app/services/adjustment_service.py#L80-L84](app/services/adjustment_service.py#L80-L84)).

## 2. Architecture

### Tech stack

| Concern | Choice | Source |
| --- | --- | --- |
| Language | Python 3.12 (slim base image; CI sets 3.12) | [Dockerfile#L1](Dockerfile#L1), [.github/workflows/docker-build.yml#L29](.github/workflows/docker-build.yml#L29) |
| Local venv hint | `billsonline-env` via pyenv | [.python-version](.python-version) |
| Web framework | Flask 3.1.2 | [requirements.txt#L1](requirements.txt#L1) |
| ORM / migrations | Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.45, Flask-Migrate 4.1.0 (Alembic) | [requirements.txt#L2-L4](requirements.txt#L2-L4) |
| Forms / CSRF | Flask-WTF 1.2.2, WTForms 3.2.1 | [requirements.txt#L11-L12](requirements.txt#L11-L12) |
| Validation models | Pydantic 2.12.5 (output shapes only) | [requirements.txt#L5](requirements.txt#L5) |
| ASGI bridge | `asgiref` 3.11.0 + Uvicorn 0.40.0 | [requirements.txt#L14-L15](requirements.txt#L14-L15), [asgi.py#L1-L8](asgi.py#L1-L8) |
| Datastore | SQLite via `DATABASE_URL` (default `sqlite:///billsonline.db`) | [app/config.py#L1-L10](app/config.py#L1-L10) |
| Tests | pytest 9.0.2, pytest-bdd 8.1.0, pytest-playwright 0.7.2, Playwright 1.57.0 | [requirements.txt#L6-L9](requirements.txt#L6-L9) |
| Misc | openpyxl 3.1.5 (declared but no current importers in `app/`), python-dotenv 1.2.1 | [requirements.txt#L13](requirements.txt#L13) |

Version drift to watch: pytest 9.x is recent — some pytest plugins still target 8.x. Pydantic 2.x is used with `ConfigDict(arbitrary_types_allowed=True)` to hold SQLAlchemy models, which is unusual; do not assume Pydantic validation runs on inputs.

### Layout

```
billsonline/
├── app/                          # Flask application package
│   ├── __init__.py               # Re-exports create_app, get_version
│   ├── factory.py                # Application factory; init extensions, register blueprints
│   ├── config.py                 # Single Config class (SECRET_KEY, DATABASE_URL)
│   ├── extensions.py             # db, migrate, csrf singletons
│   ├── version.py                # Reads VERSION file
│   ├── models.py                 # SQLAlchemy models (Participant, MonthlyBill, MeterReading,
│   │                             #   MonthParticipant, BillComponent, ComponentAdjustment)
│   ├── repositories.py           # All DB access; one *Repository class per aggregate
│   ├── forms.py                  # MonthForm (WTForms); only one form class exists
│   ├── routes/                   # One blueprint per domain area
│   │   ├── registration.py       # register_blueprints(app)
│   │   ├── home.py               # /  → redirect to latest month
│   │   ├── admin.py              # /admin
│   │   ├── months.py             # /months (CRUD + show + edit + CSV)
│   │   ├── participants.py       # /participants
│   │   ├── components.py         # /months/<id>/components
│   │   ├── adjustments.py        # /months/<id>/adjustments
│   │   ├── reports.py            # /reports + /reports/data JSON
│   │   └── settings.py           # /settings (db backup/restore)
│   ├── services/                 # Business logic, dependency-injected
│   │   ├── bill_calculator.py    # Pure calculation engine (no DB)
│   │   ├── month_service.py      # Month orchestration, CSV export
│   │   └── adjustment_service.py # Adjustment validation + persistence
│   ├── templates/                # Jinja2 templates (one per page)
│   └── static/                   # base.css, style.css, js/, themes/
├── migrations/                   # Alembic config + versions/*.py
├── tests/
│   ├── features/                 # *.feature Gherkin (logic layer)
│   ├── bdd/                      # pytest-bdd step defs for logic features
│   │   └── conftest.py           # Mock dataclasses + MockCalculator
│   └── ui/
│       ├── features/             # *.feature Gherkin (UI)
│       └── steps/                # pytest-bdd + Playwright step defs
├── docs/screenshots/             # Documentation assets
├── main.py / asgi.py / wsgi.py   # Entrypoints
├── Dockerfile / docker-compose.yml
├── pytest.ini
├── requirements.txt
└── VERSION                       # Plain-text semver, single line
```

The `billsonline.db.backup_*` files at the repo root are leftover backups produced by the settings upload path (see Pitfalls).

### State / data flow

Single source of truth: the SQLite database, accessed exclusively through the repositories in [app/repositories.py](app/repositories.py). Models in [app/models.py](app/models.py) own the schema and relationships; nothing else should touch `db.session` directly. Routes do touch `db.session` in a handful of places to roll back on `IntegrityError` (e.g. [app/routes/months.py#L125-L128](app/routes/months.py#L125-L128)) — that is the only sanctioned exception.

Request lifecycle (typical write):

1. Blueprint route in [app/routes/](app/routes) parses `request.form` / `request.args`.
2. Route instantiates a service via a `_get_*` factory function (poor-man's DI seam used by tests).
3. Service uses one or more repositories to load aggregates, calls `BillCalculator` for pure math, then writes through repositories.
4. Route flashes a message and redirects (`redirect(url_for(...))`); GETs render Jinja templates.

Derived values (per-participant contributions per component) are not stored — they are recomputed on every render and CSV/JSON export by `BillCalculator.compute_contributions_dynamic` ([app/services/bill_calculator.py#L26-L113](app/services/bill_calculator.py#L26-L113)).

Membership: when a `MonthlyBill` has no rows in `month_participants`, the month service backfills membership with every current participant (legacy compatibility) — [app/services/month_service.py#L56-L65](app/services/month_service.py#L56-L65).

### Key patterns in use

- **Application factory** — `create_app()` is the composition root; `wsgi.py`/`asgi.py`/`main.py` import it. See [app/factory.py#L7-L30](app/factory.py#L7-L30).
- **Repository pattern** — one class per aggregate in [app/repositories.py](app/repositories.py); all `db.session` queries live there. Add a new repository alongside its model.
- **Service layer with constructor injection** — [app/services/month_service.py#L29-L43](app/services/month_service.py#L29-L43) and [app/services/adjustment_service.py#L25-L41](app/services/adjustment_service.py#L25-L41) accept repositories and a calculator as optional constructor args (defaulting to real instances) so tests can swap them.
- **Blueprint-per-domain** — each route module declares its own `bp = Blueprint(...)` with a URL prefix and is registered in [app/routes/registration.py](app/routes/registration.py).
- **Strategy-by-string** — `BillComponent.split_method` is a free-form string (`"equal" | "usage" | "percentage" | "amount"`). The dispatch is an `if/elif` chain inside [app/services/bill_calculator.py#L60-L96](app/services/bill_calculator.py#L60-L96). To add a method, extend that chain and (separately) the validation in [app/routes/months.py#L161-L162](app/routes/months.py#L161-L162) and [app/routes/components.py#L62-L63](app/routes/components.py#L62-L63).
- **Pydantic DTO for output** — `DynamicContribution` is the calculator's return type, with a `computed_field` `total` ([app/services/bill_calculator.py#L13-L23](app/services/bill_calculator.py#L13-L23)).

### Cross-cutting concerns

- **Persistence / migrations.** Alembic via Flask-Migrate; versions in [migrations/versions/](migrations/versions). The factory also calls `db.create_all()` inside an app context ([app/factory.py#L17-L19](app/factory.py#L17-L19)), so a fresh SQLite file works without running `flask db upgrade`. The settings upload path bypasses Alembic and patches schema with raw SQL ([app/routes/settings.py#L74-L93](app/routes/settings.py#L74-L93)) — see Pitfalls.
- **Auth.** None. The app is single-tenant and unauthenticated.
- **Config / secrets.** Read from env in [app/config.py](app/config.py). Only `SECRET_KEY` and `DATABASE_URL` are used; `SECRET_KEY` defaults to `"dev-secret"` which must be overridden in production.
- **CSRF.** `flask_wtf.CSRFProtect` is initialised globally ([app/extensions.py#L5](app/extensions.py#L5), [app/factory.py#L14](app/factory.py#L14)); every form template must include the CSRF token.
- **Logging.** Standard `current_app.logger` only (see [app/routes/adjustments.py#L27-L37](app/routes/adjustments.py#L27-L37)). No structured logging, no observability stack.
- **Template context.** `app_version` is injected into every template via a `context_processor` ([app/factory.py#L25-L28](app/factory.py#L25-L28)).
- **Error handling.** Repositories call `flask.abort(404)` when an entity is missing ([app/repositories.py#L26-L29](app/repositories.py#L26-L29)). Routes flash a message and redirect; there are no custom error pages.
- **Pagination.** Server-side via SQLAlchemy `.paginate(...)` ([app/repositories.py#L86-L91](app/repositories.py#L86-L91)).
- **i18n / accessibility / feature flags / background jobs / PWA.** None.

### Concurrency / runtime model

Synchronous WSGI. Under Uvicorn the Flask app is wrapped by `WsgiToAsgi` and runs on a thread executor; do not introduce `async def` Flask views — they will not be awaited correctly through the wrapper.

### Reusable conventions

- Every route module defines small `_get_<repo>` and `_get_<service>` factory functions at module top. Reuse this pattern so tests can monkeypatch them.
- Flash categories used in templates: `info`, `error`, `warning`, `success` (e.g. [app/routes/settings.py#L82-L94](app/routes/settings.py#L82-L94)).
- Redirect target after writes is almost always `url_for("months.show", bill_id=...)` or `url_for("home.index")`.
- CSV column ordering: `Participant`, each component name in order, `Total`, with a trailing `Totals` row ([app/services/month_service.py#L171-L189](app/services/month_service.py#L171-L189)).

## 3. Functional decisions and unique attributes

**Domain model.**

- `MonthlyBill` keeps three legacy float columns (`electricity_amount`, `water_amount`, `internet_amount`) even though the canonical model is dynamic `BillComponent` rows ([app/models.py#L20-L31](app/models.py#L20-L31)). New month creation writes both: legacy columns plus auto-synthesised "Electricity"/"Water"/"Internet" components ([app/services/month_service.py#L242-L286](app/services/month_service.py#L242-L286)). CSV export falls back to synthesising components from legacy amounts when none exist ([app/services/month_service.py#L196-L218](app/services/month_service.py#L196-L218)).
- `Participant.include_in_internet` was removed (see [migrations/versions/7c2b1a4f1e3b_remove_include_in_internet.py](migrations/versions/7c2b1a4f1e3b_remove_include_in_internet.py)) — exclusions are now expressed as `ComponentAdjustment` rows. The comment in [app/models.py#L11-L13](app/models.py#L11-L13) notes the column may still exist in older databases.
- `(year, month)` is unique on `MonthlyBill` ([app/models.py#L31](app/models.py#L31)); `(month_id, name)` is unique on `BillComponent` ([app/models.py#L82](app/models.py#L82)); `(month_id, component_id, participant_id)` is unique on `ComponentAdjustment` ([app/models.py#L103-L105](app/models.py#L103-L105)). Routes catch `IntegrityError` to surface friendly flash messages — preserve that behaviour.

**Calculation / redistribution.**

- `BillCalculator` normalises percentage distributions even when they do not sum to 100, dividing by the actual total ([app/services/bill_calculator.py#L72-L82](app/services/bill_calculator.py#L72-L82)).
- An unknown `split_method` is treated as `equal` rather than raising ([app/services/bill_calculator.py#L93-L96](app/services/bill_calculator.py#L93-L96)).
- A participant with a `redis_rule` is implicitly zeroed even if `zero=False` ([app/services/bill_calculator.py#L122-L127](app/services/bill_calculator.py#L122-L127)).
- After applying the per-zeroed-participant rules, any **leftover** (zeroed amount not covered by rules) is split equally across remaining members ([app/services/bill_calculator.py#L249-L255](app/services/bill_calculator.py#L249-L255)).
- Rounding correction: contributions are forced to sum back to the component total by adjusting the largest remaining contribution ([app/services/bill_calculator.py#L158-L168](app/services/bill_calculator.py#L158-L168)).
- Validation forbids submitting a `percent` rule that does not sum to 100% or an `amount` rule that does not sum to the zeroed participant's base amount ([app/services/adjustment_service.py#L73-L86](app/services/adjustment_service.py#L73-L86)).

**Persistence.**

- The app uses both Flask-Migrate (Alembic) **and** `db.create_all()` at startup. New tables get created automatically, but column additions still require an Alembic revision.
- The settings upload endpoint replaces the raw `.db` file and then runs a hand-coded `ALTER TABLE` to add the `notes` column to `component_adjustments` ([app/routes/settings.py#L74-L93](app/routes/settings.py#L74-L93)). Only one column is patched there; other schema drift on uploaded databases is silently tolerated.

**UI.**

- `GET /` redirects to the most recent non-archived month, or `/admin` if there is none ([app/routes/home.py#L18-L25](app/routes/home.py#L18-L25)).
- Compact mode is toggled with `?compact=1` (handled in templates).

**Pitfalls to watch.**

- *Two sources of truth for split methods.* `BillCalculator` accepts `usage | equal | percentage | amount`, but [app/routes/components.py#L62-L63](app/routes/components.py#L62-L63) hard-codes the allowed list as `("usage", "equal")` only, while [app/routes/months.py#L161-L162](app/routes/months.py#L161-L162) accepts all four. Adding or renaming a method requires updating both routes and the calculator.
- *Backup file sprawl.* The settings upload path writes `billsonline.db.backup_<timestamp>` next to the live DB on every restore ([app/routes/settings.py#L62-L65](app/routes/settings.py#L62-L65)). In Docker the live DB is at `/app/instance/billsonline.db` ([docker-compose.yml#L9](docker-compose.yml#L9)) but locally it sits in the repo root, which is why many `billsonline.db.backup_*` files are committed/visible there. Do not commit new backups.
- *Schema-patch-on-upload is incomplete.* Only the `notes` column is patched; future migrations must extend [app/routes/settings.py#L74-L93](app/routes/settings.py#L74-L93) or restore will silently leave the DB stale.
- *`db.create_all()` masks missing migrations.* A new table will appear in dev without an Alembic revision, then break in any deployment that ships migrations only. Always generate a migration for new tables/columns.
- *Legacy columns must keep working.* Removing `electricity_amount`/`water_amount`/`internet_amount` would break the legacy-synthesis paths in [app/services/month_service.py#L196-L218](app/services/month_service.py#L196-L218) and [app/services/month_service.py#L242-L286](app/services/month_service.py#L242-L286).
- *Pydantic + SQLAlchemy.* `DynamicContribution` holds raw SQLAlchemy `Participant` objects via `arbitrary_types_allowed=True`. Do not call `.model_dump()` expecting clean JSON — serialise explicitly.
- *Component splits ≠ legacy distribution code paths.* The new dynamic-component code path and the legacy `_synthesize_legacy_components` path diverge in subtle ways (the synthetic components get hard-coded IDs 1/2/3 — [app/services/month_service.py#L201-L218](app/services/month_service.py#L201-L218)); do not rely on IDs from synthesised components.
- *Currency formatting.* Error strings hard-code `₱`. If you internationalise, search the codebase for that glyph before changing anything.

## 4. How to add functionality (engineering playbook)

### The change loop

1. Read the relevant feature file under [tests/features/](tests/features) to understand the expected behaviour in Gherkin.
2. Read the matching repository, service, and route. Trace one request from blueprint → service → repository → model.
3. If you are changing data: write an Alembic migration (`flask --app wsgi:app db migrate -m "..."` then edit). Do **not** rely on `db.create_all()`.
4. Implement the change in the smallest layer that owns the concern (model → repository → service → route; never skip a layer upward).
5. Add or extend a feature file + step definition under [tests/features/](tests/features) and [tests/bdd/](tests/bdd). Add a UI scenario in [tests/ui/](tests/ui) only if the change is visible in a page flow.
6. Run `pytest --cov=app --cov-fail-under=80 tests/` locally.
7. Update [README.md](README.md) and this `handoff.md` in the same commit if a documented behaviour changes.

### Layering rules

| Layer | May depend on | May NOT depend on |
| --- | --- | --- |
| [app/models.py](app/models.py) | `app/extensions.py` only | repositories, services, routes, Flask request context |
| [app/repositories.py](app/repositories.py) | models, `db` | services, routes, `request`, templates |
| [app/services/](app/services) | repositories, models, calculator | `request`, `flash`, `url_for`, templates |
| [app/routes/](app/routes) | services, repositories (read-only), forms, templates | direct `db.session.query(...)` for writes |
| [app/forms.py](app/forms.py) | repositories (for cross-field validation) | services, routes |

`BillCalculator` is intentionally pure: it must not import Flask, `db`, or any repository.

### DRY rules — canonical locations

| Concept | Single source of truth |
| --- | --- |
| Schema | [app/models.py](app/models.py) (plus Alembic in [migrations/versions/](migrations/versions)) |
| DB queries | [app/repositories.py](app/repositories.py) |
| Bill math | [app/services/bill_calculator.py](app/services/bill_calculator.py) |
| Month orchestration | [app/services/month_service.py](app/services/month_service.py) |
| Adjustment validation | [app/services/adjustment_service.py](app/services/adjustment_service.py) |
| Blueprint registration | [app/routes/registration.py](app/routes/registration.py) |
| Config / env | [app/config.py](app/config.py) |
| App version string | [VERSION](VERSION), read through [app/version.py](app/version.py) |
| Flask extensions | [app/extensions.py](app/extensions.py) |

Do not introduce a second copy of any of these. In particular, do not query `Participant.query` or `db.session` outside repositories (the only sanctioned exception is `db.session.rollback()` after a caught `IntegrityError` in a route).

### Extension points

- **New blueprint.** Create `app/routes/<area>.py` with `bp = Blueprint("<area>", __name__, url_prefix="/<area>")`, then add `app.register_blueprint(<area>_bp)` to [app/routes/registration.py](app/routes/registration.py).
- **New repository.** Add a class to [app/repositories.py](app/repositories.py); inject it as an optional ctor arg into services that need it.
- **New service.** Add `app/services/<name>.py`, export from [app/services/__init__.py](app/services/__init__.py), use constructor injection mirroring `MonthService`.
- **New split method.** Extend the dispatch in [app/services/bill_calculator.py#L60-L96](app/services/bill_calculator.py#L60-L96), allow it in `request.form` validation in [app/routes/months.py#L161](app/routes/months.py#L161) and [app/routes/components.py#L62](app/routes/components.py#L62), and add a scenario to [tests/features/calculator.feature](tests/features/calculator.feature).
- **New migration.** `flask --app wsgi:app db migrate -m "msg" && flask --app wsgi:app db upgrade`. If the migration adds a column relevant to backup-restore, also extend the ad-hoc patch block in [app/routes/settings.py#L74-L93](app/routes/settings.py#L74-L93).

### Avoiding over-engineering

- No new dependencies without a concrete need; the stack above is the whole list.
- Do not introduce DTOs, mappers, async, dataclasses for inputs, or a third "rich domain" layer. Repositories return models; services return primitives or `DynamicContribution`.
- Do not add docstrings, type hints, or comments to code you are not modifying.
- Do not refactor route modules into class-based views or rewrite the synchronous flow as async.
- Validate at boundaries: WTForms in [app/forms.py](app/forms.py) for HTML forms, and `adjustment_service.validate_redistribution_rule` for adjustment payloads. Trust validated values inside services.

### Tests — what to add, where

All tests live under [tests/](tests) and use `pytest` + `pytest-bdd`. Logic feature files are auto-discovered from `bdd_features_base_dir = tests/features` ([pytest.ini#L9](pytest.ini#L9)). Step modules are named `test_bdd_<feature>.py` for logic and `test_<area>_steps.py` for UI.

| Kind of change | Feature file | Step module | Style |
| --- | --- | --- | --- |
| Calculator math | [tests/features/calculator.feature](tests/features/calculator.feature) | [tests/bdd/test_bdd_calculator.py](tests/bdd/test_bdd_calculator.py) | Unit, uses mock dataclasses from [tests/bdd/conftest.py](tests/bdd/conftest.py) |
| Model / relationship | [tests/features/models.feature](tests/features/models.feature) | [tests/bdd/test_bdd_models.py](tests/bdd/test_bdd_models.py) | Unit against real models |
| Repository CRUD | [tests/features/repositories.feature](tests/features/repositories.feature) | [tests/bdd/test_bdd_repositories.py](tests/bdd/test_bdd_repositories.py) | Integration with SQLite |
| Service business logic | `month_service.feature` / `adjustment_service.feature` | matching `test_bdd_*` | Integration |
| Route behaviour | `routes.feature` / `routes_complex.feature` / `extended_routes.feature` | matching `test_bdd_*` | Flask test client |
| Form validation | [tests/features/forms.feature](tests/features/forms.feature) | [tests/bdd/test_bdd_forms.py](tests/bdd/test_bdd_forms.py) | Unit |
| Reports endpoint | [tests/features/reports.feature](tests/features/reports.feature) | [tests/bdd/test_bdd_reports.py](tests/bdd/test_bdd_reports.py) | Integration |
| Page flow (browser) | [tests/ui/features/](tests/ui/features) | [tests/ui/steps/](tests/ui/steps) | Playwright, default chromium headless |

Markers (declared in [pytest.ini#L13-L23](pytest.ini#L13-L23)): `bdd`, `ui`, `slow`, `integration`, plus per-area UI markers (`components`, `readings`, `months`, `navigation`, `participants`, `settings`).

### Documentation

Update in the same commit as a behaviour change:

- This file (`handoff.md`).
- [README.md](README.md) — feature list, env vars, test counts/sections if they shift materially.
- [VERSION](VERSION) — bump per the semver-ish convention already in use.

Do not create new top-level markdown files. There are no ADRs, OpenAPI specs, or changelogs to update.

### Applicable checklists

- **Security / secret handling.** Never commit a real `SECRET_KEY`; never commit a real `billsonline.db` (the upload path will overwrite it locally). CSRF tokens must be present on every POST form.
- **Backward compatibility.** Preserve the legacy `electricity_amount`/`water_amount`/`internet_amount` columns and the synthesis fallback in `MonthService`.
- **Database migrations.** Always pair schema changes with an Alembic revision in [migrations/versions/](migrations/versions); update the upload-time SQL patch in [app/routes/settings.py#L74-L93](app/routes/settings.py#L74-L93) if the column is needed for restore to work.

Not applicable to this project: i18n, accessibility audits beyond plain HTML, API versioning (no public API contract), telemetry/PII, performance budgets.

### Pre-merge checklist

- [ ] `pytest --cov=app --cov-report=term-missing --cov-fail-under=80 tests/` passes (matches CI in [.github/workflows/docker-build.yml#L43-L45](.github/workflows/docker-build.yml#L43-L45)).
- [ ] `pytest tests/ui/ -v` passes (Playwright chromium installed: `playwright install --with-deps chromium`).
- [ ] If schema changed: new file in [migrations/versions/](migrations/versions); upgrade + downgrade both implemented.
- [ ] If a `component_adjustments` column was added: corresponding `ALTER TABLE` added to [app/routes/settings.py#L74-L93](app/routes/settings.py#L74-L93).
- [ ] If a split method was added: validated in both [app/routes/months.py#L161](app/routes/months.py#L161) and [app/routes/components.py#L62](app/routes/components.py#L62).
- [ ] No new top-level dependency unless justified in the PR description.
- [ ] [README.md](README.md) and `handoff.md` reflect any user-visible behaviour change.
- [ ] [VERSION](VERSION) bumped if shipping a release.
- [ ] No new `billsonline.db*` or `.coverage` files staged.

## Quick orientation checklist for a new agent

1. Read [README.md](README.md) for product context and run commands.
2. Read [app/factory.py](app/factory.py) and [app/routes/registration.py](app/routes/registration.py) to see how the app boots and what routes exist.
3. Read [app/models.py](app/models.py) — the entire domain fits on one screen.
4. Read [app/repositories.py](app/repositories.py) and [app/services/bill_calculator.py](app/services/bill_calculator.py) to understand data access and the core math.
5. Skim [app/services/month_service.py](app/services/month_service.py) and [app/services/adjustment_service.py](app/services/adjustment_service.py) to see orchestration.
6. Pick a feature file in [tests/features/](tests/features) and its `test_bdd_*` counterpart in [tests/bdd/](tests/bdd) to learn the testing idiom.
7. Confirm the baseline:

   ```bash
   pyenv install 3.12 --skip-existing && pyenv virtualenv 3.12 billsonline-env
   pyenv version  # billsonline-env auto-activates via the committed .python-version
   python -m pip install -r requirements.txt -r requirements-dev.txt
   playwright install --with-deps chromium
   flask --app wsgi:app db upgrade
   pytest --cov=app --cov-report=term-missing --cov-fail-under=80 tests/
   flask --app wsgi:app run --debug --port 5000
   ```
