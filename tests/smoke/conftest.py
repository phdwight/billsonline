"""
Smoke test configuration.

These tests run against a REAL locally deployed instance (the billsonline:local
Docker container — see scripts/smoke.sh), not an in-process Flask test server.
CSRF stays enabled and the app runs exactly as it does in production.

The suite is skipped entirely unless SMOKE_BASE_URL is set, so a plain
`pytest` run is unaffected. Each visited page is screenshotted to
tests/smoke/screenshots/ so a human (or agent) can visually inspect what the
app actually renders.
"""
import os
import time
import urllib.request
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

BASE_URL = os.environ.get("SMOKE_BASE_URL", "").rstrip("/")
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"

pytestmark = pytest.mark.smoke


def pytest_collection_modifyitems(config, items):
    if BASE_URL:
        return
    skip = pytest.mark.skip(reason="SMOKE_BASE_URL not set — deploy locally first (scripts/smoke.sh)")
    for item in items:
        if item.path and "tests/smoke" in str(item.path):
            item.add_marker(skip)


@pytest.fixture(scope="session")
def base_url() -> str:
    # Fail fast with a clear message if the deployment isn't reachable.
    deadline = time.time() + 30
    last_err = None
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BASE_URL}/", timeout=4)
            return BASE_URL
        except Exception as exc:  # noqa: BLE001 - any failure means "not up yet"
            last_err = exc
            time.sleep(1)
    pytest.exit(f"Smoke target {BASE_URL} not reachable after 30s ({last_err}). "
                "Deploy the local container first: bash scripts/smoke.sh")


@pytest.fixture(scope="session")
def playwright_instance() -> Generator[Playwright, None, None]:
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright) -> Generator[Browser, None, None]:
    browser = playwright_instance.chromium.launch(headless=True)
    yield browser
    browser.close()


class ErrorMonitor:
    """Collects everything that smells like an error while browsing.

    - console.error messages
    - uncaught page exceptions (pageerror)
    - HTTP responses >= 500 (any request) and >= 400 for top-level documents
    """

    IGNORED_CONSOLE = ("favicon",)

    def __init__(self, page: Page):
        self.console_errors: list[str] = []
        self.page_errors: list[str] = []
        self.bad_responses: list[str] = []
        page.on("console", self._on_console)
        page.on("pageerror", lambda exc: self.page_errors.append(str(exc)))
        page.on("response", self._on_response)

    def _on_console(self, msg):
        if msg.type == "error" and not any(s in msg.text for s in self.IGNORED_CONSOLE):
            self.console_errors.append(msg.text)

    def _on_response(self, response):
        if response.status >= 500:
            self.bad_responses.append(f"{response.status} {response.url}")
        elif response.status >= 400 and response.request.resource_type == "document":
            self.bad_responses.append(f"{response.status} {response.url}")

    def assert_clean(self, where: str):
        problems = []
        if self.console_errors:
            problems.append(f"console errors: {self.console_errors}")
        if self.page_errors:
            problems.append(f"uncaught page errors: {self.page_errors}")
        if self.bad_responses:
            problems.append(f"failed requests: {self.bad_responses}")
        assert not problems, f"Errors while smoking {where}: " + "; ".join(problems)


@pytest.fixture
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="en-US")
    yield ctx
    ctx.close()


@pytest.fixture
def page(context: BrowserContext) -> Generator[Page, None, None]:
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture
def monitor(page: Page) -> ErrorMonitor:
    return ErrorMonitor(page)


@pytest.fixture(scope="session", autouse=True)
def screenshot_dir() -> Path:
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    return SCREENSHOT_DIR


def snap(page: Page, name: str) -> Path:
    """Full-page screenshot for visual inspection after the run."""
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return path


# Text that must never appear on a rendered page.
SERVER_ERROR_MARKERS = ("Internal Server Error", "Traceback (most recent call last)", "werkzeug.exceptions")


def assert_page_healthy(page: Page, monitor: ErrorMonitor, name: str):
    body = page.locator("body").inner_text()
    for marker in SERVER_ERROR_MARKERS:
        assert marker not in body, f"'{marker}' visible on {name} ({page.url})"
    monitor.assert_clean(name)
