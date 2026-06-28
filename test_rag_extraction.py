# test_rag_extraction.py
import json
from extract import load_taxonomy, run_extraction

taxonomy = load_taxonomy()

print("Testing RAG extraction on: claude_system_card.pdf\n")
findings = run_extraction("docs/claude_system_card.pdf", taxonomy)

if findings:
    print(f"\nExtracted {len(findings)} findings\n")
    for f in findings:
        print(f"[{f['control_id']}] {f['status']} / {f['severity']}")
        print(f"  Finding    : {f['finding']}")
        print(f"  Legal basis: {f['legal_basis'][:120]}...")
        print()

    with open("outputs/test_rag_claude.json", "w") as out:
        json.dump(findings, out, indent=2)
    print("Saved to outputs/test_rag_claude.json")