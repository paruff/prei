Feature: Investor journey, steps 1-4 (identify, discover, screen, underwrite)

  As a buy-and-hold investor
  I want to go from a ranked market to an underwritten property
  So that I can decide whether to make an offer

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
