"""Main simulation orchestrator.

Runs one round (26 weeks) using all engine modules.
Returns a SimResult with financial and operational metrics.
"""
from __future__ import annotations
import math
import numpy as np
from dataclasses import dataclass, field

from tfc.engine.loader import (
    load_products, load_customers, load_suppliers,
    load_operations, load_assumptions, list_unverified
)
from tfc.engine.demand import DemandConfig, build_weekly_demand, build_weekly_forecast, compute_bias, total_promo_uplift
from tfc.engine.production import (
    LineConfig, ProductionPlan, pit_utilization, effective_speed,
    compute_safety_stock_units
)
from tfc.engine.warehouse import (
    WarehouseConfig, rm_pallets_needed, total_rm_pallets,
    rm_overflow_pallets, fg_overflow_pallets,
    warehouse_total_cost, overflow_cost_per_round
)
from tfc.engine.purchasing import (
    SupplierConfig, compute_all_purchases, compute_volume_index, working_capital_from_terms
)
from tfc.engine.customer import (
    CustomerConfig, compute_contract_index, service_bonus_penalty, simulate_service_level
)
from tfc.engine.finance import (
    PLResult, compute_distribution_cost, compute_interest,
    compute_equipment_investment, compute_working_capital,
    compute_mixing_cost, compute_pallets_dispatched
)

WEEKS_PER_ROUND = 26
DAYS_PER_WEEK = 7


@dataclass
class ScenarioParams:
    """All tunable parameters for one simulation scenario."""
    # Production
    production_interval_days: int = 10
    frozen_period_weeks: int = 2
    fg_safety_stock_weeks: dict = field(default_factory=lambda: {
        "orange_1l": 2.3, "c_power_1l": 2.5, "mango_1l": 2.2,
        "orange_pet": 2.0, "c_power_pet": 2.5, "mango_pet": 2.2
    })

    # Purchasing
    rm_safety_stock_weeks: dict = field(default_factory=lambda: {
        "pet": 1.5, "pack": 1.7, "orange": 1.9, "mango": 1.9, "vitamin_c": 4.0
    })
    rm_lot_size_weeks: dict = field(default_factory=lambda: {
        "pet": 2.0, "pack": 2.5, "orange": 2.5, "mango": 4.0, "vitamin_c": 4.0
    })
    supplier_payment_terms: dict = field(default_factory=lambda: {
        "orange": 8, "pet": 8, "pack": 8, "mango": 8, "vitamin_c": 8
    })
    supplier_vmi: dict = field(default_factory=lambda: {
        "orange": True, "pet": False, "pack": False, "mango": False, "vitamin_c": False
    })

    # Warehouses
    rm_locations: int = 700
    rm_perm_fte: int = 3
    fg_locations: int = 1100
    fg_perm_fte: int = 4
    inflate_pet: bool = False

    # Customers
    customer_payment_terms: dict = field(default_factory=lambda: {
        "fg": 1, "land": 1, "dominicks": 1
    })
    customer_vmi: dict = field(default_factory=lambda: {
        "fg": False, "land": False, "dominicks": False
    })
    promotional_pressure: dict = field(default_factory=lambda: {
        "fg": "heavy", "land": "middle", "dominicks": "none"
    })
    promotion_horizon: dict = field(default_factory=lambda: {
        "fg": "short", "land": "short", "dominicks": "short"
    })
    trade_unit: dict = field(default_factory=lambda: {
        "fg": "pallet_layer", "land": "pallet_layer", "dominicks": "box"
    })
    order_deadline: dict = field(default_factory=lambda: {
        "fg": "20:00", "land": "17:00", "dominicks": "20:00"
    })
    requested_shelf_life_pct: float = 0.78
    service_promise: float = 0.94

    # Outsourcing
    outsource_fg: str | None = None  # None, "conventional", "automated", "mcc"

    # Bottling
    bottling_line: str = "swiss_fill_2"
    shifts: int = 2

    # Forecast
    forecast_adjustments: dict = field(default_factory=lambda: {
        "orange_1l": 0.0, "c_power_1l": 0.0, "mango_1l": 0.0,
        "orange_pet": 0.0, "c_power_pet": 0.0, "mango_pet": 0.0
    })

    # Random seed
    seed: int = 42

    # Assumption overrides
    assumption_overrides: dict = field(default_factory=dict)


