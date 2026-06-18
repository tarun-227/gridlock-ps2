"""PS2 — Event-Driven Congestion: decision-support dashboard.

  Predict tab  : form → closure probability + deployment plan + SHAP drivers
  Insights tab : dataset patterns, model metrics vs baselines, SHAP, data findings

Run from the project root:  streamlit run app/dashboard.py
"""
from __future__ import annotations
import os
import sys
import json
from datetime import datetime, time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

os.environ.setdefault("PYTHONBREAKPOINT", "0")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src import config as C
from src.predict import predict_all, load_artifacts

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GridLock — BTP Congestion Intelligence",
    layout="wide",
    page_icon="🚦",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
NAVY   = "#0D1B3E"
TEAL   = "#00C2A8"
ICE    = "#C8DEFF"
LIGHT  = "#F2F6FC"
CARD   = "#FFFFFF"
SUBTEXT = "#4A6080"

ALERT_CFG = {
    "LOW":      {"bg": "#E8F5E9", "border": "#2E7D32", "text": "#1B5E20", "icon": "🟢"},
    "MEDIUM":   {"bg": "#FFF3E0", "border": "#E65100", "text": "#BF360C", "icon": "🟡"},
    "HIGH":     {"bg": "#FFEBEE", "border": "#B71C1C", "text": "#B71C1C", "icon": "🔴"},
    "CRITICAL": {"bg": "#1a0000", "border": "#ff1744", "text": "#ff6b6b", "icon": "🚨"},
}

