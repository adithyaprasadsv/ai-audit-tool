
# test_single.py
from extract import load_taxonomy, run_extraction
import json

taxonomy = load_taxonomy()

print("Running extraction on: meta_llama_card.pdf\n")
findings = run_extraction("docs/claude_system_card.pdf", taxonomy)

if findings:
    print(f"Extracted {len(findings)} findings:\n")
    for f in findings:
        severity_label = f["severity"].upper() if f["severity"] != "none" else "—"
        print(f"  [{f['control_id']}] {f['control_name']}")
        print(f"  Status  : {f['status']}")
        print(f"  Severity: {severity_label}")
        print(f"  Finding : {f['finding']}")
        print(f"  Evidence: {f['evidence'][:120]}...")
        print()

    with open("outputs/test_claude_system_card.json", "w") as out:
        json.dump(findings, out, indent=2)
    print("Saved to outputs/claude_system_card.json")