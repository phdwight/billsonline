Feature: Monthly Bills UI
  As a user of Bills Online
  I want to manage monthly bills through the web interface
  So that I can track and split household expenses

  Background:
    Given I am on the home page

  @ui @months
  Scenario: Create a new monthly bill
    Given a participant named "Alice" exists
    When I fill in the new month form with:
      | field       | value   |
      | year        | 2024    |
      | month       | January |
      | electricity | 100     |
      | water       | 50      |
      | internet    | 30      |
    And I click "Create Month"
    Then I should see "2024-January" in the month list

  @ui @months
  Scenario: View month details
    Given a participant named "Alice" exists
    And a monthly bill for "January 2024" exists
    When I click on "2024-January" in the month list
    Then I should be on the month detail page
    And I should see the bill components section
    And I should see the contributions section

  @ui @months
  Scenario: Archive a month
    Given a participant named "Alice" exists
    And a monthly bill for "January 2024" exists
    When I click the more actions button for "2024-January"
    And I click "Archive"
    Then I should not see "2024-January" in the month list
