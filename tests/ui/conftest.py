"""
Playwright + pytest-bdd UI test configuration and fixtures.

This module provides:
- Playwright browser fixtures
- Flask test server management
- Database cleanup between tests
- Common page objects and utilities
"""
import os
import sys
import time
import threading
import tempfile
import shutil
from pathlib import Path
from typing import Generator
from contextlib import contextmanager

import pytest
from playwright.sync_api import Page, Browser, BrowserContext, Playwright, sync_playwright

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================
# Test Server Configuration
# ============================================

TEST_HOST = "127.0.0.1"
TEST_PORT = 5099  # Use non-standard port to avoid conflicts


def create_test_app():
    """Create a Flask app instance for testing."""
    from app.factory import create_app
    
    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_ui.db")
    
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SECRET_KEY": "test-secret-key",
    })
    
    # Create tables
    with app.app_context():
        from app.extensions import db
        db.create_all()
    
    return app, temp_dir


class TestServer:
    """Manages a Flask test server in a background thread."""
    
    def __init__(self):
        self.app = None
        self.temp_dir = None
        self.server_thread = None
        self.is_running = False
    
    def start(self):
        """Start the test server."""
        if self.is_running:
            return
        
        self.app, self.temp_dir = create_test_app()
        
        def run_server():
            self.app.run(host=TEST_HOST, port=TEST_PORT, use_reloader=False, threaded=True)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.is_running = True
        
        # Wait for server to be ready
        time.sleep(1)
    
    def stop(self):
        """Stop the test server and cleanup."""
        self.is_running = False
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def reset_database(self):
        """Reset the database to a clean state."""
        with self.app.app_context():
            from app.extensions import db
            db.drop_all()
            db.create_all()
    
    @property
    def base_url(self) -> str:
        return f"http://{TEST_HOST}:{TEST_PORT}"


# Global test server instance
_test_server = None


def get_test_server() -> TestServer:
    """Get or create the test server singleton."""
    global _test_server
    if _test_server is None:
        _test_server = TestServer()
        _test_server.start()
    return _test_server


# ============================================
# Pytest Fixtures
# ============================================

@pytest.fixture(scope="session")
def test_server() -> Generator[TestServer, None, None]:
    """Session-scoped test server fixture."""
    server = get_test_server()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def playwright_instance() -> Generator[Playwright, None, None]:
    """Session-scoped Playwright instance."""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright, request) -> Generator[Browser, None, None]:
    """Session-scoped browser instance.
    
    Respects pytest-playwright CLI options:
      --headed     : Run browser in headed mode (visible window)
      --slowmo=N   : Slow down operations by N milliseconds
    """
    # Get CLI options (default to headless=True, slowmo=0)
    headed = request.config.getoption("--headed", default=False)
    slowmo = request.config.getoption("--slowmo", default=0)
    
    browser = playwright_instance.chromium.launch(
        headless=not headed,
        slow_mo=slowmo,
    )
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Function-scoped browser context for test isolation."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def mobile_context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Function-scoped mobile browser context."""
    context = browser.new_context(
        viewport={"width": 430, "height": 932},  # iPhone 14 Pro Max
        locale="en-US",
        is_mobile=True,
        has_touch=True,
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext, test_server: TestServer) -> Generator[Page, None, None]:
    """Function-scoped page with test server reset."""
    test_server.reset_database()
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="function")
def mobile_page(mobile_context: BrowserContext, test_server: TestServer) -> Generator[Page, None, None]:
    """Function-scoped mobile page with test server reset."""
    test_server.reset_database()
    page = mobile_context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session")
def app_base_url(test_server: TestServer) -> str:
    """Base URL for the test server."""
    return test_server.base_url


# ============================================
# Page Object Helpers
# ============================================

class BasePage:
    """Base page object with common functionality."""
    
    def __init__(self, page: Page, app_base_url: str):
        self.page = page
        self.base_url = app_base_url
    
    def goto(self, path: str = "/"):
        """Navigate to a path."""
        self.page.goto(f"{self.base_url}{path}")
    
    def wait_for_load(self):
        """Wait for page to fully load."""
        self.page.wait_for_load_state("networkidle")
    
    def get_flash_messages(self) -> list[str]:
        """Get all flash messages on the page."""
        messages = self.page.locator(".flashes li").all()
        return [m.text_content() for m in messages]
    
    def has_text(self, text: str) -> bool:
        """Check if text is visible on page."""
        return self.page.locator(f"text={text}").is_visible()


class HomePage(BasePage):
    """Page object for the home page."""
    
    def __init__(self, page: Page, base_url: str):
        super().__init__(page, base_url)
        self.participant_input = page.locator(".card-header:has-text('Participants') + form input[name='name']")
        self.add_participant_btn = page.locator(".card-header:has-text('Participants') + form button[type='submit']")
        self.participant_list = page.locator(".participant-list")
        self.month_list = page.locator(".month-list")
    
    def add_participant(self, name: str):
        """Add a participant via the UI."""
        self.participant_input.fill(name)
        self.add_participant_btn.click()
        self.wait_for_load()
    
    def get_participants(self) -> list[str]:
        """Get list of participant names."""
        items = self.page.locator(".participant-item").all()
        return [item.text_content().strip() for item in items]
    
    def get_participant_count(self) -> int:
        """Get number of participants."""
        return len(self.page.locator(".participant-item").all())
    
    def get_months(self) -> list[str]:
        """Get list of month names."""
        items = self.page.locator(".month-item .month-name").all()
        return [item.text_content().strip() for item in items]
    
    def create_month(self, year: int, month: int, electricity: float, water: float, internet: float):
        """Create a new month via the form."""
        self.page.locator("input[name='year']").fill(str(year))
        self.page.locator("select[name='month']").select_option(str(month))
        self.page.locator("input[name='electricity_amount']").fill(str(electricity))
        self.page.locator("input[name='water_amount']").fill(str(water))
        self.page.locator("input[name='internet_amount']").fill(str(internet))
        self.page.locator("button:has-text('Create Month')").click()
        self.wait_for_load()
    
    def click_month(self, month_name: str):
        """Click on a month to view details."""
        self.page.locator(f".month-link:has-text('{month_name}')").click()
        self.wait_for_load()
    
    def click_manage_participants(self):
        """Click the manage participants link."""
        self.page.locator("a:has-text('Manage')").first.click()
        self.wait_for_load()
    
    def open_month_actions(self, month_name: str):
        """Open the more actions dropdown for a month."""
        month_item = self.page.locator(f".month-item:has-text('{month_name}')")
        month_item.locator(".btn-more").click()


