# app.py
import streamlit as st

st.set_page_config(
    page_title="AI Audit Tool",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("AI Governance Audit")
st.sidebar.caption("EU AI Act · Articles 9–15")

pages = {
    "Upload & Extract":  "../pages/upload.py",
    "Compliance Dashboard": "../pages/dashboard.py",
    "Auditor Review":    "../pages/review.py",
    "Ask the Audit":     "../pages/chat.py"
}

page = st.sidebar.radio("Navigation", list(pages.keys()))

st.sidebar.divider()
st.sidebar.caption("Model: gpt-4o · RAG: ChromaDB\nScoring: weighted v1.0 · Author: AP")

if page == "Upload & Extract":
    exec(open("../pages/upload.py", encoding="utf-8").read())
elif page == "Compliance Dashboard":
    exec(open("../pages/dashboard.py", encoding="utf-8").read())
elif page == "Auditor Review":
    exec(open("../pages/review.py", encoding="utf-8").read())
elif page == "Ask the Audit":
    exec(open("../pages/chat.py", encoding="utf-8").read())