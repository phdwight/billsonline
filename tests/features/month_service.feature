Feature: Month Service
  As a user
  I want the month service to handle bill-related operations
  So that I can view, export, and manage monthly bills

  Background:
    Given the month service is initialized

  # Get Month Detail Data
  Scenario: Get month detail returns None for nonexistent bill
    When I get month detail data for bill ID 99999
    Then the result should be None

  Scenario: Get month detail returns data for existing bill
    Given a bill exists for year 2025 month 3
    When I get month detail data for that bill
    Then the result should contain the bill
    And the result should contain participant data

  Scenario: Get month detail backfills membership for legacy month
    Given a bill exists for year 2025 month 4
    And participants exist but no month memberships
    When I get month detail data for that bill
    Then member_ids should be populated

  Scenario: Get month detail computes dynamic contributions
    Given a bill exists with components
    And participants exist with meter readings
    When I get month detail data for that bill
    Then dynamic_contributions should be computed

  # Export to CSV
  Scenario: Export returns None for nonexistent bill
    When I export bill ID 99999 to CSV
    Then the export result should be None

  Scenario: Export returns CSV content for existing bill
    Given a bill exists with components
    And participants exist with meter readings
    When I export that bill to CSV
    Then the export result should contain CSV content
    And the filename should match the month

  Scenario: Export synthesizes components for legacy bill
    Given a legacy bill exists without components
    When I export that bill to CSV
    Then the export result should contain CSV content
    And legacy components should be synthesized

  # Synthesize Legacy Components
  Scenario: Synthesize creates electricity component
    Given a legacy bill with electricity amount 100.0
    When I synthesize legacy components
    Then "Electricity" component should be created with amount 100.0

  Scenario: Synthesize creates water component
    Given a legacy bill with water amount 50.0
    When I synthesize legacy components
    Then "Water" component should be created with amount 50.0

  Scenario: Synthesize creates internet component
    Given a legacy bill with internet amount 30.0
    When I synthesize legacy components
    Then "Internet" component should be created with amount 30.0

  Scenario: Synthesize skips zero amounts
    Given a legacy bill with only electricity amount 100.0
    When I synthesize legacy components
    Then only 1 component should be created

  # Convert Legacy to Components
  Scenario: Convert legacy fails for nonexistent month
    When I convert legacy for bill ID 99999
    Then the convert result should be failure with message "Month not found"

  Scenario: Convert legacy fails for archived month
    Given an archived bill exists for year 2025 month 5
    When I convert legacy for that bill
    Then the convert result should be failure with message containing "archived"

  Scenario: Convert legacy fails if components already exist
    Given a bill exists with components
    When I convert legacy for that bill
    Then the convert result should be failure with message "This month already has components."

  Scenario: Convert legacy fails if no legacy amounts
    Given a bill exists with zero amounts
    When I convert legacy for that bill
    Then the convert result should be failure with message "No legacy amounts found to convert."

  Scenario: Convert legacy succeeds for valid bill
    Given a legacy bill without existing components
    When I convert legacy for that bill
    Then the convert result should be success
    And components should be created from legacy amounts

  # Compute Base Map
  Scenario: Compute base map with equal split
    Given a component with amount 300.0 and equal split
    And there are 3 member participants
    When I compute the base map
    Then each participant should have base amount 100.0

  Scenario: Compute base map with usage split
    Given a component with amount 300.0 and usage split
    And participants have different usage amounts
    When I compute the base map
    Then base amounts should be proportional to usage
