"""CLI entry point: python -m tfc <command> [args]

Commands:
  run <scenario.yaml>           Run a single scenario and print comparison table
  montecarlo <scenario.yaml>    Monte Carlo + GO/NO-GO verdict
  calibrate                     Run calibration against R2 actuals
  tornado <scenario.yaml>       Sensitivity tornado chart
  scenarios                     Run all pre-built decision scenarios
"""
from __future__ import annotations
import sys
import time
import pathlib
import argparse

from tfc import DISCLAIMER

ROOT = pathlib.Path(__file__).parent.parent
SCENARIOS_DIR = ROOT / "scenarios"


def cmd_run(args):
    from tfc.engine.scenarios import load_scenario, compare_scenarios, format_comparison_table, accept_rule_checker
    from tfc.engine.simulation import build_r2_scenario, run_simulation

    path = pathlib.Path(args.scenario)
    if not path.exists():
        print(f"Error: scenario file not found: {path}")
        sys.exit(1)

    print(f"\n{DISCLAIMER}\n")
    print(f"Loading scenario: {path.name} ...")

    scenario = load_scenario(path)
    baseline = build_r2_scenario()

    n_seeds = getattr(args, "seeds", 5)
    table = compare_scenarios(baseline, scenario, n_seeds=n_seeds)
    print(format_comparison_table(table, path.stem))

    # Accept rules
    baseline_result = run_simulation(baseline)
    scenario_result = run_simulation(scenario)
    checks = accept_rule_checker(scenario_result, baseline_result, scenario)
    if checks:
        print("\n--- ACCEPT-RULE CHECKER ---")
        for c in checks:
            verdict = c.get("model_verdict", "?")
            print(f"\n[{verdict}] {c['decision']}")
            print(f"  Threshold: {c['accept_threshold']}")
            print(f"  {c['note']}")


def cmd_montecarlo(args):
    from tfc.engine.scenarios import load_scenario
    from tfc.engine.montecarlo import run_monte_carlo, format_mc_report, tornado_analysis, format_tornado
    from tfc.engine.simulation import build_r2_scenario

    path = pathlib.Path(args.scenario)
    if not path.exists():
        print(f"Error: scenario file not found: {path}")
        sys.exit(1)

    print(f"\n{DISCLAIMER}\n")
    n = getattr(args, "n", 500)
    print(f"Running {n} Monte Carlo simulations for: {path.name} ...")
    t0 = time.time()

    scenario = load_scenario(path)
    mc = run_monte_carlo(scenario, n_runs=n)
    elapsed = time.time() - t0
    print(format_mc_report(mc, path.stem))
    print(f"\nCompleted in {elapsed:.1f}s")

    print("\nRunning tornado analysis ...")
    t1 = time.time()
    tornado = tornado_analysis(scenario)
    print(format_tornado(tornado))
    print(f"Tornado completed in {time.time() - t1:.1f}s")


def cmd_calibrate(args):
    from tfc.engine.calibration import run_calibration, format_calibration_report
    n = getattr(args, "seeds", 10)
    print(f"\n{DISCLAIMER}\n")
    print(f"Running calibration with {n} seeds ...")
    t0 = time.time()
    targets = run_calibration(n_seeds=n)
    print(format_calibration_report(targets))
    print(f"\nCalibration completed in {time.time() - t0:.1f}s")


def cmd_tornado(args):
    from tfc.engine.scenarios import load_scenario
    from tfc.engine.montecarlo import tornado_analysis, format_tornado
    path = pathlib.Path(args.scenario)
    print(f"\n{DISCLAIMER}\n")
    scenario = load_scenario(path)
    print(f"Running tornado for: {path.name} ...")
    tornado = tornado_analysis(scenario)
    print(format_tornado(tornado))


def cmd_scenarios(args):
    """Run all pre-built decision scenarios and print a summary table."""
    from tfc.engine.simulation import build_r2_scenario, run_simulation
    from tfc.engine.scenarios import load_scenario, compare_scenarios, format_comparison_table

    print(f"\n{DISCLAIMER}\n")
    print("Running all pre-built decision scenarios ...\n")

    baseline = build_r2_scenario()

    scenario_files = sorted(SCENARIOS_DIR.glob("*.yaml"))
    if not scenario_files:
        print(f"No scenario files found in {SCENARIOS_DIR}")
        return

    rows = []
    for sf in scenario_files:
        try:
            scenario = load_scenario(sf)
            table = compare_scenarios(baseline, scenario, n_seeds=3)
            rows.append({
                "name": sf.stem,
                "roi_baseline": table["baseline"]["roi"],
                "roi_scenario": table["scenario"]["roi"],
                "delta_roi": table["delta"]["roi"],
                "profit_delta": table["delta"]["operating_profit"],
                "rm_overflow": table["rm_overflow"],
                "pit": table["pit_utilization"],
                "warnings": len(table["warnings"]),
            })
        except Exception as e:
            rows.append({"name": sf.stem, "error": str(e)})

    print(f"{'Scenario':<35} {'ROI (base)':>10} {'ROI (scen)':>10} {'Delta ROI':>10} {'RM Oflow':>10} {'PIT':>8}")
    print("-" * 85)
    for r in rows:
        if "error" in r:
            print(f"{r['name']:<35} ERROR: {r['error'][:40]}")
        else:
            warn = " ⚠" if r["warnings"] > 0 else ""
            print(f"{r['name']:<35} {r['roi_baseline']:>9.2f}% {r['roi_scenario']:>9.2f}% "
                  f"{r['delta_roi']:>+9.2f}pp {r['rm_overflow']:>9.0f} {r['pit']:>7.1f}%{warn}")


def main():
    parser = argparse.ArgumentParser(
        prog="python -m tfc",
        description="TFC Practice Simulator CLI — Practice model, estimates only",
    )
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="Run a scenario")
    p_run.add_argument("scenario", help="Path to scenario YAML file")
    p_run.add_argument("--seeds", type=int, default=5, help="Number of seeds to average")
    p_run.set_defaults(func=cmd_run)

    p_mc = sub.add_parser("montecarlo", help="Monte Carlo simulation")
    p_mc.add_argument("scenario", help="Path to scenario YAML file")
    p_mc.add_argument("-n", type=int, default=500, help="Number of MC runs")
    p_mc.set_defaults(func=cmd_montecarlo)

    p_cal = sub.add_parser("calibrate", help="Run calibration against R2 actuals")
    p_cal.add_argument("--seeds", type=int, default=10)
    p_cal.set_defaults(func=cmd_calibrate)

    p_tor = sub.add_parser("tornado", help="Sensitivity tornado chart")
    p_tor.add_argument("scenario", help="Path to scenario YAML file")
    p_tor.set_defaults(func=cmd_tornado)

    p_all = sub.add_parser("scenarios", help="Run all pre-built scenarios")
    p_all.set_defaults(func=cmd_scenarios)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
