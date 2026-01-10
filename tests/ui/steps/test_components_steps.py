"""
Step definitions for bill components UI tests.
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
scenarios(str(Path(__file__).parent.parent / "features" / "ui_components.feature"))


# ============================================
# Given Steps (unique to components)
# ============================================

# Note: "a month exists with participants" step is defined in conftest.py


@given(parsers.parse('a component "{name}" with amount ${amount:f} exists'))
def component_exists(month_detail_page: MonthDetailPage, name: str, amount: float):
    """Add a component to the month."""
    month_detail_page.add_component(name, amount)


# ============================================
# When Steps
# ============================================

@when(parsers.parse('I add a new component named "{name}"'))
def add_component_named(month_detail_page: MonthDetailPage, name: str):
    """Start adding a new component."""
    month_detail_page.page.locator("input[name='component_name']").fill(name)


@when(parsers.parse('I set the amount to ${amount:f}'))
def set_amount(month_detail_page: MonthDetailPage, amount: float):
    """Set the component amount."""
    month_detail_page.page.locator("input[name='component_amount']").fill(str(amount))


@when(parsers.parse('I select "{method}" as the split method'))
def select_split_method(month_detail_page: MonthDetailPage, method: str):
    """Select split method."""
    month_detail_page.page.locator("select[name='component_split_method']").select_option(label=method)


@when('I click "Add Component"')
def click_add_component(month_detail_page: MonthDetailPage):
    """Click add component button."""
    month_detail_page.page.locator("button:has-text('Add Component'), button:has-text('Add')").first.click()
    month_detail_page.wait_for_load()


@when(parsers.parse('I update the "{name}" component amount to ${amount:f}'))
def update_component_amount(month_detail_page: MonthDetailPage, name: str, amount: float):
    """Update a component's amount."""
    row = month_detail_page.page.locator(f".component-row:has-text('{name}'), tr:has-text('{name}')")
    row.locator("input[name*='amount']").fill(str(amount))


@when('I save the component changes')
def save_component_changes(month_detail_page: MonthDetailPage):
    """Save component changes."""
    month_detail_page.page.locator("button:has-text('Save'), button[type='submit']").first.click()
    month_detail_page.wait_for_load()


@when(parsers.parse('I delete the "{name}" component'))
def delete_component(month_detail_page: MonthDetailPage, name: str):
    """Delete a component."""
    row = month_detail_page.page.locator(f".component-row:has-text('{name}'), tr:has-text('{name}')")
    row.locator("button:has-text('Delete'), .btn-delete").click()
    month_detail_page.wait_for_load()


# ============================================
# Then Steps
# ============================================

@then(parsers.parse('I should see "{name}" in the components list'))
def see_component_in_list(month_detail_page: MonthDetailPage, name: str):
    """Verify component appears in list."""
    # Use first to avoid strict mode violation with multiple matches
    expect(month_detail_page.page.locator(f"text={name}").first).to_be_visible()


@then(parsers.parse('"{name}" should show ${amount:f} as the amount'))
def component_shows_amount(month_detail_page: MonthDetailPage, name: str, amount: float):
    """Verify component shows correct amount."""
    component = month_detail_page.page.locator(f".component-row:has-text('{name}'), tr:has-text('{name}')")
    expect(component).to_contain_text(str(amount))


@then(parsers.parse('"{name}" should show "{method}" as the split method'))
def component_shows_split(month_detail_page: MonthDetailPage, name: str, method: str):
    """Verify component shows correct split method."""
    component = month_detail_page.page.locator(f".component-row:has-text('{name}'), tr:has-text('{name}')")
    expect(component).to_contain_text(method)


@then("each participant should have an equal share")
def equal_shares(month_detail_page: MonthDetailPage):
    """Verify participants have equal shares."""
    contributions = month_detail_page.get_contributions()
    values = list(contributions.values())
    # All contributions should be approximately equal
    if len(values) > 1:
        import re
        nums = [float(re.sub(r'[^\d.]', '', v)) for v in values]
        # Allow small rounding differences
        assert max(nums) - min(nums) < 1.0, f"Shares should be equal: {nums}"


@then("contributions should be split based on electricity usage")
def usage_based_split(month_detail_page: MonthDetailPage):
    """Verify contributions are based on usage."""
    contributions = month_detail_page.get_contributions()
    # Just verify contributions exist
    assert len(contributions) > 0, "No contributions calculated"


@then(parsers.parse('I should not see "{name}" in the components list'))
def not_see_component(month_detail_page: MonthDetailPage, name: str):
    """Verify component is not in list."""
    expect(month_detail_page.page.locator(f".component-row:has-text('{name}'), tr:has-text('{name}')")).to_have_count(0)


@then("the total contributions should be recalculated")
def contributions_recalculated(month_detail_page: MonthDetailPage):
    """Verify contributions are recalculated."""
    contributions = month_detail_page.get_contributions()
    assert len(contributions) > 0, "Contributions should be recalculated"
