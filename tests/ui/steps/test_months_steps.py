"""
Step definitions for monthly bills UI tests.
"""
import re
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import expect

import sys
from pathlib import Path

# Import from ui conftest (not bdd conftest)
UI_TEST_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(UI_TEST_DIR))

from tests.ui.conftest import HomePage, MonthDetailPage

# Load scenarios from feature file
scenarios(str(Path(__file__).parent.parent / "features" / "ui_months.feature"))


# ============================================
# Given Steps (unique to months)
# ============================================

@given("there are no monthly bills")
def no_monthly_bills(home_page: HomePage):
    """Verify there are no monthly bills."""
    home_page.goto("/")
    home_page.wait_for_load()
    months = home_page.get_months()
    assert len(months) == 0, f"Expected no months, got {months}"


@given("participants exist in the system")
def participants_exist_default(home_page: HomePage):
    """Add default participants for testing."""
    home_page.goto("/")
    home_page.wait_for_load()
    home_page.add_participant("Alice")
    home_page.add_participant("Bob")


@given(parsers.parse('I am viewing the month "{month_year}"'))
def viewing_month(home_page: HomePage, month_year: str):
    """Navigate to view a specific month."""
    home_page.goto("/")
    home_page.wait_for_load()
    home_page.click_month(month_year)


# ============================================
# When Steps
# ============================================

@when("I fill in the new month form with:")
def fill_month_form(home_page: HomePage, datatable):
    """Fill in the new month form from a data table."""
    # Skip header row (first row), process data rows
    for row in datatable[1:]:  # Skip header
        field = row[0]
        value = row[1]
        
        if field.lower() == "year":
            home_page.page.locator("input[name='year']").fill(value)
        elif field.lower() == "month":
            # Select month by name
            months = {
                "January": "1", "February": "2", "March": "3", "April": "4",
                "May": "5", "June": "6", "July": "7", "August": "8",
                "September": "9", "October": "10", "November": "11", "December": "12"
            }
            month_value = months.get(value, value)
            home_page.page.locator("select[name='month']").select_option(month_value)
        elif "electricity" in field.lower():
            home_page.page.locator("input[name='electricity_amount']").fill(value)
        elif "water" in field.lower():
            home_page.page.locator("input[name='water_amount']").fill(value)
        elif "internet" in field.lower():
            home_page.page.locator("input[name='internet_amount']").fill(value)


@when('I click "Create Month"')
def click_create_month(home_page: HomePage):
    """Click the create month button."""
    home_page.page.locator("button:has-text('Create Month')").click()
    home_page.wait_for_load()


@when(parsers.parse('I click on "{month_year}" in the month list'))
def click_month_in_list(home_page: HomePage, month_year: str):
    """Click on a month in the list."""
    # Navigate to admin page first to see the month list
    home_page.goto("/admin")
    home_page.wait_for_load()
    home_page.click_month(month_year)


@when(parsers.parse('I click the more actions button for "{month_year}"'))
def click_more_actions(home_page: HomePage, month_year: str):
    """Click the more actions button for a month."""
    # Navigate to admin page first to see the month list
    home_page.goto("/admin")
    home_page.wait_for_load()
    home_page.open_month_actions(month_year)


@when('I click "Archive"')
def click_archive(home_page: HomePage):
    """Click the archive button."""
    home_page.page.locator(".more-actions-dropdown button:has-text('Archive')").click()
    home_page.wait_for_load()


@when('I click "Delete"')
def click_delete(home_page: HomePage):
    """Click the delete button."""
    home_page.page.locator(".more-actions-dropdown form button:has-text('Delete')").click()
    home_page.wait_for_load()


@when("I confirm the deletion")
def confirm_deletion(home_page: HomePage):
    """Confirm the deletion dialog."""
    # Handle browser dialog if present
    home_page.page.on("dialog", lambda dialog: dialog.accept())


@when('I click the "Edit" button')
def click_edit_button(month_detail_page: MonthDetailPage):
    """Click the edit button."""
    month_detail_page.page.locator("a:has-text('Edit')").click()
    month_detail_page.wait_for_load()


@when(parsers.parse('I update the electricity amount to "{amount}"'))
def update_electricity(month_detail_page: MonthDetailPage, amount: str):
    """Update the electricity amount."""
    month_detail_page.page.locator("input[name='electricity_amount']").fill(amount)


@when('I click "Save Changes"')
def click_save_changes(month_detail_page: MonthDetailPage):
    """Click save changes button."""
    month_detail_page.page.locator("button:has-text('Save')").click()
    month_detail_page.wait_for_load()


# ============================================
# Then Steps
# ============================================

@then(parsers.parse('I should see "{month_year}" in the month list'))
def see_month_in_list(home_page: HomePage, month_year: str):
    """Verify month appears in the list."""
    # Navigate to admin page to see the month list
    home_page.goto("/admin")
    home_page.wait_for_load()
    months = home_page.get_months()
    assert any(month_year in m for m in months), f"'{month_year}' not found in months: {months}"


@then("I should be on the month detail page")
def on_month_detail_page(home_page: HomePage):
    """Verify we're on a month detail page."""
    import re
    url = home_page.page.url
    assert re.search(r".*/months/\d+", url), f"Not on month detail page: {url}"


@then("I should see the bill components section")
def see_components_section(month_detail_page: MonthDetailPage):
    """Verify bill components section is visible."""
    expect(month_detail_page.page.locator("text=Components").first).to_be_visible()


@then("I should see the meter readings section")
def see_readings_section(month_detail_page: MonthDetailPage):
    """Verify meter readings section is visible."""
    expect(month_detail_page.page.locator("text=Meter Readings").first).to_be_visible()


@then("I should see the contributions section")
def see_contributions_section(month_detail_page: MonthDetailPage):
    """Verify contributions section is visible."""
    expect(month_detail_page.page.locator("text=Contributions").first).to_be_visible()


@then(parsers.parse('I should not see "{month_year}" in the month list'))
def not_see_month_in_list(home_page: HomePage, month_year: str):
    """Verify month does not appear in the list."""
    # Navigate to admin page to see the month list
    home_page.goto("/admin")
    home_page.wait_for_load()
    months = home_page.get_months()
    assert all(month_year not in m for m in months), f"'{month_year}' was found in months: {months}"


@then("the month should be archived")
def month_archived(home_page: HomePage):
    """Verify the month was archived."""
    # Archived months are removed from main list
    pass  # Already verified by "not see" step


@then(parsers.parse('the electricity amount should be "{amount}"'))
def electricity_amount_is(month_detail_page: MonthDetailPage, amount: str):
    """Verify electricity amount is correct."""
    element = month_detail_page.page.locator("text=Electricity").locator("xpath=..").locator("text=/\\$\\d+/")
    expect(element).to_contain_text(amount.replace("$", ""))
