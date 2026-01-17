Feature: Adjustment Service
  As a user
  I want to manage component adjustments
  So that I can customize how costs are redistributed among participants

  Background:
    Given the adjustment service is initialized

  # Validate Redistribution Rule - Percent Mode
  Scenario: Valid percent redistribution totaling 100%
    Given a component "Electricity" with amount 100.0
    When I validate a percent rule with targets summing to 100.0
    Then the validation should pass

  Scenario: Invalid percent redistribution not totaling 100%
    Given a component "Electricity" with amount 100.0
    When I validate a percent rule with targets summing to 90.0
    Then the validation should fail with error containing "must sum to 100%"

  Scenario: Percent redistribution with small rounding tolerance
    Given a component "Water" with amount 100.0
    When I validate a percent rule with targets summing to 99.995
    Then the validation should pass

  # Validate Redistribution Rule - Amount Mode
  Scenario: Valid amount redistribution totaling base amount
    Given a component "Water" with amount 150.0
    And the base amount for participant is 50.0
    When I validate an amount rule with targets summing to 50.0
    Then the validation should pass

  Scenario: Invalid amount redistribution not totaling base amount
    Given a component "Water" with amount 150.0
    And the base amount for participant is 50.0
    When I validate an amount rule with targets summing to 40.0
    Then the validation should fail with error containing "must sum to"

  Scenario: Validate with empty rule returns valid
    Given a component "Internet" with amount 100.0
    When I validate an empty rule
    Then the validation should pass

  Scenario: Validate with None rule returns valid
    Given a component "Internet" with amount 100.0
    When I validate a None rule
    Then the validation should pass

  # Compute Base Amount
  Scenario: Compute base amount with equal split
    Given a component with amount 300.0 and split method "equal"
    And there are 3 participants
    When I compute the base amount for participant 1
    Then the base amount should be 100.0

  Scenario: Compute base amount with usage split
    Given a component with amount 300.0 and split method "usage"
    And participant 1 has usage 100 out of total 300
    When I compute the base amount for participant 1
    Then the base amount should be 100.0

  Scenario: Compute base amount with zero total usage
    Given a component with amount 300.0 and split method "usage"
    And total usage is 0
    When I compute the base amount for participant 1
    Then the base amount should be 0.0

  Scenario: Compute base amount with equal split and no participants
    Given a component with amount 300.0 and split method "equal"
    And there are 0 participants
    When I compute the base amount for participant 1
    Then the base amount should be 0.0

  # Process Adjustments
  Scenario: Process adjustments for nonexistent month
    When I process adjustments for bill ID 99999
    Then the result should be failure with message "Month not found"

  Scenario: Process adjustments for archived month
    Given an archived month exists
    When I process adjustments for that month
    Then the result should be failure with message containing "archived"

  Scenario: Process valid adjustments with percent redistribution
    Given an active month with components and participants
    And participant 1 redistributes 100% of component 1 to participant 2
    When I process the adjustments
    Then the result should be success
    And 1 redistribution rule should be saved

  Scenario: Process adjustments with invalid percent redistribution
    Given an active month with components and participants
    And participant 1 redistributes 80% of component 1 to participant 2
    When I process the adjustments
    Then the result should be failure
    And the error should contain "must sum to 100%"

  Scenario: Process adjustments with notes
    Given an active month with components and participants
    And participant 1 has adjustment notes "Away on vacation"
    When I process the adjustments
    Then the result should be success
    And the notes should be saved

  Scenario: Process adjustments with no rules returns success
    Given an active month with components and participants
    When I process empty adjustments
    Then the result should be success with message "Component adjustments saved"
    And 0 redistribution rules should be saved

  Scenario: Process valid amount redistribution
    Given an active month with components and participants
    And participant 1 redistributes their base amount equally to others using amount mode
    When I process the adjustments
    Then the result should be success
    And 1 redistribution rule should be saved

  Scenario: Process adjustments with invalid amount redistribution
    Given an active month with components and participants
    And participant 1 redistributes wrong amount to participant 2 using amount mode
    When I process the adjustments
    Then the result should be failure
    And the error should contain "must sum to"