class MonthDetailPage(BasePage):
    """Page object for month detail page."""
    
    def enter_reading(self, participant: str, previous: int, current: int):
        """Enter meter reading for a participant."""
        row = self.page.locator(f"tr:has-text('{participant}')")
        row.locator("input[name^='previous_']").fill(str(previous))
        row.locator("input[name^='current_']").fill(str(current))
    
    def save_readings(self):
        """Save meter readings."""
        self.page.locator("button:has-text('Save Readings')").click()
        self.wait_for_load()
    
    def add_component(self, name: str, amount: float, split: str = "Equal"):
        """Add a new component."""
        self.page.locator("input[name='component_name']").fill(name)
        self.page.locator("input[name='component_amount']").fill(str(amount))
        self.page.locator("select[name='component_split_method']").select_option(label=split)
        self.page.locator("button:has-text('Add Component')").click()
        self.wait_for_load()
    
    def get_contributions(self) -> dict:
        """Get contribution data from the table."""
        contributions = {}
        rows = self.page.locator(".card:has-text('Contributions') tbody tr").all()
        for row in rows:
            cells = row.locator("td").all()
            if cells:
                name = cells[0].text_content().strip()
                total = cells[-1].text_content().strip()
                contributions[name] = total
        return contributions


class ParticipantsPage(BasePage):
    """Page object for participants management page."""
    
    def update_participant(self, old_name: str, new_name: str):
        """Update a participant's name."""
        # Find the row by looking for input with matching value
        row = self.page.locator(f".participant-edit-row:has(input[value='{old_name}'])")
        row.locator("input[name='name']").fill(new_name)
        # Use title attribute to specifically target the save button (not delete)
        row.locator("button[title='Save changes']").click()
        self.wait_for_load()


class SettingsPage(BasePage):
    """Page object for settings page."""
    
    def select_theme(self, theme: str):
        """Select a theme."""
        self.page.locator(f"input[value='{theme}']").click()


# ============================================
# Pytest-BDD Fixtures
# ============================================

@pytest.fixture
def home_page(page: Page, app_base_url: str) -> HomePage:
    """Home page object fixture."""
    return HomePage(page, app_base_url)


@pytest.fixture
def month_detail_page(page: Page, app_base_url: str) -> MonthDetailPage:
    """Month detail page object fixture."""
    return MonthDetailPage(page, app_base_url)


@pytest.fixture
def participants_page(page: Page, app_base_url: str) -> ParticipantsPage:
    """Participants page object fixture."""
    return ParticipantsPage(page, app_base_url)


@pytest.fixture
def settings_page(page: Page, app_base_url: str) -> SettingsPage:
    """Settings page object fixture."""
    return SettingsPage(page, app_base_url)


@pytest.fixture
def mobile_home_page(mobile_page: Page, app_base_url: str) -> HomePage:
    """Mobile home page object fixture."""
    return HomePage(mobile_page, app_base_url)


# ============================================
# Shared Step Definitions
# ============================================
from pytest_bdd import given, parsers


@given("I am on the home page")
def on_home_page(home_page: HomePage):
    """Navigate to the home page."""
    home_page.goto("/")
    home_page.wait_for_load()


@given(parsers.parse('a participant named "{name}" exists'))
def participant_named_exists(home_page: HomePage, name: str):
    """Create a participant if not already exists."""
    home_page.goto("/")
    home_page.wait_for_load()
    home_page.add_participant(name)


@given(parsers.parse('a monthly bill for "{month_year}" exists'))
def monthly_bill_for_exists(home_page: HomePage, month_year: str):
    """Create a monthly bill."""
    parts = month_year.split()
    month_name = parts[0]
    year = int(parts[1])
    
    months = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }
    month_num = months.get(month_name, 1)
    
    home_page.goto("/")
    home_page.wait_for_load()
    home_page.create_month(year, month_num, 100.0, 50.0, 40.0)


@given("I am viewing the month detail page")
def viewing_month_detail(home_page: HomePage, month_detail_page: MonthDetailPage):
    """Navigate to month detail page (assume we're already there from month creation)."""
    # After creating a month, we get redirected to it directly
    # Just verify we're on a month detail page
    current_url = home_page.page.url
    if "/months/" not in current_url:
        # Navigate to the first month
        home_page.goto("/")
        home_page.wait_for_load()
        home_page.page.locator(".month-link").first.click()
        home_page.wait_for_load()


@given("a month exists with participants")
def month_with_participants(home_page: HomePage):
    """Create a month with participants."""
    home_page.goto("/")
    home_page.wait_for_load()
    home_page.add_participant("Alice")
    home_page.add_participant("Bob")
    home_page.create_month(2024, 1, 100.00, 50.00, 40.00)
