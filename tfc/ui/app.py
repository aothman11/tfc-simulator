"""TFC Practice Simulator — Streamlit UI (TFC-style redesign).

Run with:   streamlit run tfc/ui/app.py
"""
from __future__ import annotations
import copy
import pathlib
import sys

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

# ── CSS: TFC visual style ──────────────────────────────────────────────────────
st.markdown("""
<style>
/* App background */
.stApp { background-color: #f5f7fa; }

/* Sidebar dark navy */
[data-testid="stSidebar"] > div:first-child {
    background-color: #2d3561 !important;
    color: white !important;
}
[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stFileUploader label { color: white !important; }
[data-testid="stSidebar"] .stButton > button {
    background: #f27d00; color: white; border: none;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0px;
    border-bottom: 2px solid #dae8f0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    color: #666;
    font-size: 13px;
    padding: 8px 18px;
    margin: 0;
}
.stTabs [aria-selected="true"] {
    color: #8b1a4a !important;
    border-bottom: 3px solid #8b1a4a !important;
    font-weight: 600;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 16px; }

/* Metric tiles */
[data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 700; color: #333; }
[data-testid="stMetricLabel"] { font-size: 0.8rem; color: #666; }

/* Tables */
.tfc-section { background: #dae8f0; font-weight: bold; padding: 6px 10px; }

/* Buttons */
.stButton > button[kind="primary"] {
    background-color: #f27d00 !important;
    color: white !important;
    border: none !important;
}
.stButton > button:hover { opacity: 0.9; }

/* Expander headers */
.streamlit-expanderHeader { font-weight: 600; color: #2d3561; }

/* Disclaimer banner */
.disclaimer-banner {
    background: #c0392b; color: white; padding: 8px 16px;
    border-radius: 4px; font-weight: bold; font-size: 13px;
    text-align: center; margin-bottom: 14px;
}

/* Round chip */
.round-chip {
    display: inline-block;
    background: #f0f0f0;
    border: 1px solid #ccc;
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 12px;
    color: #555;
    margin-left: 8px;
    vertical-align: middle;
}

/* Role tab row */
.role-tab-row { display: flex; gap: 8px; margin-bottom: 8px; }
.role-tab {
    padding: 7px 18px; border-radius: 6px 6px 0 0;
    font-size: 13px; font-weight: 600; cursor: pointer;
    background: #e8e8e8; color: #555;
}
.role-tab.active { background: #f27d00; color: white; }

/* Insight panel */
.insight-panel { background: #fff; border-left: 3px solid #dae8f0; padding: 14px; font-size: 13px; }
.insight-panel h4 { font-size: 13px; font-weight: 700; color: #333; margin: 8px 0 2px 0; }
.insight-panel p { color: #555; margin: 0 0 6px 0; }
</style>
""", unsafe_allow_html=True)

# ── Disclaimer banner ─────────────────────────────────────────────────────────
st.markdown(
    '<div class="disclaimer-banner">⚠ PRACTICE MODEL – NOT THE REAL GAME – All numbers are approximate estimates only</div>',
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────
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


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🧃 TFC Practice Simulator")
st.sidebar.markdown(f"<small>{DISCLAIMER}</small>", unsafe_allow_html=True)
st.sidebar.divider()

st.sidebar.markdown("**📋 My Company** | **💰 Finance** | **⚙️ PIT**")
st.sidebar.divider()

st.sidebar.markdown("**Round selector:**")
for r in range(5):
    dot = "🔴" if r == 0 else "⚫"
    st.sidebar.markdown(f"{dot} Round {r}")

st.sidebar.divider()

presets = {"Round 2 baseline": "r2", "Round 3 (current screen)": "r3"}
preset = st.sidebar.selectbox("Load preset", list(presets.keys()))
if st.sidebar.button("Load preset"):
    from tfc.engine.simulation import build_r3_scenario
    if presets[preset] == "r2":
        st.session_state.params = build_r2_scenario()
    else:
        st.session_state.params = build_r3_scenario()
    st.session_state.result = None
    st.rerun()

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

# ── Helper functions ──────────────────────────────────────────────────────────

def calculate_button(key: str = "calc") -> bool:
    col1, col2 = st.columns([1, 5])
    calc = col1.button("▶ Calculate", key=f"calc_{key}", type="primary")
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


def make_kpi_line_chart(title: str, values: list, rounds: list = None,
                        y_suffix: str = "", color: str = "#8b1a4a"):
    """Return a Plotly figure for a KPI line chart."""
    if rounds is None:
        rounds = [-2, -1, 0]
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        for r in rounds:
            fig.add_vrect(x0=r - 0.15, x1=r + 0.15, fillcolor="#f27d00",
                          opacity=0.15, line_width=0)
        fig.add_trace(go.Scatter(
            x=rounds, y=values,
            mode="lines+markers+text",
            line=dict(color=color, width=2),
            marker=dict(color=color, size=8),
            text=[f"{v:.1f}{y_suffix}" for v in values],
            textposition="bottom center",
        ))
        fig.update_layout(
            title=dict(text=title, font=dict(size=13, color="#333"), x=0.02),
            xaxis=dict(title="Round:", tickvals=rounds, showgrid=False, zeroline=False),
            yaxis=dict(showgrid=True, gridcolor="#eee", zeroline=False),
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=40, r=20, t=40, b=40),
            height=220, showlegend=False,
        )
        return fig
    except ImportError:
        return None