@dataclass
class SimResult:
    """Complete simulation result."""
    pl: PLResult
    production_pit: dict  # from pit_utilization()
    service_by_customer: dict  # customer_id → {service_units, service_lines, service_orders}
    bias_by_product: dict
    rm_overflow_avg_pallets: float
    fg_overflow_avg_pallets: float
    rm_total_pallets: float
    fg_total_pallets: float
    warnings: list[str]
    unverified_assumptions_used: list[str]

    # Convenience
    @property
    def roi(self) -> float:
        return self.pl.roi

    @property
    def operating_profit(self) -> float:
        return self.pl.operating_profit

    def summary(self) -> dict:
        return {
            "roi": self.roi,
            "operating_profit": self.operating_profit,
            "realized_revenue": self.pl.realized_revenue,
            "investment": self.pl.investment,
            "pit_utilization": self.production_pit.get("pit_utilization"),
            "actual_line_utilization": self.production_pit.get("actual_utilization"),
            "rm_overflow_pallets": self.rm_overflow_avg_pallets,
            "fg_overflow_pallets": self.fg_overflow_avg_pallets,
            "rm_total_pallets": self.rm_total_pallets,
            "service_by_customer": {
                cid: v.get("service_lines", 0) for cid, v in self.service_by_customer.items()
            },
            "bias_by_product": self.bias_by_product,
            "warnings": self.warnings,
            "unverified": self.unverified_assumptions_used,
        }


def _get_a(name: str, overrides: dict, assumptions: dict):
    if name in overrides:
        return overrides[name]
    return assumptions[name]["default"]


