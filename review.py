# review.py
import json

INPUT = "outputs/all_findings.json"
OUTPUT = "outputs/all_findings_reviewed.json"

OVERRIDES = {
    ("claude_system_card", "RC-05"): {
        "status": "gap",
        "severity": "high",
        "finding": "Human review is described as an internal QA mechanism for classifier accuracy, not an operator-level override capability as required by Article 14.",
        "evidence": "We use a combination of automated monitoring for potential harms and violations of our AUP, as well as human review to audit the accuracy of our classifiers."
    },
    ("claude_system_card", "RC-01"): {
        "status": "gap",
        "severity": "high",
        "finding": "The Responsible Scaling Policy is a policy commitment document, not a documented lifecycle risk management process as required by Article 9.",
        "evidence": "focusing on core capabilities, safety, societal impacts, and the catastrophic risk assessments we committed to in our Responsible Scaling Policy"
    },
    ("meta_llama_card", "RC-05"): {
        "evidence": "Developers are expected to deploy system safeguards when building agentic systems."
    }
}

AUDITOR_RECOMMENDATIONS = {
    ("claude_system_card",  "RC-01"): "Anthropic should produce a standalone lifecycle risk management document mapping risks at each stage: development, deployment, and post-deployment monitoring. The Responsible Scaling Policy alone is insufficient for Article 9 compliance.",
    ("claude_system_card",  "RC-03"): "Model card must be self-contained for regulatory purposes. Anthropic should either consolidate key technical details inline or formally reference a publicly accessible annex that satisfies Article 11 requirements.",
    ("claude_system_card",  "RC-05"): "Anthropic must document explicit operator-level override mechanisms separate from internal classifier review. This should include who can pause the system, under what conditions, and how.",
    ("google_gemini_card",  "RC-01"): "Google DeepMind should publish a lifecycle risk management process covering pre-training, fine-tuning, deployment, and post-deployment monitoring phases.",
    ("google_gemini_card",  "RC-03"): "Redirecting to an external model card list is insufficient under Article 11. Each model card must be self-contained or accompanied by a linked compliance annex.",
    ("google_gemini_card",  "RC-05"): "No override or intervention mechanism documented anywhere in the card. Google DeepMind must document how operators can halt, pause, or override the system in deployment.",
    ("gpt5_system_card",    "RC-01"): "Preparedness Framework references are promising but insufficient. OpenAI should produce a full Article 9-compliant risk register with lifecycle coverage and residual risk disclosures.",
    ("gpt5_system_card",    "RC-03"): "Technical documentation gap is the most severe finding in this document. OpenAI must provide self-contained technical specs — architecture, training methodology, evaluation results — within the system card itself.",
    ("gpt5_system_card",    "RC-04"): "Usage policy URL reference does not satisfy Article 13. Inline instructions for interpreting model outputs and known failure modes must be present in the system card.",
    ("gpt5_system_card",    "RC-05"): "No human oversight mechanism documented. OpenAI must specify operator controls, escalation paths, and override procedures as required by Article 14.",
    ("meta_llama_card",     "RC-01"): "Meta provides no lifecycle risk management documentation. Given Llama's open-source distribution model, this is especially critical — downstream deployers have no risk baseline to build from.",
    ("meta_llama_card",     "RC-03"): "Redirecting to GitHub for technical details does not satisfy Article 11. Meta must publish a self-contained compliance document, particularly given the open-source deployment context.",
    ("meta_llama_card",     "RC-05"): "Delegating oversight entirely to downstream developers without baseline requirements creates an accountability gap. Meta should define minimum human oversight requirements for all Llama deployments."
}

def apply_review(findings):
    for f in findings:
        key = (f["document"], f["control_id"])

        if key in OVERRIDES:
            for field, value in OVERRIDES[key].items():
                f[field] = value
            print(f"  Override applied: {f['document']} {f['control_id']}")

        if key in AUDITOR_RECOMMENDATIONS:
            f["auditor_recommendation"] = AUDITOR_RECOMMENDATIONS[key]
            f["auditor_reviewed"] = True
        else:
            f["auditor_reviewed"] = False

    return findings

def summarise(findings):
    reviewed = sum(1 for f in findings if f["auditor_reviewed"])
    gaps = sum(1 for f in findings if f["status"] == "gap")
    high = sum(1 for f in findings if f["severity"] == "high")
    print(f"\n--- Review summary ---")
    print(f"Total findings     : {len(findings)}")
    print(f"Auditor reviewed   : {reviewed}")
    print(f"Gaps               : {gaps}")
    print(f"High severity      : {high}")
    print(f"Pending review     : {len(findings) - reviewed}")

with open(INPUT) as f:
    findings = json.load(f)

print("Applying overrides and auditor recommendations...\n")
findings = apply_review(findings)
for f in findings:
    if not f["auditor_reviewed"] and f["status"] == "partial":
        f["auditor_recommendation"] = (
            "Partial compliance noted. Provider should expand documentation "
            "to fully satisfy the relevant EU AI Act article. "
            "Re-assess at next audit cycle."
        )
        f["auditor_reviewed"] = True
summarise(findings)

for f in findings:
    if f.get("requires_human_review") and not f["auditor_reviewed"]:
        f["auditor_recommendation"] = (
            f"LOW CONFIDENCE FLAG — {f.get('confidence_reason', '')} "
            f"Human auditor must verify before this finding is reported."
        )

with open(OUTPUT, "w") as f:
    json.dump(findings, f, indent=2)

print(f"\nSaved: {OUTPUT}")