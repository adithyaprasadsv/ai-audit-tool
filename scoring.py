# scoring.py
import json
import pandas as pd
from datetime import date

FINDINGS_PATH = "outputs/all_findings_reviewed.json"
MODEL_PATH    = "scoring_model.json"
OUTPUT_JSON   = "outputs/compliance_scores.json"
OUTPUT_CSV    = "outputs/compliance_scores.csv"

def load_inputs():
    with open(FINDINGS_PATH) as f:
        findings = json.load(f)
    with open(MODEL_PATH) as f:
        model = json.load(f)
    return findings, model

def get_band(score, bands):
    for band in bands:
        if band["min"] <= score <= band["max"]:
            return band["label"]
    return "Unknown"

def score_document(doc_findings, model):
    weights        = model["weights"]
    status_scores  = model["status_scores"]
    sev_penalties  = model["severity_penalty"]
    bands          = model["bands"]

    control_scores = {}
    for f in doc_findings:
        cid          = f["control_id"]
        base         = status_scores.get(f["status"], 0)
        penalty      = sev_penalties.get(f["severity"], 0)
        raw          = max(0, base + penalty)
        weight       = weights.get(cid, 0)
        weighted     = raw * weight * 100

        control_scores[cid] = {
            "control_name":   f["control_name"],
            "status":         f["status"],
            "severity":       f["severity"],
            "base_score":     round(base * 100, 1),
            "penalty":        round(penalty * 100, 1),
            "raw_score":      round(raw * 100, 1),
            "weight":         weight,
            "weighted_score": round(weighted, 2)
        }

    total = sum(c["weighted_score"] for c in control_scores.values())
    total = round(total, 1)

    compliant_count = sum(
    1 for c in control_scores.values()
    if c["status"] == "compliant"
    )
    bonus = compliant_count * 2.5
    total = round(min(100, total + bonus), 1)

    return {
        "total_score": total,
        "band":        get_band(total, bands),
        "controls":    control_scores
    }

def run_scoring():
    findings, model = load_inputs()
    df = pd.DataFrame(findings)

    results    = {}
    csv_rows   = []

    for doc in df["document"].unique():
        doc_findings = [f for f in findings if f["document"] == doc]
        scored       = score_document(doc_findings, model)
        results[doc] = scored

        label = doc.replace("_system_card","").replace("_card","").replace("_"," ").title()
        for cid, ctrl in scored["controls"].items():
            csv_rows.append({
                "document":      label,
                "control_id":    cid,
                "control_name":  ctrl["control_name"],
                "status":        ctrl["status"],
                "severity":      ctrl["severity"],
                "base_score":    ctrl["base_score"],
                "penalty":       ctrl["penalty"],
                "raw_score":     ctrl["raw_score"],
                "weight":        ctrl["weight"],
                "weighted_score":ctrl["weighted_score"],
                "total_score":   scored["total_score"],
                "band":          scored["band"]
            })

    output = {
        "generated":      date.today().isoformat(),
        "model_version":  model["model_version"],
        "author":         model["author"],
        "scores":         results
    }

    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)

    pd.DataFrame(csv_rows).to_csv(OUTPUT_CSV, index=False)

    return results, model

def confidence_summary(findings):
    print("\nConfidence summary:")
    print(f"{'Document':<28} {'Avg confidence':>16} {'Flagged for review':>20}")
    print("-" * 68)

    df = pd.DataFrame(findings)
    for doc in df["document"].unique():
        doc_df   = df[df["document"] == doc]
        avg_conf = doc_df["confidence"].mean()
        flagged  = doc_df["requires_human_review"].sum()
        label    = doc.replace("_system_card","").replace("_card","") \
                      .replace("_"," ").title()
        print(f"{label:<28} {avg_conf:>15.2f}  {flagged:>18}/6")

def print_summary(results, model):
    print("\n--- Compliance score summary ---\n")
    print(f"{'Document':<28} {'Score':>7} {'Band':<12} {'Weakest control'}")
    print("-" * 70)

    for doc, data in sorted(results.items(),
                             key=lambda x: x[1]["total_score"],
                             reverse=True):
        label   = doc.replace("_system_card","").replace("_card","") \
                     .replace("_"," ").title()
        weakest   = max(data["controls"].items(), key=lambda x: x[1]["raw_score"])
        impactful = max(data["controls"].items(), key=lambda x: x[1]["weighted_score"])

        print(f"{label:<28} {data['total_score']:>6.1f}%  "
            f"{data['band']:<12} "
            f"weakest: {weakest[0]} ({weakest[1]['raw_score']}%)  "
            f"costliest: {impactful[0]} ({impactful[1]['weighted_score']}pt)")

    print()
    print("Control weight breakdown:")
    for cid, w in model["weights"].items():
        print(f"  {cid}  {w*100:.0f}%  {model['rationale'][cid][:60]}...")

    with open(FINDINGS_PATH) as f:
        all_findings = json.load(f)
    confidence_summary(all_findings)

if __name__ == "__main__":
    results, model = run_scoring()
    print_summary(results, model)
    print(f"\nSaved: {OUTPUT_JSON}")
    print(f"Saved: {OUTPUT_CSV}")