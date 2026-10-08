from agents.manager import run


def main():
    print("Enterprise RAG System")
    print("Type 'exit' to quit.\n")
    while True:
        try:
            query = input("Ask a question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if query.lower() in ["exit", "quit"]:
            break
        if not query:
            continue

        try:
            run(query)
        except Exception as e:
            print(f"\n⚠️  Request failed: {e}\nPlease try again.\n")


if __name__ == "__main__":
    main()