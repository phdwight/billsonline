# UI Tests with Playwright and pytest-bdd

This directory contains end-to-end UI tests for the Bills Online application using:
- **Playwright** - Browser automation
- **pytest-bdd** - Behavior-Driven Development testing
- **Gherkin** - Feature file syntax

## Directory Structure

```
tests/ui/
├── conftest.py           # Playwright fixtures, test server, page objects
├── features/             # Gherkin feature files
│   ├── ui_participants.feature
│   ├── ui_months.feature
│   ├── ui_navigation.feature
│   ├── ui_meter_readings.feature
│   └── ui_components.feature
├── steps/                # Step definitions
│   ├── test_participants_steps.py
│   ├── test_months_steps.py
│   ├── test_navigation_steps.py
│   ├── test_meter_readings_steps.py
│   └── test_components_steps.py
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
# Or install all browsers:
playwright install
```

## Running Tests

### Run all UI tests

```bash
pytest tests/ui/ -v
```

### Run specific feature

```bash
pytest tests/ui/steps/test_participants_steps.py -v
```

### Run with visible browser (debugging)

```bash
pytest tests/ui/ -v --headed
```

### Run with slow motion (easier to follow)

```bash
pytest tests/ui/ -v --headed --slowmo 500
```

### Run specific scenario by keyword

```bash
pytest tests/ui/ -v -k "add participant"
```

## Test Architecture

### Page Objects

Located in `conftest.py`, these encapsulate page interactions:

- `BasePage` - Common methods (goto, wait, flash messages)
- `HomePage` - Home page interactions (add participants, create months)
- `MonthDetailPage` - Month detail page (readings, components)
- `ParticipantsPage` - Participant management
- `SettingsPage` - Settings page

### Fixtures

- `test_server` - Manages Flask test server
- `browser` - Session-scoped Chromium browser
- `context` / `mobile_context` - Browser contexts (desktop/mobile)
- `page` / `mobile_page` - Page instances with DB reset
- `home_page`, `month_detail_page`, etc. - Page object instances

### Test Server

The tests start a real Flask server on port 5099 with:
- Separate test database
- CSRF disabled
- Database reset between tests

## Writing New Tests

### 1. Add Feature File

Create `features/ui_new_feature.feature`:

```gherkin
Feature: New Feature
    As a user
    I want to do something
    So that I get value

    Scenario: Basic action
        Given I am on the home page
        When I perform some action
        Then I should see the expected result
```

### 2. Add Step Definitions

Create `steps/test_new_feature_steps.py`:

```python
from pytest_bdd import scenarios, given, when, then
from tests.ui.conftest import HomePage

scenarios("../features/ui_new_feature.feature")

@given("I am on the home page")
def on_home_page(home_page: HomePage):
    home_page.goto("/")
    home_page.wait_for_load()

@when("I perform some action")
def perform_action(home_page: HomePage):
    home_page.page.click("button")

@then("I should see the expected result")
def see_result(home_page: HomePage):
    assert home_page.has_text("Expected")
```

## Mobile Testing

Use `mobile_page` or `mobile_home_page` fixtures for mobile viewport testing:

```python
@given("I am viewing on a mobile device")
def on_mobile(mobile_home_page: HomePage):
    mobile_home_page.goto("/")
```

## Debugging Tips

1. **Run headed**: `pytest tests/ui/ --headed`
2. **Add breakpoints**: Use `page.pause()` to pause execution
3. **Screenshots**: `page.screenshot(path="debug.png")`
4. **Traces**: `pytest tests/ui/ --tracing on`

## CI/CD Integration

For CI environments, ensure browsers are installed:

```yaml
- name: Install Playwright
  run: |
    pip install playwright
    playwright install chromium --with-deps
```
