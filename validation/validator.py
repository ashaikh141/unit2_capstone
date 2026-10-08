import re


def validate_qualitative(answer: str, chunks: list[dict]) -> dict:
    cited = sorted({int(n) for n in re.findall(r"Source\s+(\d+)", answer)})
    valid = [n for n in cited if 1 <= n <= len(chunks)]
    invalid = [n for n in cited if n not in valid]
    sources_cited = sorted({chunks[n - 1]["source"] for n in valid})

    grounded = len(valid) > 0 and not invalid
    refused = "cannot find" in answer.lower()
    flag = (not grounded) and (not refused)

    warning = None
    if invalid:
        warning = f"Answer cites sources that were not retrieved: {invalid}"
    elif flag:
        warning = "Response may not be grounded in source documents"

    return {
        "is_grounded": grounded,
        "refused_to_answer": refused,
        "sources_cited": sources_cited,
        "invalid_citations": invalid,
        "flag": flag or bool(invalid),
        "warning": warning,
    }


def validate_quantitative(answer: str, sql: str, validation_status: str) -> dict:
    ok = validation_status == "PASSED"
    return {
        "sql_validated": ok,
        "sql_blocked": validation_status == "FAILED",
        "execution_error": validation_status == "ERROR",
        "flag": not ok,
        "warning": None if ok else f"SQL validation status: {validation_status}",
    }