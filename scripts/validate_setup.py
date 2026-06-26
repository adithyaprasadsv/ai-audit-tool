# pip install openai pandas requests PyPDF2 python-dotenv# validate_setup.py
import json
import os
from PyPDF2 import PdfReader

with open("../config/risk_taxonomy.json") as f:
    taxonomy = json.load(f)

print(f"Taxonomy loaded: {len(taxonomy['risk_categories'])} risk categories")
for cat in taxonomy['risk_categories']:
    print(f"  {cat['id']} — {cat['name']} ({cat['article']})")

print("\nDocuments found:")
for fname in os.listdir("../docs"):
    if fname.endswith(".pdf"):
        path = f"docs/{fname}"
        reader = PdfReader(path)
        print(f"  {fname} — {len(reader.pages)} pages")