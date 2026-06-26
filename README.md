# AI Governance Audit Tool

An end-to-end AI compliance audit system that assesses AI system
documentation against EU AI Act Articles 9–15 using RAG-grounded
LLM extraction, a custom weighted scoring model, and a human
auditor sign-off workflow.

Web App Access deployed through GitHub: [text](https://ai-audit-tool-poc.streamlit.app/)

## What it does

1. **Extracts** compliance findings from AI system documents (PDFs)
   using GPT-4o, grounded in the actual EU AI Act legal text via RAG
2. **Scores** each document using a weighted compliance model
   designed around Article criticality
3. **Flags** low-confidence findings automatically for human review
4. **Provides** a structured auditor sign-off workflow with full
   audit trail and timestamps
5. **Answers** natural language questions over findings and legal
   text via a RAG chat interface

## Architecture
**PDF documents**
        ↓
**Text extraction** (PyPDF2)
        ↓
**RAG retrieval** (ChromaDB + text-embedding-3-small)
        ↓
**LLM extraction** (GPT-4o) → *findings JSON*
        ↓
**Confidence scoring** → *human review flags*
        ↓
**Weighted compliance scoring** (custom model)
        ↓
**Streamlit app** (4 pages) + **PDF report** (ReportLab)

## Controls assessed

| ID | Article | Control |
|----|---------|---------|
| RC-01 | Article 9  | Risk management system |
| RC-02 | Article 10 | Data governance |
| RC-03 | Article 11 | Technical documentation |
| RC-04 | Article 13 | Transparency & instructions for use |
| RC-05 | Article 14 | Human oversight |
| RC-06 | Article 15 | Accuracy, robustness & cybersecurity |

## Scoring model

Each control is weighted by operational criticality:

| Control | Weight | Rationale |
|---------|--------|-----------|
| RC-05   | 25%    | Most critical for deployed systems |
| RC-01   | 20%    | Lifecycle risk process underpins all controls |
| RC-03   | 18%    | Regulators cannot assess undocumented systems |
| RC-02   | 15%    | Foundational data quality requirement |
| RC-04   | 12%    | Surface-level transparency is common |
| RC-06   | 10%    | Benchmarks often present even if incomplete |

Score = Σ (base_score − severity_penalty) × weight × 100

## Setup

```bash
git clone https://github.com/yourname/ai-audit-tool
cd ai-audit-tool
pip install -r requirements.txt
cp .env.example .env  # add your OpenAI API key
python build_vectorstore.py
streamlit run scripts/app.py
```

## Documents assessed

Claude 4 System Card · GPT-5 System Card ·
Google Gemini Model Card · Meta Llama 3.1 Model Card

## Key findings

- RC-05 (Human oversight) is the most systemic gap —
  absent in 3/4 documents
- RC-03 (Technical documentation) fails across all 4 —
  every provider redirects to external sources
- No document scores above 60% — none would satisfy
  a full EU AI Act regulatory submission

## Limitations

Findings are based on public model cards only, not internal
compliance documentation. A gap indicates absence of evidence
in the public document, not absence of the control in practice.

## Tech stack

Python · OpenAI GPT-4o · ChromaDB · Streamlit ·
ReportLab · Plotly · Pandas