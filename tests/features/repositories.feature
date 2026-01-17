Feature: Repository Layer
  As a system
  I want repositories to manage data access
  So that business logic is decoupled from persistence

  Background:
    Given the database is initialized

  # Participant Repository
  Scenario: Add a participant via repository
    When I add a participant "Alice" via repository
    Then the participant should have an ID
    And the participant name should be "Alice"

  Scenario: List participants returns ordered by name
    Given I add participants "Zara, Alice, Bob" via repository
    When I list all participants
    Then the participants should be in order "Alice, Bob, Zara"

  Scenario: Get participant by ID
    Given I add a participant "TestUser" via repository
    When I get the participant by ID
    Then the participant should be found
    And the participant name should be "TestUser"

  Scenario: Get nonexistent participant returns none
    When I get participant with ID 9999
    Then the result should be none

  Scenario: Update participant name
    Given I add a participant "OldName" via repository
    When I update the participant name to "NewName"
    Then the participant name should be "NewName"

  Scenario: Delete participant
    Given I add a participant "ToDelete" via repository
    When I delete the participant
    Then the participant should no longer exist

  # Monthly Bill Repository
  Scenario: Create bill via repository
    When I create a bill for year 2025 month 1 with amounts 100.0, 50.0, 30.0 via repository
    Then the bill should have an ID
    And the bill year should be 2025
    And the bill month should be 1

  Scenario: List bills excludes archived
    Given I create bills:
      | year | month | archived |
      | 2025 | 1     | true     |
      | 2025 | 2     | false    |
    When I list all bills
    Then only 1 bill should be returned
    And the bill month should be 2

  Scenario: Paginated list returns correct page
    Given I create bills for months 1 through 5 of 2025
    When I list bills page 1 with 2 per page
    Then 2 bills should be returned
    And the total count should be 5

  Scenario: Get bill by ID
    Given I create a bill for year 2025 month 3 via repository
    When I get the bill by ID
    Then the bill month should be 3

  Scenario: Get previous bill same year
    Given I create bills:
      | year | month |
      | 2025 | 2     |
      | 2025 | 3     |
    When I get the previous bill for 2025 month 3
    Then the previous bill month should be 2

  Scenario: Get previous bill year wrap
    Given I create bills:
      | year | month |
      | 2024 | 12    |
      | 2025 | 1     |
    When I get the previous bill for 2025 month 1
    Then the previous bill year should be 2024
    And the previous bill month should be 12

  Scenario: Find bill by year and month
    Given I create a bill for year 2025 month 6 via repository
    When I find the bill by year 2025 and month 6
    Then the bill should be found
    When I find the bill by year 2025 and month 7
    Then the bill should not be found

  Scenario: Update bill amounts
    Given I create a bill for year 2025 month 1 with amounts 100.0, 50.0, 30.0 via repository
    When I update the bill amounts to 200.0, 100.0, 60.0
    Then the electricity amount should be 200.0
    And the water amount should be 100.0
    And the internet amount should be 60.0

  Scenario: Delete bill
    Given I create a bill for year 2025 month 1 via repository
    When I delete the bill
    Then the bill should no longer exist

  Scenario: Set bill archived status
    Given I create a bill for year 2025 month 1 via repository
    Then the bill should not be archived
    When I set the bill as archived
    Then the bill should be archived

  # Meter Reading Repository
  Scenario: Upsert creates new reading
    Given a participant "Reader" exists
    And a bill for year 2025 month 1 exists
    When I upsert a reading with current 150.0 and previous 100.0
    Then the reading current should be 150.0
    And the reading previous should be 100.0

  Scenario: Upsert updates existing reading
    Given a participant "Reader" exists
    And a bill for year 2025 month 1 exists
    And a reading exists with current 150.0 and previous 100.0
    When I upsert a reading with current 200.0 and previous 150.0
    Then the reading current should be 200.0
    And the reading previous should be 150.0
    And there should be only 1 reading for the month

  Scenario: List readings for month
    Given participants "P1, P2" exist
    And a bill for year 2025 month 1 exists
    And readings exist for both participants
    When I list readings for the month
    Then 2 readings should be returned

  # Month Participant Repository
  Scenario: Add and list month participants
    Given a participant "Member" exists
    And a bill for year 2025 month 1 exists
    When I add the participant to the month
    And I list participants for the month
    Then 1 participant should be linked

  Scenario: Add participant is idempotent
    Given a participant "Member" exists
    And a bill for year 2025 month 1 exists
    When I add the participant to the month twice
    And I list participants for the month
    Then 1 participant should be linked

  Scenario: Remove participant from month
    Given a participant "Member" exists
    And a bill for year 2025 month 1 exists
    And the participant is linked to the month
    When I remove the participant from the month
    And I list participants for the month
    Then 0 participants should be linked

  # Bill Component Repository
  Scenario: Add component
    Given a bill for year 2025 month 1 exists
    When I add a component "Electricity" with amount 150.0 and split method "usage"
    Then the component should have an ID
    And the component name should be "Electricity"
    And the component amount should be 150.0
    And the component split method should be "usage"

  Scenario: Add component with distribution
    Given a bill for year 2025 month 1 exists
    When I add a component "Custom" with amount 100.0 and distribution:
      | participant_id | percent |
      | 1              | 50      |
      | 2              | 30      |
      | 3              | 20      |
    Then the component distribution should have 3 entries
    And the distribution sum should be 100

  Scenario: List components returns ordered by position
    Given a bill for year 2025 month 1 exists
    And components exist:
      | name   | amount | position |
      | Third  | 30.0   | 2        |
      | First  | 10.0   | 0        |
      | Second | 20.0   | 1        |
    When I list components for the month
    Then the components should be in order "First, Second, Third"

  Scenario: Update component
    Given a bill for year 2025 month 1 exists
    And a component "Old" exists with amount 100.0
    When I update the component to name "New" with amount 200.0 and split method "usage"
    Then the component name should be "New"
    And the component amount should be 200.0
    And the component split method should be "usage"

  Scenario: Delete component
    Given a bill for year 2025 month 1 exists
    And a component "ToDelete" exists with amount 100.0
    When I delete the component
    Then 0 components should exist for the month

  # Component Adjustment Repository
  Scenario: Upsert creates new adjustment
    Given a participant exists
    And a bill for year 2025 month 1 exists
    And a component "Electricity" exists
    When I upsert an adjustment with zero flag true
    Then the adjustment zero flag should be true

  Scenario: Upsert updates existing adjustment
    Given a participant exists
    And a bill for year 2025 month 1 exists
    And a component "Electricity" exists
    And an adjustment exists with zero flag true
    When I upsert an adjustment with zero flag false
    Then the adjustment zero flag should be false
    And there should be only 1 adjustment for the month

  Scenario: List adjustments for month
    Given participants "P1, P2" exist
    And a bill for year 2025 month 1 exists
    And a component "Electricity" exists
    And adjustments exist for both participants
    When I list adjustments for the month
    Then 2 adjustments should be returned

  Scenario: Clear adjustments for month
    Given a participant exists
    And a bill for year 2025 month 1 exists
    And a component "Electricity" exists
    And an adjustment exists
    When I clear adjustments for the month
    Then 0 adjustments should exist for the month
