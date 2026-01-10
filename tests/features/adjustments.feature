Feature: Component Adjustments and Redistribution
  As a household administrator
  I want to adjust and redistribute component costs
  So that temporary absences or special arrangements are handled fairly

  Background:
    Given the system is initialized
    And participants "Alice, Bob, Charlie" exist
    And a bill for January 2025 exists
    And a component "Electricity" exists with amount 300.00 split "equal"

  Scenario: Zero out a participant's share with equal redistribution
    When I zero out Alice's share of "Electricity"
    Then Alice should pay 0.00 for "Electricity"
    And Bob should pay 150.00 for "Electricity"
    And Charlie should pay 150.00 for "Electricity"
    And the component total should remain 300.00

  Scenario: Redistribute by percentage to specific participants
    When I zero out Alice's share of "Electricity" with redistribution:
      | mode    | targets              |
      | percent | Bob:70, Charlie:30   |
    Then Alice should pay 0.00 for "Electricity"
    And Bob should pay 170.00 for "Electricity"
    And Charlie should pay 130.00 for "Electricity"

  Scenario: Redistribute by fixed amounts
    When I zero out Alice's share of "Electricity" with redistribution:
      | mode   | targets             |
      | amount | Bob:60, Charlie:40  |
    Then Alice should pay 0.00 for "Electricity"
    And Bob should pay 160.00 for "Electricity"
    And Charlie should pay 140.00 for "Electricity"

  Scenario: Validate percent redistribution sums to 100
    When I try to redistribute Alice's share with invalid percentages:
      | mode    | targets              |
      | percent | Bob:50, Charlie:30   |
    Then the operation should fail with "must sum to 100%"

  Scenario: Multiple participants zeroed out
    When I zero out Alice's share of "Electricity"
    And I zero out Bob's share of "Electricity"
    Then Alice should pay 0.00 for "Electricity"
    And Bob should pay 0.00 for "Electricity"
    And Charlie should pay 300.00 for "Electricity"

  Scenario: Rounding preserves total amount
    Given a component "Test" exists with amount 100.00 split "equal"
    When contributions are calculated
    Then the sum of all contributions should equal 100.00
