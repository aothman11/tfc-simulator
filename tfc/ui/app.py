"""TFC Practice Simulator — Streamlit UI.

Run with:   streamlit run tfc/ui/app.py
"""
from __future__ import annotations
import copy
import pathlib
import sys
import numpy as np

# Add project root to path
ROOT = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from tfc import DISCLAIMER
from tfc.engine.simulation import ScenarioParams, SimResult, run_simulation, build_r2_scenario
from tfc.engine.loader import load_assumptions, list_unverified
from tfc.engine.calibration import run_calibration, format_calibration_report
from tfc.engine.montecarlo import run_monte_carlo, tornado_analysis
from tfc.engine.scenarios import compare_scenarios, accept_rule_checker

st.set_page_config(
    page_title="TFC Practice Simulator",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Banner ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style='background-color:#c0392b;color:white;padding:8px 16px;border-radius:4px;
    font-weight:bold;font-size:14px;text-align:center;margin-bottom:12px;'>
    ⚠ PRACTICE MODEL – NOT THE REAL GAME – All numbers are approximate estimates only
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Session state init ─────────────────────────────────────────────────────────
if "params" not in st.session_state:
    st.session_state.params = build_r2_scenario()
if "result" not in st.session_state:
    st.session_state.result = None
if "assumption_overrides" not in st.session_state:
    st.session_state.assumption_overrides = {}


def get_params() -> ScenarioParams:
    p = copy.deepcopy(st.session_state.params)
    p.assumption_overrides = copy.deepcopy(st.session_state.assumption_overrides)
    return p


def run_and_store():
    params = get_params()
    st.session_state.result = run_simulation(params)


# ── Sidebar: load preset ───────────────────────────────────────────────────────
st.sidebar.title("TFC Practice Simulator")
st.sidebar.caption(DISCLAIMER)

presets = {
    "Round 2 baseline": "r2",
    "Round 3 (current screen)": "r3",
}
preset = st.sidebar.selectbox("Load preset", list(presets.keys()))

if st.sidebar.button("Load preset"):
    from tfc.engine.simulation import build_r3_scenario
    if presets[preset] == "r2":
        st.session_state.params = build_r2_scenario()
    else:
        st.session_state.params = build_r3_scenario()
    st.session_state.result = None
    st.rerun()

# Load scenario file
uploaded = st.sidebar.file_uploader("Upload scenario YAML", type=["yaml", "yml"])
if uploaded:
    import yaml
    from tfc.engine.scenarios import load_scenario
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        f.write(uploaded.read())
        tmp_path = f.name
    try:
        st.session_state.params = load_scenario(tmp_path)
        st.session_state.result = None
    finally:
        os.unlink(tmp_path)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📊 Dashboard",
    "🛒 Sales",
    "📦 Purchasing",
    "🏭 Operations",
    "🔗 Supply Chain",
    "💰 Finance Report",
    "📋 Decision Log",
    "🎲 Scenarios",
    "🔧 Assumptions",
])

tab_dash, tab_sales, tab_purch, tab_ops, tab_sc, tab_fin, tab_log, tab_scen, tab_assump = tabs

# ── Helper: Calculate button ──────────────────────────────────────────────────
def calculate_button(key: str = "calc") -> bool:
    col1, col2 = st.columns([1, 4])
    calc = col1.button("Calculate", key=f"calc_{key}", type="primary")
    if calc:
        with st.spinner("Running simulation..."):
            run_and_store()
        return True
    return False