def tfc_table_html(rows: list, section_key: str = "section") -> str:
    """Render a TFC-style HTML table."""
    html = ['<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:12px;">']
    alt = False
    for row in rows:
        if section_key in row and len(row) == 1:
            html.append(
                f'<tr><td colspan="99" style="background:#dae8f0;font-weight:bold;'
                f'padding:6px 10px;border-bottom:1px solid #c5d9e8;">'
                f'{row[section_key]}</td></tr>'
            )
            alt = False
        else:
            bg = "#f5f7fa" if alt else "white"
            cells = "".join(
                f'<td style="padding:5px 10px;border-bottom:1px solid #eee;">{v}</td>'
                for v in row.values()
            )
            html.append(f'<tr style="background:{bg};">{cells}</tr>')
            alt = not alt
    html.append('</table>')
    return "\n".join(html)


def insight_panel(items: list[tuple[str, str]]) -> str:
    """items: list of (heading, text) for insight panel."""
    content = ""
    for heading, text in items:
        content += f"<h4>ⓘ {heading}</h4><p>{text}</p>"
    return f'<div class="insight-panel">{content}</div>'


# ── R2 reference values (flat history lines) ──────────────────────────────────
R2_ROI = 6.12
R2_RM_UTIL = 93.4
R2_FG_UTIL = 70.7
R2_PROD_PLAN = 78.7
R2_SERVICE = 94.0
ROUNDS = [-2, -1, 0]


def flat_vals(v: float) -> list:
    return [v, v, v]


# ── MAIN TABS ─────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-size:15px;font-weight:700;color:#2d3561;margin-bottom:4px;">'
    'ROUND 0 <span class="round-chip">Read-only</span></div>',
    unsafe_allow_html=True,
)

tab_purch, tab_ops, tab_sales, tab_sc, tab_overview, tab_scen, tab_assump = st.tabs([
    "🛒 Purchasing",
    "🏭 Operations",
    "📦 Sales",
    "🔗 Supply Chain",
    "📊 Overview",
    "🎲 Scenarios",
    "🔧 Assumptions",
])

# ══════════════════════════════════════════════════════════════════════════════
# PURCHASING
# ══════════════════════════════════════════════════════════════════════════════
with tab_purch:
    p_sub = st.tabs(["dashboard", "supplier", "component", "analysis", "decision log"])
    p_dash, p_sup, p_comp, p_analysis, p_log = p_sub

    params = st.session_state.params
    result = st.session_state.result

    # ── Purchasing > dashboard ─────────────────────────────────────────────
    with p_dash:
        col_charts, col_insights = st.columns([7, 3])
        with col_charts:
            roi_val = result.pl.roi * 100 if result else R2_ROI
            fig_roi = make_kpi_line_chart("ROI (%)", flat_vals(roi_val), y_suffix="%")
            if fig_roi:
                st.plotly_chart(fig_roi, use_container_width=True, key="p_roi")
            else:
                st.metric("ROI (%)", f"{roi_val:.2f}%")

            svc_val = 94.0
            if result:
                svcs = [v.get("service_lines", 0) * 100
                        for v in result.service_by_customer.values()]
                svc_val = sum(svcs) / len(svcs) if svcs else 94.0
            fig_svc = make_kpi_line_chart("Service level (%)", flat_vals(svc_val), y_suffix="%")
            if fig_svc:
                st.plotly_chart(fig_svc, use_container_width=True, key="p_svc")

        with col_insights:
            roi_insight = (
                "The company is making a loss. Measures must quickly be taken."
                if roi_val < 0 else
                f"ROI is {roi_val:.1f}%. Target: improve toward 8%+."
            )
            st.markdown(insight_panel([
                ("ROI (%)", roi_insight),
                ("Service level", f"Average service level is {svc_val:.1f}%. Target ≥ 94%."),
                ("Supplier index", "Supplier price index reflects current payment terms and VMI."),
                ("Customer index", "Customer index reflects trade unit, VMI, and promo pressure."),
            ]), unsafe_allow_html=True)

        calculate_button("p_dash")

    # ── Purchasing > supplier ──────────────────────────────────────────────
    with p_sup:
        st.markdown("**Supplier settings** — set VMI and payment terms per supplier.")
        suppliers = [
            ("orange", "🍊 Orange"),
            ("pet", "🍶 PET"),
            ("pack", "📦 Pack"),
            ("mango", "🥭 Mango"),
            ("vitamin_c", "💊 Vitamin C"),
        ]
        hdr = st.columns([2, 1, 1, 1, 1])
        hdr[0].markdown("**💡 Supplier**")
        hdr[1].markdown("**ⓘ VMI**")
        hdr[2].markdown("**ⓘ Payment term (wks)**")
        hdr[3].markdown("**ⓘ Price index**")
        hdr[4].markdown("**ⓘ Stock index**")

        st.divider()
        for sid, label in suppliers:
            c0, c1, c2, c3, c4 = st.columns([2, 1, 1, 1, 1])
            c0.markdown(label)
            vmi = c1.checkbox("", value=params.supplier_vmi.get(sid, False),
                              key=f"svmi_{sid}", label_visibility="collapsed")
            params.supplier_vmi[sid] = vmi
            pt = c2.number_input("", 1, 20,
                                 value=params.supplier_payment_terms.get(sid, 8),
                                 key=f"spt_{sid}", label_visibility="collapsed")
            params.supplier_payment_terms[sid] = pt
            pi_label = "VMI active" if vmi else "standard"
            c3.caption(pi_label)
            c4.caption("—")

        st.session_state.params = params

    # ── Purchasing > component ─────────────────────────────────────────────
    with p_comp:
        st.markdown("**Component settings** — safety stock and lot size in weeks.")
        components = [
            ("orange", "🍊 Orange"),
            ("pet", "🍶 PET"),
            ("pack", "📦 Pack"),
            ("mango", "🥭 Mango"),
            ("vitamin_c", "💊 Vitamin C"),
        ]
        hdr2 = st.columns([2, 1, 1])
        hdr2[0].markdown("**💡 Component**")
        hdr2[1].markdown("**ⓘ Safety stock (wks)**")
        hdr2[2].markdown("**ⓘ Lot size (wks)**")
        st.divider()

        for sid, label in components:
            c0, c1, c2 = st.columns([2, 1, 1])
            c0.markdown(label)
            ss = c1.number_input("", 0.5, 10.0,
                                 value=float(params.rm_safety_stock_weeks.get(sid, 2.0)),
                                 step=0.5, key=f"ss_{sid}", label_visibility="collapsed")
            params.rm_safety_stock_weeks[sid] = ss
            ls = c2.number_input("", 0.5, 10.0,
                                 value=float(params.rm_lot_size_weeks.get(sid, 2.0)),
                                 step=0.5, key=f"ls_{sid}", label_visibility="collapsed")
            params.rm_lot_size_weeks[sid] = ls

        st.session_state.params = params

    # ── Purchasing > analysis ──────────────────────────────────────────────
    with p_analysis:
        st.info("Analysis charts — run simulation to populate.")

    # ── Purchasing > decision log ──────────────────────────────────────────
    with p_log:
        params = st.session_state.params
        rows = [{"section": "Suppliers"}]
        for sid, label in [("orange", "Orange"), ("pet", "PET"), ("pack", "Pack"),
                           ("mango", "Mango"), ("vitamin_c", "Vitamin C")]:
            rows.append({
                "Supplier": f"💡 {label}",
                "VMI": "Yes" if params.supplier_vmi.get(sid, False) else "No",
                "Payment term (wks)": str(params.supplier_payment_terms.get(sid, 8)),
            })
        rows.append({"section": "Components"})
        for sid, label in [("orange", "Orange"), ("pet", "PET"), ("pack", "Pack"),
                           ("mango", "Mango"), ("vitamin_c", "Vitamin C")]:
            rows.append({
                "Component": f"💡 {label}",
                "ⓘ Safety stock (wks)": str(params.rm_safety_stock_weeks.get(sid, 2.0)),
                "ⓘ Lot size (wks)": str(params.rm_lot_size_weeks.get(sid, 2.0)),
            })
        st.markdown(tfc_table_html(rows), unsafe_allow_html=True)
        calculate_button("p_log")
        result = st.session_state.result
        if result:
            show_unverified_warning(result)


