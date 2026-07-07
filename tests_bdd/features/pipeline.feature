Feature: Property pipeline discovers and screens deals

  As an investor evaluating properties
  I want discovered properties screened against my investment thresholds
  So that I only analyze deals that meet my minimum criteria

  Scenario: Discovery normalizes messy MLS data
    Given a raw MLS listing with address "123 Main St., Apt #4B", price "350000", beds "3", baths "2.5"
    When the listing is transformed through the discovery sanitizer
    Then the address hash should be a 64-character SHA-256 string
    And the canonical price should be 350000.0
    And the canonical beds should be 3
    And the canonical baths should be 2.5

  Scenario: Duplicate address detected and skipped
    Given a discovery processor with no existing addresses
    When I process a batch of 2 listings with the same address "100 Oak St"
    Then only 1 asset should be discovered
    And 1 duplicate should be skipped

  Scenario: Screening rejects low-yield properties
    Given a screening threshold of 7% minimum gross yield and 15 maximum price-to-rent ratio
    When I evaluate a property with $2,500 monthly rent and $300,000 purchase price
    Then the screening should pass
    When I evaluate a property with $1,200 monthly rent and $500,000 purchase price
    Then the screening should fail
    And the failure reason should contain "yield"

  Scenario: Batch screening processes mixed properties
    Given a screening threshold of 7% minimum gross yield
    And a batch of 4 properties: 2 passing and 2 failing
    When I run the batch screening processor
    Then the result should show 4 processed
    And 2 advanced to underwriting
    And 2 killed

  Scenario: Underwriting computes correct MAO
    Given a property with $2,500 monthly rent and $300,000 purchase price
    And annual property taxes of $3,600 and insurance of $1,200
    When I run the underwriting solver with 8% target cap rate
    Then the NOI should be greater than $15,000
    And the cap rate should be approximately 5.94%
    And the MAO should be approximately $222,750
