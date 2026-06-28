# views/review.py
import streamlit as st
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

st.title("Auditor Review")
st.caption("Review LLM findings, apply overrides, and sign off. All actions are timestamped.")

# FINDINGS_PATH = "../outputs/all_findings_reviewed.json"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FINDINGS_PATH = os.path.join(BASE_DIR, "outputs/all_findings_reviewed.json")
CHROMA_PATH   = os.path.join(BASE_DIR, "vectorstore")
SCORES_PATH   = os.path.join(BASE_DIR, "outputs/compliance_scores.json")


if not os.path.exists(FINDINGS_PATH):
    st.warning("No findings found. Run the extraction pipeline first.")
    st.stop()

with open(FINDINGS_PATH, encoding="utf-8") as f:
    findings = json.load(f)

def save_findings(findings):
    with open(FINDINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)

# --- summary bar ---
total    = len(findings)
reviewed = sum(1 for f in findings if f["auditor_reviewed"])
pending  = total - reviewed
flagged  = sum(1 for f in findings if f.get("requires_human_review") and not f["auditor_reviewed"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total findings",   total)
c2.metric("Reviewed",         reviewed)
c3.metric("Pending",          pending)
c4.metric("Flagged priority", flagged)

if pending == 0:
    st.success("All findings reviewed and signed off.")
else:
    st.info(f"{pending} findings pending auditor review.")

st.divider()

# --- filters ---
col1, col2, col3 = st.columns(3)
with col1:
    docs = sorted(set(f["document"] for f in findings))
    doc_labels = {
        d: d.replace("_system_card","").replace("_card","")
            .replace("_"," ").title()
        for d in docs
    }
    selected_doc = st.selectbox(
        "Document",
        options=["All"] + list(doc_labels.values())
    )

with col2:
    review_filter = st.selectbox(
        "Review status",
        options=["All", "Pending only", "Reviewed only", "Flagged priority"]
    )

with col3:
    sev_filter = st.selectbox(
        "Severity",
        options=["All", "high", "medium", "low", "none"]
    )

# --- apply filters ---
filtered = findings.copy()

if selected_doc != "All":
    doc_key = next((k for k,v in doc_labels.items() if v == selected_doc), None)
    if doc_key:
        filtered = [f for f in filtered if f["document"] == doc_key]

if review_filter == "Pending only":
    filtered = [f for f in filtered if not f["auditor_reviewed"]]
elif review_filter == "Reviewed only":
    filtered = [f for f in filtered if f["auditor_reviewed"]]
elif review_filter == "Flagged priority":
    filtered = [f for f in filtered if f.get("requires_human_review") and not f["auditor_reviewed"]]

if sev_filter != "All":
    filtered = [f for f in filtered if f["severity"] == sev_filter]

st.caption(f"Showing {len(filtered)} findings")
st.divider()

# --- finding cards ---
SEV_COLOR = {
    "high":   "#FAECE7",
    "medium": "#FAEEDA",
    "low":    "#EAF3DE",
    "none":   "#E1F5EE"
}
SEV_TEXT = {
    "high":   "#712B13",
    "medium": "#633806",
    "low":    "#27500A",
    "none":   "#085041"
}
STATUS_COLOR = {
    "gap":          "#FAECE7",
    "partial":      "#FAEEDA",
    "compliant":    "#E1F5EE",
    "not_assessed": "#F1EFE8"
}

for idx, finding in enumerate(filtered):
    global_idx = next(
        (i for i, f in enumerate(findings)
         if f["document"] == finding["document"]
         and f["control_id"] == finding["control_id"]),
        None
    )
    if global_idx is None:
        continue

    sev    = finding["severity"]
    status = finding["status"]
    label  = finding["document"].replace("_system_card","") \
                                .replace("_card","") \
                                .replace("_"," ").title()

    reviewed_flag = "✅" if finding["auditor_reviewed"] else (
        "⚠️" if finding.get("requires_human_review") else "⏳"
    )

    with st.expander(
        f"{reviewed_flag} {finding['control_id']} — {finding['control_name']} · {label}",
        expanded=not finding["auditor_reviewed"]
    ):
        # finding details
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.markdown(
            f"<span style='background:{STATUS_COLOR.get(status,'#eee')};"
            f"color:{SEV_TEXT.get(sev,'#333')};padding:3px 10px;"
            f"border-radius:99px;font-size:12px;font-weight:500;'>"
            f"{status}</span>",
            unsafe_allow_html=True
        )
        col_b.markdown(
            f"<span style='background:{SEV_COLOR.get(sev,'#eee')};"
            f"color:{SEV_TEXT.get(sev,'#333')};padding:3px 10px;"
            f"border-radius:99px;font-size:12px;font-weight:500;'>"
            f"{sev}</span>",
            unsafe_allow_html=True
        )
        col_c.markdown(
            f"<span style='font-size:12px;color:#888;'>"
            f"Confidence: {finding.get('confidence', 0):.2f}</span>",
            unsafe_allow_html=True
        )
        col_d.markdown(
            f"<span style='font-size:12px;color:#888;'>"
            f"{'⚠️ Review flagged' if finding.get('requires_human_review') else '✓ Auto-cleared'}</span>",
            unsafe_allow_html=True
        )

        st.markdown(f"**Finding:** {finding['finding']}")
        st.markdown(
            f"<div style='background:#F9F8F6;border-left:3px solid #D3D1C7;"
            f"padding:8px 12px;border-radius:4px;font-size:13px;"
            f"color:#5F5E5A;font-style:italic;margin:8px 0;'>"
            f"\"{finding['evidence']}\"</div>",
            unsafe_allow_html=True
        )

        if finding.get("legal_basis"):
            st.markdown(
                f"<div style='background:#E6F1FB;border-left:3px solid #85B7EB;"
                f"padding:8px 12px;border-radius:4px;font-size:12px;"
                f"color:#0C447C;margin:8px 0;'>"
                f"⚖️ <b>Legal basis:</b> {finding['legal_basis']}</div>",
                unsafe_allow_html=True
            )

        st.markdown(
            f"**LLM recommendation:** {finding.get('llm_recommendation','—')}"
        )

        st.divider()

        # auditor action
        st.markdown("**Auditor action**")

        action_key = f"action_{global_idx}"
        action = st.radio(
            "Decision",
            options=["Agree with LLM", "Override", "Escalate"],
            index=0,
            key=action_key,
            horizontal=True
        )

        rec_key = f"rec_{global_idx}"
        if finding.get("auditor_recommendation"):
            default_rec = finding["auditor_recommendation"]
        elif action == "Agree with LLM":
            default_rec = finding.get("llm_recommendation", "")
        else:
            default_rec = ""

        auditor_rec = st.text_area(
            "Auditor recommendation",
            value=default_rec,
            height=100,
            key=rec_key,
            placeholder="Write your recommendation here..."
        )

        if action == "Override":
            ov_col1, ov_col2 = st.columns(2)
            with ov_col1:
                new_status = st.selectbox(
                    "Override status",
                    options=["compliant","partial","gap","not_assessed"],
                    index=["compliant","partial","gap","not_assessed"].index(
                        finding["status"]
                    ),
                    key=f"ovstatus_{global_idx}"
                )
            with ov_col2:
                new_severity = st.selectbox(
                    "Override severity",
                    options=["none","low","medium","high"],
                    index=["none","low","medium","high"].index(
                        finding["severity"]
                    ),
                    key=f"ovsev_{global_idx}"
                )

        if st.button(
            "Sign off",
            key=f"signoff_{global_idx}",
            type="primary"
        ):
            findings[global_idx]["auditor_recommendation"] = auditor_rec
            findings[global_idx]["auditor_reviewed"]       = True
            findings[global_idx]["auditor_action"]         = action
            findings[global_idx]["auditor_timestamp"]      = datetime.now().isoformat()

            if action == "Override":
                findings[global_idx]["status"]   = new_status
                findings[global_idx]["severity"]  = new_severity
                findings[global_idx]["auditor_override"] = True

            if action == "Escalate":
                findings[global_idx]["escalated"] = True

            save_findings(findings)
            st.success(
                f"✅ {finding['control_id']} signed off — "
                f"{action} · {datetime.now().strftime('%H:%M:%S')}"
            )
            st.rerun()

        if finding["auditor_reviewed"]:
            ts = finding.get("auditor_timestamp","")
            if ts:
                dt = datetime.fromisoformat(ts).strftime("%d %b %Y %H:%M")
                st.caption(
                    f"Signed off · {finding.get('auditor_action','—')} · {dt}"
                )

st.divider()

# --- bulk sign-off for low-risk findings ---
st.subheader("Bulk sign-off")
st.caption("Sign off all partial/low-confidence findings at once with a standard recommendation.")

pending_partial = [
    f for f in findings
    if not f["auditor_reviewed"] and f["status"] == "partial"
]

if pending_partial:
    st.info(f"{len(pending_partial)} partial findings pending.")
    if st.button("Bulk sign off all partial findings", type="secondary"):
        for f in findings:
            if not f["auditor_reviewed"] and f["status"] == "partial":
                f["auditor_recommendation"] = (
                    "Partial compliance noted. Provider should expand "
                    "documentation to fully satisfy the relevant EU AI Act "
                    "article. Re-assess at next audit cycle."
                )
                f["auditor_reviewed"]  = True
                f["auditor_action"]    = "Agree with LLM"
                f["auditor_timestamp"] = datetime.now().isoformat()
        save_findings(findings)
        st.success("Bulk sign-off complete.")
        st.rerun()
else:
    st.caption("No partial findings pending bulk sign-off.")

# --- audit trail export ---
st.divider()
st.subheader("Audit trail")

trail = [
    {
        "document":        f["document"],
        "control_id":      f["control_id"],
        "status":          f["status"],
        "severity":        f["severity"],
        "action":          f.get("auditor_action","pending"),
        "override":        f.get("auditor_override", False),
        "escalated":       f.get("escalated", False),
        "recommendation":  f.get("auditor_recommendation",""),
        "timestamp":       f.get("auditor_timestamp","")
    }
    for f in findings if f["auditor_reviewed"]
]

if trail:
    import pandas as pd
    trail_df = pd.DataFrame(trail)
    st.dataframe(trail_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download audit trail CSV",
        data=trail_df.to_csv(index=False),
        file_name="audit_trail.csv",
        mime="text/csv"
    )
else:
    st.caption("No signed-off findings yet.")