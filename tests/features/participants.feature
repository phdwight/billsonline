Feature: Participant Management
  As a household administrator
  I want to manage participants
  So that I can track who shares the bills

  Background:
    Given the system is initialized

  Scenario: Add a new participant
    When I add a participant named "Alice"
    Then the participant "Alice" should exist
    And the total number of participants should be 1

  Scenario: Add multiple participants
    When I add a participant named "Alice"
    And I add a participant named "Bob"
    And I add a participant named "Charlie"
    Then the total number of participants should be 3

  Scenario: Prevent duplicate participant names
    Given a participant named "Alice" exists
    When I try to add a participant named "alice"
    Then the operation should fail with "already exists"
    And the total number of participants should be 1

  Scenario: Update participant name
    Given a participant named "Alice" exists
    When I update the participant "Alice" to "Alicia"
    Then the participant "Alicia" should exist
    And the participant "Alice" should not exist

  Scenario: List all participants
    Given a participant named "Alice" exists
    And a participant named "Bob" exists
    When I list all participants
    Then I should see 2 participants
    And the participants should be ordered alphabetically
