# pipeline.py
import json
import os
import pandas as pd
from extract import load_taxonomy, run_extraction

DOCS_DIR = "../docs"
OUTPUT_DIR = "../outputs"

def run_pipeline():
    taxonomy = load_taxonomy()
    
    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith("card.pdf")]
    print(f"Found {len(pdf_files)} documents\n")
    
    all_findings = []

    for pdf_file in pdf_files:
        doc_name = pdf_file.replace(".pdf", "")
        pdf_path = os.path.join(DOCS_DIR, pdf_file)
        print(f"Processing: {pdf_file}...")

        findings = run_extraction(pdf_path, taxonomy)

        if findings:
            for f in findings:
                f["document"] = doc_name
            all_findings.extend(findings)
            print(f"  {len(findings)} findings extracted")

            doc_output = os.path.join(OUTPUT_DIR, f"{doc_name}_findings.json")
            with open(doc_output, "w") as out:
                json.dump(findings, out, indent=2)
        else:
            print(f"  FAILED — skipping")

    # save master JSON
    master_path = os.path.join(OUTPUT_DIR, "all_findings.json")
    with open(master_path, "w") as out:
        json.dump(all_findings, out, indent=2)
    print(f"\nMaster findings saved: {master_path}")

    # save flat CSV for easy review
    df = pd.DataFrame(all_findings)
    cols = ["document", "control_id", "control_name", "status",
            "severity", "finding", "evidence",
            "llm_recommendation", "auditor_recommendation", "auditor_reviewed"]
    df = df[cols]
    csv_path = os.path.join(OUTPUT_DIR, "all_findings.csv")
    df.to_csv(csv_path, index=False)
    print(f"CSV saved: {csv_path}")

    return df

if __name__ == "__main__":
    df = run_pipeline()
    print("\n--- Summary ---")
    print(df.groupby(["document", "status"]).size().unstack(fill_value=0))
    print("\nSeverity breakdown:")
    print(df.groupby(["document", "severity"]).size().unstack(fill_value=0))


# import subprocess
# subprocess.run(["python", "scoring.py"])