def show_unverified_warning(result: SimResult | None):
    if result and result.unverified_assumptions_used:
        st.warning(
            f"⚠ Depends on **UNVERIFIED** assumptions: "
            f"{', '.join(result.unverified_assumptions_used[:6])}. "
            "Results are estimates only."
        )


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
with tab_dash:
    st.header("Dashboard")
    calculate_button("dashboard")
    result = st.session_state.result

    if result:
        show_unverified_warning(result)

        col1, col2, col3, col4 = st.columns(4)
        roi = result.pl.roi * 100
        col1.metric("ROI", f"{roi:.2f}%", f"{roi - 6.12:+.2f} pp vs R2")
        col2.metric("Operating Profit", f"€{result.pl.operating_profit:,.0f}",
                    f"€{result.pl.operating_profit - 215399:+,.0f} vs R2")
        col3.metric("Revenue", f"€{result.pl.realized_revenue:,.0f}")
        col4.metric("Investment", f"€{result.pl.investment:,.0f}")

        st.divider()
        col5, col6, col7 = st.columns(3)
        pit = result.production_pit.get("pit_utilization", 0) * 100
        pit_color = "inverse" if pit > 80 else "normal"
        col5.metric("PIT Utilization", f"{pit:.1f}%",
                    delta="⚠ > 80% target" if pit > 80 else "OK",
                    delta_color=pit_color)
        col6.metric("RM Overflow Pallets", f"{result.rm_overflow_avg_pallets:.0f}",
                    delta="⚠ Overflow!" if result.rm_overflow_avg_pallets > 0 else "OK",
                    delta_color="inverse" if result.rm_overflow_avg_pallets > 0 else "normal")
        col7.metric("FG Overflow Pallets", f"{result.fg_overflow_avg_pallets:.0f}",
                    delta="⚠ Overflow!" if result.fg_overflow_avg_pallets > 0 else "OK",
                    delta_color="inverse" if result.fg_overflow_avg_pallets > 0 else "normal")

        st.divider()
        st.subheader("Service Level by Customer")
        svc_data = []
        for cid, svc in result.service_by_customer.items():
            sl = svc.get("service_lines", 0) * 100
            svc_data.append({
                "Customer": cid.upper(),
                "Order-line service": f"{sl:.1f}%",
                "vs promise": f"{sl - 94.0:+.1f} pp",
                "Status": "✓ OK" if sl >= 94.0 else "✗ BELOW 94%",
            })
        st.table(svc_data)

        if result.warnings:
            st.subheader("Warnings")
            for w in result.warnings:
                st.error(f"⚠ {w}")
    else:
        st.info("Press **Calculate** to run the simulation.")

