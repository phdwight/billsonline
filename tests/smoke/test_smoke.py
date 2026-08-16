"""
Playwright smoke tests against a real local deployment.

Two layers:
1. A sweep of every top-level page — loads, screenshots, and error-checks each.
2. A minimal end-to-end flow (add participant -> create month -> view detail)
   exercising real form posts with CSRF enabled, screenshotting the populated
   month detail page.

Run via: bash scripts/smoke.sh   (builds billsonline:local, deploys, runs this)
"""
import re

import pytest
from playwright.sync_api import Page

from .conftest import ErrorMonitor, assert_page_healthy, snap

PAGES = [
    ("home", "/"),
    ("admin", "/admin"),
    ("new-month", "/months/new"),
    ("archived", "/months/archived"),
    ("participants", "/participants"),
    ("reports", "/reports"),
    ("settings", "/settings"),
]


@pytest.mark.smoke
@pytest.mark.parametrize("name,path", PAGES, ids=[p[0] for p in PAGES])
def test_page_renders_without_errors(page: Page, monitor: ErrorMonitor, base_url: str, name: str, path: str):
    response = page.goto(f"{base_url}{path}", wait_until="networkidle")
    assert response is not None and response.ok, f"{path} returned {response and response.status}"
    snap(page, name)
    assert_page_healthy(page, monitor, name)


@pytest.mark.smoke
def test_month_creation_flow(page: Page, monitor: ErrorMonitor, base_url: str):
    # Add a participant through the real admin form (CSRF token included).
    page.goto(f"{base_url}/admin", wait_until="networkidle")
    form = page.locator(".card-header:has-text('Participants') + form")
    form.locator("input[name='name']").fill("Smoke Tester")
    form.locator("button[type='submit']").click()
    page.wait_for_load_state("networkidle")
    assert_page_healthy(page, monitor, "admin after add-participant")

    # Create a month; all participants are selected by default, but year and
    # the legacy amounts are required with no defaults.
    page.goto(f"{base_url}/months/new", wait_until="networkidle")
    page.locator("input[name='year']").fill("2026")
    page.locator("select[name='month']").select_option("1")
    page.locator("input[name='electricity_amount']").fill("1000")
    page.locator("input[name='water_amount']").fill("300")
    page.locator("input[name='internet_amount']").fill("500")
    page.locator("button:has-text('Create Month')").click()
    page.wait_for_load_state("networkidle")

    # Success redirects to the billing-periods home with a "Month created"
    # flash and a card linking to the new month.
    assert "Month created" in page.locator("body").inner_text(), (
        f"month creation did not confirm (url: {page.url})"
    )
    page.locator("a.month-card").first.click()
    page.wait_for_load_state("networkidle")
    assert re.search(r"/months/\d+", page.url), f"expected month detail page, got {page.url}"
    snap(page, "month-detail")
    assert_page_healthy(page, monitor, "month detail")

    # Archive the month and confirm home renders it as a greyed-out card.
    page.locator("form[action$='/archive'] button:has-text('Archive')").click()
    page.wait_for_load_state("networkidle")
    page.goto(f"{base_url}/", wait_until="networkidle")
    assert page.locator("a.month-card.is-archived").count() == 1, (
        "archived month should render with the is-archived card style"
    )
    snap(page, "home-archived")
    assert_page_healthy(page, monitor, "home with archived month")
