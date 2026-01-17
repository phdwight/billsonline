Feature: Extended Route Coverage
  As a user
  I want comprehensive route functionality
  So that I can manage all aspects of the billing application

  Background:
    Given the extended route app is running

  # Extended Month Routes
  Scenario: Update month with valid data
    Given a bill exists with ID for year 2025 month 2
    When I POST to update the month with amounts 150.0, 75.0, 45.0
    Then the bill amounts should be updated

  Scenario: Update month on archived bill fails
    Given an archived bill exists with ID for year 2025 month 3
    When I POST to update the month with amounts 200.0, 100.0, 60.0
    Then the page should contain "archived"

  Scenario: Update month also updates matching components
    Given a bill exists with ID for year 2025 month 4
    And the bill has component "Electricity" with amount 100.0
    When I POST to update the month with amounts 200.0, 100.0, 60.0
    Then the component "Electricity" amount should be 200.0

  # Extended Component Routes
  Scenario: Update component with empty name
    Given a bill exists with component "TestComp" for update
    When I POST to update component with empty name
    Then the component name should still be "TestComp"

  Scenario: Update component with negative amount fails
    Given a bill exists with component "NegativeTest" for update
    When I POST to update component with negative amount
    Then the page should contain "non-negative"

  Scenario: Update component with invalid position
    Given a bill exists with component "PosTest" for update
    When I POST to update component with invalid position "abc"
    Then the page should contain "integer"

  Scenario: Update component split method to usage
    Given a bill exists with component "SplitTest" split "equal"
    When I POST to update component split to "usage"
    Then the component split method should be "usage"

  Scenario: Update component with invalid split method fails
    Given a bill exists with component "InvalidSplit" for update
    When I POST to update component with invalid split method
    Then the page should contain "usage"

  Scenario: Delete component from archived month fails
    Given an archived bill with component "ArchiveComp"
    When I POST to delete that component
    Then the page should contain "archived"

  Scenario: Update component on archived month fails
    Given an archived bill with component "ArchiveUpdate"
    When I POST to update that component amount
    Then the page should contain "archived"

  Scenario: Add component with valid position
    Given a bill for component creation exists
    When I POST to add component "NewComp" with position 5
    Then the component should exist at position 5

  # Readings Routes
  Scenario: Update readings for a month
    Given a bill with participant for readings test
    When I POST meter readings current 500 previous 400
    Then the readings should be saved

  Scenario: Update readings on archived month fails
    Given an archived bill with participant for readings
    When I POST meter readings current 500 previous 400
    Then the page should contain "archived"

  Scenario: Update readings with missing month
    When I POST readings to nonexistent month 99999
    Then the page should contain "not found"

  # Month Participant Routes Extended
  Scenario: Add participant to nonexistent month fails
    When I POST to add participant to nonexistent month 99999
    Then the page should contain "not found"

  Scenario: Add participant without selecting one fails
    Given a bill for participant test exists
    When I POST to add participant without selection
    Then the page should contain "Select"

  Scenario: Remove participant from nonexistent month fails
    Given a participant "RemoveTest" exists
    When I POST to remove participant from nonexistent month
    Then the page should contain "not found"

  # Export Route
  Scenario: Export month as CSV
    Given a bill with data for export exists
    When I GET the export CSV endpoint
    Then the response should be a CSV file

  Scenario: Export nonexistent month fails
    When I GET export CSV for nonexistent month 99999
    Then I should be redirected

  # Adjustments Route
  Scenario: Update adjustments for a month
    Given a bill with components and participants for adjustments
    When I POST adjustment form data
    Then the adjustments should be saved

  Scenario: Update adjustments on archived month fails
    Given an archived bill with components for adjustments
    When I POST adjustment form data
    Then the page should contain "archived"

  Scenario: Update adjustments on nonexistent month fails
    When I POST adjustments to nonexistent month 99999
    Then the page should contain "not found"

  # Form validation edge cases
  Scenario: Create month with form validation failure
    When I POST to create month with invalid form data
    Then the page should contain "error"

  Scenario: Edit nonexistent month shows error
    When I visit edit page for nonexistent month 99999
    Then the page should contain "not found"
