Feature: Meter Readings Management
  As a household administrator
  I want to record and manage meter readings
  So that usage-based billing is accurate

  Background:
    Given the system is initialized
    And participants "Alice, Bob, Charlie" exist
    And a bill for January 2025 exists

  Scenario: Record meter readings for participants
    When I record meter readings:
      | participant | previous | current |
      | Alice       | 1000     | 1050    |
      | Bob         | 2000     | 2100    |
      | Charlie     | 3000     | 3030    |
    Then Alice's usage should be 50
    And Bob's usage should be 100
    And Charlie's usage should be 30
    And total usage should be 180

  Scenario: Update existing meter readings
    Given meter readings exist for Alice with previous 1000 and current 1050
    When I update Alice's current reading to 1075
    Then Alice's usage should be 75

  Scenario: Pre-fill previous readings from last month
    Given a bill for December 2024 exists with readings:
      | participant | current |
      | Alice       | 950     |
      | Bob         | 1900    |
    When I view the January 2025 bill
    Then Alice's previous reading should be pre-filled with 950
    And Bob's previous reading should be pre-filled with 1900

  Scenario: Handle zero usage correctly
    When I record meter readings:
      | participant | previous | current |
      | Alice       | 1000     | 1000    |
    Then Alice's usage should be 0
    And Alice should not be charged for usage-based components

  Scenario: Prevent negative usage
    When I record meter readings:
      | participant | previous | current |
      | Alice       | 1000     | 900     |
    Then Alice's usage should be 0
