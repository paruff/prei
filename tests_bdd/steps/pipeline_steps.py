"""Step definitions for pipeline.feature."""

import pytest
from pytest_bdd import given, then, when

from prei.pipeline.handlers.discovery import DiscoverySanitizer
from prei.pipeline.handlers.discovery_processor import DiscoveryProcessor
from prei.pipeline.handlers.screening import (
    ScreeningThresholds,
    evaluate_screening_stage,
)
from prei.pipeline.handlers.underwriting import solve_underwriting, UnderwritingInput
from prei.pipeline.handlers.batch_screening import BatchScreeningProcessor
from prei.pipeline.engine import InMemoryAssetRepository, PipelineEngine


@given(
    'a raw MLS listing with address "123 Main St., Apt #4B", price "350000", beds "3", baths "2.5"',
    target_fixture="raw_listing",
)
def given_raw_listing():
    return {
        "id": "BDD-1",
        "address": "123 Main St., Apt #4B",
        "price": "350000",
        "beds": "3",
        "baths": "2.5",
    }


@given("a discovery processor with no existing addresses", target_fixture="processor")
def given_processor():
    return DiscoveryProcessor(existing_hashes=set())


@when(
    "the listing is transformed through the discovery sanitizer",
    target_fixture="canonical",
)
def when_transform(raw_listing):
    return DiscoverySanitizer.transform_input(raw_listing, source="bdd_test")


@when(
    'I process a batch of 2 listings with the same address "100 Oak St"',
    target_fixture="batch_result",
)
def when_batch(processor):
    batch = [
        {"id": "A1", "address": "100 Oak St", "price": 200_000},
        {"id": "A2", "address": "100 Oak St", "price": 200_000},
    ]
    return processor.process_batch(batch, source_name="bdd_test")


@then("the address hash should be a 64-character SHA-256 string")
def then_hash(canonical):
    assert len(canonical.address_hash) == 64


@then("the canonical price should be 350000.0")
def then_price(canonical):
    assert canonical.price == 350_000.0


@then("the canonical beds should be 3")
def then_beds(canonical):
    assert canonical.beds == 3


@then("the canonical baths should be 2.5")
def then_baths(canonical):
    assert canonical.baths == 2.5


@then("only 1 asset should be discovered")
def then_one(batch_result):
    assert batch_result["new_assets_discovered"] == 1


@then("1 duplicate should be skipped")
def then_dup(batch_result):
    assert batch_result["duplicates_skipped"] == 1


# --- Screening ---
@given(
    "a screening threshold of 7% minimum gross yield and 15 maximum price-to-rent ratio",
    target_fixture="thresholds",
)
def given_thresholds():
    return ScreeningThresholds(
        min_gross_yield=0.07, max_price_to_rent_ratio=15.0, min_beds=2, min_baths=1
    )


@when(
    "I evaluate a property with $2,500 monthly rent and $300,000 purchase price",
    target_fixture="pass_result",
)
def when_pass(thresholds):
    return evaluate_screening_stage(
        {
            "estimated_monthly_rent": 2500,
            "purchase_price": 300_000,
            "beds": 3,
            "baths": 2,
        },
        thresholds,
    )


@when(
    "I evaluate a property with $1,200 monthly rent and $500,000 purchase price",
    target_fixture="fail_result",
)
def when_fail(thresholds):
    return evaluate_screening_stage(
        {
            "estimated_monthly_rent": 1200,
            "purchase_price": 500_000,
            "beds": 2,
            "baths": 1,
        },
        thresholds,
    )


@then("the screening should pass")
def then_pass(pass_result):
    assert pass_result[0] is True


@then("the screening should fail")
def then_fail(fail_result):
    assert fail_result[0] is False


@then('the failure reason should contain "yield"')
def then_reason(fail_result):
    assert "yield" in (fail_result[1] or "").lower()


# --- Batch ---
@given(
    "a screening threshold of 7% minimum gross yield", target_fixture="batch_thresholds"
)
def given_batch_thresholds():
    return ScreeningThresholds(
        min_gross_yield=0.07, max_price_to_rent_ratio=15.0, min_beds=1, min_baths=1
    )


@given("a batch of 4 properties: 2 passing and 2 failing", target_fixture="mixed_batch")
def given_mixed_batch():
    return [
        {
            "asset_id": "P1",
            "address": "Pass 1",
            "estimated_monthly_rent": 2500,
            "purchase_price": 300_000,
            "beds": 2,
            "baths": 1,
        },
        {
            "asset_id": "P2",
            "address": "Pass 2",
            "estimated_monthly_rent": 2000,
            "purchase_price": 250_000,
            "beds": 2,
            "baths": 1,
        },
        {
            "asset_id": "F1",
            "address": "Fail 1",
            "estimated_monthly_rent": 1000,
            "purchase_price": 500_000,
            "beds": 1,
            "baths": 1,
        },
        {
            "asset_id": "F2",
            "address": "Fail 2",
            "estimated_monthly_rent": 800,
            "purchase_price": 400_000,
            "beds": 1,
            "baths": 1,
        },
    ]


@when("I run the batch screening processor", target_fixture="batch_result2")
def when_batch_process(mixed_batch, batch_thresholds):
    engine = PipelineEngine(repository=InMemoryAssetRepository())
    return BatchScreeningProcessor(engine, batch_thresholds).process(mixed_batch)


@then("the result should show 4 processed")
def then_processed(batch_result2):
    assert batch_result2["processed"] == 4


@then("2 advanced to underwriting")
def then_advanced(batch_result2):
    assert batch_result2["advanced"] == 2


@then("2 killed")
def then_killed(batch_result2):
    assert batch_result2["killed"] == 2


# --- Underwriting ---
@given(
    "a property with $2,500 monthly rent and $300,000 purchase price",
    target_fixture="uw_input",
)
def given_uw():
    return UnderwritingInput(
        purchase_price=300_000,
        estimated_rent=2500,
        property_tax_annual=3600,
        insurance_annual=1200,
        hoa_annual=600,
    )


@given("annual property taxes of $3,600 and insurance of $1,200")
def given_taxes_insurance():
    pass  # already covered in the above step


@when(
    "I run the underwriting solver with 8% target cap rate", target_fixture="uw_result"
)
def when_uw(uw_input):
    return solve_underwriting(uw_input, target_cap_rate=0.08)


@then("the NOI should be greater than $15,000")
def then_noi(uw_result):
    assert uw_result.noi > 15_000


@then("the cap rate should be approximately 5.94%")
def then_cap(uw_result):
    assert uw_result.cap_rate == pytest.approx(0.0594, rel=1e-3)


@then("the MAO should be approximately $222,750")
def then_mao(uw_result):
    assert uw_result.mao == pytest.approx(222_750, rel=1e-3)
