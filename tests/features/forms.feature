Feature: Form Validation
  As a user
  I want form inputs to be validated
  So that I cannot enter invalid data

  Background:
    Given the application is initialized

  # Valid Form Data
  Scenario: Valid month form data is accepted
    Given a form with valid data:
      | field              | value  |
      | year               | 2025   |
      | month              | 6      |
      | electricity_amount | 100.0  |
      | water_amount       | 50.0   |
      | internet_amount    | 30.0   |
    When the form is validated
    Then the form should be valid
    And the year should be 2025
    And the month should be 6

  # Year Validation with Parametrization
  Scenario Outline: Year validation rejects out of range values
    Given a form with year "<year>" and valid other fields
    When the form is validated
    Then the form should be invalid
    And there should be an error for field "year"

    Examples:
      | year |
      | 1999 |
      | 3001 |

  Scenario Outline: Valid years are accepted
    Given a form with year "<year>" and valid other fields
    When the form is validated
    Then the form should be valid

    Examples:
      | year |
      | 2000 |
      | 2025 |
      | 3000 |

  # Amount Validation with Parametrization
  Scenario Outline: Negative amounts are rejected
    Given a form with <field> set to <value> and valid other fields
    When the form is validated
    Then the form should be invalid
    And there should be an error for field "<field>"

    Examples:
      | field              | value   |
      | electricity_amount | -100.0  |
      | water_amount       | -50.0   |
      | internet_amount    | -30.0   |

  Scenario: Missing required field is rejected
    Given a form with electricity_amount missing and valid other fields
    When the form is validated
    Then the form should be invalid
    And there should be an error for field "electricity_amount"

  # Duplicate Check
  Scenario: Duplicate check disabled by default
    Given a bill exists for year 2025 month 6
    And a form with data for year 2025 month 6
    When the form is created without duplicate check
    Then the duplicate check flag should be false

  Scenario: Duplicate check catches existing bill
    Given a bill exists for year 2025 month 6
    And a form with data for year 2025 month 6
    When the form is validated with duplicate check enabled
    Then the form should be invalid
    And there should be an error for field "month"
