print("starting...", flush=True)

from agents.manager import run

print("imports done", flush=True)


def main():
    print("Enterprise RAG System")
    print("Type 'exit' to quit.\n")
    while True:
        query = input("Ask a question: ").strip()
        if query.lower() in ["exit", "quit"]:
            break
        if not query:
            continue
        run(query)


if __name__ == "__main__":
    main()