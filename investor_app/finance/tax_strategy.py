"""Tax Strategy Module for Real Estate Investment Analysis.

Implements:
1. QBI (Qualified Business Income) deduction - 20% deduction for qualified RE income
2. Passive Activity Loss (PAL) rules - $25k allowance phased out $100k-$150k AGI
3. 1031 Exchange analysis - defer capital gains by reinvesting in like-kind property

References:
- IRC Section 199A - QBI Deduction
- IRC Section 469 - Passive Activity Loss Rules
- IRC Section 1031 - Like-Kind Exchanges
"""

from __future__ import annotations

from decimal import Decimal

from investor_app.finance.utils import to_decimal

# ── Constants ─────────────────────────────────────────────────────────────────

QBI_DEDUCTION_RATE = Decimal("0.20")  # 20% QBI deduction rate
PAL_FULL_ALLOWANCE = Decimal("25000")  # Maximum $25k PAL deduction
PAL_PHASEOUT_START = Decimal("100000")  # AGI threshold for phase-out
PAL_PHASEOUT_END = Decimal("150000")  # AGI threshold for full phase-out


# ── QBI Deduction ─────────────────────────────────────────────────────────────


def calculate_qbi_deduction(
    qualified_business_income: Decimal,
    w2_wages: Decimal,
    qbi_adjusted_basis: Decimal,
    taxable_income: Decimal = Decimal("0"),
) -> Decimal:
    """Calculate Qualified Business Income (QBI) deduction under IRC Section 199A.

    The QBI deduction is generally 20% of qualified business income, subject to
    limitations for high-income taxpayers (W-2 wage limit, property basis limit).

    Args:
        qualified_business_income: Net qualified business income from the property.
        w2_wages: Total W-2 wages paid by the business (for wage limitation).
        qbi_adjusted_basis: Unadjusted basis of qualified property (for basis limitation).
        taxable_income: Taxable income for determining phase-out (default 0).

    Returns:
        QBI deduction amount as Decimal.
    """
    qbi = to_decimal(qualified_business_income)
    wages = to_decimal(w2_wages)
    basis = to_decimal(qbi_adjusted_basis)
    income = to_decimal(taxable_income)

    # Base QBI deduction: 20% of qualified business income
    base_deduction = qbi * QBI_DEDUCTION_RATE

    # For high-income taxpayers, apply W-2 wage and property limitations
    # Phase-out begins at $164,900 for single filers (2024)
    # Simplified: if taxable income is above threshold, apply limitations
    phaseout_threshold = Decimal("164900")

    if income > phaseout_threshold:
        # W-2 wage limitation: 50% of W-2 wages
        wage_limit = wages * Decimal("0.50")

        # Qualified property limitation: 2.5% of QBI adjusted basis
        property_limit = basis * Decimal("0.025")

        # Use the greater of wage limit or property limit
        limitation = max(wage_limit, property_limit)

        # QBI deduction is limited to the lesser of base deduction or limitation
        return min(base_deduction, limitation).quantize(Decimal("0.01"))

    # Below phase-out: full 20% deduction
    return base_deduction.quantize(Decimal("0.01"))


# ── Passive Activity Loss (PAL) Rules ────────────────────────────────────────


def calculate_pal_phase_out(modified_agi: Decimal) -> Decimal:
    """Calculate PAL phase-out percentage based on Modified AGI.

    The $25,000 rental loss allowance phases out linearly between
    $100,000 and $150,000 of Modified Adjusted Gross Income (MAGI).

    Args:
        modified_agi: Modified Adjusted Gross Income.

    Returns:
        Phase-out percentage as Decimal (1.0 = no reduction, 0.0 = fully phased out)
    """
    magi = to_decimal(modified_agi)

    if magi <= PAL_PHASEOUT_START:
        return Decimal("1")
    elif magi >= PAL_PHASEOUT_END:
        return Decimal("0")
    else:
        # Linear phase-out: (150000 - magi) / 50000
        reduction = (PAL_PHASEOUT_END - magi) / (PAL_PHASEOUT_END - PAL_PHASEOUT_START)
        return reduction.quantize(Decimal("0.01"))


def calculate_pal_allowance(
    active_participation: Decimal,
    modified_agi: Decimal,
    rental_losses: Decimal,
) -> Decimal:
    """Calculate Passive Activity Loss (PAL) deduction allowance.

    Under IRC Section 469, rental real estate losses can offset up to $25,000
    of other income if the taxpayer actively participates, with phase-out
    for incomes between $100k-$150k MAGI.

    Args:
        active_participation: 1.0 if active participation, 0.0 otherwise.
        modified_agi: Modified Adjusted Gross Income.
        rental_losses: Passive rental losses for the year.

    Returns:
        PAL deduction amount (capped at $25,000 and actual losses).
    """
    participation = to_decimal(active_participation)
    losses = to_decimal(rental_losses)

    # No deduction without active participation
    if participation <= 0:
        return Decimal("0")

    # Calculate phase-out adjusted allowance
    phase_out = calculate_pal_phase_out(to_decimal(modified_agi))
    allowance = PAL_FULL_ALLOWANCE * phase_out

    # Capped at actual losses
    return min(allowance, losses).quantize(Decimal("0.01"))


# ── 1031 Exchange Analysis ────────────────────────────────────────────────────


