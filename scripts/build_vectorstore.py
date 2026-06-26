# build_vectorstore.py
import os
import json
import PyPDF2
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

CHROMA_PATH = "vectorstore"
EU_AI_ACT_PDF = "../docs/eu_ai_act.pdf"

ARTICLES_OF_INTEREST = [
    "Article 9",  "Article 10", "Article 11",
    "Article 13", "Article 14", "Article 15"
]

def extract_pdf_text(path):
    reader = PyPDF2.PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def chunk_text(text, chunk_size=800, overlap=100):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

def filter_relevant_chunks(chunks):
    relevant = []
    for chunk in chunks:
        for article in ARTICLES_OF_INTEREST:
            if article.lower() in chunk.lower():
                relevant.append(chunk)
                break
    return relevant

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def build_vectorstore():
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        chroma_client.delete_collection("eu_ai_act")
        print("Cleared existing collection")
    except:
        pass

    collection = chroma_client.create_collection(
        name="eu_ai_act",
        metadata={"hnsw:space": "cosine"}
    )

    print("Extracting text from EU AI Act PDF...")
    text = extract_pdf_text(EU_AI_ACT_PDF)
    print(f"  Extracted {len(text.split())} words")

    print("Chunking text...")
    all_chunks = chunk_text(text)
    relevant_chunks = filter_relevant_chunks(all_chunks)
    print(f"  Total chunks: {len(all_chunks)}")
    print(f"  Relevant chunks (Articles 9-15): {len(relevant_chunks)}")

    print("Embedding and storing chunks...")
    for i, chunk in enumerate(relevant_chunks):
        embedding = get_embedding(chunk)
        collection.add(
            ids=[f"chunk_{i}"],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[{"source": "eu_ai_act", "chunk_index": i}]
        )
        if (i+1) % 10 == 0:
            print(f"  Stored {i+1}/{len(relevant_chunks)} chunks")

    print(f"\nVector store built: {len(relevant_chunks)} chunks stored")
    return collection

def test_retrieval(collection):
    print("\n--- Test retrieval ---")
    test_queries = [
        "risk management system lifecycle",
        "human oversight intervention override",
        "technical documentation regulatory assessment"
    ]
    for query in test_queries:
        embedding = get_embedding(query)
        results = collection.query(
            query_embeddings=[embedding],
            n_results=2
        )
        print(f"\nQuery: '{query}'")
        for doc in results["documents"][0]:
            print(f"  Match: {doc[:120]}...")

if __name__ == "__main__":
    collection = build_vectorstore()
    test_retrieval(collection)
    print("\nSprint S1 complete. Vector store ready at ./vectorstore")
    client = chromadb.PersistentClient(path="../vectorstore")
    collection = client.get_collection("eu_ai_act")
    print(f"Collection count: {collection.count()} chunks")