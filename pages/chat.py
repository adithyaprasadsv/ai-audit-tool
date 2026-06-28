# pages/chat.py
import streamlit as st
import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv
import chromadb

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extract import get_embedding

load_dotenv()

import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

openai_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_key)

st.title("Ask the Audit")
st.caption("Ask questions grounded in the EU AI Act and your extracted findings.")

# FINDINGS_PATH = "outputs/all_findings_reviewed.json"
# CHROMA_PATH   = "vectorstore"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FINDINGS_PATH = os.path.join(BASE_DIR, "outputs/all_findings_reviewed.json")
CHROMA_PATH   = os.path.join(BASE_DIR, "vectorstore")
SCORES_PATH   = os.path.join(BASE_DIR, "outputs/compliance_scores.json")

# --- load data ---
if not os.path.exists(FINDINGS_PATH):
    st.warning("No findings found. Run the extraction pipeline first.")
    st.stop()

with open(FINDINGS_PATH, encoding="utf-8") as f:
    findings = json.load(f)

# --- build findings collection in chroma ---
@st.cache_resource
def get_collections():
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    law_collection = chroma_client.get_collection("eu_ai_act")

    try:
        chroma_client.delete_collection("audit_findings")
    except:
        pass

    findings_collection = chroma_client.create_collection(
        name="audit_findings",
        metadata={"hnsw:space": "cosine"}
    )

    for i, f in enumerate(findings):
        text = (
            f"Document: {f['document']}. "
            f"Control: {f['control_id']} — {f['control_name']}. "
            f"Status: {f['status']}. Severity: {f['severity']}. "
            f"Finding: {f['finding']}. "
            f"Evidence: {f['evidence']}. "
            f"Legal basis: {f.get('legal_basis','')}. "
            f"Auditor recommendation: {f.get('auditor_recommendation','')}."
        )
        embedding = get_embedding(text)
        findings_collection.add(
            ids=[f"finding_{i}"],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "document":   f["document"],
                "control_id": f["control_id"],
                "status":     f["status"],
                "severity":   f["severity"]
            }]
        )

    return law_collection, findings_collection

with st.spinner("Loading knowledge base..."):
    law_col, findings_col = get_collections()

# --- suggested questions ---
st.markdown("**Suggested questions**")
suggestions = [
    "Which documents fail RC-05 human oversight?",
    "What does the EU AI Act say about risk management?",
    "What are the highest severity gaps across all documents?",
    "Which document is most compliant overall?",
    "What recommendations were made for data governance?",
    "Which findings were flagged for human review?"
]

cols = st.columns(3)
for i, suggestion in enumerate(suggestions):
    with cols[i % 3]:
        if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
            st.session_state["chat_input"] = suggestion

st.divider()

# --- chat history ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- chat input ---
user_input = st.chat_input(
    "Ask about the audit findings or EU AI Act...",
    key="chat_input_box"
)

if "chat_input" in st.session_state and st.session_state["chat_input"]:
    user_input = st.session_state.pop("chat_input")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving relevant context..."):

            query_embedding = get_embedding(user_input)

            law_results = law_col.query(
                query_embeddings=[query_embedding],
                n_results=3
            )
            findings_results = findings_col.query(
                query_embeddings=[query_embedding],
                n_results=4
            )

            law_context = "\n\n".join(law_results["documents"][0])
            findings_context = "\n\n".join(findings_results["documents"][0])

            finding_metas = findings_results["metadatas"][0]

        system_prompt = """You are an expert EU AI Act compliance auditor assistant.
You answer questions using two sources of information:
1. EU AI Act legal text (retrieved from the regulation)
2. Audit findings extracted from real AI system documents

Rules:
- Always cite which document and control your finding references
- Always cite the specific EU AI Act article when referencing legal requirements
- Be concise and precise — this is an audit context, not a general chat
- If the answer is not in the retrieved context, say so clearly
- Format your answer with clear sections when answering complex questions
- Flag when findings were auditor-reviewed vs LLM-only"""

        user_prompt = f"""Question: {user_input}

RETRIEVED EU AI ACT LEGAL TEXT:
{law_context}

RETRIEVED AUDIT FINDINGS:
{findings_context}

Answer the question using only the retrieved context above.
Cite sources explicitly: mention the document name and control ID for findings,
and the Article number for legal text."""

        history = [{"role": "system", "content": system_prompt}]
        for msg in st.session_state.messages[:-1]:
            history.append({"role": msg["role"], "content": msg["content"]})
        history.append({"role": "user", "content": user_prompt})

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=history,
            temperature=0.2,
            max_tokens=1000,
            stream=True
        )

        response_text = ""
        placeholder   = st.empty()
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            response_text += delta
            placeholder.markdown(response_text + "▌")
        placeholder.markdown(response_text)

        # --- show sources ---
        with st.expander("Sources used", expanded=False):
            st.markdown("**EU AI Act passages retrieved:**")
            for i, passage in enumerate(law_results["documents"][0]):
                st.markdown(
                    f"<div style='background:#E6F1FB;border-left:3px solid "
                    f"#85B7EB;padding:8px 12px;border-radius:4px;font-size:12px;"
                    f"color:#0C447C;margin:6px 0;'>{passage[:300]}...</div>",
                    unsafe_allow_html=True
                )

            st.markdown("**Audit findings retrieved:**")
            for meta in finding_metas:
                sev_color = {
                    "high": "#FAECE7", "medium": "#FAEEDA",
                    "low":  "#EAF3DE", "none":   "#E1F5EE"
                }.get(meta.get("severity",""), "#F1EFE8")
                sev_text = {
                    "high": "#712B13", "medium": "#633806",
                    "low":  "#27500A", "none":   "#085041"
                }.get(meta.get("severity",""), "#333")
                label = meta["document"].replace("_system_card","") \
                                        .replace("_card","") \
                                        .replace("_"," ").title()
                st.markdown(
                    f"<div style='background:{sev_color};border-left:3px solid;"
                    f"padding:8px 12px;border-radius:4px;font-size:12px;"
                    f"color:{sev_text};margin:6px 0;'>"
                    f"<b>{meta['control_id']}</b> · {label} · "
                    f"{meta['status']} / {meta['severity']}</div>",
                    unsafe_allow_html=True
                )

        st.session_state.messages.append({
            "role": "assistant", "content": response_text
        })

# --- clear chat ---
if st.session_state.messages:
    st.divider()
    if st.button("Clear conversation", type="secondary"):
        st.session_state.messages = []
        st.rerun()