Feature: Navigation UI
  As a user of Bills Online
  I want to navigate through the application
  So that I can access all features easily

  Background:
    Given I am on the home page

  @ui @navigation
  Scenario: Home page loads correctly
    Then I should see the navigation header
    And I should see the quick links section

  @ui @navigation
  Scenario: Navigate to settings page
    When I click the "Settings" link
    Then I should be on the settings page

  @ui @navigation
  Scenario: Navigate to archived months
    When I click the "Archived" link
    Then I should be on the archived page

  @ui @navigation
  Scenario: Navigate back from settings
    When I click the "Settings" link
    And I click the "Home" link
    Then I should be on the home page
