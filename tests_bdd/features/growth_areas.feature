Feature: Growth area discovery leads to property pipeline

  As an investor looking for the right place to invest
  I want to discover promising areas and pipe properties into screening
  So that I can find the best deals in the best markets

  Scenario: Discover top places in a state
    Given I am on the growth area explorer page
    When I select state "TX"
    And I run the analysis
    Then I should see 10 places ranked by composite score
    And the top place should be in "TX"
    And each place should have a population growth rate greater than -50%
    And each place should have a composite score

  Scenario: Export growth areas to CSV
    Given there are 5 growth areas in the database
    When I download the growth areas CSV
    Then the response content type should be text/csv
    And the CSV should contain a header row with "State" and "City"
    And the CSV should contain 5 data rows plus header

  Scenario: View growth areas with pagination
    Given there are 30 growth areas in the database
    When I visit the growth areas page
    Then I should see 25 results displayed
    And I should see pagination links "Next" and "Last"
    When I click "Next"
    Then I should see the remaining 5 results
