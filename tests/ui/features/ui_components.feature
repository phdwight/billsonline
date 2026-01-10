Feature: Bill Components UI
  As a user of Bills Online
  I want to manage bill components through the web interface
  So that I can track different types of expenses

  Background:
    Given I am on the home page

  @ui @components
  Scenario: Add a custom component to a month
    Given a participant named "Alice" exists
    And a participant named "Bob" exists
    And a monthly bill for "January 2024" exists
    And I am viewing the month detail page
    When I add a new component named "Gas"
    And I set the amount to $75.00
    And I select "Equal" as the split method
    And I click "Add Component"
    Then I should see "Gas" in the components list

  @ui @components
  Scenario: Add component with usage-based split
    Given a participant named "Alice" exists
    And a participant named "Bob" exists
    And a monthly bill for "January 2024" exists
    And I am viewing the month detail page
    When I add a new component named "Heating"
    And I set the amount to $200.00
    And I select "By usage" as the split method
    And I click "Add Component"
    Then I should see "Heating" in the components list

  @ui @components
  Scenario: Components affect contributions
    Given a participant named "Alice" exists
    And a participant named "Bob" exists
    And a monthly bill for "January 2024" exists
    And I am viewing the month detail page
    When I add a new component named "Gas"
    And I set the amount to $100.00
    And I select "Equal" as the split method
    And I click "Add Component"
    Then the total contributions should be recalculated
