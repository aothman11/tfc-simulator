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
[data-testid="stSidebar"] .stFileUploader label,
[data-testid="stSidebar"] .stRadio label { color: white !important; }
[data-testid="stSidebar"] .stButton > button {
    background: #f27d00 !important; color: white !important; border: none !important;
}
/* Sidebar select box */
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: rgba(255,255,255,0.1) !important; color: white !important;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0px;
    border-bottom: 2px solid #dae8f0;
    background: transparent;
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
[data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700; color: #333; }
[data-testid="stMetricLabel"] { font-size: 0.8rem; color: #666; }

/* Buttons */
.stButton > button[kind="primary"] {
    background-color: #f27d00 !important;
    color: white !important;
    border: none !important;
    font-weight: 600;
}

/* Expander headers */
.streamlit-expanderHeader { font-weight: 600; color: #2d3561; }

/* Insight panel */
.insight-panel {
    background: #fff; border-left: 3px solid #dae8f0;
    padding: 14px 14px; font-size: 13px; min-height: 200px;
}
.insight-panel h4 { font-size: 13px; font-weight: 700; color: #333; margin: 10px 0 2px 0; }
.insight-panel p { color: #555; margin: 0 0 6px 0; }

/* Round chip */
.round-chip {
    display: inline-block; background: #f0f0f0; border: 1px solid #ccc;
    padding: 2px 10px; border-radius: 4px; font-size: 12px; color: #555;
    margin-left: 8px; vertical-align: middle;
}

/* TFC section-header row (simulated via markdown) */
.tfc-sec { background:#dae8f0; font-weight:bold; padding:5px 8px; font-size:13px; margin-top:8px; }
</style>
""", unsafe_allow_html=True)

# ── Disclaimer banner ─────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:#c0392b;color:white;padding:8px 16px;border-radius:4px;'
    'font-weight:bold;font-size:13px;text-align:center;margin-bottom:12px;">'
    '⚠ PRACTICE MODEL – NOT THE REAL GAME – All numbers are approximate estimates only'
    '</div>',
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


# ── Sidebar: My Company / Finance / PIT + Round selector ─────────────────────
with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:12px 0 4px 0;">'
        '<span style="font-size:22px;">📋</span><br>'
        '<span style="font-size:11px;font-weight:600;">My Company</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="text-align:center;padding:8px 0 4px 0;">'
        '<span style="font-size:22px;">💰</span><br>'
        '<span style="font-size:11px;font-weight:600;">Finance</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="text-align:center;padding:8px 0 4px 0;">'
        '<span style="font-size:22px;">⚙️</span><br>'
        '<span style="font-size:11px;font-weight:600;">Production<br>interval tool</span></div>',
        unsafe_allow_html=True,
    )
    st.divider()

    # Round selector styled as dots
    st.markdown(
        '<div style="background:#f27d00;padding:6px;border-radius:4px;text-align:center;'
        'font-size:12px;font-weight:700;margin-bottom:8px;">🍊 Round</div>',
        unsafe_allow_html=True,
    )
    for r_num in range(5):
        dot_color = "#8b1a4a" if r_num == 0 else "#555"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;padding:3px 8px;">'
            f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
            f'background:{dot_color};"></span>'
            f'<span style="font-size:13px;">{r_num}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.divider()

    # Presets & file upload
    st.markdown("**Load preset:**")
    presets = {"Round 2 baseline": "r2", "Round 3 (current screen)": "r3"}
    preset = st.selectbox("Preset", list(presets.keys()), label_visibility="collapsed")
    if st.button("Load preset"):
        from tfc.engine.simulation import build_r3_scenario
        if presets[preset] == "r2":
            st.session_state.params = build_r2_scenario()
        else:
            st.session_state.params = build_r3_scenario()
        st.session_state.result = None
        st.rerun()

    uploaded = st.file_uploader("Upload scenario YAML", type=["yaml", "yml"])
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

    st.divider()
    st.markdown(f'<small style="opacity:0.7;">{DISCLAIMER}</small>', unsafe_allow_html=True)


# ── Helper functions ──────────────────────────────────────────────────────────

def calculate_button(key: str = "calc") -> bool:
    col1, col2 = st.columns([1, 5])
    calc = col1.button("▶ Calculate", key=f"calc_{key}", type="primary")
    if calc:
        with st.spinner("Running simulation..."):
            run_and_store()
        return True
    return False


def show_unverified_warning(result):
    if result and result.unverified_assumptions_used:
        st.warning(
            f"⚠ Depends on **UNVERIFIED** assumptions: "
            f"{', '.join(result.unverified_assumptions_used[:6])}. "
            "Results are estimates only."
        )


def make_kpi_line_chart(title: str, values: list, rounds: list = None,
                        y_suffix: str = "", color: str = "#8b1a4a", height: int = 220):
    if rounds is None:
        rounds = [-2, -1, 0]
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        for r in rounds:
            fig.add_vrect(x0=r - 0.15, x1=r + 0.15,
                          fillcolor="#f27d00", opacity=0.15, line_width=0)
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
            height=height, showlegend=False,
        )
        return fig
    except ImportError:
        return None


def tfc_table_html(rows: list, section_key: str = "section") -> str:
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


def tfc_header_row(cols: list) -> str:
    """Returns a styled header row for a multi-column table."""
    cells = "".join(
        f'<th style="background:#dae8f0;padding:6px 10px;text-align:left;'
        f'font-size:12px;color:#444;border-bottom:2px solid #c5d9e8;">{c}</th>'
        for c in cols
    )
    return f'<thead><tr>{cells}</tr></thead>'


def insight_panel(items: list) -> str:
    content = ""
    for heading, text in items:
        content += f"<h4>ⓘ {heading}</h4><p>{text}</p>"
    return f'<div class="insight-panel">{content}</div>'


# ── R2 reference values ────────────────────────────────────────────────────────
R2_ROI = 6.12
R2_RM_UTIL = 93.4
R2_FG_UTIL = 70.7
R2_PROD_PLAN = 78.7
ROUNDS = [-2, -1, 0]

def flat_vals(v: float) -> list:
    return [v, v, v]

# Product display info
PRODUCTS = [
    ("orange_1l",    "💡 Fressie Orange 1 liter"),
    ("c_power_1l",   "💡 Fressie Orange/C-power 1 liter"),
    ("mango_1l",     "💡 Fressie Orange/Mango 1 liter"),
    ("orange_pet",   "💡 Fressie Orange PET"),
    ("c_power_pet",  "💡 Fressie Orange/C-power PET"),
    ("mango_pet",    "💡 Fressie Orange/Mango PET"),
]
R2_UNIT_PRICES = {
    "orange_1l": 0.379, "c_power_1l": 0.463, "mango_1l": 0.404,
    "orange_pet": 0.203, "c_power_pet": 0.295, "mango_pet": 0.230,
}
CUSTOMERS = [("fg", "💡 Food & Groceries"), ("land", "💡 LAND Market"), ("dominicks", "💡 Dominick's")]
SUPPLIERS = [
    ("orange", "💡 Orange"), ("pet", "💡 PET"), ("pack", "💡 Pack"),
    ("mango", "💡 Mango"), ("vitamin_c", "💡 Vitamin C"),
]

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
# PURCHASING  — sub-tabs: dashboard | supplier (read) | component (read) | analysis | decision log
# ══════════════════════════════════════════════════════════════════════════════
with tab_purch:
    p_sub = st.tabs(["dashboard", "supplier", "component", "analysis", "decision log"])
    p_dash, p_sup, p_comp, p_analysis, p_log = p_sub

    with p_dash:
        result = st.session_state.result
        roi_val = result.pl.roi * 100 if result else R2_ROI
        svc_val = 94.0
        if result:
            svcs = [v.get("service_lines", 0) * 100 for v in result.service_by_customer.values()]
            svc_val = sum(svcs) / len(svcs) if svcs else 94.0

        col_charts, col_insights = st.columns([7, 3])
        with col_charts:
            r1c, r2c = st.columns(2)
            with r1c:
                fig = make_kpi_line_chart("ROI (%)", flat_vals(roi_val), y_suffix="%")
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key="p_roi")
                else:
                    st.metric("ROI (%)", f"{roi_val:.2f}%")
            with r2c:
                fig2 = make_kpi_line_chart("Service level (%)", flat_vals(svc_val), y_suffix="%")
                if fig2:
                    st.plotly_chart(fig2, use_container_width=True, key="p_svc")
                else:
                    st.metric("Service level", f"{svc_val:.1f}%")

        with col_insights:
            roi_txt = ("The company is making a loss. Measures must quickly be taken."
                       if roi_val < 0 else f"ROI is {roi_val:.1f}%.")
            st.markdown(insight_panel([
                ("ROI (%)", roi_txt),
                ("Service level", f"Average service level {svc_val:.1f}%. Target ≥ 94%."),
                ("Supplier index", "Reflects payment terms and VMI settings."),
                ("Customer index", "Reflects trade unit, VMI, and promo pressure."),
            ]), unsafe_allow_html=True)

        calculate_button("p_dash")

    with p_sup:
        # Read-only supplier report
        st.markdown("**Supplier report** — read-only. Edit decisions in the Decision Log tab.")
        result = st.session_state.result
        sup_rows = [{"section": "Suppliers"}]
        params = st.session_state.params
        for sid, label in SUPPLIERS:
            sup_rows.append({
                "Supplier": label,
                "ⓘ VMI": "Yes" if params.supplier_vmi.get(sid, False) else "No",
                "ⓘ Payment term (wks)": str(params.supplier_payment_terms.get(sid, 8)),
                "ⓘ Price index": "—",
                "ⓘ Stock index": "—",
            })
        st.markdown(tfc_table_html(sup_rows), unsafe_allow_html=True)

    with p_comp:
        # Read-only component report (R2 baseline data)
        st.markdown("**Component report** — read-only. Edit SS/lot-size in Supply Chain → Decision Log.")
        params = st.session_state.params
        comp_data = [
            ("pack",      "💡 Pack 1 liter",  "92.3%", "564,440", "4.3", "€17,553"),
            ("pet",       "💡 PET",            "84.1%", "851,667", "4.2", "€46,566"),
            ("orange",    "💡 Orange",          "97.8%", "160,757", "4.5", "€70,610"),
            ("mango",     "💡 Mango",           "93.7%",  "14,089", "4.4", "€13,983"),
            ("vitamin_c", "💡 Vitamin C",       "81.5%",      "769", "4.2",    "€364"),
        ]
        comp_rows = [{"section": "Components"}]
        for sid, label, delrel, stock, stock_wks, stock_val in comp_data:
            ss = params.rm_safety_stock_weeks.get(sid, 2.0)
            ls = params.rm_lot_size_weeks.get(sid, 2.0)
            comp_rows.append({
                "Component": label,
                "ⓘ Delivery reliability": delrel,
                "ⓘ Stock (pcs/ltr)": stock,
                "ⓘ Stock (weeks)": stock_wks,
                "ⓘ Stock value": stock_val,
                "ⓘ SS (wks)": f"{ss:.1f}",
                "ⓘ Lot size (wks)": f"{ls:.1f}",
                "ⓘ Availability": "—",
            })
        st.markdown(tfc_table_html(comp_rows), unsafe_allow_html=True)

    with p_analysis:
        st.info("Analysis charts — run simulation to populate.")

    with p_log:
        # Purchasing decision log: supplier VMI + payment terms only
        st.markdown("#### Purchasing decisions")
        params = st.session_state.params
        st.markdown('<div class="tfc-sec">Suppliers</div>', unsafe_allow_html=True)
        hdr = st.columns([2, 1, 2])
        hdr[0].markdown("**💡 Supplier**")
        hdr[1].markdown("**ⓘ VMI**")
        hdr[2].markdown("**ⓘ Payment term (weeks)**")
        st.divider()
        for sid, label in SUPPLIERS:
            c0, c1, c2 = st.columns([2, 1, 2])
            c0.markdown(label)
            vmi = c1.checkbox("", value=params.supplier_vmi.get(sid, False),
                              key=f"svmi_{sid}", label_visibility="collapsed")
            params.supplier_vmi[sid] = vmi
            pt = c2.number_input("", 1, 20,
                                 value=params.supplier_payment_terms.get(sid, 8),
                                 key=f"spt_{sid}", label_visibility="collapsed")
            params.supplier_payment_terms[sid] = pt

        st.session_state.params = params
        calculate_button("p_log")
        result = st.session_state.result
        if result:
            show_unverified_warning(result)


# ══════════════════════════════════════════════════════════════════════════════
# OPERATIONS — sub-tabs: dashboard | warehousing | mixing and bottling | analysis | decision log
# ══════════════════════════════════════════════════════════════════════════════
with tab_ops:
    o_sub = st.tabs(["dashboard", "warehousing", "mixing and bottling", "analysis", "decision log"])
    o_dash, o_wh, o_mix, o_analysis, o_log = o_sub

    with o_dash:
        result = st.session_state.result
        params = st.session_state.params
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
                    st.metric("ROI", f"{roi_val:.2f}%")
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
            pit_txt = ("The production plan adherence on the Swiss Fill 2 is low."
                       if pit_val < 85 else "Production plan adherence is satisfactory.")
            st.markdown(insight_panel([
                ("ROI (%)", roi_txt),
                ("Cube util RM warehouse", rm_txt),
                ("Cube util FG warehouse", fg_txt),
                ("Production plan adherence", pit_txt),
            ]), unsafe_allow_html=True)

        calculate_button("o_dash")

    with o_wh:
        result = st.session_state.result
        params = st.session_state.params
        rm_cap = params.rm_locations
        fg_cap = params.fg_locations
        rm_use = int(result.rm_total_pallets) if result else 840
        fg_use = int(result.fg_total_pallets) if result else 1061
        rm_util_pct = f"{rm_use / rm_cap * 100:.1f}%" if rm_cap else "—"
        fg_util_pct = f"{fg_use / fg_cap * 100:.1f}%" if fg_cap else "—"
        rm_overflow = (f"{result.rm_overflow_avg_pallets / rm_cap * 100:.1f}%"
                       if result and rm_cap else "10.8%")
        fg_overflow = (f"{result.fg_overflow_avg_pallets / fg_cap * 100:.1f}%"
                       if result and fg_cap else "0.1%")

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

        st.markdown("#### Warehouse workload")
        try:
            import plotly.graph_objects as go
            import numpy as np
            rng = np.random.default_rng(42)
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Raw materials warehouse**")
                hours_rm = rng.exponential(20, 26).tolist()
                fig_rm = go.Figure(go.Bar(y=list(range(len(hours_rm))), x=hours_rm,
                                          orientation="h", marker_color="#8b1a4a"))
                fig_rm.update_layout(xaxis_title="hours per day", height=220,
                                     margin=dict(l=30, r=10, t=20, b=30),
                                     plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig_rm, use_container_width=True, key="wh_rm")
            with col_b:
                st.markdown("**💡 DC Netherlands**")
                hours_fg = rng.exponential(15, 26).tolist()
                fig_fg = go.Figure(go.Bar(y=list(range(len(hours_fg))), x=hours_fg,
                                          orientation="h", marker_color="#8b1a4a"))
                fig_fg.update_layout(xaxis_title="hours per day", height=220,
                                     margin=dict(l=30, r=10, t=20, b=30),
                                     plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig_fg, use_container_width=True, key="wh_fg")
        except ImportError:
            st.info("Install plotly for warehouse charts.")

    with o_mix:
        result = st.session_state.result
        pit = result.production_pit if result else {}
        run_h = pit.get("production_h_per_week", 62.6)
        co_h = pit.get("changeover_h_per_week", 12.1)
        try:
            from tfc.engine.loader import load_assumptions as _la
            _a = _la()
            bd_h = float(_a.get("breakdown_hours_per_week", {}).get("default", 10.8))
        except Exception:
            bd_h = 10.8
        ot_h = 9.4
        total_avail = run_h + co_h + bd_h + 3.9 + ot_h
        def pct(x): return f"{x / total_avail * 100:.1f}%" if total_avail else "—"
        unused_h = max(0.0, total_avail - run_h - co_h - bd_h - ot_h)

        mb_rows = [
            {"section": "Mixing and Bottling"},
            {
                "💡 Line": "Swiss Fill 2",
                "ⓘ Run (h)": f"{run_h:.1f}",
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

        try:
            import plotly.graph_objects as go
            cats = ["Overtime", "Unutilized", "Breakdown", "Changeover", "Run time"]
            vals_h = [ot_h, unused_h, bd_h, co_h, run_h]
            fig_mb = go.Figure(go.Bar(
                y=cats, x=vals_h, orientation="h", marker_color="#8b1a4a",
                text=[f"{v:.1f}" for v in vals_h], textposition="outside",
            ))
            fig_mb.update_layout(
                title="Swiss Fill 2 — Hours per week",
                xaxis_title="Hours per week",
                plot_bgcolor="white", paper_bgcolor="white",
                height=260, margin=dict(l=100, r=60, t=40, b=30),
            )
            st.plotly_chart(fig_mb, use_container_width=True, key="mb_chart")
        except ImportError:
            pass

        st.markdown(tfc_table_html([
            {"section": "Mixer"},
            {"Mixer": "💡 Fruitmix MQ", "ⓘ Cleaning time": "—", "ⓘ Average lot": "—"},
        ]), unsafe_allow_html=True)

    with o_analysis:
        st.info("Analysis charts — run simulation to populate.")

    with o_log:
        params = st.session_state.params
        st.markdown("#### Operations decisions")
        line_opts = ["swiss_fill_2", "swiss_fill_1", "multiflex_1", "topspeed_1"]
        line_labels = ["Swiss Fill 2 (current)", "Swiss Fill 1", "MultiFlex 1", "TopSpeed 1"]

        col1, col2 = st.columns(2)
        params.rm_locations = col1.number_input(
            "ⓘ RM pallet locations", 100, 2000, value=params.rm_locations, step=50, key="rm_loc")
        params.rm_perm_fte = col1.number_input(
            "ⓘ RM permanent FTE", 1, 10, value=params.rm_perm_fte, key="rm_fte")
        params.fg_locations = col2.number_input(
            "ⓘ FG pallet locations", 100, 3000, value=params.fg_locations, step=50, key="fg_loc")
        params.fg_perm_fte = col2.number_input(
            "ⓘ FG permanent FTE", 1, 10, value=params.fg_perm_fte, key="fg_fte")

        line_idx = line_opts.index(params.bottling_line) if params.bottling_line in line_opts else 0
        chosen_label = st.selectbox("Bottling line", line_labels, index=line_idx, key="line_sel2")
        params.bottling_line = line_opts[line_labels.index(chosen_label)]
        params.shifts = st.number_input("ⓘ Shifts", 1, 3, value=params.shifts, key="shifts")

        outsource_opts_map = {None: 0, "conventional": 1, "automated": 2, "mcc": 3}
        out_idx = outsource_opts_map.get(params.outsource_fg, 0)
        out_str = st.selectbox(
            "FG Warehouse Outsourcing", ["None", "Conventional", "Automated", "MCC"],
            index=out_idx, key="fg_outsource")
        params.outsource_fg = None if out_str == "None" else out_str.lower()

        params.inflate_pet = st.checkbox(
            "💡 Inflate PET bottles (€700K investment, €70K/round)",
            value=params.inflate_pet, key="inflate")
        if params.inflate_pet:
            st.info("Preforms cost 50% of ready PET. Transport saving is UNVERIFIED.")

        st.session_state.params = params

        # Decision log table
        rows_log = [
            {"section": "Raw materials warehouse"},
            {"ⓘ Pallet locations": str(params.rm_locations), "ⓘ Permanent FTE": str(params.rm_perm_fte)},
            {"section": "Mixers available"},
            {"💡 Fruitmix MQ": "", "": ""},
            {"section": "Line settings"},
            {"ⓘ Bottling line": f"💡 {chosen_label}", "ⓘ Shifts": str(params.shifts)},
            {"section": "Finished goods warehouse"},
            {"💡 DC Netherlands": "", "": ""},
            {"ⓘ Pallet locations": str(params.fg_locations), "ⓘ Permanent FTE": str(params.fg_perm_fte)},
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
# SALES — sub-tabs: dashboard | customer | product | customer product | product customer | analysis | decision log
# ══════════════════════════════════════════════════════════════════════════════
with tab_sales:
    s_sub = st.tabs([
        "dashboard", "customer", "product",
        "customer product", "product customer",
        "analysis", "decision log"
    ])
    s_dash, s_cust, s_prod, s_custprod, s_prodcust, s_analysis, s_log = s_sub

    with s_dash:
        result = st.session_state.result
        roi_val = result.pl.roi * 100 if result else R2_ROI
        col_charts, col_insights = st.columns([7, 3])
        with col_charts:
            r1, r2 = st.columns(2)
            with r1:
                fig = make_kpi_line_chart("ROI (%)", flat_vals(roi_val), y_suffix="%")
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key="s_roi")
                else:
                    st.metric("ROI", f"{roi_val:.2f}%")
                fig3 = make_kpi_line_chart("Obsolete products (%)", flat_vals(8.0), y_suffix="%")
                if fig3:
                    st.plotly_chart(fig3, use_container_width=True, key="s_obs")
            with r2:
                fig2 = make_kpi_line_chart("Gross margin customer (%)", flat_vals(22.5), y_suffix="%")
                if fig2:
                    st.plotly_chart(fig2, use_container_width=True, key="s_gm")
                fig4 = make_kpi_line_chart("Service level outbound (%)", flat_vals(94.0), y_suffix="%")
                if fig4:
                    st.plotly_chart(fig4, use_container_width=True, key="s_svc")

        with col_insights:
            st.markdown(insight_panel([
                ("ROI (%)", f"ROI is {roi_val:.1f}%."),
                ("Gross margin customer", "Gross margin reflects revenue minus direct costs."),
                ("Obsolete products", "Obsoletes at ~8% of production. Reduce safety stock to lower."),
                ("Service level", "Target ≥ 94% order-line service for all customers."),
            ]), unsafe_allow_html=True)

        calculate_button("s_dash")

    with s_cust:
        result = st.session_state.result
        st.markdown("**Customer report** — read-only. Run simulation to update.")
        # R2 baseline data
        r2_cust = {
            "fg":       {"idx": 0.8120, "rev": 1045136, "dist": 94368,  "svc_lines": 92.1},
            "land":     {"idx": 0.8910, "rev": 586461,  "dist": 52623,  "svc_lines": 95.3},
            "dominicks":{"idx": 0.9820, "rev": 674658,  "dist": 45124,  "svc_lines": 96.8},
        }
        cust_rows = [{"section": "Customer report"}]
        for cid, clabel in CUSTOMERS:
            base = r2_cust.get(cid, {})
            if result:
                svc = result.service_by_customer.get(cid, {})
                svc_pcs = f"{svc.get('service_pieces', base.get('svc_lines', 0) / 100) * 100:.1f}%"
                svc_lines = f"{svc.get('service_lines', base.get('svc_lines', 0) / 100) * 100:.1f}%"
            else:
                svc_pcs = f"{base.get('svc_lines', 0):.1f}%"
                svc_lines = f"{base.get('svc_lines', 0):.1f}%"
            cust_rows.append({
                "Customer": clabel,
                "ⓘ Contract index": f"{base.get('idx', 1.0):.4f}",
                "ⓘ SL (pieces)": svc_pcs,
                "ⓘ SL (order lines)": svc_lines,
                "ⓘ SL (orders)": "—",
                "ⓘ OSA": "—",
                "ⓘ Revenue": f"€{base.get('rev', 0):,.0f}",
                "ⓘ Gross margin": "—",
                "ⓘ Shipments/wk": "—",
                "ⓘ Order lines/wk": "—",
                "ⓘ Pallets/wk": "—",
                "ⓘ Days in WH": "—",
                "ⓘ Shelf life (%)": "—",
                "ⓘ Dist. costs": f"€{base.get('dist', 0):,.0f}",
            })
        st.markdown(tfc_table_html(cust_rows), unsafe_allow_html=True)

    with s_prod:
        result = st.session_state.result
        st.markdown("**Product report** — read-only.")
        r2_prod_data = {
            "orange_1l":   {"demand": 67394, "svc_pcs": 93.4, "svc_lines": 92.1, "obs": 8.4},
            "c_power_1l":  {"demand": 11361, "svc_pcs": 83.8, "svc_lines": 80.3, "obs": 7.1},
            "mango_1l":    {"demand": 42162, "svc_pcs": 97.4, "svc_lines": 97.0, "obs": 8.8},
            "orange_pet":  {"demand": 118084,"svc_pcs": 98.0, "svc_lines": 97.5, "obs": 8.2},
            "c_power_pet": {"demand": 17741, "svc_pcs": 83.6, "svc_lines": 80.6, "obs": 5.5},
            "mango_pet":   {"demand": 51040, "svc_pcs": 97.1, "svc_lines": 96.1, "obs": 8.0},
        }
        prod_rows = [{"section": "Product report"}]
        for pid, plabel in PRODUCTS:
            d = r2_prod_data.get(pid, {})
            price = R2_UNIT_PRICES.get(pid, 0.0)
            demand = d.get("demand", 0)
            demand_val = demand * price
            prod_rows.append({
                "Product": plabel,
                "ⓘ Demand/wk (pcs)": f"{demand:,}",
                "ⓘ Demand value/wk": f"€{demand_val:,.0f}",
                "ⓘ Unit price": f"€{price:.3f}",
                "ⓘ GM/piece": "—",
                "ⓘ SL (pcs)": f"{d.get('svc_pcs', 0):.1f}%",
                "ⓘ SL (lines)": f"{d.get('svc_lines', 0):.1f}%",
                "ⓘ OSA": "—",
                "ⓘ Lines/wk": "—",
                "ⓘ ACR": "—",
                "ⓘ Bias": "—",
                "ⓘ Obsoletes (%)": f"{d.get('obs', 0):.1f}%",
                "ⓘ Obs value/wk": "—",
            })
        st.markdown(tfc_table_html(prod_rows), unsafe_allow_html=True)

        st.markdown("#### Demand pattern")
        try:
            import plotly.graph_objects as go
            import numpy as np
            rng = np.random.default_rng(42)
            cols_dp = st.columns(2)
            for i, (pid, plabel) in enumerate(PRODUCTS):
                d_base = r2_prod_data.get(pid, {}).get("demand", 1000)
                noise = rng.normal(d_base, d_base * 0.15, 26)
                noise = np.maximum(noise, 0)
                fig_dp = go.Figure(go.Scatter(
                    x=list(range(1, 27)), y=noise.tolist(),
                    mode="lines", line=dict(color="#8b1a4a", width=1.5),
                ))
                fig_dp.update_layout(
                    title=plabel.replace("💡 ", ""),
                    xaxis_title="weeks", yaxis_title="pieces/week",
                    height=160, margin=dict(l=40, r=10, t=30, b=30),
                    plot_bgcolor="white", paper_bgcolor="white",
                )
                with cols_dp[i % 2]:
                    st.plotly_chart(fig_dp, use_container_width=True, key=f"dp_{pid}")
        except ImportError:
            st.info("Install plotly for demand charts.")

    with s_custprod:
        st.markdown("**Customer Product report** — read-only, grouped by customer.")
        r2_prod_data2 = {
            "orange_1l": {"demand": 67394}, "c_power_1l": {"demand": 11361},
            "mango_1l": {"demand": 42162}, "orange_pet": {"demand": 118084},
            "c_power_pet": {"demand": 17741}, "mango_pet": {"demand": 51040},
        }
        # Customer-product cross table
        html_cp = ['<table style="width:100%;border-collapse:collapse;font-size:12px;">']
        html_cp.append(tfc_header_row([
            "Product / Customer", "ⓘ Demand/wk (pcs)", "ⓘ Demand value/wk",
            "ⓘ Sales price", "ⓘ GM/wk", "ⓘ GM/piece",
            "ⓘ Shelf life (%)", "ⓘ SL (pcs)", "ⓘ SL (lines)", "ⓘ OSA", "ⓘ Promo uplift (%)"
        ]))
        html_cp.append('<tbody>')
        params = st.session_state.params
        for cid, clabel in CUSTOMERS:
            html_cp.append(
                f'<tr><td colspan="11" style="background:#dae8f0;font-weight:bold;'
                f'padding:6px 10px;border-bottom:1px solid #c5d9e8;">{clabel}</td></tr>'
            )
            for pid, plabel in PRODUCTS:
                price = R2_UNIT_PRICES.get(pid, 0)
                demand = r2_prod_data2.get(pid, {}).get("demand", 0) // 3
                dv = demand * price
                cells = "".join(
                    f'<td style="padding:5px 8px;border-bottom:1px solid #eee;">{v}</td>'
                    for v in [
                        f"  {plabel}", f"{demand:,}", f"€{dv:,.0f}", f"€{price:.3f}",
                        "—", "—", "—", "—", "—", "—", "—"
                    ]
                )
                html_cp.append(f'<tr style="background:white;">{cells}</tr>')
        html_cp.append('</tbody></table>')
        st.markdown("\n".join(html_cp), unsafe_allow_html=True)

    with s_prodcust:
        st.markdown("**Product Customer report** — read-only, grouped by product.")
        html_pc = ['<table style="width:100%;border-collapse:collapse;font-size:12px;">']
        html_pc.append(tfc_header_row([
            "Product / Customer", "ⓘ Demand/wk (pcs)", "ⓘ Demand value/wk",
            "ⓘ Sales price", "ⓘ GM/wk", "ⓘ GM/piece",
            "ⓘ Shelf life (%)", "ⓘ SL (pcs)", "ⓘ SL (lines)", "ⓘ OSA", "ⓘ Promo uplift (%)"
        ]))
        html_pc.append('<tbody>')
        for pid, plabel in PRODUCTS:
            html_pc.append(
                f'<tr><td colspan="11" style="background:#dae8f0;font-weight:bold;'
                f'padding:6px 10px;border-bottom:1px solid #c5d9e8;">{plabel}</td></tr>'
            )
            price = R2_UNIT_PRICES.get(pid, 0)
            demand_total = r2_prod_data2.get(pid, {}).get("demand", 0) if pid in r2_prod_data2 else 0
            for cid, clabel in CUSTOMERS:
                demand = demand_total // 3
                dv = demand * price
                cells = "".join(
                    f'<td style="padding:5px 8px;border-bottom:1px solid #eee;">{v}</td>'
                    for v in [
                        f"  {clabel}", f"{demand:,}", f"€{dv:,.0f}", f"€{price:.3f}",
                        "—", "—", "—", "—", "—", "—", "—"
                    ]
                )
                html_pc.append(f'<tr style="background:white;">{cells}</tr>')
        html_pc.append('</tbody></table>')
        st.markdown("\n".join(html_pc), unsafe_allow_html=True)

    with s_analysis:
        st.info("Analysis charts — run simulation to populate.")

    with s_log:
        params = st.session_state.params
        result = st.session_state.result
        st.markdown("#### Sales decisions")

        # Order management
        st.markdown('<div class="tfc-sec">Order management</div>', unsafe_allow_html=True)
        st.markdown("**ⓘ Shortage rule:** Proportional")

        # Category management cross-matrix
        st.markdown('<div class="tfc-sec">Category management</div>', unsafe_allow_html=True)
        # F&G carries 1l products, LAND carries 1l, Dominick's only PET
        avail_map = {
            "orange_1l":  {"fg": "✅", "land": "✅", "dominicks": "❌"},
            "c_power_1l": {"fg": "✅", "land": "✅", "dominicks": "❌"},
            "mango_1l":   {"fg": "✅", "land": "✅", "dominicks": "❌"},
            "orange_pet": {"fg": "✅", "land": "✅", "dominicks": "✅"},
            "c_power_pet":{"fg": "✅", "land": "✅", "dominicks": "✅"},
            "mango_pet":  {"fg": "✅", "land": "✅", "dominicks": "✅"},
        }
        cm_html = ['<table style="width:auto;border-collapse:collapse;font-size:13px;margin-bottom:8px;">']
        cm_html.append(tfc_header_row(["Product", "💡 Food & Groceries", "💡 LAND Market", "💡 Dominick's"]))
        cm_html.append('<tbody>')
        for pid, plabel in PRODUCTS:
            av = avail_map.get(pid, {})
            row_cells = "".join(
                f'<td style="padding:5px 12px;border-bottom:1px solid #eee;text-align:center;">{v}</td>'
                for v in [plabel, av.get("fg","—"), av.get("land","—"), av.get("dominicks","—")]
            )
            cm_html.append(f'<tr style="background:white;">{row_cells}</tr>')
        cm_html.append('</tbody></table>')
        st.markdown("\n".join(cm_html), unsafe_allow_html=True)

        # Product settings
        st.markdown('<div class="tfc-sec">Product settings</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        params.service_promise = col1.slider(
            "ⓘ Service promise (%)", 90, 99,
            int(params.service_promise * 100), key="svc_promise") / 100.0
        params.requested_shelf_life_pct = col2.slider(
            "ⓘ Requested shelf life (%)", 40, 85,
            int(params.requested_shelf_life_pct * 100), key="sl_pct") / 100.0

        # Per-customer settings
        cust_r2_defaults = {
            "fg":        {"idx": 1.0085, "deadline": "20:00", "tu": "pallet_layer", "pt": 4, "pp": "middle", "ph": "short"},
            "land":      {"idx": 0.9615, "deadline": "17:00", "tu": "pallet_layer", "pt": 4, "pp": "middle", "ph": "short"},
            "dominicks": {"idx": 1.0166, "deadline": "12:00", "tu": "pallet",       "pt": 4, "pp": "middle", "ph": "short"},
        }
        for cid, clabel in CUSTOMERS:
            defaults = cust_r2_defaults.get(cid, {})
            if result:
                idx_val = result.service_by_customer.get(cid, {}).get("index", defaults.get("idx", 1.0))
                idx_display = f"{idx_val:.4f}"
            else:
                idx_display = "—"
            st.markdown(f'<div class="tfc-sec">{clabel}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.markdown(f"**ⓘ Contract index:** {idx_display}")
            c1.markdown("**ⓘ Service level type:** Order lines")
            c1.markdown(f"**ⓘ Service level (%):** {params.service_promise * 100:.0f}")
            c1.markdown(f"**ⓘ Shelf life (%):** {params.requested_shelf_life_pct * 100:.0f}")

            vmi = params.customer_vmi.get(cid, False)
            dl_opts = ["12:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "23:59"]
            cur_dl = params.order_deadline.get(cid, defaults.get("deadline", "20:00"))
            if vmi:
                cur_dl = "14:00"
            dl_idx = dl_opts.index(cur_dl) if cur_dl in dl_opts else 7
            dl = c2.selectbox(f"ⓘ Order deadline — {cid}", dl_opts, index=dl_idx,
                              key=f"dl_{cid}", disabled=vmi, label_visibility="visible")
            params.order_deadline[cid] = "14:00" if vmi else dl

            tu_opts = ["box", "pallet_layer", "pallet"]
            tu_idx = tu_opts.index(params.trade_unit.get(cid, defaults.get("tu", "pallet_layer")))
            tu = c2.selectbox(f"ⓘ Trade unit — {cid}", tu_opts, index=tu_idx,
                              key=f"tu_{cid}", disabled=vmi)
            params.trade_unit[cid] = tu if not vmi else "pallet"

            pterm = c1.number_input(f"ⓘ Payment term (wks) — {cid}", 0, 8,
                                    value=params.customer_payment_terms.get(cid, defaults.get("pt", 4)),
                                    key=f"pt_{cid}")
            params.customer_payment_terms[cid] = pterm

            pressure_opts = ["none", "low", "middle", "heavy"]
            pp_idx = pressure_opts.index(params.promotional_pressure.get(cid, defaults.get("pp", "middle")))
            pp = c2.selectbox(f"ⓘ Promotional pressure — {cid}", pressure_opts,
                              index=pp_idx, key=f"pp_{cid}")
            params.promotional_pressure[cid] = pp

            horizon_opts = ["short", "long"]
            ph_idx = horizon_opts.index(params.promotion_horizon.get(cid, defaults.get("ph", "short")))
            ph = c1.selectbox(f"ⓘ Promotion horizon — {cid}", horizon_opts,
                              index=ph_idx, key=f"ph_{cid}")
            params.promotion_horizon[cid] = ph

            vmi_new = c2.checkbox(f"ⓘ Customer VMI — {cid}",
                                  value=params.customer_vmi.get(cid, False), key=f"vmi_{cid}")
            params.customer_vmi[cid] = vmi_new

        st.session_state.params = params
        calculate_button("s_log")
        result = st.session_state.result
        if result:
            show_unverified_warning(result)


# ══════════════════════════════════════════════════════════════════════════════
# SUPPLY CHAIN — sub-tabs: dashboard | component | product | analysis | decision log
# ══════════════════════════════════════════════════════════════════════════════
with tab_sc:
    sc_sub = st.tabs(["dashboard", "component", "product", "analysis", "decision log"])
    sc_dash, sc_comp, sc_prod, sc_analysis, sc_log = sc_sub

    with sc_dash:
        result = st.session_state.result
        params = st.session_state.params
        pit_val = (result.production_pit.get("pit_utilization", 0) * 100
                   if result else R2_PROD_PLAN)
        rm_of = result.rm_overflow_avg_pallets if result else 0

        col_charts, col_insights = st.columns([7, 3])
        with col_charts:
            r1, r2 = st.columns(2)
            with r1:
                fig = make_kpi_line_chart("ROI (%)", flat_vals(R2_ROI), y_suffix="%")
                if fig:
                    st.plotly_chart(fig, use_container_width=True, key="sc_roi")
                else:
                    st.metric("ROI", f"{R2_ROI:.2f}%")
                fig3 = make_kpi_line_chart("Stock components (weeks)", flat_vals(4.5))
                if fig3:
                    st.plotly_chart(fig3, use_container_width=True, key="sc_stk_comp")
            with r2:
                fig2 = make_kpi_line_chart("Availability components (%)", flat_vals(99.4), y_suffix="%")
                if fig2:
                    st.plotly_chart(fig2, use_container_width=True, key="sc_avail")
                fig4 = make_kpi_line_chart("Stock products (weeks)", flat_vals(3.3))
                if fig4:
                    st.plotly_chart(fig4, use_container_width=True, key="sc_stk_prod")

        with col_insights:
            st.markdown(insight_panel([
                ("ROI (%)", "The company is making a loss. Measures must quickly be taken."),
                ("Availability components (%)", "There is a low level of availability for component Vitamin C for production."),
                ("Stock components (weeks)", "Pack 1 liter and PET have a high level of stock."),
            ]), unsafe_allow_html=True)

        calculate_button("sc_dash")

    with sc_comp:
        result = st.session_state.result
        st.markdown("**Component report** — read-only.")
        comp_report = [
            ("pack",      "💡 Pack 1 liter", "92.3%", "564,440",  "4.3", "€17,553",  "8.7",  "132,257",  "0.0%", "99.5%",  "0.1%",  "3,559,348",  "619,636"),
            ("pet",       "💡 PET",           "84.1%", "851,667",  "4.2", "€46,566",  "7.7",  "204,297",  "0.0%", "99.5%",  "-0.0%", "5,631,948",  "951,612"),
            ("orange",    "💡 Orange",         "97.8%", "160,757",  "4.5", "€70,610",  "10.8",  "35,360",  "0.0%", "99.3%",  "0.0%",   "931,265",  "172,581"),
            ("mango",     "💡 Mango",          "93.7%",  "14,089",  "4.4", "€13,983",  "7.7",    "3,165",  "0.0%", "100.0%", "0.0%",    "82,276",   "15,497"),
            ("vitamin_c", "💡 Vitamin C",      "81.5%",     "769",  "4.2",    "€364",  "18.4",     "184",  "0.0%",  "84.3%",  "0.2%",    "4,852",    "1,032"),
        ]
        comp_rows = [{"section": "Component"}]
        for row in comp_report:
            comp_rows.append({
                "Component": row[1],
                "ⓘ Del. reliability": row[2],
                "ⓘ Stock (pcs/ltr)": row[3],
                "ⓘ Stock (wks)": row[4],
                "ⓘ Stock value": row[5],
                "ⓘ Econ. inv. (wks)": row[6],
                "ⓘ Demand/wk": row[7],
                "ⓘ Obsoletes (%)": row[8],
                "ⓘ Availability": row[9],
                "ⓘ Bias": row[10],
                "ⓘ Purchased": row[11],
                "ⓘ Order size": row[12],
            })
        st.markdown(tfc_table_html(comp_rows), unsafe_allow_html=True)

        # Inventory development charts
        st.markdown("#### Inventory development")
        try:
            import plotly.graph_objects as go
            import numpy as np
            cols_inv = st.columns(2)
            comp_inv_data = [
                ("pack",   "Pack 1 liter",  4.3, 619636),
                ("pet",    "PET",            4.2, 951612),
                ("orange", "Orange",         4.5, 172581),
                ("mango",  "Mango",          4.4, 15497),
            ]
            for i, (sid, label, ss_wks, order_sz) in enumerate(comp_inv_data):
                # Simulate sawtooth inventory
                days = np.arange(0, 130)
                inv = []
                cur = ss_wks * 1.5
                for d in days:
                    cur = cur - 1.0 / 7.0  # consume
                    if d % 14 == 0:        # reorder every 2 weeks
                        cur += ss_wks
                    inv.append(max(0.0, cur))
                fig_inv = go.Figure(go.Scatter(
                    x=days.tolist(), y=inv,
                    mode="lines", line=dict(color="#8b1a4a", width=1.5),
                ))
                fig_inv.update_layout(
                    title=label, xaxis_title="days", yaxis_title="weeks",
                    height=160, margin=dict(l=40, r=10, t=30, b=30),
                    plot_bgcolor="white", paper_bgcolor="white",
                )
                with cols_inv[i % 2]:
                    st.plotly_chart(fig_inv, use_container_width=True, key=f"inv_{sid}")
        except ImportError:
            st.info("Install plotly for inventory charts.")

    with sc_prod:
        result = st.session_state.result
        st.markdown("**Product report** — read-only.")
        r2_fg_data = [
            ("orange_1l",   "💡 Fressie Orange 1 liter",          67394,  93.4, 92.1, 3.2, "€49,522", 7.5, 8.4),
            ("c_power_1l",  "💡 Fressie Orange/C-power 1 liter",  11361,  83.8, 80.3, 2.5, "€7,466",  7.5, 7.1),
            ("mango_1l",    "💡 Fressie Orange/Mango 1 liter",    42162,  97.4, 97.0, 3.3, "€37,556", 7.5, 8.8),
            ("orange_pet",  "💡 Fressie Orange PET",              118084, 98.0, 97.5, 3.4, "€49,505", 7.6, 8.2),
            ("c_power_pet", "💡 Fressie Orange/C-power PET",      17741,  83.6, 80.6, 2.3, "€5,761",  7.4, 5.5),
            ("mango_pet",   "💡 Fressie Orange/Mango PET",        51040,  97.1, 96.1, 3.2, "€22,539", 7.5, 8.0),
        ]
        fg_rows = [{"section": "💡 DC Netherlands"}]
        for row in r2_fg_data:
            if result:
                svc = result.service_by_customer
                # aggregate across customers (approximate)
                svc_pcs = f"{row[3]:.1f}%"
                svc_lines = f"{row[4]:.1f}%"
            else:
                svc_pcs = f"{row[3]:.1f}%"
                svc_lines = f"{row[4]:.1f}%"
            fg_rows.append({
                "Product": row[1],
                "ⓘ Demand/wk (pcs)": f"{row[2]:,}",
                "ⓘ SL (pcs)": svc_pcs,
                "ⓘ SL (lines)": svc_lines,
                "ⓘ Stock (wks)": f"{row[5]:.1f}",
                "ⓘ Stock value": row[6],
                "ⓘ Econ. inv. (wks)": f"{row[7]:.1f}",
                "ⓘ Obs (%)": f"{row[8]:.1f}%",
                "ⓘ Forecast err.": "—",
                "ⓘ Bias": "—",
                "ⓘ Batches": "13.0",
            })
        st.markdown(tfc_table_html(fg_rows), unsafe_allow_html=True)

        # FG inventory development
        st.markdown("#### Inventory development — finished goods")
        try:
            import plotly.graph_objects as go
            import numpy as np
            cols_fg = st.columns(2)
            for i, row in enumerate(r2_fg_data[:4]):
                pid, label = row[0], row[1]
                days = np.arange(0, 130)
                inv = []
                cur = row[5] * 1.2
                for d in days:
                    cur = cur - (1.0 / 7.0) * 0.9
                    if d % 7 == 0:
                        cur += row[5] * 0.5
                    inv.append(max(0.0, cur))
                fig_fg_inv = go.Figure(go.Scatter(
                    x=days.tolist(), y=inv,
                    mode="lines", line=dict(color="#8b1a4a", width=1.5),
                ))
                fig_fg_inv.update_layout(
                    title=label.replace("💡 ", ""), xaxis_title="days", yaxis_title="weeks",
                    height=160, margin=dict(l=40, r=10, t=30, b=30),
                    plot_bgcolor="white", paper_bgcolor="white",
                )
                with cols_fg[i % 2]:
                    st.plotly_chart(fig_fg_inv, use_container_width=True, key=f"fg_inv_{pid}")
        except ImportError:
            pass

    with sc_analysis:
        result = st.session_state.result
        if result:
            pit = result.production_pit
            col1, col2 = st.columns(2)
            pit_val2 = pit.get("pit_utilization", 0) * 100
            col1.metric("PIT Utilization", f"{pit_val2:.1f}%",
                        delta="⚠ > 80%" if pit_val2 > 80 else "✓ ≤ 80%",
                        delta_color="inverse" if pit_val2 > 80 else "normal")
            col1.metric("Actual Line Utilization",
                        f"{pit.get('actual_utilization', 0) * 100:.1f}%")
            col2.metric("Production hours/week",
                        f"{pit.get('production_h_per_week', 0):.1f}h")
            col2.metric("Changeover hours/week",
                        f"{pit.get('changeover_h_per_week', 0):.1f}h")
        else:
            st.info("Analysis charts — run simulation to populate.")

    with sc_log:
        # Supply Chain decision log: RM SS, lot size, frozen period, FG SS, PI
        params = st.session_state.params
        st.markdown("#### Supply Chain decisions")

        # --- Stock management components ---
        st.markdown('<div class="tfc-sec">Stock management components</div>',
                    unsafe_allow_html=True)
        hdr = st.columns([2, 1, 1])
        hdr[0].markdown("**💡 Component**")
        hdr[1].markdown("**ⓘ Safety stock (weeks)**")
        hdr[2].markdown("**ⓘ Lot size (weeks)**")
        st.divider()

        comp_sc = [
            ("pack",      "💡 Pack 1 liter"),
            ("pet",       "💡 PET"),
            ("orange",    "💡 Orange"),
            ("mango",     "💡 Mango"),
            ("vitamin_c", "💡 Vitamin C"),
        ]
        for sid, label in comp_sc:
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

        # --- Production management ---
        st.markdown('<div class="tfc-sec">Production management</div>', unsafe_allow_html=True)
        params.frozen_period_weeks = st.number_input(
            "ⓘ Frozen period of production (weeks)", 0, 8,
            value=params.frozen_period_weeks, key="fp_wks")

        # --- Stock management finished goods ---
        st.markdown('<div class="tfc-sec">Stock management finished goods</div>',
                    unsafe_allow_html=True)
        st.markdown("**💡 DC Netherlands**")
        hdr2 = st.columns([2, 1, 1])
        hdr2[0].markdown("**Product**")
        hdr2[1].markdown("**ⓘ Production interval (days)**")
        hdr2[2].markdown("**ⓘ Safety stock (weeks)**")
        st.divider()

        # Shared production interval
        pi_updated = st.number_input(
            "ⓘ Production interval (days) — applies to all products",
            1, 30, value=params.production_interval_days, key="pi_days")
        params.production_interval_days = pi_updated

        products_fg = ["orange_1l", "c_power_1l", "mango_1l", "orange_pet", "c_power_pet", "mango_pet"]
        product_labels_fg = {
            "orange_1l": "💡 Fressie Orange 1 liter",
            "c_power_1l": "💡 Fressie Orange/C-power 1 liter",
            "mango_1l": "💡 Fressie Orange/Mango 1 liter",
            "orange_pet": "💡 Fressie Orange PET",
            "c_power_pet": "💡 Fressie Orange/C-power PET",
            "mango_pet": "💡 Fressie Orange/Mango PET",
        }
        for pid in products_fg:
            c0, c1, c2 = st.columns([2, 1, 1])
            c0.markdown(product_labels_fg[pid])
            c1.markdown(f"{params.production_interval_days}")
            ss_fg = c2.number_input("", 0.5, 10.0,
                                    value=float(params.fg_safety_stock_weeks.get(pid, 2.0)),
                                    step=0.5, key=f"fg_ss_{pid}", label_visibility="collapsed")
            params.fg_safety_stock_weeks[pid] = ss_fg

        st.session_state.params = params
        calculate_button("sc_log")
        result = st.session_state.result
        if result:
            show_unverified_warning(result)


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW
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
        st.markdown("**Service Level by Customer**")
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
            for w in result.warnings:
                st.error(f"⚠ {w}")

        # Full P&L
        with st.expander("Full P&L detail"):
            pl = result.pl

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
            pl = result.pl
            wb = Workbook()
            ws = wb.active
            ws.title = "P&L"
            for r_data in [
                ("Metric", "Value"),
                ("Realized Revenue", pl.realized_revenue),
                ("Operating Profit", pl.operating_profit),
                ("Investment", pl.investment),
                ("ROI", pl.roi),
            ]:
                ws.append(r_data)
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            st.download_button(
                "⬇ Download P&L (.xlsx)", data=buf,
                file_name="tfc_scenario.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except ImportError:
            st.caption("Install openpyxl for Excel export.")
    else:
        st.info("Press **▶ Calculate** to run the simulation.")

    # Accept-rule checker
    with st.expander("Decision Log & Accept-Rule Checker"):
        result2 = st.session_state.result
        params = st.session_state.params
        st.caption("Enter the real game index for decisions you've tested in the real game.")
        ri_fg = st.number_input("F&G real index (from game)", 0.90, 1.20, value=0.90,
                                step=0.0001, format="%.4f", key="ri_fg")
        ri_land = st.number_input("LAND real index (from game)", 0.90, 1.20, value=0.90,
                                  step=0.0001, format="%.4f", key="ri_land")
        ri_dom = st.number_input("Dominick's real index (from game)", 0.90, 1.20, value=0.90,
                                 step=0.0001, format="%.4f", key="ri_dom")

        real_overrides = {}
        if ri_fg != 0.90:
            real_overrides["fg"] = ri_fg
        if ri_land != 0.90:
            real_overrides["land"] = ri_land
        if ri_dom != 0.90:
            real_overrides["dominicks"] = ri_dom

        if result2 and st.button("Run Accept-Rule Checker"):
            baseline_params = build_r2_scenario()
            baseline_result = run_simulation(baseline_params)
            checks = accept_rule_checker(result2, baseline_result, params, real_overrides)
            for c in checks:
                verdict = c.get("model_verdict", "?")
                st.markdown(f"**[{verdict}]** {c['decision']}")
                st.caption(f"Threshold: {c['accept_threshold']}")
                st.caption(c["note"])
                st.divider()
        elif not result2:
            st.info("Run a simulation first.")


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════
with tab_scen:
    st.markdown("## Scenario Comparison & Monte Carlo")
    st.caption(DISCLAIMER)

    sc_tab1, sc_tab2, sc_tab3 = st.tabs(["Compare Scenarios", "Monte Carlo", "Tornado"])
    SCENARIOS_DIR = ROOT / "scenarios"
    yaml_files = sorted(SCENARIOS_DIR.glob("*.yaml"))
    scen_names = [f.stem for f in yaml_files]

    with sc_tab1:
        st.subheader("Run Pre-built Scenarios")
        if st.button("Run all pre-built scenarios"):
            from tfc.engine.scenarios import load_scenario
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
                fig = px.histogram(x=mc.roi_samples * 100, nbins=30,
                                   labels={"x": "ROI (%)"}, title=f"ROI Distribution — {scen_choice}",
                                   color_discrete_sequence=["#8b1a4a"])
                fig.add_vline(x=mc.baseline_roi * 100, line_dash="dash",
                              annotation_text="R2 baseline")
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                pass

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
                fig = px.bar(x=[t["swing_pp"] for t in top10], y=[t["name"] for t in top10],
                             orientation="h", labels={"x": "ROI swing (pp)", "y": "Assumption"},
                             title=f"Tornado Chart — {scen_choice_t}",
                             color_discrete_sequence=["#8b1a4a"])
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
