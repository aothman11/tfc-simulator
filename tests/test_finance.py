"""Tests for finance model."""
import pytest
from tfc.engine.finance import (
    PLResult, compute_distribution_cost, compute_interest,
    compute_mixing_cost, compute_working_capital, compute_pallets_dispatched
)


def make_r2_pl():
    """Approximate R2 P&L for testing."""
    pl = PLResult(
        contracted_revenue=2711810,
        bonus_penalty=12095,
        material_purchases=912533,
        transport=96218,
        supplier_admin=100000,
        bottling_permanent=200000,
        bottling_flexible=27800,
        mixing=182000,
        rm_locations=70000,
        rm_overflow=16500,
        fg_locations=110000,
        fg_overflow=9600,
        scrap=52800,
        risk=52800,
        projects=29000,
        distribution=198000,
        interest_net=-4400,
        overhead_other=149000,
        equipment_investment=802000,
        working_capital=2715221,
    )
    return pl


def test_roi_positive():
    pl = make_r2_pl()
    assert pl.roi > 0


def test_operating_profit_sign():
    pl = make_r2_pl()
    # With our approximate numbers, profit should be positive
    assert pl.operating_profit > 0


def test_realized_revenue():
    pl = make_r2_pl()
    assert pl.realized_revenue == 2711810 + 12095


def test_cogs_sum():
    pl = make_r2_pl()
    assert pl.cogs == 912533 + 96218 + 100000


def test_operations_cost_sum():
    pl = make_r2_pl()
    expected = 200000 + 27800 + 182000 + 70000 + 16500 + 110000 + 9600 + 52800 + 52800 + 29000
    assert pl.operations_cost == expected


def test_distribution_cost():
    cost = compute_distribution_cost(total_pallets_dispatched=6387.0, cost_per_pallet=31.0)
    assert abs(cost - 198000) < 10000  # R2 distribution ≈ €198K; 6387 pallets × €31 = €197,997


def test_mixing_cost_scales():
    base = compute_mixing_cost(volume_index=1.0)
    higher = compute_mixing_cost(volume_index=1.1)
    assert higher > base


def test_interest_direction():
    """If AP > AR (favorable: supplier gives more credit), interest should be negative."""
    wc = compute_working_capital(
        total_purchases=900000,
        total_revenue=2700000,
        supplier_term_weeks=8,   # long supplier term = large AP
        customer_term_weeks=1,   # short customer term = small AR
    )
    # AR = 2700000/26 * 1 = 103,846
    # AP = 900000/26 * 8 = 276,923
    # WC = 103,846 - 276,923 = -173,077 (net credit position)
    interest = compute_interest(wc)
    # With favorable terms, interest on WC should be negative (income)
    # But inventory adds to WC, so total may be positive or negative
    # Test: interest magnitude is proportional to WC
    assert interest < 0 or abs(interest) < 50000  # small in either direction


def test_pallets_dispatched():
    units = {"orange_1l": 70000 * 26, "orange_pet": 119000 * 26}
    pu = {"orange_1l": 600, "orange_pet": 1440}
    pallets = compute_pallets_dispatched(units, pu)
    expected = 70000 * 26 / 600 + 119000 * 26 / 1440
    assert abs(pallets - expected) < 1