# ══════════════════════════════════════════════════════════════════════════════
# OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab_ops:
    o_sub = st.tabs(["dashboard", "warehousing", "mixing and bottling", "analysis", "decision log"])
    o_dash, o_wh, o_mix, o_analysis, o_log = o_sub

    params = st.session_state.params
    result = st.session_state.result

    # ── Operations > dashboard ─────────────────────────────────────────────
    with o_dash:
        roi_val = result.pl.roi * 100 if result else R2_ROI
        rm_util = (result.rm_total_pallets / params.rm_locations * 100
                   if result and params.rm_locations > 0 else R2_RM_UTIL)
        fg_util = (result.fg_total_pallets / params.fg_locations * 100
                   if result and params.fg_locations > 0 else R2_FG_UTIL)
        pit_val = (result.production_pit.get("pit_utilization", 0) * 100
                   if result else R2_PROD_PLAN)

        col_charts, col_insights = st.columns([7, 3])
        with col_charts:
            r1, r2 = st.columns(2)
            with r1:
                fig = make_kpi_line_chart("ROI (%)", flat_vals(roi_val), y_suffix="%")
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key="o_roi")
                else:
                    st.metric("ROI (%)", f"{roi_val:.2f}%")
                fig2 = make_kpi_line_chart("Cube util FG warehouse (%)",
                                           flat_vals(fg_util), y_suffix="%")
                if fig2:
                    st.plotly_chart(fig2, use_container_width=True, key="o_fg")
            with r2:
                fig3 = make_kpi_line_chart("Cube util RM warehouse (%)",
                                           flat_vals(rm_util), y_suffix="%")
                if fig3:
                    st.plotly_chart(fig3, use_container_width=True, key="o_rm")
                fig4 = make_kpi_line_chart("Production plan adherence (%)",
                                           flat_vals(pit_val), y_suffix="%")
                if fig4:
                    st.plotly_chart(fig4, use_container_width=True, key="o_pit")

        with col_insights:
            roi_txt = ("The company is making a loss. Measures must quickly be taken."
                       if roi_val < 0 else f"ROI is {roi_val:.1f}%.")
            rm_txt = ("The raw materials warehouse is relatively full."
                      if rm_util > 85 else "The raw materials warehouse has available space.")
            fg_txt = ("The finished goods warehouse is relatively empty, with pallet locations open."
                      if fg_util < 80 else "The finished goods warehouse is near capacity.")
            pit_txt = ("The production plan adherence on Swiss Fill 2 is low."
                       if pit_val < 85 else "Production plan adherence is satisfactory.")
            st.markdown(insight_panel([
                ("ROI (%)", roi_txt),
                ("Cube util RM warehouse", rm_txt),
                ("Cube util FG warehouse", fg_txt),
                ("Production plan adherence", pit_txt),
            ]), unsafe_allow_html=True)

        calculate_button("o_dash")

    # ── Operations > warehousing ───────────────────────────────────────────
    with o_wh:
        rm_cap = params.rm_locations
        fg_cap = params.fg_locations
        rm_use = int(result.rm_total_pallets) if result else 840
        fg_use = int(result.fg_total_pallets) if result else 1061
        rm_util_pct = f"{rm_use / rm_cap * 100:.1f}%" if rm_cap else "—"
        fg_util_pct = f"{fg_use / fg_cap * 100:.1f}%" if fg_cap else "—"
        rm_overflow = (f"{result.rm_overflow_avg_pallets / rm_cap * 100:.1f}%"
                       if result else "10.8%")
        fg_overflow = (f"{result.fg_overflow_avg_pallets / fg_cap * 100:.1f}%"
                       if result else "0.1%")

        wh_rows = [
            {"section": "Warehousing"},
            {
                "Inbound/Outbound": "Raw materials warehouse",
                "ⓘ Capacity": str(rm_cap),
                "ⓘ Usage": str(rm_use),
                "ⓘ Cube util (%)": rm_util_pct,
                "ⓘ Overflow (%)": rm_overflow,
                "ⓘ Order lines/wk": "1.0",
                "ⓘ Pallets/wk": "212.4",
                "ⓘ Hours/wk": "74",
                "ⓘ Flex FTE": str(params.rm_perm_fte),
            },
            {"section": "Outsourcing tank yard"},
            {
                "Inbound/Outbound": "💡 DC Netherlands",
                "ⓘ Capacity": str(fg_cap),
                "ⓘ Usage": str(fg_use),
                "ⓘ Cube util (%)": fg_util_pct,
                "ⓘ Overflow (%)": fg_overflow,
                "ⓘ Order lines/wk": "17.8",
                "ⓘ Pallets/wk": "334.5",
                "ⓘ Hours/wk": "100",
                "ⓘ Flex FTE": str(params.fg_perm_fte),
            },
        ]
        st.markdown(tfc_table_html(wh_rows), unsafe_allow_html=True)

        st.markdown("#### Warehouse workload charts")
        try:
            import plotly.graph_objects as go
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Raw materials warehouse**")
                import numpy as np
                rng = np.random.default_rng(42)
                hours_rm = rng.exponential(20, 26).tolist()
                fig_rm = go.Figure(go.Bar(
                    y=list(range(len(hours_rm))), x=hours_rm,
                    orientation="h", marker_color="#8b1a4a",
                    name="hours per day"
                ))
                fig_rm.update_layout(
                    xaxis_title="hours per day", yaxis_title="week",
                    height=220, margin=dict(l=30, r=10, t=20, b=30),
                    plot_bgcolor="white", paper_bgcolor="white",
                )
                st.plotly_chart(fig_rm, use_container_width=True, key="wh_rm")
            with col_b:
                st.markdown("**💡 DC Netherlands**")
                hours_fg = rng.exponential(15, 26).tolist()
                fig_fg = go.Figure(go.Bar(
                    y=list(range(len(hours_fg))), x=hours_fg,
                    orientation="h", marker_color="#8b1a4a",
                ))
                fig_fg.update_layout(
                    xaxis_title="hours per day", yaxis_title="week",
                    height=220, margin=dict(l=30, r=10, t=20, b=30),
                    plot_bgcolor="white", paper_bgcolor="white",
                )
                st.plotly_chart(fig_fg, use_container_width=True, key="wh_fg")
        except ImportError:
            st.info("Install plotly for warehouse charts: pip install plotly")

    # ── Operations > mixing and bottling ──────────────────────────────────
    with o_mix:
        pit = result.production_pit if result else {}
        run_h = pit.get("production_h_per_week", 62.6)
        co_h = pit.get("changeover_h_per_week", 12.1)
        from tfc.engine.loader import load_assumptions as _la
        _a = _la()
        bd_h = float(_a.get("breakdown_hours_per_week", {}).get("default", 10.8))
        total_h = run_h + co_h + bd_h
        unused_h = max(0.0, 84 - total_h - 9.4)
        ot_h = pit.get("overtime_h_per_week", 9.4) if result else 9.4
        total_avail = run_h + co_h + bd_h + unused_h + ot_h
        def pct(x): return f"{x / total_avail * 100:.1f}%" if total_avail else "—"

        mb_rows = [
            {"section": "Mixing and Bottling"},
            {
                "💡 Line": "Swiss Fill 2",
                "ⓘ Run time (h)": f"{run_h:.1f}",
                "ⓘ Changeover (h)": f"{co_h:.1f}",
                "ⓘ Breakdown (h)": f"{bd_h:.1f}",
                "ⓘ Unused (h)": f"{unused_h:.1f}",
                "ⓘ Overtime (h)": f"{ot_h:.1f}",
                "ⓘ Run (%)": pct(run_h),
                "ⓘ Changeover (%)": pct(co_h),
                "ⓘ Breakdown (%)": pct(bd_h),
                "ⓘ Unused (%)": pct(unused_h),
                "ⓘ Overtime (%)": pct(ot_h),
                "ⓘ Prod plan (%)": f"{pit.get('pit_utilization', 0.787) * 100:.1f}%",
            },
        ]
        st.markdown(tfc_table_html(mb_rows), unsafe_allow_html=True)

        st.markdown("#### Swiss Fill 2 — Hours per week")
        try:
            import plotly.graph_objects as go
            cats = ["Overtime", "Unutilized", "Breakdown", "Changeover", "Run time"]
            vals_h = [ot_h, unused_h, bd_h, co_h, run_h]
            fig_mb = go.Figure(go.Bar(
                y=cats, x=vals_h, orientation="h",
                marker_color="#8b1a4a",
                text=[f"{v:.1f}" for v in vals_h],
                textposition="outside",
            ))
            fig_mb.update_layout(
                xaxis_title="Hours per week",
                plot_bgcolor="white", paper_bgcolor="white",
                height=260, margin=dict(l=100, r=60, t=30, b=30),
            )
            st.plotly_chart(fig_mb, use_container_width=True, key="mb_chart")
        except ImportError:
            pass

        st.markdown(tfc_table_html([{"section": "Mixer"}, {"Mixer": "Fruitmix MQ",
                                     "ⓘ Cleaning time": "—", "ⓘ Average lot": "—"}]),
                    unsafe_allow_html=True)

    # ── Operations > analysis ──────────────────────────────────────────────
    with o_analysis:
        st.info("Analysis charts — run simulation to populate.")

    # ── Operations > decision log ──────────────────────────────────────────
    with o_log:
        params = st.session_state.params
        line_opts = ["swiss_fill_2", "swiss_fill_1", "multiflex_1", "topspeed_1"]
        line_labels = ["Swiss Fill 2 (current)", "Swiss Fill 1", "MultiFlex 1", "TopSpeed 1"]

        st.markdown("#### Configure operations decisions")
        col1, col2 = st.columns(2)
        params.rm_locations = col1.number_input(
            "RM pallet locations", 100, 2000, value=params.rm_locations, step=50, key="rm_loc")
        params.rm_perm_fte = col1.number_input(
            "RM permanent FTE", 1, 10, value=params.rm_perm_fte, key="rm_fte")
        params.fg_locations = col2.number_input(
            "FG pallet locations", 100, 3000, value=params.fg_locations, step=50, key="fg_loc")
        params.fg_perm_fte = col2.number_input(
            "FG permanent FTE", 1, 10, value=params.fg_perm_fte, key="fg_fte")

        line_idx = line_opts.index(params.bottling_line) if params.bottling_line in line_opts else 0
        chosen_label = st.selectbox("Bottling line", line_labels, index=line_idx, key="line_sel2")
        params.bottling_line = line_opts[line_labels.index(chosen_label)]
        params.shifts = st.number_input("Shifts", 1, 3, value=params.shifts, key="shifts")

        outsource_opts = [None, "conventional", "automated", "mcc"]
        out_idx = outsource_opts.index(params.outsource_fg) if params.outsource_fg in outsource_opts else 0
        out_str = st.selectbox(
            "FG Warehouse Outsourcing", ["None", "Conventional", "Automated", "MCC"],
            index=out_idx, key="fg_outsource")
        params.outsource_fg = None if out_str == "None" else out_str.lower()

        params.inflate_pet = st.checkbox(
            "💡 Inflate PET bottles (€700K investment, €70K/round)",
            value=params.inflate_pet, key="inflate")
        if params.inflate_pet:
            st.info("Preforms cost 50% of ready PET. Transport saving is UNVERIFIED (see Assumptions tab).")

        st.session_state.params = params
        st.markdown("---")

        rows_log = [
            {"section": "Raw materials warehouse"},
            {"ⓘ Number of pallet locations": str(params.rm_locations),
             " ": ""},
            {"ⓘ Number of permanent employees (FTE)": str(params.rm_perm_fte),
             " ": ""},
            {"section": "Mixers available"},
            {"💡 Fruitmix MQ": "", " ": ""},
            {"section": "Line settings"},
            {"Bottling line": f"💡 {chosen_label}", " ": ""},
            {"ⓘ Number of shifts": str(params.shifts), " ": ""},
            {"section": "Finished goods warehouse"},
            {"💡 DC Netherlands": "", " ": ""},
            {"ⓘ Number of pallet locations": str(params.fg_locations), " ": ""},
            {"ⓘ Number of permanent employees (FTE)": str(params.fg_perm_fte), " ": ""},
        ]
        st.markdown(tfc_table_html(rows_log), unsafe_allow_html=True)
        calculate_button("o_log")
        result = st.session_state.result
        if result:
            show_unverified_warning(result)
            col_a, col_b = st.columns(2)
            col_a.metric("RM pallets needed", f"{result.rm_total_pallets:.0f}")
            col_b.metric("FG pallets avg", f"{result.fg_total_pallets:.0f}")
            if result.rm_overflow_avg_pallets > 0:
                col_a.error(f"⚠ RM OVERFLOW: {result.rm_overflow_avg_pallets:.0f} pallets")
            else:
                col_a.success("✓ RM fits")
            if result.fg_overflow_avg_pallets > 0:
                col_b.warning(f"FG overflow: {result.fg_overflow_avg_pallets:.0f} pallets")
            else:
                col_b.success("✓ FG no overflow")


