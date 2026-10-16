"""Calibration runner.

Runs the model with R2 settings and compares to known R2 actuals.
Reports target vs model vs gap for every calibration metric.
"""
from __future__ import annotations
import textwrap
from dataclasses import dataclass

from tfc.engine.simulation import run_simulation, build_r2_scenario, SimResult


@dataclass
class CalibTarget:
    name: str
    target: float
    tolerance_pct: float | None   # None = absolute tolerance
    tolerance_abs: float | None
    model_value: float = 0.0

    @property
    def gap_pct(self) -> float:
        if self.target == 0:
            return 0.0
        return (self.model_value - self.target) / abs(self.target) * 100

    @property
    def passed(self) -> bool:
        if self.tolerance_pct is not None:
            return abs(self.gap_pct) <= self.tolerance_pct
        if self.tolerance_abs is not None:
            return abs(self.model_value - self.target) <= self.tolerance_abs
        return True


TARGETS = [
    CalibTarget("Operating profit (€)", 215399, tolerance_pct=3.0, tolerance_abs=None),
    CalibTarget("Investment (€)", 3517221, tolerance_pct=3.0, tolerance_abs=None),
    CalibTarget("ROI (%)", 6.12, tolerance_pct=None, tolerance_abs=0.15),
    CalibTarget("Realized revenue (€)", 2723905, tolerance_pct=1.5, tolerance_abs=None),
    CalibTarget("Product bias: orange_1l (%)", 0.9, tolerance_pct=None, tolerance_abs=3.0),
    CalibTarget("Product bias: c_power_1l (%)", -3.9, tolerance_pct=None, tolerance_abs=3.0),
    CalibTarget("Product bias: mango_1l (%)", 0.7, tolerance_pct=None, tolerance_abs=3.0),
    CalibTarget("Product bias: orange_pet (%)", -0.9, tolerance_pct=None, tolerance_abs=3.0),
    CalibTarget("Service lines: orange_1l (%)", 93.6, tolerance_pct=None, tolerance_abs=3.0),
    CalibTarget("Service lines: c_power_1l (%)", 91.7, tolerance_pct=None, tolerance_abs=3.0),
    CalibTarget("Service lines: mango_1l (%)", 95.9, tolerance_pct=None, tolerance_abs=3.0),
    CalibTarget("Service lines: orange_pet (%)", 97.0, tolerance_pct=None, tolerance_abs=3.0),
]


def run_calibration(n_seeds: int = 10) -> list[CalibTarget]:
    """
    Run calibration: average over multiple seeds to reduce noise impact.
    Returns updated targets with model_value filled in.
    """
    import copy
    import numpy as np

    base = build_r2_scenario()
    results: list[SimResult] = []
    for seed in range(n_seeds):
        base.seed = seed
        r = run_simulation(base)
        results.append(r)

    # Average financial metrics across seeds
    avg_op = float(np.mean([r.pl.operating_profit for r in results]))
    avg_inv = float(np.mean([r.pl.investment for r in results]))
    avg_roi = float(np.mean([r.pl.roi for r in results])) * 100
    avg_rev = float(np.mean([r.pl.realized_revenue for r in results]))

    # Average bias per product (available for 4 products)
    bias_products = ["orange_1l", "c_power_1l", "mango_1l", "orange_pet"]
    avg_bias = {
        pid: float(np.mean([r.bias_by_product.get(pid, 0.0) for r in results])) * 100
        for pid in bias_products
    }

    # Average service by product — we only have customer-level; map products to customers
    # For simplicity, use FG service lines as overall proxy (all customers aggregate)
    def avg_svc(cid: str) -> float:
        return float(np.mean([
            r.service_by_customer.get(cid, {}).get("service_lines", 0.0) for r in results
        ])) * 100

    targets = copy.deepcopy(TARGETS)
    for t in targets:
        if t.name == "Operating profit (€)":
            t.model_value = avg_op
        elif t.name == "Investment (€)":
            t.model_value = avg_inv
        elif t.name == "ROI (%)":
            t.model_value = avg_roi
        elif t.name == "Realized revenue (€)":
            t.model_value = avg_rev
        elif "bias: orange_1l" in t.name:
            t.model_value = avg_bias.get("orange_1l", 0.0)
        elif "bias: c_power_1l" in t.name:
            t.model_value = avg_bias.get("c_power_1l", 0.0)
        elif "bias: mango_1l" in t.name:
            t.model_value = avg_bias.get("mango_1l", 0.0)
        elif "bias: orange_pet" in t.name:
            t.model_value = avg_bias.get("orange_pet", 0.0)
        elif "Service lines: orange_1l" in t.name:
            t.model_value = avg_svc("fg")   # approximate
        elif "Service lines: c_power_1l" in t.name:
            t.model_value = avg_svc("fg")
        elif "Service lines: mango_1l" in t.name:
            t.model_value = avg_svc("land")
        elif "Service lines: orange_pet" in t.name:
            t.model_value = avg_svc("dominicks")

    return targets


def format_calibration_report(targets: list[CalibTarget]) -> str:
    lines = [
        "=" * 72,
        "TFC PRACTICE MODEL — CALIBRATION REPORT (Round 2 baseline)",
        "Practice model – estimates only",
        "=" * 72,
        f"{'Metric':<38} {'Target':>12} {'Model':>12} {'Gap':>8} {'OK?':>5}",
        "-" * 72,
    ]
    for t in targets:
        if "%" in t.name:
            target_str = f"{t.target:.2f}%"
            model_str = f"{t.model_value:.2f}%"
            gap_str = f"{t.model_value - t.target:+.2f} pp"
        else:
            target_str = f"€{t.target:,.0f}"
            model_str = f"€{t.model_value:,.0f}"
            gap_str = f"{t.gap_pct:+.1f}%"
        ok = "✓" if t.passed else "✗"
        lines.append(f"{t.name:<38} {target_str:>12} {model_str:>12} {gap_str:>8} {ok:>5}")

    n_pass = sum(1 for t in targets if t.passed)
    lines.append("-" * 72)
    lines.append(f"Passed: {n_pass}/{len(targets)}")
    lines.append("")
    lines.append("NOTE: Stochastic demand means results vary by seed. Model averaged")
    lines.append("over multiple seeds. Large gaps are honest — the model is approximate.")
    lines.append("=" * 72)
    return "\n".join(lines)
