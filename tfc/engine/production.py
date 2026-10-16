"""Production planning and execution model.

Models the bottling line using a cyclic schedule:
  - Products are scheduled in a fixed rotation every `interval_days` days.
  - Safety stock and frozen period determine when to produce more.
  - Production Interval Tool utilization = (production_hours + changeover_hours) / available_hours.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any


WEEKS_PER_ROUND = 26
DAYS_PER_WEEK = 5   # working days


@dataclass
class LineConfig:
    speed_lph: float                    # liters per hour
    shifts: int                         # number of shifts per day
    shift_hours_per_week: float         # total line hours per week (e.g., 80 for 2×8h×5d)
    changeover_same_type_h: float       # hours for changeover within 1L or PET group
    changeover_cross_type_h: float      # hours for changeover between groups
    startup_loss_pct: float             # fraction of production time lost at start
    smed_active: bool = True
    increase_speed_active: bool = True
    smed_reduction: float = 0.50        # fraction by which SMED cuts changeover time
    speed_increase_factor: float = 1.05 # speed multiplier from Increase Speed project


@dataclass
class ProductionPlan:
    interval_days: int
    frozen_period_weeks: int
    safety_stock_weeks: dict[str, float]   # product_id → weeks of cover
    product_volumes_weekly: dict[str, float]  # product_id → liters/week average


def effective_speed(config: LineConfig) -> float:
    base = config.speed_lph
    if config.increase_speed_active:
        base *= config.speed_increase_factor
    return base


def pit_utilization(
    plan: ProductionPlan,
    line: LineConfig,
    product_ids: list[str],
    product_liters_weekly: dict[str, float],
) -> dict[str, float]:
    """
    Returns a dict with:
      pit_utilization: Production Interval Tool value (production + changeovers) / available
      actual_utilization: pit + startup losses (approximate real load)
    """
    available_h_per_week = line.shift_hours_per_week
    speed = effective_speed(line)

    # Pure production hours per week
    total_liters_per_week = sum(product_liters_weekly.values())
    production_h = total_liters_per_week / speed

    # Changeovers per week
    # Each product gets one run per interval.
    # Assume products are split: 3 carton + 3 PET → at least 1 cross-type changeover per interval.
    carton = [p for p in product_ids if not p.endswith("_pet")]
    pet = [p for p in product_ids if p.endswith("_pet")]

    interval_weeks = plan.interval_days / DAYS_PER_WEEK

    # Within-group changeovers per interval (n_prods - 1 per group) + 1 cross per group boundary
    same_co_per_interval = (max(0, len(carton) - 1) + max(0, len(pet) - 1))
    cross_co_per_interval = 2 if (carton and pet) else 0  # carton→PET and PET→carton

    co_same_h = line.changeover_same_type_h
    co_cross_h = line.changeover_cross_type_h
    if line.smed_active:
        co_same_h *= (1 - line.smed_reduction)
        co_cross_h *= (1 - line.smed_reduction)

    changeover_h_per_interval = (
        same_co_per_interval * co_same_h + cross_co_per_interval * co_cross_h
    )
    changeover_h_per_week = changeover_h_per_interval / interval_weeks

    pit = (production_h + changeover_h_per_week) / available_h_per_week
    startup_h_per_week = production_h * line.startup_loss_pct
    actual = (production_h + changeover_h_per_week + startup_h_per_week) / available_h_per_week

    return {
        "pit_utilization": pit,
        "actual_utilization": actual,
        "production_h_per_week": production_h,
        "changeover_h_per_week": changeover_h_per_week,
        "startup_h_per_week": startup_h_per_week,
        "available_h_per_week": available_h_per_week,
        "is_feasible": pit <= 1.0,
        "pit_over_80pct": pit > 0.80,
    }


def compute_safety_stock_units(
    plan: ProductionPlan,
    demand_weekly: dict[str, float],
) -> dict[str, float]:
    """Safety stock in units for each product."""
    return {
        pid: demand_weekly[pid] * plan.safety_stock_weeks.get(pid, 2.0)
        for pid in demand_weekly
    }


def simulate_production_week(
    week: int,
    inventory_fg: dict[str, float],  # current FG inventory in units
    demand_weekly: dict[str, float],  # average weekly demand (deterministic forecast)
    plan: ProductionPlan,
    line: LineConfig,
    product_ids: list[str],
) -> dict[str, float]:
    """
    Returns production quantities (units) for each product this week.
    Uses a simplified MRP: produce when inventory falls below reorder point.
    Lot size = demand × interval days / 7 (one production run per interval).
    """
    produced: dict[str, float] = {pid: 0.0 for pid in product_ids}

    speed = effective_speed(line)
    max_liters_per_week = speed * line.shift_hours_per_week

    # For each product: produce one run per interval
    interval_weeks = plan.interval_days / DAYS_PER_WEEK
    for pid in product_ids:
        # Schedule one production run every interval_weeks
        if week % max(1, round(interval_weeks)) == (hash(pid) % max(1, round(interval_weeks))):
            # Produce enough for one interval + safety stock
            target_stock = demand_weekly[pid] * (interval_weeks + plan.safety_stock_weeks.get(pid, 2.0))
            shortfall = max(0.0, target_stock - inventory_fg.get(pid, 0.0))
            # Minimum: one interval's demand
            min_lot = demand_weekly[pid] * interval_weeks
            qty = max(min_lot, shortfall)
            produced[pid] = qty

    return produced


def operator_cost(line: LineConfig, ops_data: dict[str, Any]) -> float:
    """Annual bottling operator cost."""
    operators_total = ops_data["operators_per_shift"] * line.shifts
    return operators_total * ops_data["operator_cost_per_year"]


def bottling_flexible_labour_cost(
    actual_utilization: float,
    base_utilization: float,
    base_flexible_r2: float,
) -> float:
    """
    Approximate flexible labour cost: scales with how much actual utilization
    exceeds the base (R2) value.
    """
    ratio = actual_utilization / max(0.01, base_utilization)
    return base_flexible_r2 * ratio