def calculate_1031_deferral_ratio(
    sale_price: Decimal,
    replacement_price: Decimal,
    selling_costs: Decimal,
) -> Decimal:
    """Calculate the ratio of gain that can be deferred in a 1031 exchange.

    Deferral ratio = replacement_price / (sale_price - selling_costs)
    Capped at 1.0 when replacement price >= net sale price (100% deferral).

    Args:
        sale_price: Gross sale price of relinquished property.
        replacement_price: Purchase price of replacement property.
        selling_costs: Costs to sell (agent commission, closing costs).

    Returns:
        Deferral ratio as Decimal (1.0 = 100% deferral, <1.0 = partial deferral).
    """
    sp = to_decimal(sale_price)
    rp = to_decimal(replacement_price)
    sc = to_decimal(selling_costs)

    net_proceeds = sp - sc
    if net_proceeds <= 0:
        return Decimal("0")

    ratio = rp / net_proceeds

    # Cap at 1.0 for 100% deferral
    return min(ratio, Decimal("1")).quantize(Decimal("0.0001"))


def calculate_1031_exchange(
    sale_price: Decimal,
    original_cost_basis: Decimal,
    accumulated_depreciation: Decimal,
    replacement_price: Decimal,
    selling_costs: Decimal,
) -> dict[str, Decimal]:
    """Calculate 1031 exchange outcomes and deferral.

    In a 1031 exchange, capital gains tax is deferred by reinvesting
    sale proceeds into a like-kind property of equal or greater value.

    Args:
        sale_price: Gross sale price of relinquished property.
        original_cost_basis: Original purchase price of relinquished property.
        accumulated_depreciation: Total depreciation taken.
        replacement_price: Purchase price of replacement property.
        selling_costs: Costs to sell (agent commission, closing costs).

    Returns:
        Dictionary with exchange metrics:
        - deferred_gain: Portion of gain deferred
        - boot_received: Taxable boot (if replacement price < net sale price)
        - adjusted_basis: New basis in replacement property
        - depreciation_recapture: Depreciation recapture on boot
    """
    sp = to_decimal(sale_price)
    cb = to_decimal(original_cost_basis)
    ad = to_decimal(accumulated_depreciation)
    rp = to_decimal(replacement_price)
    sc = to_decimal(selling_costs)

    # Calculate net sale proceeds
    net_proceeds = sp - sc

    # Calculate realized gain
    realized_gain = sp - cb

    # Calculate depreciation recapture (for reporting purposes)
    if realized_gain > ad:
        depreciation_recapture = ad
    else:
        depreciation_recapture = realized_gain

    # In a 1031 exchange, depreciation recapture is DEFERRED (not immediately taxed)
    # Calculate boot (taxable portion if replacement price < net proceeds)
    if rp >= net_proceeds:
        # Full deferral - no boot, entire realized gain is deferred
        boot_received = Decimal("0")
        deferred_gain = realized_gain  # Full gain deferred
    else:
        # Partial deferral - boot = net_proceeds - replacement_price
        boot_received = net_proceeds - rp
        deferred_gain = realized_gain - boot_received

    # Ensure deferred_gain is not negative
    deferred_gain = max(deferred_gain, Decimal("0"))

    # Calculate adjusted basis for replacement property
    adjusted_basis = rp + deferred_gain

    return {
        "deferred_gain": deferred_gain.quantize(Decimal("0.01")),
        "boot_received": boot_received.quantize(Decimal("0.01")),
        "adjusted_basis": adjusted_basis.quantize(Decimal("0.01")),
        "depreciation_recapture": depreciation_recapture.quantize(Decimal("0.01")),
    }


# ── Combined Tax Benefit Calculator ────────────────────────────────────────────


def calculate_total_tax_benefit(
    qbi_income: Decimal,
    rental_losses: Decimal,
    modified_agi: Decimal,
    marginal_tax_rate: Decimal,
) -> Decimal:
    """Calculate total annual tax benefit from QBI and PAL.

    Combines QBI deduction and Passive Activity Loss allowance into
    a single tax benefit amount.

    Args:
        qbi_income: Net qualified business income from real estate activities.
        rental_losses: Passive rental losses for the year.
        modified_agi: Modified Adjusted Gross Income.
        marginal_tax_rate: Marginal income tax rate as decimal (e.g., 0.24 for 24%).

    Returns:
        Total tax benefit as Decimal.
    """
    qbi = to_decimal(qbi_income)
    losses = to_decimal(rental_losses)
    agi = to_decimal(modified_agi)
    rate = to_decimal(marginal_tax_rate)

    # Calculate QBI deduction (assume $0 W-2 wages and $0 basis for simplicity)
    qbi_deduction = calculate_qbi_deduction(
        qualified_business_income=qbi,
        w2_wages=Decimal("0"),
        qbi_adjusted_basis=Decimal("0"),
        taxable_income=agi,
    )

    # Calculate PAL allowance
    pal_allowance = calculate_pal_allowance(
        active_participation=Decimal("1"),  # Assume active participation
        modified_agi=agi,
        rental_losses=losses,
    )

    # Total deductions
    total_deductions = qbi_deduction + pal_allowance

    # Tax benefit
    tax_benefit = total_deductions * rate

    return tax_benefit.quantize(Decimal("0.01"))
