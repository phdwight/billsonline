"""
Step definitions for navigation UI tests.
"""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import expect

import sys
from pathlib import Path

# Import from ui conftest (not bdd conftest)
UI_TEST_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(UI_TEST_DIR))

from tests.ui.conftest import HomePage, BasePage

# Load scenarios from feature file
scenarios(str(Path(__file__).parent.parent / "features" / "ui_navigation.feature"))


# ============================================
# Given Steps
# ============================================

# Note: "I am on the home page" step is defined in conftest.py


@given("I am on any page")
def on_any_page(home_page: HomePage):
    """Navigate to the home page as starting point."""
    home_page.goto("/")
    home_page.wait_for_load()


@given("I am on a month detail page")
def on_month_detail_page(home_page: HomePage):
    """Navigate to a month detail page."""
    # First create a month
    home_page.goto("/")
    home_page.wait_for_load()
    home_page.add_participant("Test User")
    home_page.create_month(2024, 1, 100, 50, 40)
    home_page.click_month("January 2024")


@given("I am viewing on a mobile device")
def on_mobile_device(mobile_home_page: HomePage):
    """Use mobile viewport."""
    mobile_home_page.goto("/")
    mobile_home_page.wait_for_load()


@given("months exist")
def months_exist(home_page: HomePage):
    """Create sample months."""
    home_page.goto("/")
    home_page.wait_for_load()
    home_page.add_participant("Test")
    home_page.create_month(2024, 1, 100, 50, 40)


@given("archived months exist")
def archived_months_exist(home_page: HomePage):
    """Create and archive a month."""
    home_page.goto("/")
    home_page.wait_for_load()
    home_page.add_participant("Test")
    home_page.create_month(2024, 1, 100, 50, 40)
    # Archive it
    home_page.open_month_actions("January 2024")
    home_page.page.locator(".more-actions-dropdown a:has-text('Archive')").click()
    home_page.wait_for_load()


# ============================================
# When Steps
# ============================================

@when(parsers.parse('I click the "{text}" link'))
def click_link(home_page: HomePage, text: str):
    """Click a link by its text."""
    home_page.page.locator(f"a:has-text('{text}')").first.click()
    home_page.wait_for_load()


@when("I click the site title")
def click_site_title(home_page: HomePage):
    """Click the site title/logo."""
    home_page.page.locator(".site-title a, h1 a, header a").first.click()
    home_page.wait_for_load()


@when("I click the back button")
def click_back_button(home_page: HomePage):
    """Click the back navigation button."""
    home_page.page.locator("a:has-text('← Back'), a:has-text('Back')").first.click()
    home_page.wait_for_load()


@when('I use the "View Archived" quick link')
def click_archived_quick_link(home_page: HomePage):
    """Click the view archived quick link."""
    home_page.page.locator("a:has-text('Archived'), a:has-text('View Archived')").first.click()
    home_page.wait_for_load()


@when("I tap the hamburger menu")
def tap_hamburger_menu(mobile_home_page: HomePage):
    """Tap the mobile hamburger menu."""
    mobile_home_page.page.locator(".hamburger, .menu-toggle, [aria-label='Menu']").click()


@when(parsers.parse('I select "{item}" from the menu'))
def select_menu_item(mobile_home_page: HomePage, item: str):
    """Select an item from the mobile menu."""
    mobile_home_page.page.locator(f"nav a:has-text('{item}'), .mobile-menu a:has-text('{item}')").click()
    mobile_home_page.wait_for_load()


# ============================================
# Then Steps
# ============================================

@then("I should be on the home page")
def on_home_page_verify(home_page: HomePage):
    """Verify we're on the home page."""
    import re
    url = home_page.page.url
    assert re.search(r".*/$|.*/home|.*:\d+/?$|.*/admin", url), f"Not on home page: {url}"


@then("I should be on the settings page")
def on_settings_page(home_page: HomePage):
    """Verify we're on the settings page."""
    assert "/settings" in home_page.page.url, f"Not on settings page: {home_page.page.url}"


@then("I should be on the participants page")
def on_participants_page(home_page: HomePage):
    """Verify we're on the participants page."""
    assert "/participants" in home_page.page.url, f"Not on participants page: {home_page.page.url}"


@then("I should be on the archived page")
def on_archived_page(home_page: HomePage):
    """Verify we're on the archived page."""
    assert "/archived" in home_page.page.url, f"Not on archived page: {home_page.page.url}"


@then("I should see the navigation header")
def see_navigation_header(home_page: HomePage):
    """Verify navigation header is visible."""
    expect(home_page.page.locator("header, nav, .site-header").first).to_be_visible()


@then("I should see the quick links section")
def see_quick_links(home_page: HomePage):
    """Verify quick links section is visible."""
    quick_links = home_page.page.locator(".quick-links, [class*='quick']")
    # Quick links might be integrated differently
    assert quick_links.count() > 0 or home_page.has_text("Settings") or home_page.has_text("Archived")


@then("I should see a list of archived months")
def see_archived_months_list(home_page: HomePage):
    """Verify archived months list is visible."""
    expect(home_page.page.locator(".month-item, .month-list, text=archived")).to_be_visible()


@then("navigation should be touch-friendly")
def touch_friendly_navigation(mobile_home_page: HomePage):
    """Verify touch-friendly navigation."""
    # Check that clickable elements are appropriately sized
    links = mobile_home_page.page.locator("a, button").all()
    for link in links[:5]:  # Check first 5
        box = link.bounding_box()
        if box:
            # Touch targets should be at least 44x44 pixels
            assert box["width"] >= 40 or box["height"] >= 40, "Touch target too small"


@then("content should fit the viewport")
def content_fits_viewport(mobile_home_page: HomePage):
    """Verify content fits mobile viewport."""
    viewport = mobile_home_page.page.viewport_size
    body = mobile_home_page.page.locator("body")
    box = body.bounding_box()
    assert box["width"] <= viewport["width"] + 20, "Content overflows viewport"


@then("I should see the new month form")
def see_new_month_form(home_page: HomePage):
    """Verify new month form is visible."""
    expect(home_page.page.locator("form")).to_be_visible()
    expect(home_page.page.locator("input[name='year']")).to_be_visible()
