# app.py
import streamlit as st
import os

import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

openai_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_key)

st.set_page_config(
    page_title="AI Audit Tool",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("AI Governance Audit")
st.sidebar.caption("EU AI Act · Articles 9–15")

pages = {
    "Upload & Extract":  "pages/upload.py",
    "Compliance Dashboard": "pages/dashboard.py",
    "Auditor Review":    "pages/review.py",
    "Ask the Audit":     "pages/chat.py"
}

page = st.sidebar.radio("Navigation", list(pages.keys()))

st.sidebar.divider()
st.sidebar.caption("Model: gpt-4o · RAG: ChromaDB\nScoring: weighted v1.0 · Author: AP")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(BASE_DIR, "outputs"), exist_ok=True)

if page == "Upload & Extract":
    exec(open(os.path.join(BASE_DIR, "pages/upload.py"), encoding="utf-8").read())
elif page == "Compliance Dashboard":
    exec(open(os.path.join(BASE_DIR, "pages/dashboard.py"), encoding="utf-8").read())
elif page == "Auditor Review":
    exec(open(os.path.join(BASE_DIR, "pages/review.py"), encoding="utf-8").read())
elif page == "Ask the Audit":
    exec(open(os.path.join(BASE_DIR, "pages/chat.py"), encoding="utf-8").read())