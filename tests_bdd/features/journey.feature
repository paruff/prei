Feature: Investor journey, steps 1-7 (identify through own)

  As a buy-and-hold investor
  I want to go from a ranked market to an underwritten property
  So that I can buy it and track how it performs

  Runs over HTTP against the seeded container (BASE_URL). Seed with
  `manage.py seed_market`; see `make docker-accept`.

  Scenario: Find and underwrite the best property in the seeded market
    Given I am signed in as the demo investor
    When I open the growth areas list
    Then Dallas, TX is ranked with a composite score
    When I discover VRM properties in Dallas, TX
    Then the screener lists "1200 Seed Pass Ln" and "3400 Seed Fail Ct"
    When I open "1200 Seed Pass Ln" from the screener
    Then its gross yield is "12.0%" and its price-to-rent is "8.33"
    And it shows NOI, cap rate, cash-on-cash and DSCR
    When I open "3400 Seed Fail Ct" from the screener
    Then its gross yield is "5.9%" and its price-to-rent is "17.05"

  Scenario: Buy the best property and track its monthly actuals
    Given I am signed in as the demo investor
    When I discover VRM properties in the seeded market
    And I open "1200 Seed Pass Ln" from the screener
    And I advance it to the Offer stage
    And I record an offer of 95000
    Then the offer is listed for the property
    When I advance it to the Due Diligence stage
    And I mark due diligence go
    And I advance it to the Closing stage
    And I close the deal at 95000
    Then it is in the portfolio
    When I enter monthly actuals for it
    Then the portfolio shows its actuals

  Scenario: Buy the best property and track its monthly actuals
    Given I am signed in as the demo investor
    When I open the growth areas list
    And I discover VRM properties in the seeded market
    And I open "1200 Seed Pass Ln" from the screener
    And I advance it to the Offer stage
    And I record an offer of 175000
    Then the offer is listed for the property
    When I advance it to the Due Diligence stage
    And I mark due diligence go
    And I advance it to the Closing stage
    And I close the deal at 175000
    Then it is in the portfolio
    When I enter monthly actuals for it
    Then the portfolio shows its actuals
