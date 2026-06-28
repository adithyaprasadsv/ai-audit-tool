# extract.py
import json
import os
import chromadb
from openai import OpenAI
from PyPDF2 import PdfReader
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

CHROMA_PATH = "vectorstore"

def load_taxonomy(path="config/risk_taxonomy.json"):
    with open(path) as f:
        return json.load(f)

def get_chroma_collection():
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return chroma_client.get_collection("eu_ai_act")

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def retrieve_legal_context(collection, control, n_results=3):
    query = f"{control['name']} {control['article']} {' '.join(control['audit_questions'])}"
    embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results
    )
    chunks = results["documents"][0]
    return "\n\n".join(chunks)

def extract_text_from_pdf(path, max_chars=8000):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
        if len(text) >= max_chars:
            break
    return text[:max_chars]

def build_prompt(doc_text, control, legal_context):
    return f"""You are an EU AI Act compliance auditor assessing a single control.

CONTROL BEING ASSESSED:
ID: {control['id']}
Name: {control['name']}
Article: {control['article']}
Description: {control['description']}

Audit questions:
{chr(10).join(f'- {q}' for q in control['audit_questions'])}

RELEVANT EU AI ACT LEGAL TEXT (retrieved):
{legal_context}

DOCUMENT BEING AUDITED:
{doc_text}

SEVERITY RULES (strictly follow):
- "high": evidence entirely absent, or document redirects to external source
- "medium": evidence exists but vague, incomplete, or lacks lifecycle coverage
- "low": evidence exists, mostly adequate, minor gaps only
- "none": compliant status only
Do NOT default to medium. When unsure between high and medium, assign high.

REASONING STEP (do this silently before outputting JSON):
1. Is there direct evidence in THIS document, or does it redirect elsewhere?
2. Redirects to external documents = gap/high, not partial/medium.
3. Does the evidence satisfy the specific legal text retrieved above?

EXAMPLES OF CORRECT OUTPUT:

Example 1 — gap, high severity:
Document says: "For full technical details, please refer to our technical report."
Correct output:
{{
  "status": "gap",
  "severity": "high",
  "finding": "Document redirects to external source rather than providing self-contained compliance documentation.",
  "evidence": "For full technical details, please refer to our technical report.",
  "legal_basis": "Article 11 requires technical documentation to be drawn up before the system is placed on the market."
}}

Example 2 — compliant:
Document says: "The system includes a kill switch accessible to all operators. Override procedures are documented in Section 4."
Correct output:
{{
  "status": "compliant",
  "severity": "none",
  "finding": "Human override mechanisms are explicitly documented with operator access confirmed.",
  "evidence": "The system includes a kill switch accessible to all operators.",
  "legal_basis": "Article 14 requires high-risk AI systems to allow human intervention and override."
}}

OUTPUT INSTRUCTIONS:
Return ONLY a single valid JSON object — not an array. No markdown, no explanation, no preamble.

Required fields:
- "control_id": "{control['id']}"
- "control_name": "{control['name']}"
- "status": one of "compliant", "partial", "gap", "not_assessed"
- "severity": one of "high", "medium", "low", "none"
- "finding": one sentence describing what is present or missing
- "evidence": short direct quote from the document, or "none found"
- "legal_basis": the specific EU AI Act requirement this finding maps to, quoted from the retrieved legal text above
- "llm_recommendation": suggested remediation for gaps or partials, or "none" if compliant
- "auditor_recommendation": ""
- "auditor_reviewed": false"""

def get_confidence_score(finding, doc_text):
    prompt = f"""You just produced this audit finding:

Control: {finding['control_id']} — {finding['control_name']}
Status: {finding['status']}
Severity: {finding['severity']}
Finding: {finding['finding']}
Evidence: {finding['evidence']}

Rate your confidence in this finding on a scale of 0.0 to 1.0.

Consider:
- Is the evidence a direct quote from the document? If yes, confidence should be 0.75+
- Is status "gap" with evidence "none found"? Confidence should be 0.65-0.70 — absence is uncertain by nature
- Is the status clearly supported by the quote? If yes, add 0.10 to your base score
- Only score below 0.60 if the finding contradicts the evidence or the status is a significant judgment call

Calibration guide:
- Direct quote + clear status match = 0.75-0.95
- Partial evidence + reasonable inference = 0.70-0.85
- "none found" gap findings = 0.50-0.75
- Contradictory or ambiguous evidence = 0.40-0.60

Output ONLY a valid JSON object. No markdown, no explanation.

Required fields:
- "confidence": float between 0.0 and 1.0
- "confidence_reason": one sentence explaining the rating
- "requires_human_review": true if confidence < 0.70, false otherwise"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a precise auditor. Output only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=200
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "confidence": 0.5,
            "confidence_reason": "Could not parse confidence response.",
            "requires_human_review": True
        }

def run_extraction(pdf_path, taxonomy):
    doc_text  = extract_text_from_pdf(pdf_path)
    collection = get_chroma_collection()
    findings  = []

    for control in taxonomy["risk_categories"]:
        print(f"    Retrieving legal context for {control['id']}...")
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
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            finding = json.loads(raw)

            # get confidence score
            confidence = get_confidence_score(finding, doc_text)
            finding["confidence"]           = confidence["confidence"]
            finding["confidence_reason"]    = confidence["confidence_reason"]
            finding["requires_human_review"] = confidence["requires_human_review"]

            findings.append(finding)
            review_flag = "REVIEW" if finding["requires_human_review"] else "NO REVIEW"
            print(f"    {control['id']} — {finding['status']} / {finding['severity']} "
                  f"| confidence: {finding['confidence']:.2f} {review_flag}")

        except json.JSONDecodeError:
            print(f"    {control['id']} — JSON parse failed")

    return findings if findings else None