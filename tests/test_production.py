"""Tests for production model."""
import pytest
from tfc.engine.production import (
    LineConfig, ProductionPlan, pit_utilization, effective_speed
)

BASE_LINE = LineConfig(
    speed_lph=3100,
    shifts=2,
    shift_hours_per_week=80,
    changeover_same_type_h=2.0,
    changeover_cross_type_h=4.0,
    startup_loss_pct=0.10,
    smed_active=True,
    increase_speed_active=True,
    smed_reduction=0.50,
    speed_increase_factor=1.05,
)

PRODUCT_IDS = ["orange_1l", "c_power_1l", "mango_1l", "orange_pet", "c_power_pet", "mango_pet"]

R2_LITERS_WEEKLY = {
    "orange_1l": 70112 * 1.0,
    "c_power_1l": 11862 * 1.0,
    "mango_1l": 44009 * 1.0,
    "orange_pet": 119206 * 0.3,
    "c_power_pet": 17900 * 0.3,
    "mango_pet": 51600 * 0.3,
}


def test_pit_near_77pct():
    """Calibration: R2 PIT utilization should be close to 77%."""
    plan = ProductionPlan(
        interval_days=10,
        frozen_period_weeks=2,
        safety_stock_weeks={"orange_1l": 2.3, "c_power_1l": 2.5},
        product_volumes_weekly=R2_LITERS_WEEKLY,
    )
    result = pit_utilization(plan, BASE_LINE, PRODUCT_IDS, R2_LITERS_WEEKLY)
    pit = result["pit_utilization"]
    assert 0.70 < pit < 0.85, f"PIT {pit:.2%} not in expected range 70–85%"
    # Should be close to 77%
    assert abs(pit - 0.77) < 0.06, f"PIT {pit:.2%} too far from ~77%"


def test_pit_feasible():
    result = pit_utilization(
        ProductionPlan(10, 2, {}, R2_LITERS_WEEKLY),
        BASE_LINE, PRODUCT_IDS, R2_LITERS_WEEKLY
    )
    assert result["is_feasible"], "R2 line should be feasible"


def test_actual_utilization_higher():
    """Actual utilization should be higher than PIT (includes startup losses)."""
    result = pit_utilization(
        ProductionPlan(10, 2, {}, R2_LITERS_WEEKLY),
        BASE_LINE, PRODUCT_IDS, R2_LITERS_WEEKLY
    )
    assert result["actual_utilization"] > result["pit_utilization"]


def test_smed_reduces_changeover():
    """SMED should lower PIT compared to no SMED."""
    line_smed = LineConfig(
        speed_lph=3100, shifts=2, shift_hours_per_week=80,
        changeover_same_type_h=2.0, changeover_cross_type_h=4.0,
        startup_loss_pct=0.10, smed_active=True, smed_reduction=0.50,
        increase_speed_active=False, speed_increase_factor=1.0,
    )
    line_no_smed = LineConfig(
        speed_lph=3100, shifts=2, shift_hours_per_week=80,
        changeover_same_type_h=2.0, changeover_cross_type_h=4.0,
        startup_loss_pct=0.10, smed_active=False, smed_reduction=0.50,
        increase_speed_active=False, speed_increase_factor=1.0,
    )
    plan = ProductionPlan(10, 2, {}, R2_LITERS_WEEKLY)
    r_smed = pit_utilization(plan, line_smed, PRODUCT_IDS, R2_LITERS_WEEKLY)
    r_no = pit_utilization(plan, line_no_smed, PRODUCT_IDS, R2_LITERS_WEEKLY)
    assert r_smed["pit_utilization"] < r_no["pit_utilization"]


def test_effective_speed_increases():
    """Increase speed project raises effective speed."""
    speed_base = effective_speed(LineConfig(
        speed_lph=3100, shifts=2, shift_hours_per_week=80,
        changeover_same_type_h=2, changeover_cross_type_h=4,
        startup_loss_pct=0.1, smed_active=False, increase_speed_active=False,
        smed_reduction=0.5, speed_increase_factor=1.05,
    ))
    speed_fast = effective_speed(LineConfig(
        speed_lph=3100, shifts=2, shift_hours_per_week=80,
        changeover_same_type_h=2, changeover_cross_type_h=4,
        startup_loss_pct=0.1, smed_active=False, increase_speed_active=True,
        smed_reduction=0.5, speed_increase_factor=1.05,
    ))
    assert speed_fast > speed_base


def test_infeasible_line():
    """A very small available_h should produce infeasible."""
    tiny_line = LineConfig(
        speed_lph=3100, shifts=1, shift_hours_per_week=20,
        changeover_same_type_h=2.0, changeover_cross_type_h=4.0,
        startup_loss_pct=0.10, smed_active=True, increase_speed_active=True,
        smed_reduction=0.5, speed_increase_factor=1.05,
    )
    result = pit_utilization(
        ProductionPlan(10, 2, {}, R2_LITERS_WEEKLY),
        tiny_line, PRODUCT_IDS, R2_LITERS_WEEKLY
    )
    assert not result["is_feasible"]
