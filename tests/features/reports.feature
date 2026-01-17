Feature: Reports
  As a user
  I want to view reports of participant contributions over time
  So that I can analyze spending trends

  Background:
    Given the reports app is running

  # Reports Page
  Scenario: Reports page loads successfully
    When I visit the reports page
    Then the response status should be 200
    And the page should contain "Reports"

  Scenario: Reports page shows available months
    Given bills exist for months 1 through 3 of 2025
    When I visit the reports page
    Then the page should contain "January 2025"
    And the page should contain "February 2025"
    And the page should contain "March 2025"

  Scenario: Reports page shows no data message when no bills
    Given no bills exist
    When I visit the reports page
    Then the page should contain "No monthly bills found"

  # Reports Data API
  Scenario: Get report data for valid range
    Given bills exist for months 1 through 3 of 2025 with participants and components
    When I request report data from January 2025 to March 2025
    Then the response should contain labels for 3 months
    And the response should contain participant datasets

  Scenario: Get report data includes electricity usage
    Given bills exist for months 1 through 3 of 2025 with participants and meter readings
    When I request report data from January 2025 to March 2025
    Then the response should contain usage datasets
    And each usage dataset should have data for each month

  Scenario: Get report data with invalid parameters
    When I request report data with invalid parameters
    Then the response should have error status

  Scenario: Get report data with missing parameters
    When I request report data with missing parameters
    Then the response should have error "Missing parameters"

  Scenario: Get report data for range with no bills
    When I request report data from January 2020 to March 2020
    Then the response should contain empty labels

  # Navigation
  Scenario: Reports link appears in navigation
    When I visit the home page
    Then the page should contain link to reports
