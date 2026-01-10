Feature: Meter Readings UI
  As a user of Bills Online
  I want to enter meter readings through the web interface
  So that electricity can be split based on actual usage

  Background:
    Given I am on the home page

  @ui @readings
  Scenario: Enter meter readings for participants
    Given a participant named "Alice" exists
    And a participant named "Bob" exists
    And a monthly bill for "January 2024" exists
    And I am viewing the month detail page
    When I enter meter readings for each participant:
      | participant | previous | current |
      | Alice       | 1000     | 1100    |
      | Bob         | 2000     | 2050    |
    And I click "Save Readings"
    Then the readings should be saved
    And I should see usage calculated for each participant

  @ui @readings
  Scenario: Readings affect electricity contribution
    Given a participant named "Alice" exists
    And a participant named "Bob" exists
    And a monthly bill for "January 2024" exists
    And I am viewing the month detail page
    When I enter meter readings for each participant:
      | participant | previous | current |
      | Alice       | 1000     | 1200    |
      | Bob         | 2000     | 2050    |
    And I click "Save Readings"
    Then the contributions should be recalculated
    And "Alice" should have a different contribution than "Bob"
