Feature: Settings UI
  As a user of Bills Online
  I want to manage application settings
  So that I can backup and restore my data

  Background:
    Given I am on the settings page

  @ui @settings
  Scenario: Settings page displays database options
    Then I should see the "Backup" section
    And I should see the "Restore" section
    And I should see the "Download Database" button

  @ui @settings
  Scenario: Database restore file selection triggers confirmation
    When I select a database file and confirm restore
    Then I should see a success or error message
