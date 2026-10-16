"""Customer service and contract index model.

Computes contract indices, service levels, bonus/penalty, and revenue.
All magnitude parameters sourced from assumptions.yaml (unverified unless stated).
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass


WEEKS_PER_ROUND = 26


@dataclass
class CustomerConfig:
    customer_id: str
    contract_index_base: float      # R2 baseline index
    service_promise: float          # e.g. 0.94
    requested_shelf_life_pct: float # e.g. 0.78
    payment_term_weeks: int
    trade_unit: str                 # "box", "pallet_layer", "pallet"
    order_deadline: str             # "HH:MM"
    promo_pressure: str
    promo_horizon: str
    vmi_active: bool = False
    contracted_revenue_r2: float = 0.0

    # Index adjustment parameters (from assumptions; magnitudes unverified)
    vmi_delta: float = 0.0                      # loaded per customer
    payment_term_delta_per_week: float = -0.0015
    trade_unit_box_vs_layer: float = 0.003
    trade_unit_layer_vs_pallet: float = 0.002
    promo_pressure_delta_per_step: float = 0.004  # each step down raises index
    promo_horizon_long_vs_short: float = -0.002
    shelf_life_delta_per_pct: float = 0.0003
    deadline_delta_per_hour_earlier: float = -0.0005


# R2 reference settings for index delta computation
_R2_DEFAULTS = {
    "fg":       {"payment_term": 1, "trade_unit": "pallet_layer", "deadline_h": 20,
                 "promo_pressure": "heavy", "promo_horizon": "short", "shelf_life": 0.78},
    "land":     {"payment_term": 1, "trade_unit": "pallet_layer", "deadline_h": 17,
                 "promo_pressure": "middle", "promo_horizon": "short", "shelf_life": 0.78},
    "dominicks":{"payment_term": 1, "trade_unit": "box", "deadline_h": 20,
                 "promo_pressure": "none", "promo_horizon": "short", "shelf_life": 0.78},
}

_PROMO_PRESSURE_ORDER = {"none": 0, "low": 1, "middle": 2, "heavy": 3}
_TRADE_UNIT_ORDER = {"pallet": 0, "pallet_layer": 1, "box": 2}


def _deadline_hour(s: str) -> int:
    return int(s.split(":")[0])


def compute_contract_index(config: CustomerConfig) -> float:
    """
    Compute the contract index from R2 baseline plus deltas for any setting changes.
    Uses an additive model; magnitudes from assumptions.yaml (unverified).
    """
    idx = config.contract_index_base

    ref = _R2_DEFAULTS.get(config.customer_id, {})
    if not ref:
        return idx  # unknown customer; use base

    # Payment term delta
    ref_pt = ref.get("payment_term", 1)
    pt_diff = config.payment_term_weeks - ref_pt
    idx += pt_diff * config.payment_term_delta_per_week

    # Trade unit delta
    ref_tu = ref.get("trade_unit", "pallet_layer")
    cur_rank = _TRADE_UNIT_ORDER.get(config.trade_unit, 1)
    ref_rank = _TRADE_UNIT_ORDER.get(ref_tu, 1)
    if cur_rank > ref_rank:
        # smaller unit → higher index
        idx += (cur_rank - ref_rank) * config.trade_unit_box_vs_layer
    elif cur_rank < ref_rank:
        # larger unit → lower index
        idx -= (ref_rank - cur_rank) * config.trade_unit_layer_vs_pallet

    # Promotional pressure delta
    ref_pp = _PROMO_PRESSURE_ORDER.get(ref.get("promo_pressure", "heavy"), 3)
    cur_pp = _PROMO_PRESSURE_ORDER.get(config.promo_pressure, 3)
    pp_steps_down = ref_pp - cur_pp  # positive = moved to lower pressure = higher index
    idx += pp_steps_down * config.promo_pressure_delta_per_step

    # Promotion horizon delta
    if config.promo_horizon == "long" and ref.get("promo_horizon") == "short":
        idx += config.promo_horizon_long_vs_short  # negative: long horizon lowers index
    elif config.promo_horizon == "short" and ref.get("promo_horizon") == "long":
        idx -= config.promo_horizon_long_vs_short

    # Order deadline delta
    ref_dl = ref.get("deadline_h", 20)
    cur_dl = _deadline_hour(config.order_deadline)
    h_earlier = ref_dl - cur_dl  # positive = earlier deadline
    idx += h_earlier * config.deadline_delta_per_hour_earlier

    # VMI delta
    if config.vmi_active:
        idx += config.vmi_delta  # typically negative

    # Shelf life delta (relative to 78% baseline)
    sl_diff = config.requested_shelf_life_pct - ref.get("shelf_life", 0.78)
    idx += sl_diff * 100 * config.shelf_life_delta_per_pct  # per percentage point

    return idx


def contracted_revenue(
    contract_index: float,
    demand_per_product: dict[str, float],  # weekly units
    basic_price: dict[str, float],
    product_share: dict[str, float],  # fraction of each product's demand going to this customer
    n_weeks: int = WEEKS_PER_ROUND,
) -> float:
    total = 0.0
    for pid, weekly_demand in demand_per_product.items():
        share = product_share.get(pid, 1.0)
        total += weekly_demand * n_weeks * basic_price.get(pid, 0.45) * share * contract_index
    return total


def service_bonus_penalty(
    actual_service: float,
    promised_service: float,
    revenue: float,
    bonus_fraction: float = 0.0016,
    penalty_multiplier: float = 3.0,
) -> float:
    """
    Bonus if actual > promise; penalty if below.
    Returns positive for bonus, negative for penalty.
    Calibrated: R2 total €12,095 / revenue €2,723,905 ≈ 0.44%
    """
    gap = actual_service - promised_service
    if gap >= 0:
        return revenue * bonus_fraction * gap / max(0.001, 1 - promised_service)
    else:
        return revenue * bonus_fraction * penalty_multiplier * gap / max(0.001, promised_service)


def simulate_service_level(
    weekly_demands: np.ndarray,       # 26 weeks
    weekly_production: np.ndarray,    # 26 weeks FG available for dispatch
    fg_safety_stock: float,           # units
    trade_unit_size: int,             # pieces per trade unit (box=10, layer=120, pallet=600)
) -> dict[str, float]:
    """
    Simplified service level simulation.
    Returns service_units, service_lines, service_orders.
    """
    n = len(weekly_demands)
    inventory = fg_safety_stock
    units_fulfilled = 0.0
    units_demanded = 0.0
    lines_fulfilled = 0
    lines_total = 0
    orders_fulfilled = 0
    orders_total = 0

    for w in range(n):
        demand = weekly_demands[w]
        prod = weekly_production[w]
        inventory = min(inventory + prod, fg_safety_stock * 10)  # cap at 10× SS

        # Assume customer places one order per week with multiple lines
        # Lines per order ≈ trade_unit batches needed
        n_lines = max(1, int(demand / trade_unit_size))
        lines_total += n_lines
        orders_total += 1

        fulfilled = min(demand, inventory)
        inventory -= fulfilled

        units_fulfilled += fulfilled
        units_demanded += demand

        # Order-line service: each line fulfilled if the line's quantity is available
        line_qty = demand / n_lines
        lines_ok = int(fulfilled / line_qty) if line_qty > 0 else 0
        lines_fulfilled += min(lines_ok, n_lines)

        # Order service: all lines fulfilled = order fulfilled
        if lines_ok >= n_lines:
            orders_fulfilled += 1

    svc_units = units_fulfilled / max(1, units_demanded)
    svc_lines = lines_fulfilled / max(1, lines_total)
    svc_orders = orders_fulfilled / max(1, orders_total)
    return {
        "service_units": svc_units,
        "service_lines": svc_lines,
        "service_orders": svc_orders,
    }


def vmi_break_even_index(
    vmi_cost_per_round: float,
    contracted_revenue: float,
) -> float:
    """Min index the customer must reach after VMI fee for it to pay off."""
    # Without VMI: revenue = contracted_revenue
    # With VMI: revenue = contracted_revenue × (1 + delta_index) − vmi_cost
    # Break even: delta_index = vmi_cost / contracted_revenue
    return vmi_cost_per_round / contracted_revenue if contracted_revenue > 0 else 0.0
