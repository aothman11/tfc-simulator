"""Monte Carlo simulation over uncertain assumptions.

Samples every UNVERIFIED assumption from its [min, max] range
using uniform distribution, plus demand noise (varied by seed).
"""
from __future__ import annotations
import copy
import numpy as np
from dataclasses import dataclass, field
from typing import Callable

from tfc.engine.simulation import ScenarioParams, SimResult, run_simulation, build_r2_scenario
from tfc.engine.loader import load_assumptions, list_unverified


@dataclass
class MCResult:
    roi_samples: np.ndarray
    profit_samples: np.ndarray
    revenue_samples: np.ndarray
    investment_samples: np.ndarray
    n_runs: int
    baseline_roi: float

    @property
    def mean_roi(self) -> float:
        return float(np.mean(self.roi_samples)) * 100

    @property
    def median_roi(self) -> float:
        return float(np.median(self.roi_samples)) * 100

    @property
    def p10_roi(self) -> float:
        return float(np.percentile(self.roi_samples, 10)) * 100

    @property
    def p90_roi(self) -> float:
        return float(np.percentile(self.roi_samples, 90)) * 100

    @property
    def worst_roi(self) -> float:
        return float(np.min(self.roi_samples)) * 100

    @property
    def beat_baseline_pct(self) -> float:
        """Fraction of runs where ROI > baseline ROI."""
        return float(np.mean(self.roi_samples > self.baseline_roi)) * 100


def run_monte_carlo(
    scenario: ScenarioParams,
    n_runs: int = 500,
    baseline: ScenarioParams | None = None,
    rng_seed: int = 0,
) -> MCResult:
    """
    Run Monte Carlo simulation sampling UNVERIFIED assumptions.
    Each run draws assumptions from uniform(min, max) and uses a unique demand seed.
    """
    assumptions = load_assumptions()
    unverified = list_unverified(assumptions)

    master_rng = np.random.default_rng(rng_seed)

    roi_samples = []
    profit_samples = []
    revenue_samples = []
    investment_samples = []

    for i in range(n_runs):
        params = copy.deepcopy(scenario)
        params.seed = int(master_rng.integers(0, 100000))

        # Sample UNVERIFIED assumptions uniformly
        sampled_overrides = dict(params.assumption_overrides)
        for name in unverified:
            a = assumptions[name]
            lo = a.get("min")
            hi = a.get("max")
            if lo is None or hi is None or isinstance(lo, bool) or isinstance(hi, bool):
                continue
            if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
                val = float(master_rng.uniform(lo, hi))
                sampled_overrides[name] = val

        params.assumption_overrides = sampled_overrides
        result = run_simulation(params)

        roi_samples.append(result.pl.roi)
        profit_samples.append(result.pl.operating_profit)
        revenue_samples.append(result.pl.realized_revenue)
        investment_samples.append(result.pl.investment)

    # Compute baseline ROI (deterministic, no assumption sampling)
    if baseline is None:
        baseline = build_r2_scenario()
    baseline_result = run_simulation(baseline)
    baseline_roi = baseline_result.pl.roi

    return MCResult(
        roi_samples=np.array(roi_samples),
        profit_samples=np.array(profit_samples),
        revenue_samples=np.array(revenue_samples),
        investment_samples=np.array(investment_samples),
        n_runs=n_runs,
        baseline_roi=baseline_roi,
    )


def tornado_analysis(
    scenario: ScenarioParams,
    n_steps: int = 3,
) -> list[dict]:
    """
    One-at-a-time sensitivity: vary each UNVERIFIED assumption from min to max,
    measure ROI swing. Sort descending.
    Returns list of {name, roi_low, roi_high, swing}.
    """
    assumptions = load_assumptions()
    unverified = list_unverified(assumptions)

    base = copy.deepcopy(scenario)
    base_result = run_simulation(base)
    base_roi = base_result.pl.roi * 100

    results: list[dict] = []
    for name in unverified:
        a = assumptions[name]
        lo = a.get("min")
        hi = a.get("max")
        if lo is None or hi is None or isinstance(lo, bool) or isinstance(hi, bool):
            continue
        if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
            continue
        if abs(hi - lo) < 1e-10:
            continue

        # Low value
        p_lo = copy.deepcopy(scenario)
        ov_lo = dict(p_lo.assumption_overrides)
        ov_lo[name] = lo
        p_lo.assumption_overrides = ov_lo
        r_lo = run_simulation(p_lo)
        roi_lo = r_lo.pl.roi * 100

        # High value
        p_hi = copy.deepcopy(scenario)
        ov_hi = dict(p_hi.assumption_overrides)
        ov_hi[name] = hi
        p_hi.assumption_overrides = ov_hi
        r_hi = run_simulation(p_hi)
        roi_hi = r_hi.pl.roi * 100

        swing = abs(roi_hi - roi_lo)
        results.append({
            "name": name,
            "roi_at_min": roi_lo,
            "roi_at_max": roi_hi,
            "swing_pp": swing,
            "base_roi": base_roi,
            "min_val": lo,
            "max_val": hi,
        })

    results.sort(key=lambda x: x["swing_pp"], reverse=True)
    return results


def format_mc_report(mc: MCResult, scenario_name: str) -> str:
    lines = [
        "=" * 60,
        f"MONTE CARLO REPORT: {scenario_name}",
        f"Practice model – estimates only ({mc.n_runs} runs)",
        "=" * 60,
        f"{'Metric':<30} {'Value':>10}",
        "-" * 60,
        f"{'Mean ROI':<30} {mc.mean_roi:>10.2f}%",
        f"{'Median ROI':<30} {mc.median_roi:>10.2f}%",
        f"{'10th percentile ROI':<30} {mc.p10_roi:>10.2f}%",
        f"{'90th percentile ROI':<30} {mc.p90_roi:>10.2f}%",
        f"{'Worst case ROI':<30} {mc.worst_roi:>10.2f}%",
        f"{'Baseline ROI (R2 hold)':<30} {mc.baseline_roi * 100:>10.2f}%",
        f"{'Beat baseline':<30} {mc.beat_baseline_pct:>10.1f}%",
        "=" * 60,
        "",
        f"VERDICT: GO is better than hold-R2 in {mc.beat_baseline_pct:.0f}% of runs.",
        f"Worst case: {mc.worst_roi:.2f}% ROI ({mc.worst_roi - mc.baseline_roi * 100:+.2f} pp vs baseline).",
    ]
    return "\n".join(lines)


def format_tornado(tornado: list[dict], top_n: int = 10) -> str:
    lines = [
        "=" * 70,
        "TORNADO CHART — Top assumptions by ROI impact",
        "Practice model – estimates only",
        "=" * 70,
        f"{'Assumption':<40} {'Min→Max ROI swing':>15} {'At min':>8} {'At max':>8}",
        "-" * 70,
    ]
    for item in tornado[:top_n]:
        lines.append(
            f"{item['name'][:39]:<40} {item['swing_pp']:>14.2f}pp "
            f"{item['roi_at_min']:>7.2f}% {item['roi_at_max']:>7.2f}%"
        )
    lines.append("=" * 70)
    return "\n".join(lines)
