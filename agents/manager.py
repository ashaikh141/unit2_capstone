import string
from agents import qualitative, quantitative
from validation.validator import validate_qualitative, validate_quantitative
from tokenomics.logger import log
from llm import generate

ROUTES = {"qualitative", "quantitative", "both"}


def classify(query: str) -> str:
    prompt = f"""Classify this query as exactly one of: qualitative, quantitative, both.

qualitative = questions about policies, processes, procedures, explanations, documentation
quantitative = questions about numbers, metrics, trends, comparisons, SQL-queryable data
both = questions that need both document search and data analysis

Query: {query}

Reply with one word only: qualitative, quantitative, or both."""
    result = generate(prompt, max_tokens=256)
    log(query, "manager-classifier", result["input_tokens"], result["output_tokens"])
    words = result["text"].lower().split()
    route = words[0].strip(string.punctuation) if words else ""
    return route if route in ROUTES else "qualitative"


def synthesise(query: str, qual: dict, quant: dict) -> dict:
    prompt = f"""You are combining two analyst reports into one answer.

QUESTION: {query}

DOCUMENT ANALYSIS (cites documents as [Source N]):
{qual['answer']}

DATA ANALYSIS (from the SQL database):
{quant['answer']}

Write one concise answer that combines both. Use ONLY facts stated above, keep the
[Source N] citations, and say clearly if either part could not be answered."""
    return generate(prompt, max_tokens=2048)


def run(query: str) -> dict:
    print(f"\nQuery: {query}")
    route = classify(query)
    print(f"Route: {route}")

    qual_result = quant_result = None

    if route in ("qualitative", "both"):
        qual_result = qualitative.run(query)
        validation = validate_qualitative(qual_result["answer"], qual_result["chunks"])
        log(query, "qualitative", qual_result["input_tokens"], qual_result["output_tokens"])
        if validation["flag"]:
            print(f"\n⚠️  VALIDATION WARNING: {validation['warning']}")
        print(f"\n[Qualitative]\n{qual_result['answer']}")
        print(f"Sources cited: {validation['sources_cited']}")

    if route in ("quantitative", "both"):
        quant_result = quantitative.run(query)
        validation = validate_quantitative(
            quant_result["answer"], quant_result["sql"], quant_result["validation"]
        )
        log(query, "quantitative", quant_result["input_tokens"], quant_result["output_tokens"])
        if validation["flag"]:
            print(f"\n⚠️  VALIDATION WARNING: {validation['warning']}")
        print(f"\n[Quantitative]\n{quant_result['answer']}")
        print(f"SQL used: {quant_result['sql']}")

    if route == "both":
        final = synthesise(query, qual_result, quant_result)
        log(query, "manager-synthesis", final["input_tokens"], final["output_tokens"])
        check = validate_qualitative(final["text"], qual_result["chunks"])
        if check["flag"]:
            print(f"\n⚠️  VALIDATION WARNING (synthesis): {check['warning']}")
        print(f"\n[Combined answer]\n{final['text']}")

    return {"route": route, "qualitative": qual_result, "quantitative": quant_result}