Feature: Investment dashboard
  As an investor
  I want to see computed KPIs for my properties
  So that I can quickly assess deals

  Scenario: Display KPIs for a property on the dashboard
    Given a user "tester@example.com" exists
    And a property "123 Main St" with purchase price 120000 exists for "tester@example.com"
    And rental income of 2000 per month with vacancy 0.05 exists for that property
    And a monthly operating expense of 300 exists for that property
    When I visit the dashboard
    Then I see "Top Properties"
    And I see "123 Main St"
