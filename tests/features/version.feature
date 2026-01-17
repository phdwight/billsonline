Feature: Version Information
  As a user
  I want to see the application version
  So that I know which version I'm using

  Background:
    Given the application is initialized

  Scenario: Version returns a string
    When I get the application version
    Then the version should be a string

  Scenario: Version follows semver format
    When I get the application version
    Then the version should have 3 parts separated by dots
    And each part should be a number

  Scenario: Version is read from VERSION file
    Given a VERSION file exists with content "1.2.3"
    When I get the application version
    Then the version should be "1.2.3"

  Scenario: Default version when VERSION file is missing
    Given the VERSION file does not exist
    When I get the application version
    Then the version should be "0.0.1"

  Scenario: Version is available in template context
    When I render a page
    Then the app_version should be available in the template context
