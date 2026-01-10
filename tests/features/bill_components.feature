Feature: Bill Components and Splitting
  As a household administrator
  I want to define bill components with different splitting methods
  So that expenses are fairly distributed among participants

  Background:
    Given the system is initialized
    And participants "Alice, Bob, Charlie" exist
    And a bill for January 2025 exists

  Scenario: Add an equally split component
    When I add a component "Water" with amount 300.00 split "equal"
    Then each participant should pay 100.00 for "Water"

  Scenario: Add a usage-based component
    Given meter readings are:
      | participant | previous | current |
      | Alice       | 100      | 150     |
      | Bob         | 200      | 280     |
      | Charlie     | 300      | 340     |
    When I add a component "Electricity" with amount 300.00 split "usage"
    Then Alice should pay 88.24 for "Electricity"
    And Bob should pay 141.18 for "Electricity"
    And Charlie should pay 70.59 for "Electricity"

  Scenario: Add a percentage-based component
    When I add a component "Rent" with amount 1000.00 split "percentage" with distribution:
      | participant | percentage |
      | Alice       | 50         |
      | Bob         | 30         |
      | Charlie     | 20         |
    Then Alice should pay 500.00 for "Rent"
    And Bob should pay 300.00 for "Rent"
    And Charlie should pay 200.00 for "Rent"

  Scenario: Add a fixed amount component
    When I add a component "Services" with amount 600.00 split "amount" with distribution:
      | participant | amount |
      | Alice       | 300.00 |
      | Bob         | 200.00 |
      | Charlie     | 100.00 |
    Then Alice should pay 300.00 for "Services"
    And Bob should pay 200.00 for "Services"
    And Charlie should pay 100.00 for "Services"

  Scenario: Update component details
    Given a component "Water" exists with amount 300.00
    When I update the component "Water" amount to 350.00
    Then the component "Water" amount should be 350.00

  Scenario: Delete a component
    Given a component "Water" exists with amount 300.00
    When I delete the component "Water"
    Then the component "Water" should not exist
