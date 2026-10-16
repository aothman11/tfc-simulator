"""Financial model — P&L and ROI calculation.

Produces a P&L matching the real game's line structure (section 3.9).
All cost inputs come from other engine modules; this module only assembles them.
"""
from __future__ import annotations
from dataclasses import dataclass, field


WEEKS_PER_ROUND = 26
INTEREST_RATE_PER_ROUND = 0.075


@dataclass
class PLResult:
    """P&L matching game line structure."""
    # Revenue
    contracted_revenue: float = 0.0
    bonus_penalty: float = 0.0

    # Cost of goods
    material_purchases: float = 0.0
    transport: float = 0.0
    supplier_admin: float = 0.0

    # Operations
    bottling_permanent: float = 0.0
    bottling_flexible: float = 0.0
    mixing: float = 0.0
    rm_locations: float = 0.0
    rm_overflow: float = 0.0
    rm_fte: float = 0.0
    fg_locations: float = 0.0
    fg_overflow: float = 0.0
    fg_fte: float = 0.0
    scrap: float = 0.0
    risk: float = 0.0
    projects: float = 0.0
    warehouse_misc: float = 0.0   # inbound flex, RM inspection, outbound flex, outbound admin

    # Distribution
    distribution: float = 0.0

    # Interest (net; negative = net income)
    interest_net: float = 0.0

    # VMI fees
    vmi_fees_suppliers: float = 0.0
    vmi_fees_customers: float = 0.0

    # Outsourcing (FG warehouse, if applicable)
    outsourcing_fg: float = 0.0

    # Overhead
    energy_overhead: float = 0.0
    water_overhead: float = 0.0
    tank_yard: float = 0.0
    stock_interest_inventory: float = 0.0
    overhead_other: float = 0.0

    # Investment components
    equipment_investment: float = 0.0
    working_capital: float = 0.0
    inflate_pet_investment: float = 0.0
    inflate_pet_depreciation: float = 0.0

    # Unverified flags
    uses_unverified: list[str] = field(default_factory=list)

    @property
    def realized_revenue(self) -> float:
        return self.contracted_revenue + self.bonus_penalty

    @property
    def cogs(self) -> float:
        return self.material_purchases + self.transport + self.supplier_admin

    @property
    def operations_cost(self) -> float:
        return (self.bottling_permanent + self.bottling_flexible + self.mixing
                + self.rm_locations + self.rm_overflow + self.rm_fte
                + self.fg_locations + self.fg_overflow + self.fg_fte
                + self.scrap + self.risk + self.projects + self.warehouse_misc
                + self.outsourcing_fg)

    @property
    def total_cost(self) -> float:
        return (self.cogs + self.operations_cost + self.distribution
                + self.interest_net + self.vmi_fees_suppliers + self.vmi_fees_customers
                + self.inflate_pet_depreciation + self.overhead_other
                + self.energy_overhead + self.water_overhead
                + self.tank_yard + self.stock_interest_inventory)

    @property
    def operating_profit(self) -> float:
        return self.realized_revenue - self.total_cost

    @property
    def investment(self) -> float:
        return self.equipment_investment + self.working_capital + self.inflate_pet_investment

    @property
    def roi(self) -> float:
        if self.investment > 0:
            return self.operating_profit / self.investment
        return 0.0

    def as_dict(self) -> dict:
        d = {
            "realized_revenue": self.realized_revenue,
            "contracted_revenue": self.contracted_revenue,
            "bonus_penalty": self.bonus_penalty,
            "material_purchases": self.material_purchases,
            "transport": self.transport,
            "supplier_admin": self.supplier_admin,
            "cogs": self.cogs,
            "bottling_permanent": self.bottling_permanent,
            "bottling_flexible": self.bottling_flexible,
            "mixing": self.mixing,
            "rm_locations": self.rm_locations,
            "rm_overflow": self.rm_overflow,
            "rm_fte": self.rm_fte,
            "fg_locations": self.fg_locations,
            "fg_overflow": self.fg_overflow,
            "fg_fte": self.fg_fte,
            "scrap": self.scrap,
            "risk": self.risk,
            "projects": self.projects,
            "warehouse_misc": self.warehouse_misc,
            "outsourcing_fg": self.outsourcing_fg,
            "operations_cost": self.operations_cost,
            "distribution": self.distribution,
            "interest_net": self.interest_net,
            "vmi_fees_suppliers": self.vmi_fees_suppliers,
            "vmi_fees_customers": self.vmi_fees_customers,
            "inflate_pet_depreciation": self.inflate_pet_depreciation,
            "energy_overhead": self.energy_overhead,
            "water_overhead": self.water_overhead,
            "tank_yard": self.tank_yard,
            "stock_interest_inventory": self.stock_interest_inventory,
            "overhead_other": self.overhead_other,
            "total_cost": self.total_cost,
            "operating_profit": self.operating_profit,
            "equipment_investment": self.equipment_investment,
            "working_capital": self.working_capital,
            "inflate_pet_investment": self.inflate_pet_investment,
            "investment": self.investment,
            "roi": self.roi,
            "uses_unverified": self.uses_unverified,
        }
        return d


def compute_distribution_cost(
    total_pallets_dispatched: float,
    cost_per_pallet: float = 31.0,
) -> float:
    return total_pallets_dispatched * cost_per_pallet


def compute_interest(
    working_capital_net: float,
    rate: float = INTEREST_RATE_PER_ROUND,
) -> float:
    """Interest charged on net working capital. Negative = net income."""
    return working_capital_net * rate


def compute_equipment_investment(
    bottling_investment: float,
    mixer_investment: float,
    other_equipment: float = 0.0,
) -> float:
    return bottling_investment + mixer_investment + other_equipment


def compute_working_capital(
    total_purchases: float,
    total_revenue: float,
    supplier_term_weeks: float,
    customer_term_weeks: float,
    inventory_value: float = 0.0,    # RM + WIP + FG at cost
) -> float:
    """
    Working capital = AR + inventory − AP
    AR = revenue / 26 × customer_term
    AP = purchases / 26 × supplier_term
    """
    ar = total_revenue / WEEKS_PER_ROUND * customer_term_weeks
    ap = total_purchases / WEEKS_PER_ROUND * supplier_term_weeks
    return ar + inventory_value - ap


def compute_mixing_cost(
    volume_index: float,
    fixed: float = 31000.0,
    variable_r2: float = 151000.0,
) -> float:
    """Mixing cost scales variable component with volume."""
    return fixed + variable_r2 * volume_index


def compute_rm_inspection_cost(n_suppliers: int, active: bool = True) -> float:
    """Approx €3K per round when inspection active for all suppliers."""
    if not active:
        return 0.0
    return n_suppliers * 600.0  # ~€600/supplier/round ≈ €3K total


def compute_pallets_dispatched(
    units_by_product: dict[str, float],
    units_per_pallet: dict[str, int],
) -> float:
    total = 0.0
    for pid, units in units_by_product.items():
        pu = units_per_pallet.get(pid, 600)
        total += units / pu
    return total
