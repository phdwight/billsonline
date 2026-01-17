Feature: HTTP Routes
  As a user
  I want to interact with the application through HTTP endpoints
  So that I can manage bills, participants, and components

  Background:
    Given the application is running

  # Index Route
  Scenario: Index redirects to admin when no bills exist
    Given no bills exist
    When I visit the home page
    Then I should be redirected to "/admin"

  Scenario: Index redirects to latest month when bills exist
    Given a bill exists for year 2025 month 6
    When I visit the home page
    Then I should be redirected to the month detail page

  # Admin Route
  Scenario: Admin page returns 200
    When I visit "/admin"
    Then the response status should be 200
    And the page should contain "Admin"

  Scenario: Admin page supports pagination
    Given bills exist for months 1 through 5 of 2025
    When I visit "/admin?page=1"
    Then the response status should be 200

  # Participant Routes
  Scenario: Participants page returns 200
    When I visit "/participants/"
    Then the response status should be 200

  Scenario: Add participant with valid name
    When I POST to "/participants/" with name "Alice"
    Then the response status should be 200
    And participant "Alice" should exist

  Scenario: Add participant with empty name fails
    When I POST to add participant with empty name
    Then the response status should be 200
    And the page should contain "required"

  Scenario: Add duplicate participant is prevented
    Given participant "Bob" exists
    When I POST to "/participants/" with name "bob"
    Then only 1 participant named "Bob" should exist

  Scenario: Update participant name
    Given participant "TestUser" exists
    When I POST to update participant with name "UpdatedName"
    Then the participant name should be "UpdatedName"

  Scenario: Update participant with empty name fails
    Given participant "TestUser" exists
    When I POST to update participant with empty name
    Then the page should contain "required"

  Scenario: Delete participant
    Given participant "TestUser" exists
    When I POST to delete the participant
    Then the participant should not exist

  # Month Routes
  Scenario: New month page returns 200
    When I visit "/months/new"
    Then the response status should be 200

  Scenario: Add month with valid data
    When I POST to "/months" with year 2025, month 6, amounts 100.0, 50.0, 30.0
    Then the response status should be 200
    And a bill for year 2025 month 6 should exist
    And the electricity amount should be 100.0

  Scenario: Add duplicate month is prevented
    Given a bill exists for year 2025 month 7
    When I POST to "/months" with year 2025, month 7, amounts 200.0, 100.0, 60.0
    Then only 1 bill for year 2025 month 7 should exist

  Scenario: View month detail
    Given a bill exists for year 2025 month 1
    When I visit the month detail page
    Then the response status should be 200

  Scenario: View nonexistent month shows error
    When I visit "/months/9999"
    Then the page should contain "not found"

  Scenario: Edit month page returns 200
    Given a bill exists for year 2025 month 1
    When I visit the month edit page
    Then the response status should be 200

  Scenario: Edit archived month shows error
    Given an archived bill exists for year 2025 month 1
    When I visit the month edit page
    Then the page should contain "archived"

  # Component Routes
  Scenario: Add component with valid data
    Given a bill exists for year 2025 month 1
    When I POST to add component "Gas" with amount 75.0 and split method "equal"
    Then the response status should be 200
    And component "Gas" should exist with amount 75.0

  Scenario: Add component with empty name fails
    Given a bill exists for year 2025 month 1
    When I POST to add component with empty name
    Then the page should contain "required"

  Scenario: Add component with invalid split method shows error
    Given a bill exists for year 2025 month 1
    When I POST to add component "Invalid" with amount 75.0 and split method "invalid_method"
    Then the response status should be 200

  Scenario: Add component to archived month fails
    Given an archived bill exists for year 2025 month 1
    When I POST to add component "NewComp" with amount 100.0 and split method "equal"
    Then the page should contain "archived"

  Scenario: Update component
    Given a bill exists for year 2025 month 1
    And component "Original" exists with amount 100.0
    When I POST to update component to name "Updated" with amount 200.0 and split method "usage"
    Then the component name should be "Updated"
    And the component amount should be 200.0

  Scenario: Delete component
    Given a bill exists for year 2025 month 1
    And component "ToDelete" exists with amount 100.0
    When I POST to delete the component
    Then the component should not exist

  # Month Participant Routes
  Scenario: Add participant to month
    Given a bill exists for year 2025 month 1
    And participant "Member" exists
    When I POST to add the participant to the month
    Then the participant should be linked to the month

  Scenario: Remove participant from month
    Given a bill exists for year 2025 month 1
    And participant "Member" is linked to the month
    When I POST to remove the participant from the month
    Then the page should contain "unlinked"

  Scenario: Add participant to archived month fails
    Given an archived bill exists for year 2025 month 1
    And participant "Member" exists
    When I POST to add the participant to the month
    Then the page should contain "archived"

  # Convert Legacy Route
  Scenario: Convert legacy bill to dynamic components
    Given a bill without components exists for year 2025 month 8 with amounts 300, 90, 60
    When I POST to convert the bill to dynamic components
    Then 3 components should exist
    And components "Electricity, Water, Internet" should exist

  Scenario: Convert bill that already has components fails
    Given a bill exists for year 2025 month 1
    And component "Existing" exists
    When I POST to convert the bill to dynamic components
    Then the page should contain "already has components"

  Scenario: Convert archived bill fails
    Given an archived bill exists for year 2025 month 1
    When I POST to convert the bill to dynamic components
    Then the page should contain "archived"

  # Archive Routes
  Scenario: Archive a month
    Given a bill exists for year 2025 month 1
    When I POST to archive the month
    Then the bill should be archived

  Scenario: Archived page shows archived bills
    Given an archived bill exists for year 2025 month 9
    When I visit "/months/archived"
    Then the response status should be 200

  # Delete Route
  Scenario: Delete a month
    Given a bill exists for year 2025 month 1
    When I POST to delete the month
    Then the bill should not exist

  # Settings Routes
  Scenario: Settings page returns 200
    When I visit "/settings/"
    Then the response status should be 200
    And the page should contain "Settings"
    And the page should contain "Database"

  Scenario: Settings page has download link
    When I visit "/settings/"
    Then the page should contain "Download Database"

  Scenario: Settings page has upload form
    When I visit "/settings/"
    Then the page should contain "Restore"
    And the page should contain 'enctype="multipart/form-data"'
    And the page should contain "Select .db file"

  Scenario: Settings page has upload indicator
    When I visit "/settings/"
    Then the page should contain "upload-indicator"
    And the page should contain "Uploading..."

  # Database Download Route
  Scenario: Download database redirects for memory database
    When I visit "/settings/database"
    Then I should be redirected to settings

  # Database Upload Route
  Scenario Outline: Database upload validation
    When I POST to "/settings/database" with <condition>
    Then the page should contain "<error_message>"

    Examples:
      | condition       | error_message    |
      | no file         | No file uploaded |
      | empty filename  | No file selected |
      | invalid type    | Invalid file type |

  # Version Display
  Scenario: Version is displayed on pages
    When I visit "/admin"
    Then the response status should be 200
    And the page should contain "version-footer"
    And the page should contain ">v"

  # Month Participant Selection
  Scenario: Create month with all participants selected
    Given participants "Alice, Bob, Charlie" exist
    When I create a month with all participants selected
    Then all 3 participants should be linked to the month

  Scenario: Create month with subset of participants
    Given participants "Alice, Bob, Charlie" exist
    When I create a month with only "Alice, Bob" selected
    Then 2 participants should be linked to the month
    And "Charlie" should not be linked to the month

  Scenario: Create month with single participant
    Given participants "Alice, Bob, Charlie" exist
    When I create a month with only "Alice" selected
    Then 1 participant should be linked to the month

  Scenario: Create month without selection defaults to all
    Given participants "Alice, Bob, Charlie" exist
    When I create a month without participant selection
    Then all 3 participants should be linked to the month

  Scenario: Add participant to month after creation
    Given a bill exists for year 2025 month 6
    And participant "Alice" is linked to the month
    And participant "Bob" exists but is not linked
    When I add "Bob" to the month
    Then 2 participants should be linked to the month

  Scenario: Remove participant from month
    Given a bill exists for year 2025 month 7
    And participants "Alice, Bob" are linked to the month
    When I remove "Bob" from the month
    Then 1 participant should be linked to the month
    And "Alice" should still be linked

  Scenario: New month form has participant selection UI
    Given participants "Alice, Bob, Charlie" exist
    When I visit "/months/new"
    Then the page should contain "Select All"
    And the page should contain "Deselect All"
    And the page should contain "Uncheck to exclude a participant"
