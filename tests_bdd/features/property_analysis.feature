Feature: Property analysis
  Scenario: Investor adds a property and views KPIs
    Given I am logged in as an investor
    When I add a property with address "4821 Ridgewood Dr" and purchase price $325,000
    And I add rental income of $2,400 per month with 5% vacancy
    And I add a property tax expense of $3,900 per year
    And I add a maintenance expense of $200 per month
    When the investment analysis is computed
    Then the NOI should be approximately $17,016
    And the cap rate should be approximately 5.24%
    And the DSCR should be 0 (no debt service)
