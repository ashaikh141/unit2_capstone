import chromadb
from sentence_transformers import SentenceTransformer
from llm import generate

model = SentenceTransformer("all-MiniLM-L6-v2")


def retrieve(query: str, top_k: int = 6) -> list[dict]:
    chroma = chromadb.PersistentClient(path="./data/chroma")
    collection = chroma.get_collection("enterprise-docs")
    embedding = model.encode([query]).tolist()
    results = collection.query(query_embeddings=embedding, n_results=top_k)
    return [
        {"content": doc, "source": meta["source"], "chunk": meta["chunk"]}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


def build_prompt(query: str, chunks: list[dict]) -> str:
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"[Source {i+1}: {chunk['source']}]\n{chunk['content']}\n\n"

    return f"""You are a helpful enterprise documentation assistant.
Answer the question using ONLY the context provided below. Do not use outside knowledge.
If the answer is not in the context, say "I cannot find this information in the provided documents."
Always cite the source number(s) you used, in the form [Source 1].

CONTEXT:
{context}
QUESTION: {query}

ANSWER:"""


def run(query: str) -> dict:
    chunks = retrieve(query)
    result = generate(build_prompt(query, chunks), max_tokens=2048)
    return {
        "answer": result["text"],
        "chunks": chunks,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
    }