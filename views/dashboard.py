# views/dashboard.py
import streamlit as st
import json
import os
import sys
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoring import run_scoring, load_inputs

import streamlit as st
import os
from dotenv import load_dotenv

from openai import OpenAI

load_dotenv()
try:
    openai_key = st.secrets.get("OPENAI_API_KEY")
except:
    openai_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=openai_key)

st.title("Compliance Dashboard")
st.caption("EU AI Act Articles 9–15 · Weighted scoring model v1.0")

# FINDINGS_PATH = "outputs/all_findings_reviewed.json"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FINDINGS_PATH = os.path.join(BASE_DIR, "outputs/all_findings_reviewed.json")
CHROMA_PATH   = os.path.join(BASE_DIR, "vectorstore")
SCORES_PATH   = os.path.join(BASE_DIR, "outputs/compliance_scores.json")

if not os.path.exists(FINDINGS_PATH):
    st.warning("No findings found. Run the extraction pipeline first.")
    st.stop()

with open(FINDINGS_PATH) as f:
    findings = json.load(f)

if not findings:
    st.warning("Findings file is empty.")
    st.stop()

findings, model = load_inputs()
scores, _       = run_scoring(), None

with open("outputs/compliance_scores.json") as f:
    score_data = json.load(f)

scores = score_data["scores"]
df     = pd.DataFrame(findings)

# --- top metrics ---
total_findings = len(findings)
gaps           = sum(1 for f in findings if f["status"]  == "gap")
highs          = sum(1 for f in findings if f["severity"] == "high")
flagged        = sum(1 for f in findings if f.get("requires_human_review"))
reviewed       = sum(1 for f in findings if f["auditor_reviewed"])

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total findings",     total_findings)
c2.metric("Gaps identified",    gaps)
c3.metric("High severity",      highs)
c4.metric("Flagged for review", flagged)
c5.metric("Auditor reviewed",   reviewed)

st.divider()

# --- compliance scores ---
st.subheader("Compliance scores")

BAND_COLORS = {
    "Strong":   "#085041",
    "Adequate": "#633806",
    "Weak":     "#993C1D",
    "Critical": "#712B13"
}

score_cols = st.columns(len(scores))
for i, (doc, data) in enumerate(
    sorted(scores.items(), key=lambda x: x[1]["total_score"], reverse=True)
):
    label = doc.replace("_system_card","").replace("_card","") \
               .replace("_"," ").title()
    color = BAND_COLORS.get(data["band"], "#888780")
    with score_cols[i]:
        st.markdown(
            f"""<div style='text-align:center; padding:1rem;
                background:var(--background-color);
                border:0.5px solid #D3D1C7;
                border-radius:12px;'>
                <div style='font-size:28px; font-weight:500;
                     color:{color};'>{data['total_score']}%</div>
                <div style='font-size:13px; font-weight:500;
                     margin:4px 0; color:{color};'>{data['band']}</div>
                <div style='font-size:12px;
                     color:#888;'>{label}</div>
            </div>""",
            unsafe_allow_html=True
        )

st.divider()

# --- heatmap ---
st.subheader("Compliance heatmap")
st.caption("Color = severity of finding. White = compliant.")

docs     = df["document"].unique().tolist()
controls = df["control_id"].unique().tolist()

STATUS_VAL = {"compliant": 1.0, "partial": 0.5, "gap": 0.0, "not_assessed": 0.25}
COLOR_MAP  = {
    "gap":          "#FAECE7",
    "partial":      "#FAEEDA",
    "compliant":    "#E1F5EE",
    "not_assessed": "#F1EFE8"
}

z_vals   = []
z_text   = []
for ctrl in controls:
    row_vals = []
    row_text = []
    for doc in docs:
        match = df[(df["document"]==doc) & (df["control_id"]==ctrl)]
        if match.empty:
            row_vals.append(0.5)
            row_text.append("N/A")
        else:
            f = match.iloc[0]
            row_vals.append(STATUS_VAL.get(f["status"], 0.5))
            row_text.append(f"{f['status']}<br>{f['severity']}")
    z_vals.append(row_vals)
    z_text.append(row_text)