def run_simulation(params: ScenarioParams) -> SimResult:
    """Run one round simulation and return SimResult."""
    products_data = load_products()
    customers_data = load_customers()
    suppliers_data = load_suppliers()
    operations_data = load_operations()
    assumptions = load_assumptions()
    ov = params.assumption_overrides

    warnings: list[str] = []
    unverified_used: list[str] = []
    all_unverified = list_unverified(assumptions)

    def ga(name: str):
        val = _get_a(name, ov, assumptions)
        if name in all_unverified and name not in unverified_used:
            unverified_used.append(name)
        return val

    # ── Products ──────────────────────────────────────────────────────────────
    products = {p["id"]: p for p in products_data["products"]}
    product_ids = list(products.keys())
    basic_price = {p["id"]: p["basic_price"] for p in products_data["products"]}
    liters_per_piece = {p["id"]: p["liters_per_piece"] for p in products_data["products"]}
    units_per_pallet = {p["id"]: p["pieces_per_pallet"] for p in products_data["products"]}
    shelf_life_weeks = {p["id"]: p["shelf_life_weeks"] for p in products_data["products"]}

    # ── Demand ─────────────────────────────────────────────────────────────────
    base_demands = {p["id"]: p["demand_base_week"] for p in products_data["products"]}

    customer_products_map = {
        "fg": product_ids,
        "land": product_ids,
        "dominicks": [p for p in product_ids if "pet" in p],
    }

    demand_cfg = DemandConfig(
        base_demands=base_demands,
        forecast_adjustments=params.forecast_adjustments,
        promo_pressure=params.promotional_pressure,
        promo_horizon=params.promotion_horizon,
        vfm_customers={
            "fg": True,
            "land": True,
            "dominicks": bool(ga("dominicks_value_for_money")),
        },
        customer_products=customer_products_map,
        noise_cv=ga("demand_noise_cv"),
        promo_uplifts={
            "none": ga("promo_uplift_none"),
            "low": ga("promo_uplift_low"),
            "middle": ga("promo_uplift_middle"),
            "heavy": ga("promo_uplift_high"),
        },
        horizon_multipliers={
            "short": ga("promo_horizon_short_multiplier"),
            "long": ga("promo_horizon_long_multiplier"),
        },
        vfm_multiplier=ga("promo_vfm_multiplier"),
    )

    rng = np.random.default_rng(params.seed)
    weekly_demands = build_weekly_demand(demand_cfg, WEEKS_PER_ROUND, rng)
    weekly_forecasts = build_weekly_forecast(demand_cfg, WEEKS_PER_ROUND, weekly_demands)
    bias = compute_bias(weekly_forecasts, weekly_demands)

    # Mean weekly demand for capacity planning
    mean_demand_weekly = {pid: float(np.mean(weekly_demands[pid])) for pid in product_ids}

    # R2 baseline demand config (deterministic promo, R2 settings) — used for vol_scale and
    # volume_index normalization so that vi=1.0 exactly at R2 promo conditions.
    r2_demand_cfg = DemandConfig(
        base_demands=base_demands,
        forecast_adjustments={p: 0.0 for p in base_demands},
        promo_pressure={"fg": "heavy", "land": "middle", "dominicks": "none"},
        promo_horizon={"fg": "short", "land": "short", "dominicks": "short"},
        vfm_customers={"fg": True, "land": True, "dominicks": False},
        customer_products=customer_products_map,
        noise_cv=demand_cfg.noise_cv,
        promo_uplifts=demand_cfg.promo_uplifts,
        horizon_multipliers=demand_cfg.horizon_multipliers,
        vfm_multiplier=demand_cfg.vfm_multiplier,
    )

    # volume_index is DETERMINISTIC: uses expected promo-adjusted demand, not the noisy sample.
    # This gives vi=1.0 exactly at R2 promo conditions, no seed-to-seed variance in costs.
    def _promo_factor_det(pid: str, cfg: DemandConfig) -> float:
        """Average promo uplift across customers carrying this product."""
        customers_with = [cid for cid, prods in customer_products_map.items() if pid in prods]
        if not customers_with:
            return 0.0
        return sum(total_promo_uplift(cfg, c) for c in customers_with) / len(customers_with)

    r2_vol_det = sum(
        base_demands[p] * (1.0 + _promo_factor_det(p, r2_demand_cfg)) * WEEKS_PER_ROUND * liters_per_piece[p]
        for p in product_ids
    )
    cur_vol_det = sum(
        base_demands[p] * (1.0 + _promo_factor_det(p, demand_cfg)) * WEEKS_PER_ROUND * liters_per_piece[p]
        for p in product_ids
    )
    volume_index = cur_vol_det / r2_vol_det if r2_vol_det > 0 else 1.0

    # Deterministic expected demand for cost calculations (eliminates seed-to-seed cost variance).
    # Stochastic mean_demand_weekly is still used for service levels, bias, and demand reporting.
    det_demand_weekly = {
        pid: base_demands[pid] * (1.0 + _promo_factor_det(pid, demand_cfg))
        for pid in product_ids
    }

    # ── Production Interval Tool ───────────────────────────────────────────────
    line_data = operations_data["bottling_line"]
    smed_reduction = ga("smed_changeover_reduction")
    speed_factor = ga("increase_speed_factor")
    is_topspeed = params.bottling_line == "topspeed_1"
    is_multiflex = params.bottling_line == "multiflex_1"

    speed = line_data["speed_lph"]
    co_same = line_data["changeover_hours_same_type"]
    co_cross = line_data["changeover_hours_cross_type"]
    startup = line_data["startup_loss_pct"]

    if is_topspeed:
        alts = {a["id"]: a for a in line_data["alternatives"]}
        ts = alts["topspeed_1"]
        speed = ts["speed_lph"]
        co_same = ts["changeover_hours_same_type"]
        co_cross = ts["changeover_hours_cross_type"]
        startup = ts["startup_loss_pct"]
    elif is_multiflex:
        alts = {a["id"]: a for a in line_data["alternatives"]}
        mf = alts["multiflex_1"]
        speed = mf["speed_lph"]
        co_same = mf.get("changeover_hours_same_type") or co_same * 0.8  # estimated shorter
        co_cross = mf.get("changeover_hours_cross_type") or co_cross * 0.8
        startup = mf.get("startup_loss_pct", 0.10)

    if params.inflate_pet:
        speed *= (1.0 - ga("inflate_pet_speed_penalty_pct"))

    line_cfg = LineConfig(
        speed_lph=speed,
        shifts=params.shifts,
        shift_hours_per_week=params.shifts * 8 * 5,  # 2 shifts × 8h × 5 days = 80h/wk
        changeover_same_type_h=co_same,
        changeover_cross_type_h=co_cross,
        startup_loss_pct=startup,
        smed_active=True,   # SMED is always on in our baseline
        increase_speed_active=True,
        smed_reduction=smed_reduction,
        speed_increase_factor=speed_factor,
    )

    product_liters_weekly = {
        pid: det_demand_weekly[pid] * liters_per_piece[pid] for pid in product_ids
    }

    pit = pit_utilization(
        ProductionPlan(
            interval_days=params.production_interval_days,
            frozen_period_weeks=params.frozen_period_weeks,
            safety_stock_weeks=params.fg_safety_stock_weeks,
            product_volumes_weekly=product_liters_weekly,
        ),
        line_cfg,
        product_ids,
        product_liters_weekly,
    )

    if pit["pit_over_80pct"]:
        warnings.append(f"Production Interval Tool utilization {pit['pit_utilization']:.1%} > 80% target")
    if not pit["is_feasible"]:
        warnings.append(f"Line INFEASIBLE: PIT = {pit['pit_utilization']:.1%} > 100%")

    # ── Raw-material pallets and overflow ──────────────────────────────────────
    # Derive RM consumption from actual demand (not from price-based inference).
    # PET: bottles consumed = total PET product demand in pieces/week
    pet_products = [p for p in product_ids if "pet" in p]
    carton_products = [p for p in product_ids if "pet" not in p]
    pet_demand_weekly = sum(det_demand_weekly[p] for p in pet_products)
    total_demand_weekly = sum(det_demand_weekly[p] for p in product_ids)

    # Orange juice: inferred from R2 purchase value at known price (liters/week)
    orange_weekly_liters = 433498 / (ga("price_orange_per_liter") * WEEKS_PER_ROUND)
    # Mango: inferred from R2 purchase value
    mango_weekly_liters = 87399 / (ga("price_mango_per_liter") * WEEKS_PER_ROUND)
    # Vitamin C: inferred from R2 purchase value
    vitc_weekly_liters = 2493 / (ga("price_vitamin_c_per_liter") * WEEKS_PER_ROUND)

    component_consumption_weekly = {
        "orange": orange_weekly_liters * volume_index,
        "pet": pet_demand_weekly,   # pieces/week; scale by vol already in demand
        "pack": total_demand_weekly,  # each piece needs one pack
        "mango": mango_weekly_liters * volume_index,
        "vitamin_c": vitc_weekly_liters * volume_index,
    }

    # Storage capacity per pallet-equivalent location
    pallet_units_storage = {
        "pack": 17280,    # labels/wrappers per pallet
        "pet": 1080.0,    # bottles per pallet position (preforms: much smaller)
        "orange": 1000,   # liters per IBC/tank location
        "mango": 1000,    # liters per IBC location
        "vitamin_c": 250, # liters per drum location
    }
    if params.inflate_pet:
        # Preforms take inflate_pet_storage_fraction of the footprint of bottles
        pet_storage_fraction = ga("inflate_pet_storage_fraction")
        pallet_units_storage["pet"] = 1080.0 / pet_storage_fraction

    rm_pallets_dict = rm_pallets_needed(
        params.rm_safety_stock_weeks,
        params.rm_lot_size_weeks,
        component_consumption_weekly,
        pallet_units_storage,
        inflate_pet=params.inflate_pet,
        inflate_pet_fraction=ga("inflate_pet_storage_fraction") if params.inflate_pet else 1.0,
    )
    rm_total = total_rm_pallets(rm_pallets_dict)
    rm_overflow = rm_overflow_pallets(rm_total, params.rm_locations)

    # ── FG pallets ─────────────────────────────────────────────────────────────
    # Average FG inventory ≈ safety stock + half production lot
    avg_fg_units: dict[str, float] = {}
    for pid in product_ids:
        ss_weeks = params.fg_safety_stock_weeks.get(pid, 2.0)
        interval_weeks = params.production_interval_days / 5.0
        avg_inventory = det_demand_weekly[pid] * (ss_weeks + interval_weeks / 2)
        avg_fg_units[pid] = avg_inventory

    avg_fg_pallets_dict = {
        pid: avg_fg_units[pid] / units_per_pallet[pid] for pid in product_ids
    }
    fg_total = sum(avg_fg_pallets_dict.values())
    fg_overflow = fg_overflow_pallets(fg_total, params.fg_locations)

    if rm_overflow > 0:
        warnings.append(f"RM overflow: {rm_overflow:.0f} pallets overflow ({rm_total:.0f} > {params.rm_locations} locations)")
    if rm_total > params.rm_locations:
        warnings.append(f"RM warehouse infeasible: need {rm_total:.0f} locations, have {params.rm_locations}")
    if fg_overflow > 0:
        warnings.append(f"FG overflow: {fg_overflow:.0f} pallets")

    # ── Purchasing costs ───────────────────────────────────────────────────────
    supplier_cfgs: list[SupplierConfig] = []
    for s in suppliers_data["suppliers"]:
        sid = s["id"]
        sc = SupplierConfig(
            supplier_id=sid,
            component=s["component"],
            purchase_value_r2=s["purchase_value_r2"],
            payment_term_weeks=params.supplier_payment_terms.get(sid, 8),
            vmi_active=params.supplier_vmi.get(sid, False),
            vmi_cost_per_round=s["vmi_cost_per_round"],
            vmi_index_delta=s.get("vmi_index_delta_r2", 0.0),
            supplier_index=s.get("supplier_index_r2", 1.0),
            transport_cost_r2=s.get("transport_cost_r2", 0.0),
            inflate_pet=params.inflate_pet if sid == "pet" else False,
            inflate_pet_preform_fraction=ga("inflate_pet_transport_saving_pct")
                if params.inflate_pet and sid == "pet" else 1.0,
            inflate_pet_transport_saving=ga("inflate_pet_transport_saving_pct")
                if params.inflate_pet and sid == "pet" else 0.0,
            payment_term_index_delta_per_week=ga("supplier_idx_payment_term_per_week"),
        )
        # Preform fraction from operations.yaml (calibrated to R3 actual 37.3%)
        sc.inflate_pet_preform_fraction = operations_data["inflate_pet"]["preform_cost_fraction_of_bottle"]
        sc.inflate_pet_transport_saving = ga("inflate_pet_transport_saving_pct") if params.inflate_pet and sid == "pet" else 0.0
        supplier_cfgs.append(sc)

    purchase_result = compute_all_purchases(
        supplier_cfgs,
        volume_index,
        params.supplier_payment_terms,
    )

    total_material_cost = purchase_result["total_materials"]
    # Transport is bundled into supplier purchase prices in the real game — no separate line
    total_vmi_supplier = purchase_result["total_vmi_fees"]
    supplier_admin = purchase_result["admin"]

    # ── Customer contract indices and revenue ──────────────────────────────────
    customers_list = customers_data["customers"]
    customer_map = {c["id"]: c for c in customers_list}

    # Customer R2 contracted revenues (from customers.yaml, not hardcoded)
    customer_revenue_r2 = {c["id"]: c["contracted_revenue_r2"] for c in customers_list}
    total_r2_rev = sum(customer_revenue_r2.values())
    customer_shares_default = {cid: r / total_r2_rev for cid, r in customer_revenue_r2.items()}

    customer_cfgs: list[CustomerConfig] = []
    for cdata in customers_list:
        cid = cdata["id"]
        # Trade unit: VMI forces pallet + 14:00
        tu = params.trade_unit.get(cid, cdata["trade_unit"])
        dl = params.order_deadline.get(cid, cdata["order_deadline"])
        if params.customer_vmi.get(cid, False):
            tu = "pallet"
            dl = "14:00"

        vmi_delta = ga(f"idx_customer_vmi_delta_{cid}")
        cc = CustomerConfig(
            customer_id=cid,
            contract_index_base=cdata["contract_index_r2"],
            service_promise=params.service_promise,
            requested_shelf_life_pct=params.requested_shelf_life_pct,
            payment_term_weeks=params.customer_payment_terms.get(cid, 1),
            trade_unit=tu,
            order_deadline=dl,
            promo_pressure=params.promotional_pressure.get(cid, "none"),
            promo_horizon=params.promotion_horizon.get(cid, "short"),
            vmi_active=params.customer_vmi.get(cid, False),
            contracted_revenue_r2=cdata["contracted_revenue_r2"],
            vmi_delta=vmi_delta,
            payment_term_delta_per_week=ga("idx_payment_term_per_week"),
            trade_unit_box_vs_layer=ga("idx_trade_unit_box_vs_layer"),
            trade_unit_layer_vs_pallet=ga("idx_trade_unit_layer_vs_pallet"),
            promo_pressure_delta_per_step=ga("idx_promo_pressure_reduction_per_step"),
            promo_horizon_long_vs_short=ga("idx_promo_horizon_short_vs_long"),
            shelf_life_delta_per_pct=ga("idx_shelf_life_per_pct_point"),
            deadline_delta_per_hour_earlier=ga("idx_deadline_per_hour_earlier"),
        )
        customer_cfgs.append(cc)

    # Compute revenue per customer
    total_contracted = 0.0
    customer_revenue: dict[str, float] = {}
    customer_indices: dict[str, float] = {}
    service_by_customer: dict[str, dict] = {}

    # Demand split per customer per product
    product_share_by_customer: dict[str, dict[str, float]] = {}
    for cid in ["fg", "land", "dominicks"]:
        prods = customer_products_map.get(cid, product_ids)
        share = customer_shares_default.get(cid, 0.33)
        product_share_by_customer[cid] = {pid: share for pid in prods}

    # Volume scale per customer: deterministic promo ratio relative to R2 settings.
    # vs = 1.0 when promo settings match R2 exactly; r2_demand_cfg created above.
    vol_scale_by_customer: dict[str, float] = {}
    for cid in ["fg", "land", "dominicks"]:
        r2_uplift = total_promo_uplift(r2_demand_cfg, cid)
        cur_uplift = total_promo_uplift(demand_cfg, cid)
        vol_scale_by_customer[cid] = (1.0 + cur_uplift) / (1.0 + r2_uplift) if (1.0 + r2_uplift) > 0 else 1.0

    for cc in customer_cfgs:
        cid = cc.customer_id
        cdata = customer_map[cid]
        idx = compute_contract_index(cc)
        customer_indices[cid] = idx

        # Revenue anchored to R2 contracted revenue, scaled by index change and promo volume
        r2_rev = cdata["contracted_revenue_r2"]
        r2_idx = cdata["contract_index_r2"]
        vs = vol_scale_by_customer.get(cid, 1.0)
        contracted = r2_rev * (idx / r2_idx) * vs
        customer_revenue[cid] = contracted
        total_contracted += contracted

        prods_for_customer = customer_products_map.get(cid, product_ids)
        total_weekly_demand = sum(mean_demand_weekly[pid] for pid in prods_for_customer)

        # FG safety stock in pieces for service simulation
        trade_unit_sizes = {"box": 10, "pallet_layer": 120, "pallet": 600}
        tu_size = trade_unit_sizes.get(cc.trade_unit, 120)
        fg_ss = sum(
            params.fg_safety_stock_weeks.get(pid, 2.0) * mean_demand_weekly[pid]
            for pid in prods_for_customer
        )

        cust_demand_weekly = np.array([
            sum(weekly_demands[pid][w] for pid in prods_for_customer)
            for w in range(WEEKS_PER_ROUND)
        ])
        cust_prod_weekly = np.full(WEEKS_PER_ROUND, total_weekly_demand)

        svc = simulate_service_level(
            cust_demand_weekly, cust_prod_weekly, fg_ss, tu_size
        )
        service_by_customer[cid] = svc

        svc_bonus = service_bonus_penalty(
            svc["service_lines"],
            params.service_promise,
            contracted,
            bonus_fraction=ga("service_bonus_fraction_of_revenue"),
            penalty_multiplier=ga("service_penalty_multiplier_vs_bonus"),
        )
        customer_revenue[cid] = contracted + svc_bonus

    # total_contracted is the sum of contracted revenues (before bonus/penalty)
    # customer_revenue includes bonus/penalty on top
    total_bonus_penalty = sum(customer_revenue.values()) - total_contracted
    realized_revenue = sum(customer_revenue.values())

    # ── Costs ──────────────────────────────────────────────────────────────────
    # Bottling
    ops = operations_data
    operators_total = ops["bottling_line"]["operators_per_shift"] * params.shifts
    bottling_perm = operators_total * ops["bottling_line"]["operator_cost_per_year"] / 2  # per round
    bottling_perm += ops["bottling_line"]["fixed_cost_per_year"] / 2  # fixed per round

    # Line: R2 permanent staff was €200K (10 ops × €20K/yr × 1/2) = €100K + €98K/2 = €49K...
    # Actually the data says "bottling permanent staff €200K" which includes fixed line cost.
    # We calibrate: R2 perm = €200K for 2 shifts, 5 ops/shift, +fixed
    # 10 operators × €20K = €200K per year → €100K per round
    # Fixed line: €98K per year → €49K per round. Total: €149K per round.
    # But real P&L says €200K. So fixed might be higher or our interpretation differs.
    # Use calibrated value: scale by actual operators
    bottling_perm_calibrated = 200000.0 * (operators_total / 10.0)

    # Flexible labour: scales with how much we exceed baseline utilization
    base_actual_util = 0.90  # real R2 actual utilization
    actual_util = pit.get("actual_utilization", 0.90)
    bottling_flex = 27800.0 * (actual_util / base_actual_util)

    # Mixing
    mixing = compute_mixing_cost(volume_index)

    # Warehouses
    wh_cfg = WarehouseConfig(
        rm_locations=params.rm_locations,
        fg_locations=params.fg_locations,
        rm_perm_fte=params.rm_perm_fte,
        fg_perm_fte=params.fg_perm_fte,
        inflate_pet=params.inflate_pet,
    )
    wh_costs = warehouse_total_cost(wh_cfg, rm_overflow, fg_overflow)

    # For outsourced FG: replace fg_locations + fg_fte with outsourcing cost
    outsourcing_cost = 0.0
    if params.outsource_fg:
        ou_data = ops.get("outsourcing_fg", {}).get(params.outsource_fg, {})
        if ou_data:
            pallets_out = sum(det_demand_weekly[pid] * WEEKS_PER_ROUND / units_per_pallet[pid]
                              for pid in product_ids)
            days_stored = 19.0  # approximate average storage days (calibrated from game note)
            outsourcing_cost = (
                ou_data.get("cost_per_pallet_per_day", 1.30) * fg_total * 7 * WEEKS_PER_ROUND
                + ou_data.get("intake_per_pallet", 1.25) * fg_total
                + ou_data.get("outbound_per_order_line", 3.00) * pallets_out * 5  # ~5 lines/pallet
            )
            # Replace internal FG costs
            wh_costs["fg_locations"] = 0.0
            wh_costs["fg_fte"] = 0.0

    # Distribution
    total_units_sold = {pid: det_demand_weekly[pid] * WEEKS_PER_ROUND for pid in product_ids}
    total_pallets_out = compute_pallets_dispatched(total_units_sold, units_per_pallet)
    distribution = compute_distribution_cost(total_pallets_out, cost_per_pallet=float(ga("distribution_cost_per_pallet")))

    # Projects
    projects_cost = ops["bottling_line"]["project_cost_per_round"]
    if is_topspeed:
        alts_dict = {a["id"]: a for a in ops["bottling_line"]["alternatives"]}
        projects_cost += alts_dict["topspeed_1"].get("fixed_cost_extra_per_year", 16000) / 2

    # Customer VMI fees
    vmi_fees_customers = sum(
        2500.0 for cid, active in params.customer_vmi.items() if active
    )

    # Inflate PET running cost
    inflate_pet_cost = 0.0
    inflate_pet_depreciation = 0.0
    if params.inflate_pet:
        inflate_pet_cost = ops["inflate_pet"]["running_cost_per_year"] / 2
        inflate_pet_depreciation = float(ga("inflate_depreciation_per_round"))

    # Interest and WC
    avg_supplier_term = sum(params.supplier_payment_terms.values()) / len(params.supplier_payment_terms)
    avg_customer_term = sum(params.customer_payment_terms.values()) / len(params.customer_payment_terms)
    # R2 baseline terms
    R2_SUPPLIER_TERM = 8.0
    R2_CUSTOMER_TERM = 1.0
    # Interest uses AR - AP formula for the interest line item only
    inventory_val = total_material_cost * ga("working_capital_inventory_weeks") / WEEKS_PER_ROUND
    wc = compute_working_capital(
        total_material_cost, realized_revenue,
        avg_supplier_term, avg_customer_term, inventory_val
    )
    interest_net = compute_interest(wc)

    # Overhead — split into energy, water, other (all from R2 actuals, scale with volume)
    energy_overhead = float(ga("energy_overhead_r2")) * volume_index
    water_overhead = float(ga("water_overhead_r2")) * volume_index
    overhead = float(ga("overhead_other_per_round"))  # fixed component

    # Tank yard for orange (PulpStore outsourcing, scales with orange volume fraction)
    orange_vol_index = component_consumption_weekly["orange"] / (
        433498 / (ga("price_orange_per_liter") * WEEKS_PER_ROUND)
    )
    tank_yard = float(ga("tank_yard_cost_r2")) * orange_vol_index

    # Stock interest (interest on inventory value; scales with volume)
    stock_interest_inv = float(ga("stock_interest_r2")) * volume_index

    # Warehouse misc: inbound flex manpower, RM inspection, outbound flex, outbound admin
    warehouse_misc = (
        float(ga("inbound_flex_manpower_r2"))
        + float(ga("rm_inspection_cost_r2"))
        + float(ga("outbound_flex_manpower_r2"))
        + float(ga("outbound_admin_r2"))
    ) * volume_index

    # Overflow: use max(structural, calibrated R2 baseline × vi) per component
    rm_overflow_baseline = float(ga("rm_overflow_r2")) * volume_index
    fg_overflow_baseline = float(ga("fg_overflow_r2")) * volume_index
    rm_overflow_cost = max(wh_costs["rm_overflow"], rm_overflow_baseline)
    fg_overflow_cost = max(wh_costs["fg_overflow"], fg_overflow_baseline)

    # ── Investment ─────────────────────────────────────────────────────────────
    equip = compute_equipment_investment(
        bottling_investment=ops["bottling_line"]["investment"],
        mixer_investment=ops["mixer"]["investment"],
    )
    inflate_pet_invest = ops["inflate_pet"]["investment"] if params.inflate_pet else 0.0

    # Working capital investment: anchor to R2 calibrated value, then scale by:
    # (a) volume index (more volume → more capital tied up)
    # (b) payment term changes relative to R2 (longer customer term → more AR, shorter supplier term → more AP)
    R2_WC_BASELINE = 2715221.0  # R2 investment (3,517,221) minus equipment (802,000)
    ar_r2 = 2711810 / WEEKS_PER_ROUND * R2_CUSTOMER_TERM
    ap_r2 = 912533 / WEEKS_PER_ROUND * R2_SUPPLIER_TERM
    ar_now = realized_revenue / WEEKS_PER_ROUND * avg_customer_term
    ap_now = total_material_cost / WEEKS_PER_ROUND * avg_supplier_term
    wc_term_delta = (ar_now - ar_r2) - (ap_now - ap_r2)  # positive = more WC needed
    wc_investment_calibrated = max(0.0, R2_WC_BASELINE * volume_index + wc_term_delta)

    # ── Assemble P&L ──────────────────────────────────────────────────────────
    pl = PLResult(
        contracted_revenue=total_contracted,
        bonus_penalty=realized_revenue - total_contracted,
        material_purchases=total_material_cost,
        transport=0.0,  # bundled in purchase prices; no separate line in real game
        supplier_admin=supplier_admin,
        bottling_permanent=bottling_perm_calibrated,
        bottling_flexible=bottling_flex,
        mixing=mixing,
        rm_locations=wh_costs["rm_locations"],
        rm_overflow=rm_overflow_cost,
        rm_fte=wh_costs["rm_fte"],
        fg_locations=wh_costs["fg_locations"],
        fg_overflow=fg_overflow_cost,
        fg_fte=wh_costs["fg_fte"],
        scrap=sum(wh_costs.get("scrap", 0.0) for _ in [0]),  # from warehouse model
        risk=sum(wh_costs.get("risk", 0.0) for _ in [0]),
        projects=projects_cost,
        warehouse_misc=warehouse_misc,
        distribution=distribution,
        interest_net=interest_net,
        vmi_fees_suppliers=total_vmi_supplier,
        vmi_fees_customers=vmi_fees_customers,
        outsourcing_fg=outsourcing_cost,
        energy_overhead=energy_overhead,
        water_overhead=water_overhead,
        tank_yard=tank_yard,
        stock_interest_inventory=stock_interest_inv,
        overhead_other=overhead,
        equipment_investment=equip,
        working_capital=wc_investment_calibrated,
        inflate_pet_investment=inflate_pet_invest,
        inflate_pet_depreciation=inflate_pet_depreciation,
        uses_unverified=list(unverified_used),
    )

    # Calibration: add scrap/risk separately
    # Use R2 obsoletes data to estimate; scale by service level
    avg_service = np.mean([svc["service_lines"] for svc in service_by_customer.values()])
    # More stock → more obsoletes; proportional to safety stock weeks
    avg_ss_weeks = np.mean([params.fg_safety_stock_weeks.get(p, 2.0) for p in product_ids])
    r2_avg_ss = np.mean([2.3, 2.5, 2.2, 2.0, 2.5, 2.2])
    obs_scale = avg_ss_weeks / r2_avg_ss
    pl.scrap = 52800 * obs_scale * volume_index
    pl.risk = pl.scrap  # risk = scrap (R2 calibrated)

    return SimResult(
        pl=pl,
        production_pit=pit,
        service_by_customer=service_by_customer,
        bias_by_product=bias,
        rm_overflow_avg_pallets=rm_overflow,
        fg_overflow_avg_pallets=fg_overflow,
        rm_total_pallets=rm_total,
        fg_total_pallets=fg_total,
        warnings=warnings,
        unverified_assumptions_used=unverified_used,
    )


