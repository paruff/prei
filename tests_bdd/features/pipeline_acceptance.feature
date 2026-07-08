Feature: Acquisition and leasing pipeline accepts end-to-end flows

  As an investor using the pipeline
  I want to manage properties from discovery through acquisition to leasing
  So that I can execute my investment strategy

  Background:
    Given I am logged in as a user
    And I have a VRM property in Texas listed at $250,000 with $2,200/mo rent

  Scenario: Pipeline list shows my properties
    When I add the VRM property to my pipeline
    Then I should be redirected to the pipeline detail page
    And the property stage should be SCREENING
    And the screening result should be recorded

  Scenario: Pipeline list filters by status
    Given I have a pipeline property
    When I visit the pipeline list with status ACTIVE
    Then I should see my pipeline property in the list

  Scenario: Pipeline detail shows property and action buttons
    Given I have a pipeline property
    When I view the pipeline detail page
    Then I should see the property address
    And I should see action buttons including "Add Offer" and "Due Diligence"

  Scenario: Non-owners get 404 on pipeline detail
    Given I have a pipeline property
    When another user views the pipeline detail page
    Then they should get a 404 response

  Scenario: Screening settings saves criteria
    When I visit the screening settings page
    And I set minimum beds to 2 and maximum price to $400,000
    Then the criteria should be saved

  Scenario: Saving screening criteria re-screens pipeline properties
    Given I have a pipeline property at DISCOVERED stage
    When I update the screening criteria
    Then the property should be re-screened

  Scenario: Offer form creates an offer record
    Given I have a pipeline property
    When I submit an offer for $240,000 on the property
    Then an offer record should exist for the property

  Scenario: DD checklist saves and no-go kills property
    Given I have a pipeline property
    When I save the due diligence checklist with a "no_go" decision
    Then the property should be killed with the reason recorded

  Scenario: Closing converts pipeline property to portfolio property
    Given I have a pipeline property at CLOSING stage
    When I submit the closing form
    Then a Property record should be created
    And the pipeline property should be marked ACQUIRED
    And I should be redirected to the portfolio dashboard

  Scenario: Leasing list shows my leasing entries
    Given I have a property in my portfolio
    When I add the property to the leasing pipeline
    Then I should see it in the leasing list

  Scenario: Leasing detail shows listing and lease sections
    Given I have a leasing pipeline entry
    When I view the leasing detail page
    Then I should see the listing details
    And I should see the stage history

  Scenario: Nav links resolve to pipeline pages
    When I check all pipeline navigation links
    Then the Screen link should resolve to /pipeline/screening/settings/
    And the My Pipeline link should resolve to /pipeline/list/
    And the Leasing Pipeline link should resolve to /leasing/
