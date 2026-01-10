"""
Step definitions for settings UI tests.
"""
import os
import tempfile
import shutil
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from playwright.sync_api import expect, Dialog

import sys
from pathlib import Path

# Import from ui conftest (not bdd conftest)
UI_TEST_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(UI_TEST_DIR))

from tests.ui.conftest import HomePage, SettingsPage

# Load scenarios from feature file
scenarios(str(Path(__file__).parent.parent / "features" / "ui_settings.feature"))


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def temp_db_file(test_server):
    """Create a valid SQLite database file for testing restore."""
    # Copy the actual test database to use as restore file
    import sqlite3
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Create a valid SQLite database
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


# ============================================
# Given Steps
# ============================================

@given("I am on the settings page")
def on_settings_page(home_page: HomePage):
    """Navigate to the settings page."""
    home_page.goto("/settings/")
    home_page.wait_for_load()


# ============================================
# When Steps
# ============================================

@when("I select a database file and confirm restore")
def select_and_confirm_restore(home_page: HomePage, temp_db_file: str):
    """Select a .db file and confirm the restore dialog."""
    # Set up handler to auto-accept dialogs (both confirm and alert)
    def handle_dialog(dialog: Dialog):
        dialog.accept()
    
    home_page.page.on("dialog", handle_dialog)
    
    # Upload the temp file - this triggers the confirm dialog
    file_input = home_page.page.locator("#db-file-input")
    file_input.set_input_files(temp_db_file)
    
    # Wait for form submission and page reload
    home_page.page.wait_for_load_state("networkidle")
    home_page.wait_for_load()


# ============================================
# Then Steps
# ============================================

@then(parsers.parse('I should see the "{section}" section'))
def see_section(home_page: HomePage, section: str):
    """Verify a section is visible."""
    expect(home_page.page.locator(f"text={section}").first).to_be_visible()


@then(parsers.parse('I should see the "{button}" button'))
def see_button(home_page: HomePage, button: str):
    """Verify a button is visible."""
    expect(home_page.page.locator(f"text={button}").first).to_be_visible()


@then("I should see a success or error message")
def see_status_message(home_page: HomePage):
    """Verify a status message is displayed (success or error)."""
    # After restore, we should see either success or error message
    status_msg = home_page.page.locator(".status-success, .status-error")
    expect(status_msg).to_be_visible()
    
    # Verify it contains expected text
    text = status_msg.text_content()
    assert "success" in text.lower() or "error" in text.lower(), \
        f"Expected success or error message, got: {text}"
