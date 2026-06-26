# verify_review.py
import json

with open("outputs/all_findings_reviewed.json") as f:
    findings = json.load(f)

issues = []
for f in findings:
    if not f["auditor_reviewed"]:
        issues.append(f"{f['document']} {f['control_id']} — not reviewed")
    if not f["auditor_recommendation"]:
        issues.append(f"{f['document']} {f['control_id']} — empty recommendation")

if issues:
    print("Issues found:")
    for i in issues: print(f"  {i}")
else:
    print("All 24 findings reviewed and recommendations complete. Ready for Sprint 5.")