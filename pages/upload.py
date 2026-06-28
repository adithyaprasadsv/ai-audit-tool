# pages/upload.py
import streamlit as st
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extract import load_taxonomy, run_extraction, extract_text_from_pdf, get_chroma_collection, retrieve_legal_context, build_prompt, get_confidence_score
from openai import OpenAI
from dotenv import load_dotenv
import tempfile

load_dotenv()

import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

openai_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_key)

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FINDINGS_PATH = os.path.join(BASE_DIR, "outputs/all_findings_reviewed.json")
CHROMA_PATH   = os.path.join(BASE_DIR, "vectorstore")
SCORES_PATH   = os.path.join(BASE_DIR, "outputs/compliance_scores.json")

st.title("Upload & Extract")
st.caption("Upload an AI system document and run the EU AI Act compliance extraction pipeline.")

col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Upload AI system document (PDF)",
        type=["pdf"],
        help="Model cards, system cards, or technical reports"
    )

with col2:
    st.markdown("**Pipeline steps**")
    st.markdown("""
    1. Extract text from PDF
    2. Retrieve legal context per control
    3. Extract findings via LLM
    4. Score confidence per finding
    """)

if uploaded_file:
    doc_name = uploaded_file.name.replace(".pdf", "").replace(" ", "_").lower()

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Document", uploaded_file.name[:24])
    col_b.metric("Size", f"{uploaded_file.size / 1024:.1f} KB")
    col_c.metric("Status", "Ready")

    st.divider()

    if st.button("Run extraction pipeline", type="primary", use_container_width=True):

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        taxonomy   = load_taxonomy()
        collection = get_chroma_collection()
        doc_text   = extract_text_from_pdf(tmp_path)

        st.markdown("**Extracting findings...**")

        progress    = st.progress(0)
        status_box  = st.empty()
        results_box = st.container()

        findings  = []
        controls  = taxonomy["risk_categories"]
        n         = len(controls)

        for i, control in enumerate(controls):
            status_box.info(
                f"Processing {control['id']} — {control['name']}..."
            )

            legal_context = retrieve_legal_context(collection, control)
            prompt        = build_prompt(doc_text, control, legal_context)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a precise EU AI Act compliance auditor. Output only valid JSON objects. No markdown, no explanation."},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json","").replace("```","").strip()

            try:
                finding = json.loads(raw)
                conf    = get_confidence_score(finding, doc_text)
                finding.update({
                    "document":             doc_name,
                    "confidence":           conf["confidence"],
                    "confidence_reason":    conf["confidence_reason"],
                    "requires_human_review":conf["requires_human_review"],
                    "auditor_recommendation": "",
                    "auditor_reviewed":     False
                })
                findings.append(finding)

                sev_colors = {
                    "high": "🔴", "medium": "🟡",
                    "low":  "🟢", "none":   "✅"
                }
                icon = sev_colors.get(finding["severity"], "⚪")
                review_flag = "⚠️ needs review" if finding["requires_human_review"] else "✓"

                with results_box:
                    st.markdown(
                        f"{icon} **{finding['control_id']}** — "
                        f"`{finding['status']}` / `{finding['severity']}` "
                        f"· confidence: {finding['confidence']:.2f} {review_flag}"
                    )

            except Exception as e:
                st.warning(f"{control['id']} failed: {e}")

            progress.progress((i + 1) / n)

        status_box.success(f"Extraction complete — {len(findings)} findings extracted")
        os.unlink(tmp_path)

        out_path = os.path.join(OUTPUT_DIR, f"{doc_name}_findings.json")
        with open(out_path, "w") as f:
            json.dump(findings, f, indent=2)

        master_path = os.path.join(OUTPUT_DIR, "all_findings_reviewed.json")
        existing = []
        if os.path.exists(master_path):
            with open(master_path) as f:
                existing = json.load(f)
            existing = [e for e in existing if e.get("document") != doc_name]
        existing.extend(findings)
        with open(master_path, "w") as f:
            json.dump(existing, f, indent=2)

        st.divider()
        col_x, col_y, col_z = st.columns(3)
        gaps   = sum(1 for f in findings if f["status"]  == "gap")
        highs  = sum(1 for f in findings if f["severity"] == "high")
        review = sum(1 for f in findings if f["requires_human_review"])

        col_x.metric("Gaps identified",     gaps)
        col_y.metric("High severity",        highs)
        col_z.metric("Flagged for review",   review)

        st.download_button(
            "Download findings JSON",
            data=json.dumps(findings, indent=2),
            file_name=f"{doc_name}_findings.json",
            mime="application/json"
        )

elif not uploaded_file:
    st.info("Upload a PDF above to begin. Supported formats: model cards, system cards, technical reports.")

    st.divider()
    st.markdown("**Previously extracted documents**")

    existing_files = [
        f for f in os.listdir(OUTPUT_DIR)
        if f.endswith("_findings.json") and f != "all_findings.json"
    ] if os.path.exists(OUTPUT_DIR) else []

    if existing_files:
        for fname in existing_files:
            with open(os.path.join(OUTPUT_DIR, fname)) as f:
                data = json.load(f)
            gaps  = sum(1 for d in data if d["status"]  == "gap")
            highs = sum(1 for d in data if d["severity"] == "high")
            st.markdown(
                f"📄 `{fname}` — {len(data)} findings · "
                f"{gaps} gaps · {highs} high severity"
            )
    else:
        st.caption("No documents extracted yet.")