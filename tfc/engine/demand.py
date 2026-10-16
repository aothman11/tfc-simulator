"""Demand generation model.

Each week's demand for each product follows:
  demand_w = base × promo_multiplier × lognormal_noise(mean=1, cv=demand_noise_cv)

Bias = (forecast − demand) / demand  (positive → excess stock risk).
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field


@dataclass
class DemandConfig:
    base_demands: dict[str, float]          # product_id → weekly units
    forecast_adjustments: dict[str, float]  # product_id → fraction (0.0 = no adjustment)
    promo_pressure: dict[str, str]          # customer_id → "none"/"low"/"middle"/"heavy"
    promo_horizon: dict[str, str]           # customer_id → "short"/"long"
    vfm_customers: dict[str, bool]          # customer_id → bool
    customer_products: dict[str, list[str]] # customer_id → [product_ids]
    # share of each customer in total demand per product (derived)
    customer_shares: dict[str, dict[str, float]] | None = None
    noise_cv: float = 0.47
    promo_uplifts: dict[str, float] = field(default_factory=lambda: {
        "none": 0.0, "low": 0.0075, "middle": 0.0175, "heavy": 0.048
    })
    horizon_multipliers: dict[str, float] = field(default_factory=lambda: {
        "short": 1.0, "long": 1.15
    })
    vfm_multiplier: float = 2.0


def _promo_uplift(pressure: str, horizon: str, is_vfm: bool, config: DemandConfig) -> float:
    base = config.promo_uplifts.get(pressure, 0.0)
    h_mult = config.horizon_multipliers.get(horizon, 1.0)
    uplift = base * h_mult
    if is_vfm:
        uplift *= config.vfm_multiplier
    return uplift


def total_promo_uplift(config: DemandConfig, customer_id: str) -> float:
    pressure = config.promo_pressure.get(customer_id, "none")
    horizon = config.promo_horizon.get(customer_id, "short")
    is_vfm = config.vfm_customers.get(customer_id, False)
    return _promo_uplift(pressure, horizon, is_vfm, config)


def build_weekly_demand(
    config: DemandConfig,
    n_weeks: int,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """Return dict product_id → array of n_weeks demand values (units/week)."""
    demands: dict[str, np.ndarray] = {}

    # Aggregate promo uplift: weighted average across customers for each product
    # (simplified: each customer uses the same base demand; real game may split)
    for pid, base in config.base_demands.items():
        total_uplift = 0.0
        if config.customer_shares:
            for cid, share_map in config.customer_shares.items():
                share = share_map.get(pid, 0.0)
                total_uplift += total_promo_uplift(config, cid) * share
        else:
            # Equal share across all customers who carry the product
            customers_with = [
                cid for cid, prods in config.customer_products.items()
                if pid in prods or prods == ["all"]
            ]
            if customers_with:
                avg = sum(total_promo_uplift(config, c) for c in customers_with) / len(customers_with)
                total_uplift = avg

        promo_base = base * (1 + total_uplift)

        # Lognormal noise: lognormal(mu, sigma) with mean=1, cv=noise_cv
        cv = config.noise_cv
        sigma = np.sqrt(np.log(1 + cv**2))
        mu = -sigma**2 / 2  # ensures E[exp(mu + sigma*Z)] = 1
        noise = rng.lognormal(mu, sigma, n_weeks)
        demands[pid] = promo_base * noise

    return demands


def build_weekly_forecast(
    config: DemandConfig,
    n_weeks: int,
    demands: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """Forecast = base × (1 + adjustment%). Fixed for the round (no noise)."""
    forecasts: dict[str, np.ndarray] = {}
    for pid, base in config.base_demands.items():
        adj = config.forecast_adjustments.get(pid, 0.0)
        # aggregate same promo uplift as demand but no noise
        total_uplift = 0.0
        customers_with = [
            cid for cid, prods in config.customer_products.items()
            if pid in prods or prods == ["all"]
        ]
        if customers_with:
            avg = sum(total_promo_uplift(config, c) for c in customers_with) / len(customers_with)
            total_uplift = avg
        forecast_weekly = base * (1 + total_uplift) * (1 + adj)
        forecasts[pid] = np.full(n_weeks, forecast_weekly)
    return forecasts


def compute_bias(
    forecasts: dict[str, np.ndarray],
    demands: dict[str, np.ndarray],
) -> dict[str, float]:
    """Bias = (mean_forecast − mean_demand) / mean_demand over all weeks."""
    bias: dict[str, float] = {}
    for pid in forecasts:
        f_mean = float(np.mean(forecasts[pid]))
        d_mean = float(np.mean(demands[pid]))
        bias[pid] = (f_mean - d_mean) / d_mean if d_mean > 0 else 0.0
    return bias