doc_labels = [
    d.replace("_system_card","").replace("_card","")
     .replace("_"," ").title()
    for d in docs
]

fig_heat = go.Figure(data=go.Heatmap(
    z=z_vals,
    x=doc_labels,
    y=controls,
    text=z_text,
    texttemplate="%{text}",
    textfont={"size": 11},
    colorscale=[
        [0.0,  "#FAECE7"],
        [0.25, "#F1EFE8"],
        [0.5,  "#FAEEDA"],
        [1.0,  "#E1F5EE"]
    ],
    showscale=False
))
fig_heat.update_layout(
    margin=dict(l=20, r=20, t=20, b=20),
    height=320,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(size=12)
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# --- per-control breakdown ---
st.subheader("Per-control breakdown")

left, right = st.columns(2)

with left:
    status_counts = df.groupby(["control_id","status"]).size().reset_index(name="count")
    fig_bar = px.bar(
        status_counts,
        x="control_id", y="count", color="status",
        color_discrete_map={
            "gap":       "#FAECE7",
            "partial":   "#FAEEDA",
            "compliant": "#E1F5EE"
        },
        labels={"control_id":"Control","count":"Findings","status":"Status"}
    )
    fig_bar.update_layout(
        margin=dict(l=0,r=0,t=30,b=0),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.2),
        title="Status distribution per control"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with right:
    conf_df = df.groupby("document")["confidence"].mean().reset_index()
    conf_df["label"] = conf_df["document"].str.replace(
        "_system_card","").str.replace("_card","") \
        .str.replace("_"," ").str.title()
    fig_conf = px.bar(
        conf_df, x="label", y="confidence",
        labels={"label":"Document","confidence":"Avg confidence"},
        color="confidence",
        color_continuous_scale=["#FAECE7","#FAEEDA","#E1F5EE"],
        range_color=[0.5, 1.0]
    )
    fig_conf.update_layout(
        margin=dict(l=0,r=0,t=30,b=0),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False,
        title="Average confidence per document"
    )
    st.plotly_chart(fig_conf, use_container_width=True)

st.divider()

# --- detailed findings table ---
st.subheader("Findings detail")

filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    doc_filter = st.multiselect(
        "Document",
        options=doc_labels,
        default=doc_labels
    )
with filter_col2:
    status_filter = st.multiselect(
        "Status",
        options=["gap","partial","compliant","not_assessed"],
        default=["gap","partial","compliant","not_assessed"]
    )
with filter_col3:
    sev_filter = st.multiselect(
        "Severity",
        options=["high","medium","low","none"],
        default=["high","medium","low","none"]
    )

display_df = df.copy()
display_df["doc_label"] = display_df["document"].str.replace(
    "_system_card","").str.replace("_card","") \
    .str.replace("_"," ").str.title()

filtered = display_df[
    display_df["doc_label"].isin(doc_filter) &
    display_df["status"].isin(status_filter) &
    display_df["severity"].isin(sev_filter)
]

show_cols = ["doc_label","control_id","control_name",
             "status","severity","confidence","finding"]
col_labels = {
    "doc_label":    "Document",
    "control_id":   "Control",
    "control_name": "Name",
    "status":       "Status",
    "severity":     "Severity",
    "confidence":   "Confidence",
    "finding":      "Finding"
}

st.dataframe(
    filtered[show_cols].rename(columns=col_labels),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Confidence": st.column_config.ProgressColumn(
            "Confidence", min_value=0, max_value=1, format="%.2f"
        )
    }
)

# --- systemic risks ---
st.divider()
st.subheader("Systemic risks")
st.caption("Controls with gaps across 3+ documents")

gap_counts = df[df["status"]=="gap"].groupby("control_id")["document"].count()
systemic   = gap_counts[gap_counts >= 3].sort_values(ascending=False)

if systemic.empty:
    st.info("No systemic gaps found across 3+ documents.")
else:
    for ctrl_id, count in systemic.items():
        ctrl_rows = df[df["control_id"]==ctrl_id].iloc[0]
        st.error(
            f"**{ctrl_id} — {ctrl_rows['control_name']}** · "
            f"Gap in {count}/4 documents · "
            f"Weight: {int(model['weights'].get(ctrl_id,0)*100)}% of total score"
        )