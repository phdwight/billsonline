Feature: Complex Route Operations
  As a household administrator
  I want to manage months with components, readings, and adjustments
  So that I can accurately track and split expenses

  Background:
    Given the system is initialized
    And participants "Alice, Bob, Cara" exist
    And a bill for March 2025 exists with participants linked

  # ===== Month Creation with Components =====

  Scenario: Create month with legacy electricity/water/internet components
    Given a participant "TestUser" exists
    When I create a bill for April 2025 with:
      | electricity | water | internet |
      | 150.00      | 75.00 | 45.00    |
    Then a bill for April 2025 should exist
    And the bill should have component "Electricity"
    And the bill should have component "Water"
    And the bill should have component "Internet"

  Scenario: Create month with custom components
    Given a participant "TestUser" exists
    When I create a bill for May 2025 with custom components:
      | name        | amount | split  |
      | Gas         | 80.00  | equal  |
      | Maintenance | 120.00 | equal  |
    Then a bill for May 2025 should exist
    And the bill should have component "Gas"
    And the bill should have component "Maintenance"

  Scenario: Create month with percentage-based split
    Given participants "Alice, Bob" exist
    When I create a bill for June 2025 with percentage split:
      | component   | amount | Alice | Bob |
      | Electricity | 100.00 | 60    | 40  |
    Then the "Electricity" component should have split method "percentage"
    And the "Electricity" component should have distribution data

  Scenario: Empty component names are skipped during month creation
    Given a participant "TestUser" exists
    When I create a bill for July 2025 with components including empty names:
      | name      | amount |
      |           | 100    |
      | ValidName | 200    |
      |           | 300    |
    Then the bill should have component "ValidName"
    And the bill should have exactly 1 custom component

  # ===== Meter Readings =====

  Scenario: Submit meter readings for participants
    When I submit meter readings:
      | participant | current | previous |
      | Alice       | 200     | 100      |
      | Bob         | 150     | 100      |
      | Cara        | 100     | 100      |
    Then readings should be saved for all participants
    And Alice's usage should be 100.0
    And Bob's usage should be 50.0
    And Cara's usage should be 0.0

  Scenario: Submit readings without previous value
    When I submit meter readings:
      | participant | current | previous |
      | Alice       | 200     |          |
    Then Alice's reading should have no previous value
    And Alice's usage should be 0.0

  Scenario: Cannot submit readings to archived month
    Given the bill is archived
    When I try to submit meter readings:
      | participant | current | previous |
      | Alice       | 200     | 100      |
    Then I should see an archived warning

  Scenario: Submit readings to non-existent month
    When I try to submit readings to month 9999
    Then I should see a not found error

  # ===== Component Adjustments =====

  Scenario: Save adjustments without redistribution rules
    Given a component "Water" exists with amount 90.00 split "equal"
    When I save adjustments with no rules
    Then the adjustments should be saved successfully

  Scenario: Save adjustments with percent redistribution
    Given a component "Water" exists with amount 90.00 split "equal"
    When I zero out Alice's share of "Water" and redistribute:
      | mode    | Bob | Cara |
      | percent | 60  | 40   |
    Then an adjustment should exist for Alice on "Water"
    And the adjustment should have mode "percent"
    And Alice should be zeroed out

  Scenario: Invalid percent sum shows error
    Given a component "Water" exists with amount 90.00 split "equal"
    When I try to redistribute with invalid percentages:
      | mode    | Bob | Cara |
      | percent | 30  | 30   |
    Then I should see "must sum to 100%"

  Scenario: Cannot save adjustments to archived month
    Given a component "Water" exists with amount 90.00 split "equal"
    And the bill is archived
    When I try to save adjustments
    Then I should see an archived warning


  # ===== Update Month =====

  Scenario: Update month amounts
    When I update the bill amounts to:
      | electricity | water  | internet |
      | 400.00      | 120.00 | 80.00    |
    Then the bill electricity amount should be 400.00
    And the bill water amount should be 120.00
    And the bill internet amount should be 80.00

  Scenario: Update month amounts also updates components
    Given the bill has legacy components:
      | name        | amount | split_method |
      | Electricity | 300.00 | usage        |
      | Water       | 90.00  | equal        |
      | Internet    | 60.00  | equal        |
    When I update the bill amounts to:
      | electricity | water  | internet |
      | 500.00      | 150.00 | 100.00   |
    Then the bill electricity amount should be 500.00
    And the "Electricity" component amount should be 500.00
    And the "Water" component amount should be 150.00
    And the "Internet" component amount should be 100.00

  Scenario: Cannot update archived month
    Given the bill is archived
    When I try to update the bill amounts to:
      | electricity | water  | internet |
      | 999.00      | 999.00 | 999.00   |
    Then I should see an archived warning

  # ===== Component Update Validation =====

  Scenario: Update component with invalid amount
    Given a component "Test" exists with amount 100.00 split "equal"
    When I try to update the component amount to "not_a_number"
    Then I should see a number error

  Scenario: Update component with negative amount
    Given a component "Test" exists with amount 100.00 split "equal"
    When I try to update the component amount to "-50"
    Then I should see a non-negative error

  Scenario: Update component with invalid position
    Given a component "Test" exists with amount 100.00 split "equal"
    When I try to update the component position to "not_an_int"
    Then I should see an integer error

  Scenario: Update component with invalid split method
    Given a component "Test" exists with amount 100.00 split "equal"
    When I try to update the component split method to "invalid_method"
    Then I should see a split method error

  # ===== Convert Legacy Edge Cases =====

  Scenario: Convert legacy with no amounts
    Given a standalone bill for September 2025 with zero amounts
    When I try to convert legacy amounts
    Then I should see "no legacy amounts"

  # ===== Participant Edge Cases =====

  Scenario: Add participant without selecting one
    When I try to add a participant to the month without selecting one
    Then I should see a select error

  Scenario: Update participant to duplicate name
    Given participants "Alice, Bob" exist
    When I try to rename Bob to "Alice"
    Then I should see "already has that name"
