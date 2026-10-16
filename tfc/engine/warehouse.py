"""Warehouse and inventory management model.

Tracks raw-material and finished-goods inventories week by week.
Computes overflow costs, obsolete stock, and location requirements.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field


WEEKS_PER_ROUND = 26
DAYS_PER_WEEK = 7   # calendar days (overflow charged per calendar day)


@dataclass
class WarehouseConfig:
    rm_locations: int
    fg_locations: int
    rm_perm_fte: int
    fg_perm_fte: int
    location_cost_per_round: float = 100.0
    overflow_per_pallet_per_day: float = 3.0
    fte_cost_per_round: float = 20000.0
    inflate_pet: bool = False       # reduces PET storage need by ~90%
    inflate_pet_storage_fraction: float = 0.10  # preforms take 10% space of bottles


@dataclass
class ComponentInventory:
    """Track RM inventory in pallets per component."""
    levels: dict[str, float] = field(default_factory=dict)   # pallets
    ages: dict[str, list[float]] = field(default_factory=dict)  # age in weeks per batch


@dataclass
class FGInventory:
    """Track FG inventory in units per product."""
    levels: dict[str, float] = field(default_factory=dict)   # units
    ages: dict[str, list[tuple[float, float]]] = field(default_factory=dict)  # (age_weeks, units)


def rm_pallets_needed(
    safety_stock_weeks: dict[str, float],
    lot_size_weeks: dict[str, float],
    weekly_consumption: dict[str, float],  # component_id → units/week
    pallet_units: dict[str, float],         # component_id → units per pallet
    inflate_pet: bool = False,
    inflate_pet_fraction: float = 0.10,
) -> dict[str, float]:
    """Peak RM pallet requirement per component (safety stock + half lot size)."""
    pallets: dict[str, float] = {}
    for cid, wc in weekly_consumption.items():
        ss = safety_stock_weeks.get(cid, 2.0)
        lot = lot_size_weeks.get(cid, 2.0)
        peak_units = wc * (ss + lot / 2)
        pu = pallet_units.get(cid, 1.0)
        p = peak_units / pu if pu > 0 else 0.0
        if cid == "pet" and inflate_pet:
            p *= inflate_pet_fraction
        pallets[cid] = p
    return pallets


def total_rm_pallets(pallets: dict[str, float]) -> float:
    return sum(pallets.values())


def rm_overflow_pallets(rm_pallets: float, rm_locations: int) -> float:
    return max(0.0, rm_pallets - rm_locations)


def fg_pallets_from_units(
    units: dict[str, float],
    units_per_pallet: dict[str, int],
) -> dict[str, float]:
    return {pid: units[pid] / units_per_pallet.get(pid, 600) for pid in units}


def fg_overflow_pallets(
    fg_pallet_usage: float,
    fg_locations: int,
) -> float:
    return max(0.0, fg_pallet_usage - fg_locations)


def overflow_cost_per_round(overflow_pallets_avg: float) -> float:
    """Cost = avg overflow pallets × €3/pallet/day × 7 days × 26 weeks."""
    return overflow_pallets_avg * 3.0 * DAYS_PER_WEEK * WEEKS_PER_ROUND


def location_cost(n_locations: int, cost_per_round: float = 100.0) -> float:
    return n_locations * cost_per_round


def fte_cost(n_fte: int, cost_per_round: float = 20000.0) -> float:
    return n_fte * cost_per_round


def warehouse_total_cost(config: WarehouseConfig, rm_overflow_avg: float, fg_overflow_avg: float) -> dict[str, float]:
    rm_loc = location_cost(config.rm_locations)
    fg_loc = location_cost(config.fg_locations)
    rm_overflow = overflow_cost_per_round(rm_overflow_avg)
    fg_overflow = overflow_cost_per_round(fg_overflow_avg)
    rm_fte = fte_cost(config.rm_perm_fte)
    fg_fte = fte_cost(config.fg_perm_fte)
    return {
        "rm_locations": rm_loc,
        "fg_locations": fg_loc,
        "rm_overflow": rm_overflow,
        "fg_overflow": fg_overflow,
        "rm_fte": rm_fte,
        "fg_fte": fg_fte,
        "total": rm_loc + fg_loc + rm_overflow + fg_overflow + rm_fte + fg_fte,
    }


def compute_obsoletes(
    inventory_units: dict[str, float],
    inventory_age_weeks: dict[str, float],   # average age of stock
    shelf_life_weeks: dict[str, int],
    requested_shelf_life_pct: dict[str, float],  # per customer (use max)
    basic_price: dict[str, float],
    liters_per_piece: dict[str, float],
    material_cost_per_liter: float = 0.35,   # approximate; assumption
    risk_multiplier: float = 1.0,
) -> dict[str, float]:
    """
    Compute weekly obsolete cost per product.
    Allowed age = shelf_life × (1 − max_requested_shelf_life_pct).
    Stock older than allowed is scrapped at material cost + risk cost (1× scrap).
    """
    obs: dict[str, float] = {}
    for pid in inventory_units:
        sl = shelf_life_weeks.get(pid, 20)
        max_req_sl = max(requested_shelf_life_pct.values()) if requested_shelf_life_pct else 0.78
        allowed_age = sl * (1 - max_req_sl)
        avg_age = inventory_age_weeks.get(pid, 0.0)
        if avg_age > allowed_age:
            # fraction of stock that is too old (triangular approximation)
            excess_fraction = min(1.0, (avg_age - allowed_age) / max(0.1, sl - allowed_age))
            obs_units = inventory_units[pid] * excess_fraction
            price = basic_price.get(pid, 0.45)
            scrap = obs_units * price * 0.80  # scrap at ~80% of basic price (material cost)
            risk = scrap * risk_multiplier
            obs[pid] = (scrap + risk) / WEEKS_PER_ROUND  # weekly cost
        else:
            obs[pid] = 0.0
    return obs