# ══════════════════════════════════════════════════════════════════════════════
# SALES
# ══════════════════════════════════════════════════════════════════════════════
with tab_sales:
    s_sub = st.tabs(["dashboard", "customer", "product", "analysis", "decision log"])
    s_dash, s_cust, s_prod, s_analysis, s_log = s_sub

    params = st.session_state.params
    result = st.session_state.result

    # ── Sales > dashboard ──────────────────────────────────────────────────
    with s_dash:
        roi_val = result.pl.roi * 100 if result else R2_ROI
        col_charts, col_insights = st.columns([7, 3])
        with col_charts:
            fig = make_kpi_line_chart("ROI (%)", flat_vals(roi_val), y_suffix="%")
            if fig:
                st.plotly_chart(fig, use_container_width=True, key="s_roi")
            else:
                st.metric("ROI", f"{roi_val:.2f}%")

            if result:
                svc_rows = []
                for cid, svc in result.service_by_customer.items():
                    sl = svc.get("service_lines", 0) * 100
                    svc_rows.append({
                        "Customer": cid.upper(),
                        "ⓘ Order-line service (%)": f"{sl:.1f}%",
                        "ⓘ vs promise": f"{sl - 94.0:+.1f} pp",
                        "Status": "✓ OK" if sl >= 94.0 else "✗ BELOW 94%",
                    })
                st.markdown(tfc_table_html(svc_rows), unsafe_allow_html=True)
            else:
                st.caption("Run simulation to see service levels per customer.")

        with col_insights:
            st.markdown(insight_panel([
                ("ROI (%)", f"ROI is {roi_val:.1f}%."),
                ("Service level", "Ensure all customers are ≥ 94% order-line service."),
                ("Customer index", "Index reflects VMI, trade unit, promo pressure, deadline."),
            ]), unsafe_allow_html=True)

        calculate_button("s_dash")

    # ── Sales > customer ───────────────────────────────────────────────────
    with s_cust:
        for cid, cname in [("fg", "Food & Groceries (F&G)"), ("land", "LAND Market"),
                           ("dominicks", "Dominick's")]:
            with st.expander(cname, expanded=True):
                col1, col2 = st.columns(2)
                vmi = col1.checkbox("Customer VMI", value=params.customer_vmi.get(cid, False),
                                    key=f"vmi_{cid}")
                params.customer_vmi[cid] = vmi
                if vmi:
                    col2.info("VMI active → trade unit → Pallet, deadline → 14:00")

                pterm = col1.number_input(
                    "ⓘ Payment term (weeks)", 0, 8,
                    value=params.customer_payment_terms.get(cid, 1), key=f"pt_{cid}"
                )
                params.customer_payment_terms[cid] = pterm

                pressure_opts = ["none", "low", "middle", "heavy"]
                pp_idx = pressure_opts.index(params.promotional_pressure.get(cid, "none"))
                pp = col2.selectbox("ⓘ Promo pressure", pressure_opts, index=pp_idx,
                                    key=f"pp_{cid}")
                params.promotional_pressure[cid] = pp

                horizon_opts = ["short", "long"]
                ph_idx = horizon_opts.index(params.promotion_horizon.get(cid, "short"))
                ph = col1.selectbox("ⓘ Promo horizon", horizon_opts, index=ph_idx,
                                    key=f"ph_{cid}")
                params.promotion_horizon[cid] = ph

                if not vmi:
                    tu_opts = ["box", "pallet_layer", "pallet"]
                    tu_idx = tu_opts.index(params.trade_unit.get(cid, "pallet_layer"))
                    tu = col2.selectbox("ⓘ Trade unit", tu_opts, index=tu_idx, key=f"tu_{cid}")
                    params.trade_unit[cid] = tu

                dl_opts = ["14:00", "15:00", "16:00", "17:00", "18:00",
                           "19:00", "20:00", "21:00", "23:59"]
                cur_dl = params.order_deadline.get(cid, "20:00")
                if vmi:
                    cur_dl = "14:00"
                dl_idx = dl_opts.index(cur_dl) if cur_dl in dl_opts else 6
                dl = col1.selectbox("ⓘ Order deadline", dl_opts, index=dl_idx,
                                    key=f"dl_{cid}", disabled=vmi)
                params.order_deadline[cid] = "14:00" if vmi else dl

        st.session_state.params = params

    # ── Sales > product ────────────────────────────────────────────────────
    with s_prod:
        params = st.session_state.params
        params.service_promise = st.slider(
            "ⓘ Service promise (%)", 90, 99,
            int(params.service_promise * 100), key="svc_promise") / 100.0
        params.requested_shelf_life_pct = st.slider(
            "ⓘ Requested shelf life (%)", 40, 85,
            int(params.requested_shelf_life_pct * 100), key="sl_pct") / 100.0
        st.session_state.params = params

    # ── Sales > analysis ───────────────────────────────────────────────────
    with s_analysis:
        st.info("Analysis charts — run simulation to populate.")

    # ── Sales > decision log ───────────────────────────────────────────────
    with s_log:
        params = st.session_state.params
        sl_rows = [{"section": "Customer settings"}]
        for cid, cname in [("fg", "F&G"), ("land", "LAND"), ("dominicks", "Dominick's")]:
            sl_rows.append({
                "💡 Customer": cname,
                "ⓘ VMI": "Yes" if params.customer_vmi.get(cid) else "No",
                "ⓘ Payment term": str(params.customer_payment_terms.get(cid, 1)) + " wks",
                "ⓘ Promo pressure": params.promotional_pressure.get(cid, "none"),
                "ⓘ Promo horizon": params.promotion_horizon.get(cid, "short"),
                "ⓘ Trade unit": params.trade_unit.get(cid, "pallet_layer"),
                "ⓘ Deadline": params.order_deadline.get(cid, "20:00"),
            })
        sl_rows.append({"section": "Product settings"})
        sl_rows.append({
            "ⓘ Service promise": f"{params.service_promise * 100:.0f}%",
            "ⓘ Shelf life (%)": f"{params.requested_shelf_life_pct * 100:.0f}%",
        })
        st.markdown(tfc_table_html(sl_rows), unsafe_allow_html=True)
        calculate_button("s_log")
        result = st.session_state.result
        if result:
            show_unverified_warning(result)


