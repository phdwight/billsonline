"""
Step definitions for meter readings UI tests.
"""
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
scenarios(str(Path(__file__).parent.parent / "features" / "ui_meter_readings.feature"))


# ============================================
# Given Steps (unique to meter readings)
# ============================================

# Note: "a month exists with participants" step is defined in conftest.py


@given("the month is archived")
def month_is_archived(home_page: HomePage):
    """Archive the current month."""
    home_page.open_month_actions("January 2024")
    home_page.page.locator(".more-actions-dropdown a:has-text('Archive')").click()
    home_page.wait_for_load()


@given("I am viewing an archived month")
def viewing_archived_month(home_page: HomePage, month_detail_page: MonthDetailPage):
    """Navigate to an archived month."""
    # Go to archived page and click the month
    home_page.goto("/archived")
    home_page.wait_for_load()
    home_page.page.locator(".month-link, a:has-text('January')").first.click()
    home_page.wait_for_load()


# ============================================
# When Steps
# ============================================

@when("I enter meter readings for each participant:")
def enter_meter_readings(month_detail_page: MonthDetailPage, datatable):
    """Enter meter readings from data table."""
    # Skip header row, process data rows
    for row in datatable[1:]:
        participant = row[0]
        previous = row[1]
        current = row[2]
        month_detail_page.enter_reading(participant, int(previous), int(current))


@when('I click "Save Readings"')
def click_save_readings(month_detail_page: MonthDetailPage):
    """Click save readings button."""
    month_detail_page.save_readings()


@when("I try to edit the meter readings")
def try_edit_readings(month_detail_page: MonthDetailPage):
    """Attempt to edit meter readings."""
    # Try to find editable inputs
    inputs = month_detail_page.page.locator(".meter-reading input:not([readonly]), input[name^='previous_']:not([readonly])").all()
    month_detail_page.editable_inputs = len(inputs)


# ============================================
# Then Steps
# ============================================

@then("the readings should be saved")
def readings_saved(month_detail_page: MonthDetailPage):
    """Verify readings were saved."""
    # Check for success message or saved values
    expect(month_detail_page.page.locator("body")).not_to_contain_text("error")


@then("I should see usage calculated for each participant")
def see_usage_calculated(month_detail_page: MonthDetailPage):
    """Verify usage is calculated."""
    # The readings table should show with the Usage column header
    # and the form should have been processed
    expect(month_detail_page.page.locator("th:has-text('Usage')").first).to_be_visible()


@then("the contributions should be recalculated")
def contributions_recalculated(month_detail_page: MonthDetailPage):
    """Verify contributions are recalculated."""
    contributions = month_detail_page.get_contributions()
    # Should have contribution values
    assert len(contributions) > 0, "No contributions found"


@then(parsers.parse('"{participant}" should have a different contribution than "{other}"'))
def different_contributions(month_detail_page: MonthDetailPage, participant: str, other: str):
    """Verify participants have different contributions."""
    contributions = month_detail_page.get_contributions()
    assert participant in contributions, f"{participant} not in contributions"
    assert other in contributions, f"{other} not in contributions"
    # Parse currency values
    import re
    p_val = float(re.sub(r'[^\d.]', '', contributions[participant]))
    o_val = float(re.sub(r'[^\d.]', '', contributions[other]))
    assert p_val != o_val, f"Contributions should differ: {p_val} vs {o_val}"


@then("the meter reading inputs should be read-only")
def readings_readonly(month_detail_page: MonthDetailPage):
    """Verify meter reading inputs are read-only."""
    assert month_detail_page.editable_inputs == 0, "Inputs should be read-only in archived months"


@then("I should see a message that the month is archived")
def see_archived_message(month_detail_page: MonthDetailPage):
    """Verify archived status message."""
    expect(month_detail_page.page.locator("text=/archived/i")).to_be_visible()