def build_r2_scenario() -> ScenarioParams:
    """Return the Round 2 baseline scenario parameters."""
    return ScenarioParams(
        production_interval_days=10,
        frozen_period_weeks=2,
        fg_safety_stock_weeks={
            "orange_1l": 2.3, "c_power_1l": 2.5, "mango_1l": 2.2,
            "orange_pet": 2.0, "c_power_pet": 2.5, "mango_pet": 2.2,
        },
        rm_safety_stock_weeks={
            "pet": 1.5, "pack": 1.7, "orange": 1.9, "mango": 1.9, "vitamin_c": 4.0
        },
        rm_lot_size_weeks={
            "pet": 2.0, "pack": 2.5, "orange": 2.5, "mango": 4.0, "vitamin_c": 4.0
        },
        supplier_payment_terms={"orange": 8, "pet": 8, "pack": 8, "mango": 8, "vitamin_c": 8},
        supplier_vmi={"orange": True, "pet": False, "pack": False, "mango": False, "vitamin_c": False},
        rm_locations=700,
        rm_perm_fte=3,
        fg_locations=1100,
        fg_perm_fte=4,
        inflate_pet=False,
        customer_payment_terms={"fg": 1, "land": 1, "dominicks": 1},
        customer_vmi={"fg": False, "land": False, "dominicks": False},
        promotional_pressure={"fg": "heavy", "land": "middle", "dominicks": "none"},
        promotion_horizon={"fg": "short", "land": "short", "dominicks": "short"},
        trade_unit={"fg": "pallet_layer", "land": "pallet_layer", "dominicks": "box"},
        order_deadline={"fg": "20:00", "land": "17:00", "dominicks": "20:00"},
        requested_shelf_life_pct=0.78,
        service_promise=0.94,
        seed=42,
    )


def build_r3_scenario() -> ScenarioParams:
    """Return current Round 3 screen-state scenario."""
    p = build_r2_scenario()
    p.fg_safety_stock_weeks["orange_1l"] = 2.5
    p.fg_safety_stock_weeks["c_power_1l"] = 2.7
    p.rm_safety_stock_weeks["pet"] = 2.0
    p.rm_lot_size_weeks["pet"] = 3.0
    p.rm_locations = 200
    p.rm_perm_fte = 2
    p.inflate_pet = True
    p.customer_vmi = {"fg": True, "land": False, "dominicks": False}
    p.promotional_pressure = {"fg": "heavy", "land": "heavy", "dominicks": "none"}
    p.promotion_horizon = {"fg": "long", "land": "long", "dominicks": "short"}
    return p
