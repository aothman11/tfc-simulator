"""Scenario management: load from YAML, apply overrides, run accept-rule checker."""
from __future__ import annotations
import copy
import pathlib
import yaml
from dataclasses import asdict

from tfc.engine.simulation import ScenarioParams, SimResult, run_simulation, build_r2_scenario
from tfc.engine.loader import load_suppliers


ROOT = pathlib.Path(__file__).parent.parent.parent


def load_scenario(path: str | pathlib.Path) -> ScenarioParams:
    """Load a scenario YAML file, apply overrides on top of R2 baseline."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    params = build_r2_scenario()
    overrides = raw.get("overrides", {})

    # Apply overrides using dot-notation keys
    for key, val in overrides.items():
        parts = key.split(".")
        if len(parts) == 1:
            if hasattr(params, key):
                setattr(params, key, val)
        elif len(parts) == 2:
            attr, sub = parts
            d = getattr(params, attr, {})
            if isinstance(d, dict):
                d = dict(d)
                d[sub] = val
                setattr(params, attr, d)

    # Handle assumption_overrides
    if "assumption_overrides" in raw:
        params.assumption_overrides = raw["assumption_overrides"]

    if "seed" in raw:
        params.seed = raw["seed"]

    return params


def run_scenario_file(path: str | pathlib.Path) -> SimResult:
    params = load_scenario(path)
    return run_simulation(params)


def compare_scenarios(
    baseline: ScenarioParams,
    scenario: ScenarioParams,
    n_seeds: int = 5,
) -> dict:
    """Run both scenarios across multiple seeds and return comparison dict."""
    import numpy as np

    base_results = []
    scen_results = []
    for s in range(n_seeds):
        b = copy.copy(baseline)
        b.seed = s
        base_results.append(run_simulation(b))

        sc = copy.copy(scenario)
        sc.seed = s
        scen_results.append(run_simulation(sc))

    def avg(results, attr):
        vals = [getattr(r.pl, attr) for r in results]
        return float(np.mean(vals))

    metrics = ["operating_profit", "realized_revenue", "investment"]
    base_avg = {m: avg(base_results, m) for m in metrics}
    scen_avg = {m: avg(scen_results, m) for m in metrics}

    base_roi = float(np.mean([r.pl.roi for r in base_results])) * 100
    scen_roi = float(np.mean([r.pl.roi for r in scen_results])) * 100

    table: dict = {
        "baseline": {**base_avg, "roi": base_roi},
        "scenario": {**scen_avg, "roi": scen_roi},
        "delta": {},
        "delta_pp": {},
        "service_by_customer": {},
        "pit_utilization": {},
        "rm_overflow": {},
        "warnings": scen_results[0].warnings,
        "unverified": scen_results[0].unverified_assumptions_used,
    }

    for m in metrics:
        table["delta"][m] = scen_avg[m] - base_avg[m]
        table["delta_pp"][m] = (scen_avg[m] - base_avg[m]) / abs(base_avg[m]) * 100 if base_avg[m] else 0
    table["delta"]["roi"] = scen_roi - base_roi
    table["delta_pp"]["roi"] = scen_roi - base_roi  # already in pp

    # Service and operational
    table["service_by_customer"] = {
        cid: float(np.mean([
            r.service_by_customer.get(cid, {}).get("service_lines", 0) * 100
            for r in scen_results
        ]))
        for cid in ["fg", "land", "dominicks"]
    }
    table["pit_utilization"] = scen_results[0].production_pit.get("pit_utilization", 0) * 100
    table["rm_overflow"] = float(np.mean([r.rm_overflow_avg_pallets for r in scen_results]))
    table["rm_total_pallets"] = float(np.mean([r.rm_total_pallets for r in scen_results]))

    return table


def accept_rule_checker(
    scenario_result: SimResult,
    baseline_result: SimResult,
    scenario_params: ScenarioParams,
    real_game_index_overrides: dict | None = None,
) -> list[dict]:
    """
    Check each active option against the accept/reject rules.
    real_game_index_overrides: {cid: real_index} from the actual game screen,
                               used to override model-predicted indices.
    """
    suppliers_data = load_suppliers()
    s_map = {s["id"]: s for s in suppliers_data["suppliers"]}
    vmi_thresholds = suppliers_data["vmi_break_even_index_drop"]

    checks: list[dict] = []

    # ── Supplier VMI ──
    for sid, active in scenario_params.supplier_vmi.items():
        if active and sid != "orange":  # orange VMI already active in baseline
            pv = s_map[sid]["purchase_value_r2"]
            vmi_cost = 2500.0
            min_drop = vmi_cost / pv
            # Model-predicted index delta
            model_delta = scenario_result.pl.material_purchases - baseline_result.pl.material_purchases
            checks.append({
                "decision": f"Supplier VMI: {sid}",
                "accept_threshold": f"Index must fall ≥ {min_drop:.4f}",
                "model_verdict": "DEPENDS_ON_REAL_GAME_SCREEN",
                "note": f"VMI cost €2,500/round. Break-even index drop = {min_drop:.4f}. "
                        f"Read the real index from the game and enter it above.",
            })

    # ── Customer VMI ──
    customer_revenue_r2 = {"fg": 1370000, "land": 630000, "dominicks": 711810}
    customer_vmi_break_even = {
        "fg": 1.0 + 2500.0 / customer_revenue_r2["fg"],
        "land": 1.0 + 2500.0 / customer_revenue_r2["land"],
        "dominicks": 1.0 + 2500.0 / customer_revenue_r2["dominicks"],
    }
    # From prompt: actual thresholds after game data
    vmi_accept_index = {"fg": 0.9978, "land": 0.9663, "dominicks": 1.0581}
    for cid, active in scenario_params.customer_vmi.items():
        if active:
            threshold = vmi_accept_index[cid]
            real_index = (real_game_index_overrides or {}).get(cid)
            if real_index is not None:
                verdict = "ACCEPT" if real_index >= threshold else "REJECT"
                verdict_detail = f"Real index {real_index:.4f} {'≥' if real_index >= threshold else '<'} threshold {threshold:.4f}"
            else:
                verdict = "UNKNOWN"
                verdict_detail = f"Enter real game index. Model threshold: {threshold:.4f}"
            checks.append({
                "decision": f"Customer VMI: {cid.upper()}",
                "accept_threshold": f"Index ≥ {threshold:.4f}",
                "model_verdict": verdict,
                "note": verdict_detail,
            })

    # ── Inflate PET gate ──
    if scenario_params.inflate_pet:
        roi_hurdle = 0.061
        investment = 700000
        min_gain = roi_hurdle * investment  # €42,700
        model_gain = scenario_result.pl.operating_profit - baseline_result.pl.operating_profit
        model_verdict = "GO" if model_gain >= min_gain else "NO-GO"
        checks.append({
            "decision": "Inflate PET",
            "accept_threshold": f"Net profit gain ≥ €{min_gain:,.0f}/round (6.1% × €700K)",
            "model_profit_gain": model_gain,
            "model_verdict": model_verdict,
            "note": (
                f"Model shows gain €{model_gain:,.0f}/round. "
                f"{'GO' if model_gain >= min_gain else 'NO-GO'}. "
                "Check: no line slowdown, PET lead time not ≈ 26 weeks. "
                "UNVERIFIED assumptions affect this result."
            ),
        })

    # ── Horizon change ──
    for cid in ["fg", "land", "dominicks"]:
        cur_h = scenario_params.promotion_horizon.get(cid, "short")
        r2_h = "short"
        if cur_h != r2_h:
            real_index = (real_game_index_overrides or {}).get(cid)
            # Accept if index fall ≤ 0.003
            checks.append({
                "decision": f"Promo horizon Short→{cur_h.capitalize()}: {cid.upper()}",
                "accept_threshold": "Index falls ≤ 0.003",
                "model_verdict": "CHECK_REAL_GAME",
                "note": f"Enter real index from game. Current model index is approximate.",
            })

    return checks


def format_comparison_table(table: dict, scenario_name: str) -> str:
    lines = [
        "=" * 68,
        f"Scenario: {scenario_name}",
        "Practice model – estimates only",
        "=" * 68,
        f"{'Metric':<30} {'Baseline':>12} {'Scenario':>12} {'Delta':>12}",
        "-" * 68,
    ]

    def row(name, base_key, fmt="€"):
        b = table["baseline"].get(base_key, 0)
        s = table["scenario"].get(base_key, 0)
        d = table["delta"].get(base_key, 0)
        dp = table["delta_pp"].get(base_key, 0)
        if fmt == "€":
            lines.append(f"{name:<30} €{b:>10,.0f} €{s:>10,.0f} €{d:>+10,.0f} ({dp:+.1f}%)")
        elif fmt == "%":
            lines.append(f"{name:<30} {b:>11.2f}% {s:>11.2f}% {d:>+11.2f} pp")

    row("Realized revenue", "realized_revenue")
    row("Operating profit", "operating_profit")
    row("Investment", "investment")
    lines.append(f"{'ROI':<30} {table['baseline']['roi']:>11.2f}% {table['scenario']['roi']:>11.2f}% {table['delta']['roi']:>+11.2f} pp")
    lines.append("-" * 68)
    lines.append(f"{'PIT utilization':<30} {'':>12} {table['pit_utilization']:>11.1f}%")
    lines.append(f"{'RM overflow (pallets)':<30} {'':>12} {table['rm_overflow']:>11.0f}")
    lines.append(f"{'RM total pallets':<30} {'':>12} {table['rm_total_pallets']:>11.0f}")
    lines.append("-" * 68)
    lines.append("Service (order lines):")
    for cid, svc in table["service_by_customer"].items():
        lines.append(f"  {cid.upper():<28} {svc:>11.1f}%")
    if table["warnings"]:
        lines.append("-" * 68)
        lines.append("WARNINGS:")
        for w in table["warnings"]:
            lines.append(f"  ⚠ {w}")
    if table["unverified"]:
        lines.append("")
        lines.append(f"Depends on UNVERIFIED assumptions: {', '.join(table['unverified'][:5])}")
    lines.append("=" * 68)
    return "\n".join(lines)
