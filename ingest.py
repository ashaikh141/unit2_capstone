import os
import chromadb
from sentence_transformers import SentenceTransformer


def chunk_document(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunks.append(" ".join(words[i:i + chunk_size]))
        if i + chunk_size >= len(words):
            break  # avoid a trailing chunk that is only overlap
    return chunks


def ingest(docs_path: str):
    client = chromadb.PersistentClient(path="./data/chroma")
    collection = client.get_or_create_collection("enterprise-docs")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    for filename in sorted(os.listdir(docs_path)):
        if not filename.endswith(".txt"):
            continue
        with open(os.path.join(docs_path, filename), encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_document(text)
        if not chunks:
            continue
        embeddings = model.encode(chunks).tolist()
        ids = [f"{filename}-{i}" for i in range(len(chunks))]
        metadatas = [{"source": filename, "chunk": i} for i in range(len(chunks))]
        collection.upsert(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
        print(f"Ingested {len(chunks)} chunks from {filename}")


if __name__ == "__main__":
    ingest("./data/documents")