# ── SALES ─────────────────────────────────────────────────────────────────────
with tab_sales:
    st.header("Sales / Customer Settings")
    params = st.session_state.params

    for cid, cname in [("fg", "Food & Groceries (F&G)"), ("land", "LAND Market"), ("dominicks", "Dominick's")]:
        with st.expander(cname, expanded=True):
            col1, col2 = st.columns(2)
            vmi = col1.checkbox(f"Customer VMI", value=params.customer_vmi.get(cid, False), key=f"vmi_{cid}")
            params.customer_vmi[cid] = vmi
            if vmi:
                col2.info("VMI active → trade unit → Pallet, deadline → 14:00")

            pterm = col1.number_input(
                "Payment term (weeks)", 0, 8,
                value=params.customer_payment_terms.get(cid, 1), key=f"pt_{cid}"
            )
            params.customer_payment_terms[cid] = pterm

            pressure_opts = ["none", "low", "middle", "heavy"]
            pp_idx = pressure_opts.index(params.promotional_pressure.get(cid, "none"))
            pp = col2.selectbox("Promo pressure", pressure_opts, index=pp_idx, key=f"pp_{cid}")
            params.promotional_pressure[cid] = pp

            horizon_opts = ["short", "long"]
            ph_idx = horizon_opts.index(params.promotion_horizon.get(cid, "short"))
            ph = col1.selectbox("Promo horizon", horizon_opts, index=ph_idx, key=f"ph_{cid}")
            params.promotion_horizon[cid] = ph

            if not vmi:
                tu_opts = ["box", "pallet_layer", "pallet"]
                tu_idx = tu_opts.index(params.trade_unit.get(cid, "pallet_layer"))
                tu = col2.selectbox("Trade unit", tu_opts, index=tu_idx, key=f"tu_{cid}")
                params.trade_unit[cid] = tu

            dl_opts = ["14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "23:59"]
            cur_dl = params.order_deadline.get(cid, "20:00")
            if vmi:
                cur_dl = "14:00"
            dl_idx = dl_opts.index(cur_dl) if cur_dl in dl_opts else 6
            dl = col1.selectbox("Order deadline", dl_opts, index=dl_idx, key=f"dl_{cid}",
                                disabled=vmi)
            params.order_deadline[cid] = "14:00" if vmi else dl

    params.service_promise = st.slider(
        "Service promise (%)", 90, 99,
        int(params.service_promise * 100), key="svc_promise") / 100.0
    params.requested_shelf_life_pct = st.slider(
        "Requested shelf life (%)", 40, 85,
        int(params.requested_shelf_life_pct * 100), key="sl_pct") / 100.0

    st.session_state.params = params
    calculate_button("sales")

# ── PURCHASING ────────────────────────────────────────────────────────────────
with tab_purch:
    st.header("Purchasing Settings")
    params = st.session_state.params

    st.subheader("Supplier VMI")
    cols = st.columns(5)
    for i, sid in enumerate(["orange", "pet", "pack", "mango", "vitamin_c"]):
        vmi = cols[i].checkbox(f"{sid.upper()}", value=params.supplier_vmi.get(sid, False), key=f"svmi_{sid}")
        params.supplier_vmi[sid] = vmi

    st.subheader("Supplier Payment Terms (weeks)")
    cols2 = st.columns(5)
    for i, sid in enumerate(["orange", "pet", "pack", "mango", "vitamin_c"]):
        pt = cols2[i].number_input(
            f"{sid.upper()}", 1, 20,
            value=params.supplier_payment_terms.get(sid, 8), key=f"spt_{sid}"
        )
        params.supplier_payment_terms[sid] = pt

    st.subheader("RM Safety Stock & Lot Size (weeks)")
    comp_cols = st.columns(5)
    for i, (sid, label) in enumerate([("orange", "Orange"), ("pet", "PET"), ("pack", "Pack"), ("mango", "Mango"), ("vitamin_c", "Vit C")]):
        with comp_cols[i]:
            ss = st.number_input(f"{label} SS", 0.5, 10.0,
                                 value=float(params.rm_safety_stock_weeks.get(sid, 2.0)),
                                 step=0.1, key=f"ss_{sid}")
            params.rm_safety_stock_weeks[sid] = ss
            ls = st.number_input(f"{label} Lot", 0.5, 10.0,
                                 value=float(params.rm_lot_size_weeks.get(sid, 2.0)),
                                 step=0.1, key=f"ls_{sid}")
            params.rm_lot_size_weeks[sid] = ls

    st.session_state.params = params
    calculate_button("purch")

# ── OPERATIONS ────────────────────────────────────────────────────────────────
with tab_ops:
    st.header("Operations Settings")
    params = st.session_state.params

    col1, col2 = st.columns(2)

    params.rm_locations = col1.number_input(
        "RM Locations", 100, 2000, value=params.rm_locations, step=50, key="rm_loc"
    )
    params.rm_perm_fte = col1.number_input(
        "RM Permanent FTE", 1, 10, value=params.rm_perm_fte, key="rm_fte"
    )
    params.inflate_pet = col1.checkbox(
        "Inflate PET bottles (€700K investment, €70K/round)", value=params.inflate_pet, key="inflate"
    )
    if params.inflate_pet:
        col1.info("Preforms cost 50% of ready PET. Transport saving is UNVERIFIED (see Assumptions tab).")

    params.fg_locations = col2.number_input(
        "FG Locations", 100, 3000, value=params.fg_locations, step=50, key="fg_loc"
    )
    params.fg_perm_fte = col2.number_input(
        "FG Permanent FTE", 1, 10, value=params.fg_perm_fte, key="fg_fte"
    )

    outsource_opts = [None, "conventional", "automated", "mcc"]
    out_idx = outsource_opts.index(params.outsource_fg) if params.outsource_fg in outsource_opts else 0
    params.outsource_fg = col2.selectbox(
        "FG Warehouse Outsourcing",
        ["None", "Conventional", "Automated", "MCC"],
        index=out_idx, key="fg_outsource"
    )
    if params.outsource_fg == "None":
        params.outsource_fg = None
    else:
        params.outsource_fg = params.outsource_fg.lower()

    st.subheader("Bottling Line")
    line_opts = ["swiss_fill_2", "swiss_fill_1", "multiflex_1", "topspeed_1"]
    line_labels = ["Swiss Fill 2 (current)", "Swiss Fill 1", "MultiFlex 1", "TopSpeed 1"]
    line_idx = line_opts.index(params.bottling_line) if params.bottling_line in line_opts else 0
    params.bottling_line = line_opts[
        st.selectbox("Bottling line", line_labels, index=line_idx, key="line_sel")
    ] if False else line_opts[line_idx]
    # Simplified: keep as selector
    chosen_label = st.selectbox("Bottling line", line_labels, index=line_idx, key="line_sel2")
    params.bottling_line = line_opts[line_labels.index(chosen_label)]

    params.shifts = st.number_input("Shifts", 1, 3, value=params.shifts, key="shifts")

    st.session_state.params = params

    # Calculate + show RM overflow analysis
    if calculate_button("ops"):
        result = st.session_state.result
        if result:
            st.subheader("Warehouse Capacity Analysis")
            col_a, col_b = st.columns(2)
            col_a.metric("RM pallets needed", f"{result.rm_total_pallets:.0f}")
            col_a.metric("RM locations", f"{params.rm_locations}")
            if result.rm_overflow_avg_pallets > 0:
                col_a.error(f"⚠ RM OVERFLOW: {result.rm_overflow_avg_pallets:.0f} pallets can't fit!")
            else:
                col_a.success(f"✓ RM fits with {params.rm_locations - result.rm_total_pallets:.0f} spare locations")

            col_b.metric("FG pallets avg", f"{result.fg_total_pallets:.0f}")
            col_b.metric("FG locations", f"{params.fg_locations}")
            if result.fg_overflow_avg_pallets > 0:
                col_b.warning(f"FG overflow: {result.fg_overflow_avg_pallets:.0f} pallets")
            else:
                col_b.success("FG no overflow")

# ── SUPPLY CHAIN ──────────────────────────────────────────────────────────────
with tab_sc:
    st.header("Supply Chain Settings")
    params = st.session_state.params

    params.production_interval_days = st.number_input(
        "Production interval (days)", 1, 30, value=params.production_interval_days, key="pi_days"
    )
    params.frozen_period_weeks = st.number_input(
        "Frozen period (weeks)", 0, 8, value=params.frozen_period_weeks, key="fp_wks"
    )

    st.subheader("FG Safety Stock (weeks)")
    cols = st.columns(3)
    for i, pid in enumerate(["orange_1l", "c_power_1l", "mango_1l", "orange_pet", "c_power_pet", "mango_pet"]):
        c = cols[i % 3]
        ss = c.number_input(
            pid.replace("_", " ").title(),
            0.5, 10.0,
            value=float(params.fg_safety_stock_weeks.get(pid, 2.0)),
            step=0.1, key=f"fg_ss_{pid}"
        )
        params.fg_safety_stock_weeks[pid] = ss

    st.session_state.params = params
    result = st.session_state.result
    if calculate_button("sc"):
        result = st.session_state.result
    if result:
        pit = result.production_pit
        st.subheader("Production Interval Tool")
        col1, col2 = st.columns(2)
        pit_val = pit.get("pit_utilization", 0) * 100
        color = "red" if pit_val > 80 else "green"
        col1.metric("PIT Utilization", f"{pit_val:.1f}%",
                    delta=f"{'⚠ > 80%' if pit_val > 80 else '✓ ≤ 80%'}",
                    delta_color="inverse" if pit_val > 80 else "normal")
        col1.metric("Actual Line Utilization", f"{pit.get('actual_utilization', 0) * 100:.1f}%")
        col2.metric("Production hours/week", f"{pit.get('production_h_per_week', 0):.1f}h")
        col2.metric("Changeover hours/week", f"{pit.get('changeover_h_per_week', 0):.1f}h")

# ── FINANCE REPORT ─────────────────────────────────────────────────────────────
with tab_fin:
    st.header("Finance Report")
    calculate_button("fin")
    result = st.session_state.result
    if result:
        show_unverified_warning(result)
        pl = result.pl

        st.subheader("P&L")

        def row(label, val, indent=False):
            prefix = "  · " if indent else ""
            return {"Line item": prefix + label, "Amount (€)": f"€{val:+,.0f}" if val != 0 else "—"}

        pl_rows = [
            row("Realized Revenue", pl.realized_revenue),
            row("  Contracted sales", pl.contracted_revenue, True),
            row("  Bonus / Penalty", pl.bonus_penalty, True),
            row("Cost of Goods", -pl.cogs),
            row("  Material purchases", -pl.material_purchases, True),
            row("  Transport (PET)", -pl.transport, True),
            row("  Supplier admin", -pl.supplier_admin, True),
            row("Operations Costs", -pl.operations_cost),
            row("  Bottling (permanent)", -pl.bottling_permanent, True),
            row("  Bottling (flexible)", -pl.bottling_flexible, True),
            row("  Mixing", -pl.mixing, True),
            row("  RM locations", -pl.rm_locations, True),
            row("  RM overflow", -pl.rm_overflow, True),
            row("  FG locations", -pl.fg_locations, True),
            row("  FG overflow", -pl.fg_overflow, True),
            row("  Scrap + Risk", -(pl.scrap + pl.risk), True),
            row("  Projects", -pl.projects, True),
            row("Distribution", -pl.distribution),
            row("Interest (net)", -pl.interest_net),
            row("VMI fees (suppliers)", -pl.vmi_fees_suppliers),
            row("VMI fees (customers)", -pl.vmi_fees_customers),
            row("Inflate PET (running)", -pl.inflate_pet_depreciation),
            row("Overhead (other)", -pl.overhead_other),
            row("OPERATING PROFIT", pl.operating_profit),
        ]
        st.table(pl_rows)

        st.subheader("ROI")
        col1, col2, col3 = st.columns(3)
        col1.metric("Operating Profit", f"€{pl.operating_profit:,.0f}")
        col2.metric("Investment", f"€{pl.investment:,.0f}")
        col3.metric("ROI", f"{pl.roi * 100:.2f}%",
                    delta=f"{(pl.roi * 100 - 6.12):+.2f} pp vs R2")
    else:
        st.info("Press **Calculate** in any tab to compute the P&L.")

# ── DECISION LOG ──────────────────────────────────────────────────────────────
with tab_log:
    st.header("Decision Log & Accept-Rule Checker")
    st.caption("Enter the real game index for decisions you've tested in the real game.")

    result = st.session_state.result
    params = st.session_state.params

    st.subheader("Real game index overrides (optional)")
    ri_fg = st.number_input("F&G real index (from game)", 0.90, 1.20, value=0.90, step=0.0001,
                            format="%.4f", key="ri_fg")
    ri_land = st.number_input("LAND real index (from game)", 0.90, 1.20, value=0.90, step=0.0001,
                              format="%.4f", key="ri_land")
    ri_dom = st.number_input("Dominick's real index (from game)", 0.90, 1.20, value=0.90, step=0.0001,
                             format="%.4f", key="ri_dom")

    real_overrides = {}
    if ri_fg != 0.90:
        real_overrides["fg"] = ri_fg
    if ri_land != 0.90:
        real_overrides["land"] = ri_land
    if ri_dom != 0.90:
        real_overrides["dominicks"] = ri_dom

    if result and st.button("Run Accept-Rule Checker"):
        baseline_params = build_r2_scenario()
        baseline_result = run_simulation(baseline_params)
        checks = accept_rule_checker(result, baseline_result, params, real_overrides)
        for c in checks:
            verdict = c.get("model_verdict", "?")
            color = "green" if verdict in ("ACCEPT", "GO") else "red" if verdict in ("REJECT", "NO-GO") else "orange"
            st.markdown(f"**[{verdict}]** {c['decision']}")
            st.caption(f"Threshold: {c['accept_threshold']}")
            st.caption(c["note"])
            st.divider()
    elif not result:
        st.info("Run a simulation first (press Calculate in any tab).")

    st.subheader("Export")
    if result:
        import io
        try:
            import openpyxl
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "P&L"
            pl = result.pl
            rows_data = [
                ("Metric", "Value"),
                ("Realized Revenue", pl.realized_revenue),
                ("Contracted Revenue", pl.contracted_revenue),
                ("Bonus/Penalty", pl.bonus_penalty),
                ("Material Purchases", pl.material_purchases),
                ("Transport", pl.transport),
                ("Supplier Admin", pl.supplier_admin),
                ("Bottling Permanent", pl.bottling_permanent),
                ("Bottling Flexible", pl.bottling_flexible),
                ("Mixing", pl.mixing),
                ("RM Locations", pl.rm_locations),
                ("RM Overflow", pl.rm_overflow),
                ("FG Locations", pl.fg_locations),
                ("FG Overflow", pl.fg_overflow),
                ("Scrap + Risk", pl.scrap + pl.risk),
                ("Projects", pl.projects),
                ("Distribution", pl.distribution),
                ("Interest Net", pl.interest_net),
                ("Overhead", pl.overhead_other),
                ("Operating Profit", pl.operating_profit),
                ("Investment", pl.investment),
                ("ROI", pl.roi),
            ]
            for r in rows_data:
                ws.append(r)
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            st.download_button(
                "Download P&L (.xlsx)",
                data=buf,
                file_name="tfc_scenario.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except ImportError:
            st.warning("Install openpyxl for Excel export: pip install openpyxl")

# ── SCENARIOS ─────────────────────────────────────────────────────────────────
with tab_scen:
    st.header("Scenario Comparison & Monte Carlo")
    st.caption(DISCLAIMER)

    sc_tab1, sc_tab2, sc_tab3 = st.tabs(["Compare Scenarios", "Monte Carlo", "Tornado"])

    with sc_tab1:
        st.subheader("Run Pre-built Scenarios")
        SCENARIOS_DIR = ROOT / "scenarios"
        yaml_files = sorted(SCENARIOS_DIR.glob("*.yaml"))
        scen_names = [f.stem for f in yaml_files]

        if st.button("Run all pre-built scenarios"):
            from tfc.engine.scenarios import load_scenario, compare_scenarios
            baseline = build_r2_scenario()
            rows = []
            progress = st.progress(0)
            for i, sf in enumerate(yaml_files):
                try:
                    scen = load_scenario(sf)
                    tbl = compare_scenarios(baseline, scen, n_seeds=3)
                    rows.append({
                        "Scenario": sf.stem,
                        "Base ROI": f"{tbl['baseline']['roi']:.2f}%",
                        "Scen ROI": f"{tbl['scenario']['roi']:.2f}%",
                        "Δ ROI": f"{tbl['delta']['roi']:+.2f}pp",
                        "Δ Profit": f"€{tbl['delta']['operating_profit']:+,.0f}",
                        "RM Overflow": f"{tbl['rm_overflow']:.0f}",
                        "PIT": f"{tbl['pit_utilization']:.1f}%",
                        "Warns": "⚠" if tbl["warnings"] else "✓",
                    })
                except Exception as e:
                    rows.append({"Scenario": sf.stem, "Base ROI": "ERROR", "Scen ROI": str(e)[:30]})
                progress.progress((i + 1) / len(yaml_files))
            st.dataframe(rows, use_container_width=True)

    with sc_tab2:
        st.subheader("Monte Carlo Analysis")
        scen_choice = st.selectbox("Scenario for MC", scen_names, key="mc_scen")
        n_mc = st.number_input("Number of runs", 50, 500, value=200, step=50, key="mc_n")

        if st.button("Run Monte Carlo"):
            from tfc.engine.scenarios import load_scenario
            from tfc.engine.montecarlo import run_monte_carlo, format_mc_report

            sf_path = SCENARIOS_DIR / f"{scen_choice}.yaml"
            scen = load_scenario(sf_path)
            with st.spinner(f"Running {n_mc} Monte Carlo simulations..."):
                mc = run_monte_carlo(scen, n_runs=n_mc)
            st.code(format_mc_report(mc, scen_choice))

            # Distribution chart
            try:
                import plotly.express as px
                fig = px.histogram(
                    x=mc.roi_samples * 100,
                    nbins=30,
                    labels={"x": "ROI (%)"},
                    title=f"ROI Distribution — {scen_choice} ({n_mc} runs)",
                )
                fig.add_vline(x=mc.baseline_roi * 100, line_dash="dash",
                              annotation_text="R2 baseline")
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.info("Install plotly for chart: pip install plotly")

    with sc_tab3:
        st.subheader("Tornado Sensitivity Chart")
        scen_choice_t = st.selectbox("Scenario for tornado", scen_names, key="tor_scen")

        if st.button("Run Tornado"):
            from tfc.engine.scenarios import load_scenario
            from tfc.engine.montecarlo import tornado_analysis, format_tornado
            sf_path = SCENARIOS_DIR / f"{scen_choice_t}.yaml"
            scen = load_scenario(sf_path)
            with st.spinner("Running tornado analysis..."):
                tornado = tornado_analysis(scen)
            st.code(format_tornado(tornado))

            try:
                import plotly.express as px
                top10 = tornado[:10]
                fig = px.bar(
                    x=[t["swing_pp"] for t in top10],
                    y=[t["name"] for t in top10],
                    orientation="h",
                    labels={"x": "ROI swing (pp)", "y": "Assumption"},
                    title=f"Tornado Chart — {scen_choice_t}",
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                pass

# ── ASSUMPTIONS ───────────────────────────────────────────────────────────────
with tab_assump:
    st.header("Assumption Overrides")
    st.caption(
        "Every value here is NOT from the real game. "
        "Change them to see how sensitive ROI is to each assumption. "
        "UNVERIFIED = not confirmed from any source."
    )

    assumptions = load_assumptions()
    unverified = list_unverified(assumptions)

    show_all = st.checkbox("Show all assumptions (including calibrated)", value=False)

    ov = st.session_state.assumption_overrides

    for name, a in assumptions.items():
        if not show_all and a["status"] != "UNVERIFIED":
            continue
        lo = a.get("min")
        hi = a.get("max")
        default = a.get("default")
        if lo is None or hi is None or isinstance(lo, bool) or isinstance(hi, bool):
            continue
        if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
            continue

        badge = "🔴 UNVERIFIED" if a["status"] == "UNVERIFIED" else "🟡 Calibrated"
        st.markdown(f"**{name}** {badge}")
        st.caption(a.get("reason", ""))

        cur = ov.get(name, default)
        step = (hi - lo) / 100.0 if (hi - lo) > 0 else 0.001
        val = st.slider(
            f"{name}", float(lo), float(hi), float(cur),
            step=float(step), key=f"assump_{name}"
        )
        ov[name] = val

    st.session_state.assumption_overrides = ov

    if st.button("Reset all assumptions to defaults"):
        st.session_state.assumption_overrides = {}
        st.rerun()

    calculate_button("assump")
