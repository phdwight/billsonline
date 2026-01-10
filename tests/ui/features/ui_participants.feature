Feature: Participant Management UI
  As a user of Bills Online
  I want to manage participants through the web interface
  So that I can track who shares the bills

  Background:
    Given I am on the home page

  @ui @participants
  Scenario: Add a new participant via the home page
    When I enter "Alice" in the participant name field
    And I click the "Add" button
    Then I should see "Alice" in the participant list
    And I should see 1 participants

  @ui @participants
  Scenario: Add multiple participants
    When I add a participant named "Alice"
    And I add a participant named "Bob"
    And I add a participant named "Charlie"
    Then I should see 3 participants
    And I should see "Alice" in the participant list
    And I should see "Bob" in the participant list
    And I should see "Charlie" in the participant list

  @ui @participants
  Scenario: Navigate to participants management page
    Given a participant named "Alice" exists
    When I click the Manage link next to Participants
    Then I should be on the participants management page

  @ui @participants
  Scenario: Edit a participant name
    Given a participant named "Alice" exists
    And I am on the participants page
    When I update "Alice" to "Alicia"
    Then I should see "Alicia" in the participant list

  @ui @participants
  Scenario: Participant avatar displays first letter
    When I add a participant named "Bob"
    Then each participant should have an avatar icon