st.markdown(f"""
<style>
  /* ── Force light base on everything outside sidebar ── */
  [data-testid="stAppViewContainer"] {{background:{LIGHT} !important;}}
  [data-testid="stMain"] {{background:{LIGHT} !important;}}
  [data-testid="stMain"] * {{
    color:{NAVY} !important;
    -webkit-text-fill-color:{NAVY} !important;
  }}

  /* ── Metric components — explicit colors ── */
  [data-testid="stMain"] [data-testid="stMetricValue"] {{
    color:{NAVY} !important; -webkit-text-fill-color:{NAVY} !important;
    font-size:1.6rem !important; font-weight:700 !important;
  }}
  [data-testid="stMain"] [data-testid="stMetricLabel"] {{
    color:{SUBTEXT} !important; -webkit-text-fill-color:{SUBTEXT} !important;
    font-size:0.8rem !important;
  }}
  [data-testid="stMain"] [data-testid="stMetricDelta"] {{
    color:{TEAL} !important; -webkit-text-fill-color:{TEAL} !important;
  }}

  /* ── Expander: force all text dark ── */
  [data-testid="stExpander"] {{background:white !important; border-radius:10px !important;}}
  [data-testid="stExpander"] summary {{color:{NAVY} !important; -webkit-text-fill-color:{NAVY} !important; font-weight:600 !important;}}
  [data-testid="stExpander"] p,
  [data-testid="stExpander"] span,
  [data-testid="stExpander"] label,
  [data-testid="stExpander"] div {{
    color:{NAVY} !important; -webkit-text-fill-color:{NAVY} !important;
  }}
  [data-testid="stExpander"] [data-testid="stMetricValue"] {{
    color:{NAVY} !important; -webkit-text-fill-color:{NAVY} !important; font-size:1.5rem !important;
  }}
  [data-testid="stExpander"] [data-testid="stMetricLabel"] {{
    color:{SUBTEXT} !important; -webkit-text-fill-color:{SUBTEXT} !important;
  }}

  /* ── Caption / small text ── */
  [data-testid="stMain"] .stCaption,
  [data-testid="stMain"] [data-testid="stCaptionContainer"] p,
  [data-testid="stMain"] small {{
    color:{SUBTEXT} !important; -webkit-text-fill-color:{SUBTEXT} !important;
  }}

  /* ── Tab content background ── */
  .stTabs [data-baseweb="tab-panel"] {{
    background:white; border-radius:0 0 12px 12px;
    box-shadow:0 4px 20px rgba(13,27,62,0.08); padding:1.5rem;
  }}

  /* ── Sidebar: stay navy with white text ── */
  [data-testid="stSidebar"] {{background:{NAVY} !important; border-right:3px solid {TEAL};}}
  [data-testid="stSidebar"] * {{
    color:white !important; -webkit-text-fill-color:white !important;
  }}
  [data-testid="stSidebar"] .stSelectbox label,
  [data-testid="stSidebar"] .stTextArea label,
  [data-testid="stSidebar"] .stDateInput label,
  [data-testid="stSidebar"] .stTimeInput label,
  [data-testid="stSidebar"] .stCheckbox label {{
    color:{ICE} !important; -webkit-text-fill-color:{ICE} !important; font-size:0.82rem !important;
  }}
  [data-testid="stSidebar"] select,
  [data-testid="stSidebar"] input,
  [data-testid="stSidebar"] textarea {{
    background:#132654 !important; color:white !important;
    -webkit-text-fill-color:white !important; border:1px solid #2A4A80 !important;
  }}
  [data-testid="stSidebar"] .stButton>button {{
    background:{TEAL} !important; color:{NAVY} !important;
    -webkit-text-fill-color:{NAVY} !important; border:none !important;
    font-weight:700 !important; border-radius:8px !important; width:100%;
    padding:0.65rem !important; font-size:1rem !important; margin-top:0.5rem;
  }}
  [data-testid="stSidebar"] .stButton>button:hover {{opacity:0.88;}}

  /* ── Tabs nav ── */
  .stTabs [data-baseweb="tab-list"] {{background:{NAVY}; border-radius:12px 12px 0 0; padding:4px 8px 0;}}
  .stTabs [data-baseweb="tab"] {{
    color:{ICE} !important; -webkit-text-fill-color:{ICE} !important;
    font-weight:600; font-size:0.9rem; padding:10px 20px;
  }}
  .stTabs [data-baseweb="tab"][aria-selected="true"] {{
    background:{TEAL}; color:{NAVY} !important; -webkit-text-fill-color:{NAVY} !important;
    border-radius:8px 8px 0 0;
  }}

  /* ── Custom cards ── */
  .gl-card {{
    background:white; border-radius:12px; padding:1.25rem 1.5rem;
    box-shadow:0 2px 12px rgba(13,27,62,0.08); border:1px solid #D8E4F0;
    margin-bottom:1rem;
  }}
  .gl-card-accent {{border-left:4px solid {TEAL};}}
  .gl-metric-card {{
    background:white; border-radius:12px; padding:1rem 1.25rem;
    box-shadow:0 2px 12px rgba(13,27,62,0.08); text-align:center;
    border-top:3px solid {TEAL};
  }}
  .gl-metric-num {{font-size:2.2rem; font-weight:800; color:{NAVY} !important; -webkit-text-fill-color:{NAVY} !important; line-height:1.1;}}
  .gl-metric-label {{font-size:0.78rem; color:{SUBTEXT} !important; -webkit-text-fill-color:{SUBTEXT} !important; margin-top:2px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;}}
  .gl-metric-sub {{font-size:0.82rem; color:{TEAL} !important; -webkit-text-fill-color:{TEAL} !important; margin-top:4px; font-weight:600;}}

  /* ── Alert ── */
  .gl-alert {{border-radius:12px; padding:1rem 1.5rem; border-left:6px solid; margin:1rem 0;}}
  .gl-alert-title {{font-size:1.4rem; font-weight:800; margin-bottom:0.25rem;}}
  .gl-alert-sub {{font-size:0.9rem; opacity:0.9;}}

  /* ── Deploy cards ── */
  .gl-deploy-card {{
    background:{NAVY}; border-radius:12px; padding:1.1rem 1.25rem;
    box-shadow:0 4px 16px rgba(13,27,62,0.18); text-align:center;
  }}
  .gl-deploy-num {{font-size:2.4rem; font-weight:800; color:{TEAL} !important; -webkit-text-fill-color:{TEAL} !important; line-height:1;}}
  .gl-deploy-label {{font-size:0.78rem; color:{ICE} !important; -webkit-text-fill-color:{ICE} !important; text-transform:uppercase; letter-spacing:0.8px; margin-top:4px;}}

  /* ── Section headers ── */
  .gl-section {{
    font-size:1rem; font-weight:700; color:{NAVY} !important; text-transform:uppercase;
    letter-spacing:1px; padding-bottom:0.5rem; border-bottom:2px solid {TEAL};
    margin:1.5rem 0 1rem;
  }}
  .gl-sub {{font-size:0.82rem; color:{SUBTEXT} !important; margin-top:-0.5rem; margin-bottom:1rem;}}

  /* ── Hero ── */
  .gl-hero {{
    background:linear-gradient(135deg,{NAVY} 0%,#1A3A6C 100%);
    border-radius:16px; padding:1.5rem 2rem; margin-bottom:1.5rem;
    border-left:6px solid {TEAL};
  }}
  .gl-hero-title {{font-size:1.75rem; font-weight:800; color:white !important; -webkit-text-fill-color:white !important; margin:0;}}
  .gl-hero-sub {{font-size:0.9rem; color:{ICE} !important; -webkit-text-fill-color:{ICE} !important; margin-top:4px;}}

  /* ── Finding cards ── */
  .gl-finding {{border-radius:10px; padding:1rem 1.25rem; margin-bottom:0.75rem; border-left:4px solid;}}
  .gl-finding-head {{font-size:1rem; font-weight:700; margin-bottom:4px;}}
  .gl-finding-body {{font-size:0.88rem; line-height:1.5;}}

  /* ── pre / code blocks ── */
  [data-testid="stMain"] pre {{
    color:{NAVY} !important; -webkit-text-fill-color:{NAVY} !important;
    background:#F8FAFD !important; border-left:3px solid {TEAL};
    border-radius:6px; padding:1rem;
  }}

  /* ── Streamlit native metric card wrapper ── */
  div[data-testid="metric-container"] {{
    background:white !important; border:1px solid #D8E4F0; border-radius:10px;
    padding:0.75rem; box-shadow:0 2px 8px rgba(13,27,62,0.06);
  }}

  /* ── Dataframe ── */
  .stDataFrame {{border-radius:8px; overflow:hidden;}}

  /* ── Hide Streamlit chrome ── */
  footer {{display:none;}}
  #MainMenu {{visibility:hidden;}}
</style>
""", unsafe_allow_html=True)


# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_clean():
    df = pd.read_parquet(C.CLEAN_PARQUET)
    df["rc"] = df[C.T1].astype(float)
    df["hour"] = df["start_ist"].dt.hour
    return df


@st.cache_data(show_spinner=False)
def load_metrics():
    if C.METRICS_JSON.exists():
        return json.loads(C.METRICS_JSON.read_text(encoding="utf-8"))
    return {}


# ── Sidebar — incident form ───────────────────────────────────────────────────
def sidebar_form(ctx):
    st.sidebar.markdown(f"""
    <div style='text-align:center; padding:1rem 0 0.5rem;'>
      <div style='font-size:2rem;'>🚦</div>
      <div style='font-size:1.2rem; font-weight:800; color:white; letter-spacing:1px;'>GRIDLOCK</div>
      <div style='font-size:0.72rem; color:{ICE}; margin-top:2px;'>BTP Congestion Intelligence</div>
    </div>
    <hr style='border-color:#2A4A80; margin:0.75rem 0;'>
    <div style='font-size:0.72rem; color:{ICE}; text-transform:uppercase;
         letter-spacing:1px; font-weight:700; margin-bottom:0.75rem;'>INCIDENT REPORT</div>
    """, unsafe_allow_html=True)

    corridor = st.sidebar.selectbox("Corridor", ctx["corridors"],
                                    index=ctx["corridors"].index("Tumkur Road")
                                    if "Tumkur Road" in ctx["corridors"] else 0)
    cause = st.sidebar.selectbox("Event cause", ctx["event_causes"],
                                 index=ctx["event_causes"].index("tree_fall")
                                 if "tree_fall" in ctx["event_causes"] else 0)
    veh = st.sidebar.selectbox("Vehicle type", ["(none)"] + ctx["veh_types"])
    zone = st.sidebar.selectbox("Zone", ["(unknown)"] + ctx["zones"])

    col_d, col_t = st.sidebar.columns(2)
    d = col_d.date_input("Date", datetime(2024, 4, 1), label_visibility="visible")
    t = col_t.time_input("Time", time(18, 0), label_visibility="visible")

    is_planned = st.sidebar.checkbox("Planned event")
    desc = st.sidebar.text_area("Officer note", "huge tree fallen blocking the road, crane needed",
                                height=90)
    live = st.sidebar.checkbox("Live Groq LLM",
                               help="Calls Groq API for descriptions not in cache.")

    st.sidebar.markdown("<hr style='border-color:#2A4A80; margin:0.75rem 0;'>",
                        unsafe_allow_html=True)
    run = st.sidebar.button("⚡  FORECAST IMPACT", type="primary")

    return dict(corridor=corridor, event_cause=cause,
                veh_type=None if veh == "(none)" else veh,
                zone=None if zone == "(unknown)" else zone,
                datetime=datetime.combine(d, t), is_planned=is_planned,
                description=desc), live, run


