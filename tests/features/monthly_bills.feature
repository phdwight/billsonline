Feature: Monthly Bill Management
  As a household administrator
  I want to manage monthly bills
  So that I can track and split expenses among participants

  Background:
    Given the system is initialized
    And participants "Alice, Bob, Charlie" exist

  Scenario: Create a new monthly bill
    When I create a bill for January 2025 with:
      | electricity | water | internet |
      | 1000.00     | 500.00| 300.00   |
    Then a bill for January 2025 should exist
    And the bill total should be 1800.00

  Scenario: Prevent duplicate monthly bills
    Given a bill for January 2025 exists
    When I try to create another bill for January 2025
    Then the operation should fail with "already exists"

  Scenario: Update bill amounts
    Given a bill for January 2025 exists with electricity 1000.00
    When I update the bill electricity amount to 1200.00
    Then the bill electricity amount should be 1200.00

  Scenario: Update bill amounts also updates components
    Given a bill for January 2025 exists with:
      | electricity | water  | internet |
      | 300.00      | 90.00  | 60.00    |
    And the bill has legacy components:
      | name        | amount | split_method |
      | Electricity | 300.00 | usage        |
      | Water       | 90.00  | equal        |
      | Internet    | 60.00  | equal        |
    When I update the bill amounts to:
      | electricity | water  | internet |
      | 500.00      | 150.00 | 100.00   |
    Then the bill electricity amount should be 500.00
    And the bill water amount should be 150.00
    And the bill internet amount should be 100.00
    And the "Electricity" component amount should be 500.00
    And the "Water" component amount should be 150.00
    And the "Internet" component amount should be 100.00

  Scenario: Archive a monthly bill
    Given a bill for January 2025 exists
    When I archive the bill for January 2025
    Then the bill should be marked as archived
    And the bill should not appear in active bills list

  Scenario: Delete a monthly bill
    Given a bill for January 2025 exists
    When I delete the bill for January 2025
    Then the bill for January 2025 should not exist
