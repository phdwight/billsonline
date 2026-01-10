"""
Step definitions for participant management UI tests.
"""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import expect

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from conftest import HomePage, ParticipantsPage

# Load scenarios from feature file
scenarios(str(Path(__file__).parent.parent / "features" / "ui_participants.feature"))


# ============================================
# Given Steps (unique to participants)
# ============================================

@given("I am on the participants page")
def on_participants_page(participants_page: ParticipantsPage):
    """Navigate to the participants page."""
    participants_page.goto("/participants")
    participants_page.wait_for_load()


@given("there are no participants")
def no_participants(home_page: HomePage):
    """Verify there are no participants."""
    home_page.goto("/")
    home_page.wait_for_load()
    count = home_page.get_participant_count()
    assert count == 0, f"Expected 0 participants, got {count}"


@given("the following participants exist:")
def participants_exist(home_page: HomePage, datatable):
    """Add multiple participants from a data table."""
    home_page.goto("/")
    home_page.wait_for_load()
    for row in datatable:
        name = row.get("name") or row[0]
        home_page.add_participant(name)


# ============================================
# When Steps
# ============================================

@when(parsers.parse('I enter "{name}" in the participant name field'))
def enter_participant_name(home_page: HomePage, name: str):
    """Enter a name in the participant input field."""
    home_page.participant_input.fill(name)


@when('I click the "Add" button')
def click_add_button(home_page: HomePage):
    """Click the add participant button."""
    home_page.add_participant_btn.click()
    home_page.wait_for_load()


@when(parsers.parse('I add a participant named "{name}"'))
def add_participant(home_page: HomePage, name: str):
    """Add a participant by name."""
    home_page.add_participant(name)


@when("I click the Manage link next to Participants")
def click_manage_link(home_page: HomePage):
    """Click the manage participants link."""
    home_page.click_manage_participants()


@when(parsers.parse('I update "{old_name}" to "{new_name}"'))
def update_participant_name(participants_page: ParticipantsPage, old_name: str, new_name: str):
    """Update a participant's name."""
    participants_page.update_participant(old_name, new_name)


# ============================================
# Then Steps
# ============================================

@then(parsers.parse('I should see "{name}" in the participant list'))
def see_participant_in_list(home_page: HomePage, name: str):
    """Verify participant appears in the list (works on both home and participants page)."""
    # Try home page format first
    participants = home_page.get_participants()
    if participants:
        assert any(name in p for p in participants), f"'{name}' not found in participants: {participants}"
    else:
        # Try participants management page format (input values)
        inputs = home_page.page.locator("input[name='name']").all()
        values = [inp.input_value() for inp in inputs]
        assert any(name in v for v in values), f"'{name}' not found in participant inputs: {values}"


@then(parsers.parse("I should see {count:d} participants"))
def see_participant_count(home_page: HomePage, count: int):
    """Verify the number of participants."""
    actual = home_page.get_participant_count()
    assert actual == count, f"Expected {count} participants, got {actual}"

import re

@then("the participant list should be empty")
def participant_list_empty(home_page: HomePage):
    """Verify participant list is empty."""
    count = home_page.get_participant_count()
    assert count == 0, f"Expected empty list, got {count} participants"


@then("I should be on the participants management page")
def on_participants_management_page(home_page: HomePage):
    """Verify we're on the participants page."""
    expect(home_page.page).to_have_url(re.compile(r".*/participants"))


@then(parsers.parse('I should not see "{name}" in the participant list'))
def not_see_participant(home_page: HomePage, name: str):
    """Verify participant does not appear in the list."""
    participants = home_page.get_participants()
    assert all(name not in p for p in participants), f"'{name}' was found in participants: {participants}"


@then("each participant should have an avatar icon")
def participants_have_avatars(home_page: HomePage):
    """Verify all participants have avatar icons."""
    avatars = home_page.page.locator(".participant-avatar").all()
    participants = home_page.get_participant_count()
    assert len(avatars) == participants, f"Expected {participants} avatars, got {len(avatars)}"


@then(parsers.parse('I should see a success message containing "{text}"'))
def see_success_message(home_page: HomePage, text: str):
    """Verify a success flash message is shown."""
    messages = home_page.get_flash_messages()
    assert any(text.lower() in m.lower() for m in messages), f"'{text}' not found in messages: {messages}"