# ── Predict tab ───────────────────────────────────────────────────────────────
def render_predict(out):
    pred, plan = out["pred"], out["plan"]
    alc = ALERT_CFG.get(plan["alert_level"], ALERT_CFG["MEDIUM"])

    # Alert banner
    st.markdown(f"""
    <div class="gl-alert" style="background:{alc['bg']}; border-color:{alc['border']}; color:{alc['text']};">
      <div class="gl-alert-title">{alc['icon']} {plan['alert_level']} IMPACT</div>
      <div class="gl-alert-sub">{plan['estimated_clearance']} &nbsp;·&nbsp;
        {pred['event_cause'].replace('_',' ').title()} on {pred['corridor']}</div>
    </div>
    """, unsafe_allow_html=True)

    # 4 metric cards
    cols = st.columns(4)
    closure_color = TEAL if pred["closure_prob"] < 0.4 else ("#FF6B00" if pred["closure_prob"] < 0.65 else "#E53935")
    metrics = [
        (f"{pred['closure_prob']:.0%}", "Closure risk",
         "🚨 Likely closure" if pred["closure_pred"] else "✅ Low closure risk", closure_color),
        (pred["priority"], "Dispatch priority",
         f"{pred['priority_prob']:.0%} confidence", TEAL),
        (pred["duration_bucket"], "Duration estimate",
         "Operational bucket", TEAL),
        (f"{pred['severity']}/5", "Severity score",
         pred["incident_subtype"].replace("_", " "), TEAL),
    ]
    for col, (val, label, sub, color) in zip(cols, metrics):
        col.markdown(f"""
        <div class="gl-metric-card" style="border-top-color:{color};">
          <div class="gl-metric-num" style="color:{color};">{val}</div>
          <div class="gl-metric-label">{label}</div>
          <div class="gl-metric-sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div class='gl-section'>🚓 Recommended Deployment</div>",
                unsafe_allow_html=True)

    # Deploy cards row
    dcols = st.columns(4)
    divert_val = plan["diversion_to"] if plan["need_diversion"] else "Not required"
    divert_color = TEAL if plan["need_diversion"] else "#8AAAD0"
    tow_val = "Yes" if plan["tow_required"] else "No"
    tow_color = "#FF9800" if plan["tow_required"] else "#8AAAD0"

    deploy_cards = [
        (str(plan["manpower_officers"]), "Officers to deploy", ""),
        (str(plan["barricades"]), "Barricades", ""),
        (divert_val, "Diversion route", ""),
        (tow_val, "Tow / crane", ""),
    ]
    for col, (val, label, _) in zip(dcols, deploy_cards):
        vc = TEAL if val not in ("Not required", "No") else "#8AAAD0"
        col.markdown(f"""
        <div class="gl-deploy-card">
          <div class="gl-deploy-num" style="color:{vc}; font-size:1.5rem;">{val}</div>
          <div class="gl-deploy-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    # Rationale
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📋 Deployment rationale & full summary", expanded=False):
        st.markdown(f"""
        <div class='gl-card gl-card-accent'>
          <pre style='font-family:monospace; font-size:0.82rem; color:#0D1B3E !important;
               white-space:pre-wrap; background:transparent; border:none; margin:0;
               opacity:1; -webkit-text-fill-color:#0D1B3E;'>{plan['summary']}</pre>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Manpower factors: " + " · ".join(plan["manpower_rationale"]))

    # SHAP — Plotly horizontal bar
    st.markdown("<div class='gl-section'>🔍 Why This Forecast? (per-incident SHAP)</div>",
                unsafe_allow_html=True)
    st.markdown("<div class='gl-sub'>Top feature contributions toward / against closure prediction</div>",
                unsafe_allow_html=True)

    reasons = out["closure_reasons"]
    feats = [r[0].replace("_", " ") for r in reasons]
    vals  = [r[1] for r in reasons]
    colors = [TEAL if v >= 0 else "#E53935" for v in vals]

    fig = go.Figure(go.Bar(
        x=vals, y=feats, orientation="h",
        marker_color=colors,
        text=[f"{v:+.3f}" for v in vals],
        textposition="outside",
        textfont=dict(size=11, color=NAVY),
    ))
    fig.update_layout(
        height=280, margin=dict(l=10, r=80, t=10, b=10),
        paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(title="SHAP contribution", gridcolor="#EEF2F8", zeroline=True,
                   zerolinecolor=NAVY, zerolinewidth=2),
        yaxis=dict(autorange="reversed"),
        font=dict(family="Calibri, sans-serif", color=NAVY),
        bargap=0.35,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with st.expander("🤖 LLM extraction from officer note"):
        ex = out["llm_extract"]
        ec1, ec2, ec3 = st.columns(3)
        ec1.metric("Severity", f"{ex['severity_score']}/5")
        ec1.metric("Blocking lanes", "Yes" if ex["blocking_lanes"] else "No")
        ec2.metric("Vehicles involved", ex["vehicles_involved"])
        ec2.metric("Tow / crane", "Yes" if ex["requires_tow"] else "No")
        ec3.metric("Incident subtype", ex["incident_subtype"].replace("_", " "))


def predict_tab_empty():
    st.markdown(f"""
    <div class='gl-hero'>
      <div class='gl-hero-title'>⚡ Incident Impact Forecasting</div>
      <div class='gl-hero-sub'>
        Fill in the incident report in the sidebar and click
        <strong style='color:{TEAL};'>FORECAST IMPACT</strong>
        to get closure risk, dispatch priority, duration estimate and a full deployment plan.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Stats row
    stat_cols = st.columns(4)
    stats = [("8,171", "Incidents trained on"), ("47", "Leakage-safe features"),
             ("3.74×", "PR-AUC lift (T1)"), ("65.8%", "Bucket accuracy (T3)")]
    for col, (v, l) in zip(stat_cols, stats):
        col.markdown(f"""
        <div class='gl-card' style='text-align:center; padding:1rem;'>
          <div style='font-size:1.8rem; font-weight:800; color:{TEAL};'>{v}</div>
          <div style='font-size:0.78rem; color:{SUBTEXT}; text-transform:uppercase;
               letter-spacing:0.5px; margin-top:4px;'>{l}</div>
        </div>
        """, unsafe_allow_html=True)

    # How it works
    st.markdown("<div class='gl-section'>How It Works</div>", unsafe_allow_html=True)
    how_cols = st.columns(3)
    steps = [
        ("1", "Report incident", "Enter the corridor, event cause, vehicle type, time, and officer note in the sidebar."),
        ("2", "AI forecasts impact", "XGBoost models predict closure risk, dispatch priority, and duration bucket. Groq LLM mines the officer note for severity and subtype."),
        ("3", "Deploy resources", "The recommendation engine generates officer count, barricade count, diversion route, and alert level — with rationale."),
    ]
    for col, (num, title, body) in zip(how_cols, steps):
        col.markdown(f"""
        <div class='gl-card'>
          <div style='font-size:1.8rem; font-weight:800; color:{TEAL}; margin-bottom:0.4rem;'>{num}</div>
          <div style='font-size:1rem; font-weight:700; color:{NAVY}; margin-bottom:0.4rem;'>{title}</div>
          <div style='font-size:0.85rem; color:{SUBTEXT}; line-height:1.5;'>{body}</div>
        </div>
        """, unsafe_allow_html=True)


# ── Insights tab ──────────────────────────────────────────────────────────────
def insights_tab():
    df = load_clean()
    m  = load_metrics()

    # Model metrics KPIs
    st.markdown("<div class='gl-section'>📊 Model Performance</div>", unsafe_allow_html=True)
    st.markdown("<div class='gl-sub'>Held-out chronological test set · n = 1,226 incidents (last 15%)</div>",
                unsafe_allow_html=True)

    if m:
        t1, t2 = m.get("T1_closure", {}), m.get("T2_priority", {})
        t3b = m.get("T3_bucket", {})
        kpis = [
            (t1.get("pr_auc", "—"), f"{t1.get('pr_auc_lift_vs_baseline','—')}× above baseline",
             "T1 PR-AUC", TEAL, "vs 0.086 majority"),
            (t1.get("roc_auc", "—"), f"{t1.get('recall_at_ops_threshold','—')} recall@0.10",
             "T1 ROC-AUC", TEAL, "strong discrimination"),
            ("1.000", "0/27 planned closures missed", "Planned recall", "#2E7D32", "100% catch rate"),
            (t2.get("corridor_blind", {}).get("f1_weighted", "—"), "F1 on unlabelled roads",
             "T2 Corridor-blind F1", TEAL, "without corridor feature"),
            (t3b.get("accuracy", "—"),
             f"vs {t3b.get('baseline_majority_accuracy','—')} majority",
             "T3 Bucket accuracy", TEAL, "<1h/1-3h/3-8h/>8h"),
            (t3b.get("per_bucket", {}).get("1-3h", {}).get("f1", "—"), "dominant class",
             "T3 1-3h class F1", TEAL, "most common bucket"),
        ]
        kpi_cols = st.columns(6)
        for col, (val, delta, label, color, note) in zip(kpi_cols, kpis):
            col.markdown(f"""
            <div class='gl-metric-card' style='border-top-color:{color}; padding:0.85rem;'>
              <div class='gl-metric-num' style='color:{color}; font-size:1.6rem;'>{val}</div>
              <div class='gl-metric-label'>{label}</div>
              <div style='font-size:0.72rem; color:{TEAL}; margin-top:3px; font-weight:600;'>{delta}</div>
              <div style='font-size:0.68rem; color:{SUBTEXT}; margin-top:1px;'>{note}</div>
            </div>
            """, unsafe_allow_html=True)

    # Charts row
    st.markdown("<div class='gl-section'>📈 Closure Signal Analysis</div>", unsafe_allow_html=True)
    ch1, ch2 = st.columns(2)

    with ch1:
        cr = (df.groupby("event_cause_norm")["rc"].mean()
                .sort_values(ascending=True).tail(14) * 100).round(1)
        fig1 = go.Figure(go.Bar(
            x=cr.values, y=[c.replace("_", " ") for c in cr.index],
            orientation="h",
            marker=dict(
                color=cr.values,
                colorscale=[[0, "#C8DEFF"], [0.5, TEAL], [1, NAVY]],
                showscale=False,
            ),
            text=[f"{v:.1f}%" for v in cr.values],
            textposition="outside",
            textfont=dict(size=10, color=NAVY),
        ))
        fig1.update_layout(
            title=dict(text="<b>Closure rate by event cause</b>", font=dict(size=13, color=NAVY)),
            height=380, margin=dict(l=10, r=60, t=40, b=10),
            paper_bgcolor="white", plot_bgcolor="white",
            xaxis=dict(title="Closure rate (%)", gridcolor="#EEF2F8"),
            yaxis=dict(autorange="reversed"),
            font=dict(family="Calibri, sans-serif"),
            bargap=0.3,
        )
        st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    with ch2:
        by_hour = (df.groupby("hour")["rc"].mean() * 100).round(2).reset_index()
        peak_hours = {11, 12, 16, 17, 18, 19}
        by_hour["is_peak"] = by_hour["hour"].isin(peak_hours)
        fig2 = go.Figure(go.Bar(
            x=by_hour["hour"],
            y=by_hour["rc"],
            marker_color=[TEAL if p else "#C8DEFF" for p in by_hour["is_peak"]],
            text=[f"{v:.1f}%" for v in by_hour["rc"]],
            textposition="outside",
            textfont=dict(size=9, color=NAVY),
        ))
        fig2.update_layout(
            title=dict(text="<b>Closure rate by hour (IST)</b> · teal = refined peak windows",
                       font=dict(size=13, color=NAVY)),
            height=380, margin=dict(l=10, r=10, t=40, b=10),
            paper_bgcolor="white", plot_bgcolor="white",
            xaxis=dict(title="Hour of day (IST)", dtick=2, gridcolor="#EEF2F8"),
            yaxis=dict(title="Closure rate (%)", gridcolor="#EEF2F8"),
            font=dict(family="Calibri, sans-serif"),
            bargap=0.15,
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # Corridor table + planned vs unplanned
    ct1, ct2 = st.columns(2)
    with ct1:
        st.markdown("<div class='gl-section' style='font-size:0.85rem;'>Top Closure Corridors (n≥50)</div>",
                    unsafe_allow_html=True)
        ct = (df.groupby("corridor").agg(incidents=("id", "size"), closure_rate=("rc", "mean"))
                .query("incidents >= 50").sort_values("closure_rate", ascending=False)
                .round(3).head(10))
        ct["closure_rate"] = (ct["closure_rate"] * 100).round(1).astype(str) + "%"
        st.dataframe(ct, use_container_width=True, height=280)

    with ct2:
        st.markdown("<div class='gl-section' style='font-size:0.85rem;'>Planned vs Unplanned</div>",
                    unsafe_allow_html=True)
        pv = df.groupby("event_type").agg(incidents=("id", "size"),
                                           closure_rate=("rc", "mean")).round(3)
        pv["closure_rate"] = (pv["closure_rate"] * 100).round(1).astype(str) + "%"
        st.dataframe(pv, use_container_width=True)

        # Mini gauge for planned vs unplanned
        try:
            plan_rate = df[df["event_type"] == "planned"]["rc"].mean() * 100
            unpl_rate = df[df["event_type"] == "unplanned"]["rc"].mean() * 100
            fig_gauge = go.Figure()
            fig_gauge.add_trace(go.Bar(
                x=["Planned", "Unplanned"], y=[plan_rate, unpl_rate],
                marker_color=[NAVY, TEAL],
                text=[f"{plan_rate:.1f}%", f"{unpl_rate:.1f}%"],
                textposition="outside", textfont=dict(size=13, color=NAVY, family="Calibri"),
            ))
            fig_gauge.update_layout(
                height=200, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="white", plot_bgcolor="white",
                yaxis=dict(title="Closure rate (%)", gridcolor="#EEF2F8"),
                showlegend=False, bargap=0.4,
                font=dict(family="Calibri, sans-serif"),
            )
            st.plotly_chart(fig_gauge, use_container_width=True,
                            config={"displayModeBar": False})
        except Exception:
            pass

    # SHAP & calibration images
    shap_files = [
        ("t1_shap.png", "T1 Closure — Top SHAP Drivers"),
        ("t3_shap.png", "T3 Duration — Top SHAP Drivers"),
        ("t1_calibration.png", "T1 Probability Calibration"),
    ]
    img_cols = [p for fn, _ in shap_files
                if (p := C.FIGURES_DIR / fn).exists()]
    if img_cols:
        st.markdown("<div class='gl-section'>🔬 Explainability & Calibration</div>",
                    unsafe_allow_html=True)
        icols = st.columns(3)
        for col, (fn, cap) in zip(icols, shap_files):
            p = C.FIGURES_DIR / fn
            if p.exists():
                col.image(str(p), caption=cap, use_container_width=True)

    # Data findings
    st.markdown("<div class='gl-section'>⚠️ Data Findings That Shaped Everything</div>",
                unsafe_allow_html=True)
    findings = [
        ("#B71C1C", "#FFEBEE", "Leakage Trap",
         "Of 689 incidents with an end-point, 676 (98%) required closure. The end-point is "
         "recorded because a closure happened — not known at report time. A naive model "
         "scores F1 ≈ 0.98 and is meaningless. We ban all end-point and resolution-time "
         "columns from every model."),
        ("#E65100", "#FFF3E0", "Priority Is a Deterministic Rule",
         "priority = (corridor ≠ 'Non-corridor') with zero exceptions across 8,171 rows. "
         "We train a corridor-blind model (F1 0.916) that recovers priority from incident "
         "characteristics alone — enabling BTP to extend priority to new roads not yet "
         "formally classified as corridors."),
        ("#1565C0", "#E3F2FD", "Resolution Time Is Partly an Artifact",
         "60% of records (vehicle_breakdown) are auto-modified at ~130 min regardless of "
         "actual clearance. We re-frame T3 as bucket prediction (<1h / 1-3h / 3-8h / >8h) "
         "and identify which causes are reliably predictable (accidents: MAE 35 min) vs. "
         "not (potholes: MAE 9,600 min). Capturing a real 'road cleared' timestamp is the "
         "single biggest data improvement BTP can make."),
    ]
    for border, bg, title, body in findings:
        st.markdown(f"""
        <div class='gl-finding' style='background:{bg}; border-color:{border};'>
          <div class='gl-finding-head' style='color:{border};'>{title}</div>
          <div class='gl-finding-body' style='color:#333;'>{body}</div>
        </div>
        """, unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Sidebar form
    art = load_artifacts()
    ctx = art["context"]
    record, live, run = sidebar_form(ctx)

    # Sidebar info section
    st.sidebar.markdown(f"""
    <hr style='border-color:#2A4A80; margin:0.75rem 0;'>
    <div style='font-size:0.7rem; color:{ICE}; line-height:1.6;'>
      <strong style='color:{TEAL};'>Models trained on</strong><br>
      8,171 incidents · Nov 2023–Apr 2024<br>
      Bengaluru Traffic Police dataset<br>
      <br>
      <strong style='color:{TEAL};'>Three targets</strong><br>
      T1 · Closure risk (XGBoost + isotonic)<br>
      T2 · Dispatch priority (corridor-blind)<br>
      T3 · Duration bucket (4-class)<br>
      <br>
      <strong style='color:{TEAL};'>Text mining</strong><br>
      Groq llama-3.1-8b · 5,541 notes cached
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tab1, tab2 = st.tabs(["⚡  Forecast & Deploy", "📊  Insights & Performance"])

    with tab1:
        if run:
            with st.spinner("Scoring incident..."):
                out = predict_all(record, live_llm=live)
            render_predict(out)
        else:
            predict_tab_empty()

    with tab2:
        insights_tab()


if __name__ == "__main__":
    main()
