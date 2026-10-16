"""Purchasing and supplier cost model.

Computes material purchase costs, transport costs, supplier administration.
Handles VMI effects on both supplier price index and stock levels.
"""
from __future__ import annotations
from dataclasses import dataclass


WEEKS_PER_ROUND = 26


@dataclass
class SupplierConfig:
    supplier_id: str
    component: str
    purchase_value_r2: float
    payment_term_weeks: int = 8
    vmi_active: bool = False
    vmi_cost_per_round: float = 2500.0
    vmi_index_delta: float = 0.0      # change to supplier index if VMI active
    supplier_index: float = 1.0       # baseline supplier price index
    transport_cost_r2: float = 0.0    # for PET
    inflate_pet: bool = False         # affects PET cost
    inflate_pet_preform_fraction: float = 0.5  # preform = 0.5× bottle price
    inflate_pet_transport_saving: float = 0.50 # fraction of transport saved
    payment_term_index_delta_per_week: float = 0.002  # extra week → +0.2% price


def effective_supplier_index(config: SupplierConfig, payment_term_weeks: int) -> float:
    """
    Effective supplier price index accounting for payment terms and VMI.
    Longer payment term (more weeks to pay) → higher price index (supplier charges more).
    """
    base = config.supplier_index
    # Payment term effect relative to baseline 8 weeks
    term_delta = (payment_term_weeks - 8) * config.payment_term_index_delta_per_week
    if config.vmi_active:
        vmi_delta = config.vmi_index_delta
    else:
        vmi_delta = 0.0
    return base + term_delta + vmi_delta


def material_cost(
    supplier: SupplierConfig,
    volume_index: float,  # current round volume / R2 volume
    payment_term_weeks: int,
) -> float:
    """
    Approximate material cost for this supplier this round.
    Scales from R2 purchase value using volume and price index.
    """
    idx = effective_supplier_index(supplier, payment_term_weeks)
    base_material = supplier.purchase_value_r2 * volume_index

    if supplier.component == "pet" and supplier.inflate_pet:
        # Preforms cost half the price of ready bottles
        base_material *= supplier.inflate_pet_preform_fraction

    return base_material * idx


def transport_cost(supplier: SupplierConfig, volume_index: float) -> float:
    """PET transport cost, reduced if inflate PET active."""
    if supplier.component != "pet":
        return 0.0
    base = supplier.transport_cost_r2 * volume_index
    if supplier.inflate_pet:
        base *= (1.0 - supplier.inflate_pet_transport_saving)
    return base


def vmi_cost(supplier: SupplierConfig) -> float:
    return supplier.vmi_cost_per_round if supplier.vmi_active else 0.0


def supplier_admin_cost(
    n_suppliers: int,
    admin_per_supplier_per_round: float = 20000.0,
) -> float:
    return n_suppliers * admin_per_supplier_per_round


def compute_all_purchases(
    suppliers: list[SupplierConfig],
    volume_index: float,
    payment_term_overrides: dict[str, int] | None = None,
) -> dict[str, float]:
    """Return a breakdown of all purchasing costs."""
    result: dict[str, float] = {
        "total_materials": 0.0,
        "total_transport": 0.0,
        "total_vmi_fees": 0.0,
        "admin": supplier_admin_cost(len(suppliers)),
        "by_supplier": {},
    }
    for s in suppliers:
        pt = (payment_term_overrides or {}).get(s.supplier_id, s.payment_term_weeks)
        mat = material_cost(s, volume_index, pt)
        trans = transport_cost(s, volume_index)
        vmi = vmi_cost(s)
        result["by_supplier"][s.supplier_id] = {
            "materials": mat,
            "transport": trans,
            "vmi_fee": vmi,
            "index": effective_supplier_index(s, pt),
        }
        result["total_materials"] += mat
        result["total_transport"] += trans
        result["total_vmi_fees"] += vmi

    return result


def compute_volume_index(
    current_demand_weekly: dict[str, float],
    r2_demand_weekly: dict[str, float],
    liters_per_piece: dict[str, float],
) -> float:
    """Total liter volume ratio: current / R2."""
    r2_vol = sum(r2_demand_weekly[p] * WEEKS_PER_ROUND * liters_per_piece.get(p, 1.0)
                 for p in r2_demand_weekly)
    cur_vol = sum(current_demand_weekly[p] * WEEKS_PER_ROUND * liters_per_piece.get(p, 1.0)
                  for p in current_demand_weekly)
    return cur_vol / r2_vol if r2_vol > 0 else 1.0


def working_capital_from_terms(
    total_purchases: float,
    total_revenue: float,
    supplier_term_weeks_avg: float,
    customer_term_weeks_avg: float,
) -> float:
    """
    Net working capital tied up due to payment terms.
    Positive = cash tied up (increases investment), negative = net benefit.
    AR = revenue / 26 × customer_term_weeks
    AP = purchases / 26 × supplier_term_weeks
    """
    ar = total_revenue / WEEKS_PER_ROUND * customer_term_weeks_avg
    ap = total_purchases / WEEKS_PER_ROUND * supplier_term_weeks_avg
    return ar - ap   # positive means AR > AP → cash tied up
