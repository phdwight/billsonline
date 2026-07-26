Feature: Database Models
  As a system
  I want database models to enforce constraints
  So that data integrity is maintained

  Background:
    Given the database is initialized

  # Participant Model
  Scenario: Create a participant
    When I create a participant named "TestUser"
    Then the participant should have an ID
    And the participant name should be "TestUser"

  Scenario: Participant names must be unique
    Given a participant named "Unique" exists
    When I try to create a participant named "Unique"
    Then a database error should occur

  # Monthly Bill Model
  Scenario: Create a monthly bill
    When I create a bill for year 2025 month 1 with amounts 100.0, 50.0, 30.0
    Then the bill should have an ID
    And the bill should not be archived by default

  Scenario: Bill year-month combination must be unique
    Given a bill exists for year 2025 month 1
    When I try to create another bill for year 2025 month 1
    Then a database error should occur

  # Meter Reading Model
  Scenario Outline: Meter reading usage calculation
    Given a participant "Reader" exists
    And a bill for year 2025 month 1 exists
    When I create a meter reading with current <current> and previous <previous>
    Then the usage should be <usage>

    Examples:
      | current | previous | usage |
      | 150.0   | 100.0    | 5.0   |
      | 150.0   | null     | 0.0   |
      | 50.0    | 100.0    | 0.0   |

  # Month Participant Model
  Scenario: Create a month-participant link
    Given a participant "Member" exists
    And a bill for year 2025 month 1 exists
    When I link the participant to the month
    Then the link should have an ID

  Scenario: Month-participant link must be unique
    Given a participant "Member" exists
    And a bill for year 2025 month 1 exists
    And the participant is linked to the month
    When I try to link the same participant to the same month
    Then a database error should occur

  # Bill Component Model
  Scenario: Create a bill component
    Given a bill for year 2025 month 1 exists
    When I create a component "Electricity" with amount 150.0 and split method "usage"
    Then the component should have an ID
    And the component name should be "Electricity"

  Scenario: Component with percentage distribution
    Given a bill for year 2025 month 1 exists
    When I create a component "Custom" with amount 100.0 and percentage distribution:
      | participant_id | percent |
      | 1              | 50      |
      | 2              | 30      |
      | 3              | 20      |
    Then the component distribution should have 3 entries
    And the distribution values should sum to 100

  # Component Adjustment Model
  Scenario: Create a component adjustment
    Given a participant "Adjusted" exists
    And a bill for year 2025 month 1 exists
    And a component "Electricity" exists for the bill
    When I create an adjustment to zero the participant's share
    Then the adjustment should have an ID
    And the adjustment zero flag should be true