# ══════════════════════════════════════════════════════════════════════════════
# SUPPLY CHAIN
# ══════════════════════════════════════════════════════════════════════════════
with tab_sc:
    sc_sub = st.tabs(["dashboard", "planning", "analysis", "decision log"])
    sc_dash, sc_plan, sc_analysis, sc_log = sc_sub

    params = st.session_state.params
    result = st.session_state.result

    # ── Supply Chain > dashboard ───────────────────────────────────────────
    with sc_dash:
        pit_val = (result.production_pit.get("pit_utilization", 0) * 100
                   if result else R2_PROD_PLAN)
        col_charts, col_insights = st.columns([7, 3])
        with col_charts:
            fig_pit = make_kpi_line_chart("PIT Utilization (%)", flat_vals(pit_val), y_suffix="%")
            if fig_pit:
                st.plotly_chart(fig_pit, use_container_width=True, key="sc_pit")
            else:
                st.metric("PIT Utilization", f"{pit_val:.1f}%")

            rm_of = result.rm_overflow_avg_pallets if result else 0
            fig_rm = make_kpi_line_chart("RM Overflow (pallets)", flat_vals(rm_of))
            if fig_rm:
                st.plotly_chart(fig_rm, use_container_width=True, key="sc_rm")

        with col_insights:
            pit_txt = ("PIT utilization is above 80% — risk of bottleneck."
                       if pit_val > 80 else f"PIT utilization is {pit_val:.1f}% — below 80% target.")
            rm_txt = ("No RM overflow detected." if rm_of == 0
                      else f"RM overflow: {rm_of:.0f} pallets on average.")
            st.markdown(insight_panel([
                ("PIT Utilization", pit_txt),
                ("RM Overflow", rm_txt),
                ("FG Safety Stock", "Review FG safety stock weeks per product."),
            ]), unsafe_allow_html=True)

        calculate_button("sc_dash")

    # ── Supply Chain > planning ────────────────────────────────────────────
    with sc_plan:
        params = st.session_state.params
        params.production_interval_days = st.number_input(
            "ⓘ Production interval (days)", 1, 30,
            value=params.production_interval_days, key="pi_days")
        params.frozen_period_weeks = st.number_input(
            "ⓘ Frozen period (weeks)", 0, 8,
            value=params.frozen_period_weeks, key="fp_wks")

        st.markdown("#### FG Safety Stock (weeks per product)")
        products = ["orange_1l", "c_power_1l", "mango_1l", "orange_pet", "c_power_pet", "mango_pet"]
        cols = st.columns(3)
        for i, pid in enumerate(products):
            c = cols[i % 3]
            ss = c.number_input(
                pid.replace("_", " ").title(), 0.5, 10.0,
                value=float(params.fg_safety_stock_weeks.get(pid, 2.0)),
                step=0.5, key=f"fg_ss_{pid}"
            )
            params.fg_safety_stock_weeks[pid] = ss

        st.session_state.params = params

    # ── Supply Chain > analysis ────────────────────────────────────────────
    with sc_analysis:
        if result:
            pit = result.production_pit
            col1, col2 = st.columns(2)
            pit_val2 = pit.get("pit_utilization", 0) * 100
            col1.metric("PIT Utilization", f"{pit_val2:.1f}%",
                        delta="⚠ > 80% target" if pit_val2 > 80 else "✓ ≤ 80%",
                        delta_color="inverse" if pit_val2 > 80 else "normal")
            col1.metric("Actual Line Utilization",
                        f"{pit.get('actual_utilization', 0) * 100:.1f}%")
            col2.metric("Production hours/week",
                        f"{pit.get('production_h_per_week', 0):.1f}h")
            col2.metric("Changeover hours/week",
                        f"{pit.get('changeover_h_per_week', 0):.1f}h")
        else:
            st.info("Analysis charts — run simulation to populate.")

    # ── Supply Chain > decision log ────────────────────────────────────────
    with sc_log:
        params = st.session_state.params
        products = ["orange_1l", "c_power_1l", "mango_1l", "orange_pet", "c_power_pet", "mango_pet"]
        sc_rows = [
            {"section": "Planning settings"},
            {"ⓘ Production interval (days)": str(params.production_interval_days), " ": ""},
            {"ⓘ Frozen period (weeks)": str(params.frozen_period_weeks), " ": ""},
            {"section": "FG Safety Stock (weeks)"},
        ]
        for pid in products:
            sc_rows.append({
                "💡 Product": pid.replace("_", " ").title(),
                "ⓘ Safety stock (wks)": str(params.fg_safety_stock_weeks.get(pid, 2.0)),
            })
        st.markdown(tfc_table_html(sc_rows), unsafe_allow_html=True)
        calculate_button("sc_log")
        result = st.session_state.result
        if result:
            show_unverified_warning(result)


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW (formerly Dashboard)
# ══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    st.markdown("## Company Overview")
    calculate_button("overview")
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
        col5.metric("PIT Utilization", f"{pit:.1f}%",
                    delta="⚠ > 80%" if pit > 80 else "✓ OK",
                    delta_color="inverse" if pit > 80 else "normal")
        col6.metric("RM Overflow Pallets", f"{result.rm_overflow_avg_pallets:.0f}",
                    delta="⚠ Overflow!" if result.rm_overflow_avg_pallets > 0 else "✓ OK",
                    delta_color="inverse" if result.rm_overflow_avg_pallets > 0 else "normal")
        col7.metric("FG Overflow Pallets", f"{result.fg_overflow_avg_pallets:.0f}",
                    delta="⚠ Overflow!" if result.fg_overflow_avg_pallets > 0 else "✓ OK",
                    delta_color="inverse" if result.fg_overflow_avg_pallets > 0 else "normal")

        st.divider()
        st.subheader("P&L Summary")
        pl = result.pl
        pl_rows = [
            {"section": "Revenue"},
            {"Line item": "Realized Revenue", "Amount (€)": f"€{pl.realized_revenue:,.0f}"},
            {"Line item": "  · Contracted sales", "Amount (€)": f"€{pl.contracted_revenue:,.0f}"},
            {"Line item": "  · Bonus / Penalty", "Amount (€)": f"€{pl.bonus_penalty:+,.0f}"},
            {"section": "Costs"},
            {"Line item": "Material purchases", "Amount (€)": f"€{pl.material_purchases:,.0f}"},
            {"Line item": "Operations", "Amount (€)": f"€{pl.operations_cost:,.0f}"},
            {"Line item": "Distribution", "Amount (€)": f"€{pl.distribution:,.0f}"},
            {"Line item": "Overhead (other)", "Amount (€)": f"€{pl.overhead_other:,.0f}"},
            {"section": "Result"},
            {"Line item": "OPERATING PROFIT", "Amount (€)": f"€{pl.operating_profit:,.0f}"},
            {"Line item": "Investment", "Amount (€)": f"€{pl.investment:,.0f}"},
            {"Line item": "ROI", "Amount (€)": f"{pl.roi * 100:.2f}%"},
        ]
        st.markdown(tfc_table_html(pl_rows), unsafe_allow_html=True)

        st.subheader("Service Level by Customer")
        svc_data = []
        for cid, svc in result.service_by_customer.items():
            sl = svc.get("service_lines", 0) * 100
            svc_data.append({
                "Customer": cid.upper(),
                "ⓘ Order-line service": f"{sl:.1f}%",
                "ⓘ vs promise": f"{sl - 94.0:+.1f} pp",
                "Status": "✓ OK" if sl >= 94.0 else "✗ BELOW 94%",
            })
        st.markdown(tfc_table_html(svc_data), unsafe_allow_html=True)

        if result.warnings:
            st.subheader("Warnings")
            for w in result.warnings:
                st.error(f"⚠ {w}")

        # Detailed P&L export
        with st.expander("Full P&L detail"):
            def row(label, val):
                return {"Line item": label, "Amount (€)": f"€{val:+,.0f}" if val != 0 else "—"}

            full_rows = [
                row("Realized Revenue", pl.realized_revenue),
                row("  Contracted sales", pl.contracted_revenue),
                row("  Bonus / Penalty", pl.bonus_penalty),
                row("Material purchases", -pl.material_purchases),
                row("Transport (PET)", -pl.transport),
                row("Supplier admin", -pl.supplier_admin),
                row("Bottling (permanent)", -pl.bottling_permanent),
                row("Bottling (flexible)", -pl.bottling_flexible),
                row("Mixing", -pl.mixing),
                row("RM locations", -pl.rm_locations),
                row("RM overflow", -pl.rm_overflow),
                row("FG locations", -pl.fg_locations),
                row("FG overflow", -pl.fg_overflow),
                row("Scrap + Risk", -(pl.scrap + pl.risk)),
                row("Projects", -pl.projects),
                row("Distribution", -pl.distribution),
                row("Interest (net)", -pl.interest_net),
                row("VMI fees (suppliers)", -pl.vmi_fees_suppliers),
                row("VMI fees (customers)", -pl.vmi_fees_customers),
                row("Inflate PET (running)", -pl.inflate_pet_depreciation),
                row("Overhead (other)", -pl.overhead_other),
                row("OPERATING PROFIT", pl.operating_profit),
            ]
            st.table(full_rows)

        # Excel export
        try:
            import io
            import openpyxl
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "P&L"
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
            for r_data in rows_data:
                ws.append(r_data)
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            st.download_button(
                "⬇ Download P&L (.xlsx)",
                data=buf,
                file_name="tfc_scenario.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except ImportError:
            st.caption("Install openpyxl for Excel export: pip install openpyxl")
    else:
        st.info("Press **▶ Calculate** to run the simulation.")


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_scen:
    st.markdown("## Scenario Comparison & Monte Carlo")
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
            rows2 = []
            progress = st.progress(0)
            for i, sf in enumerate(yaml_files):
                try:
                    scen = load_scenario(sf)
                    tbl = compare_scenarios(baseline, scen, n_seeds=3)
                    rows2.append({
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
                    rows2.append({"Scenario": sf.stem, "Base ROI": "ERROR",
                                  "Scen ROI": str(e)[:30]})
                progress.progress((i + 1) / len(yaml_files))
            st.dataframe(rows2, use_container_width=True)

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
            try:
                import plotly.express as px
                fig = px.histogram(
                    x=mc.roi_samples * 100, nbins=30,
                    labels={"x": "ROI (%)"},
                    title=f"ROI Distribution — {scen_choice} ({n_mc} runs)",
                    color_discrete_sequence=["#8b1a4a"],
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
                    color_discrete_sequence=["#8b1a4a"],
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                pass


# ══════════════════════════════════════════════════════════════════════════════
# ASSUMPTIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab_assump:
    st.markdown("## Assumption Overrides")
    st.caption(
        "Every value here is NOT from the real game. "
        "Change them to see how sensitive ROI is to each assumption. "
        "UNVERIFIED = not confirmed from any source."
    )

    assumptions = load_assumptions()
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
        val = st.slider(f"{name}", float(lo), float(hi), float(cur),
                        step=float(step), key=f"assump_{name}")
        ov[name] = val

    st.session_state.assumption_overrides = ov

    if st.button("Reset all assumptions to defaults"):
        st.session_state.assumption_overrides = {}
        st.rerun()

    calculate_button("assump")
