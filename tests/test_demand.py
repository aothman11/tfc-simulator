"""Tests for demand model."""
import numpy as np
import pytest
from tfc.engine.demand import (
    DemandConfig, build_weekly_demand, build_weekly_forecast, compute_bias,
    total_promo_uplift
)

BASE_DEMANDS = {
    "orange_1l": 70100,
    "c_power_1l": 11900,
    "mango_1l": 44000,
    "orange_pet": 119200,
    "c_power_pet": 17900,
    "mango_pet": 51600,
}

CUSTOMER_PRODUCTS = {
    "fg": ["orange_1l", "c_power_1l", "mango_1l", "orange_pet", "c_power_pet", "mango_pet"],
    "land": ["orange_1l", "c_power_1l", "mango_1l", "orange_pet", "c_power_pet", "mango_pet"],
    "dominicks": ["orange_pet", "c_power_pet", "mango_pet"],
}


def make_config(**kwargs):
    defaults = dict(
        base_demands=BASE_DEMANDS,
        forecast_adjustments={p: 0.0 for p in BASE_DEMANDS},
        promo_pressure={"fg": "heavy", "land": "middle", "dominicks": "none"},
        promo_horizon={"fg": "short", "land": "short", "dominicks": "short"},
        vfm_customers={"fg": True, "land": True, "dominicks": False},
        customer_products=CUSTOMER_PRODUCTS,
        noise_cv=0.47,
    )
    defaults.update(kwargs)
    return DemandConfig(**defaults)


def test_demand_shape():
    cfg = make_config()
    rng = np.random.default_rng(0)
    demands = build_weekly_demand(cfg, 26, rng)
    assert set(demands.keys()) == set(BASE_DEMANDS.keys())
    for pid, arr in demands.items():
        assert arr.shape == (26,)
        assert np.all(arr > 0)


def test_demand_positive():
    cfg = make_config()
    rng = np.random.default_rng(42)
    demands = build_weekly_demand(cfg, 26, rng)
    for arr in demands.values():
        assert np.all(arr > 0), "Demand must always be positive"


def test_demand_mean_near_base():
    """With many runs, mean demand should be close to base × promo_uplift."""
    cfg = make_config(
        promo_pressure={"fg": "none", "land": "none", "dominicks": "none"},
        vfm_customers={"fg": False, "land": False, "dominicks": False},
    )
    all_demands = []
    for seed in range(100):
        rng = np.random.default_rng(seed)
        d = build_weekly_demand(cfg, 26, rng)
        all_demands.append(np.mean(d["orange_1l"]))
    grand_mean = np.mean(all_demands)
    assert abs(grand_mean - 70100) / 70100 < 0.05, f"Mean demand {grand_mean} too far from base {70100}"


def test_forecast_no_noise():
    cfg = make_config()
    rng = np.random.default_rng(0)
    demands = build_weekly_demand(cfg, 26, rng)
    forecasts = build_weekly_forecast(cfg, 26, demands)
    for pid, arr in forecasts.items():
        assert np.std(arr) < 1e-6, "Forecast should have no noise"
        assert arr[0] > 0


def test_bias_direction():
    """Positive forecast adjustment → positive bias."""
    cfg = make_config(
        forecast_adjustments={"orange_1l": 0.20, "c_power_1l": 0.0, "mango_1l": 0.0,
                              "orange_pet": -0.20, "c_power_pet": 0.0, "mango_pet": 0.0},
        promo_pressure={"fg": "none", "land": "none", "dominicks": "none"},
        vfm_customers={"fg": False, "land": False, "dominicks": False},
    )
    # Average over many seeds to reduce noise
    biases = {"orange_1l": [], "orange_pet": []}
    for seed in range(50):
        rng = np.random.default_rng(seed)
        d = build_weekly_demand(cfg, 26, rng)
        f = build_weekly_forecast(cfg, 26, d)
        b = compute_bias(f, d)
        biases["orange_1l"].append(b["orange_1l"])
        biases["orange_pet"].append(b["orange_pet"])
    assert np.mean(biases["orange_1l"]) > 0, "Positive adjustment → positive bias on average"
    assert np.mean(biases["orange_pet"]) < 0, "Negative adjustment → negative bias on average"


def test_promo_uplift_none():
    cfg = make_config()
    uplift = total_promo_uplift(cfg, "dominicks")
    assert uplift == 0.0


def test_promo_uplift_heavy_vfm():
    """Heavy pressure + VFM customer → higher than heavy alone."""
    cfg_vfm = make_config(vfm_customers={"fg": True, "land": False, "dominicks": False})
    cfg_no = make_config(vfm_customers={"fg": False, "land": False, "dominicks": False})
    assert total_promo_uplift(cfg_vfm, "fg") > total_promo_uplift(cfg_no, "fg")
