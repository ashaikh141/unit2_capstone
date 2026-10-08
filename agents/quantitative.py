import re
import sqlite3
from llm import generate

SCHEMA_CONTEXT = """You write SQLite queries for this database.

Tables:
- sales(id, region, product, revenue, date, units_sold)
- customers(id, name, industry, churn_date, satisfaction_score)
- employees(id, department, satisfaction_score, tenure_years)

Notes:
- sales.date and customers.churn_date are TEXT in ISO format (YYYY-MM-DD). All sales are in calendar year 2025.
- Use strftime('%Y-%m', date) for months. Q4 means months 10, 11 and 12.
- sales.region is one of: 'North America', 'EMEA', 'APAC', 'LATAM'.
- sales.product is one of: 'Platform', 'Analytics Suite', 'Support Services'.
- sales.revenue is in US dollars.
- customers.churn_date IS NULL means the customer is still active. Churn rate = churned customers / total customers.
- satisfaction_score is on a 1-5 scale for both customers and employees.
- employees.department is one of: 'Engineering', 'Customer Support', 'Sales', 'Customer Success', 'G&A'.
"""

BLOCKED = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
           "CREATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA"]


def validate_sql(query: str) -> dict:
    q = query.strip().rstrip(";").strip()
    upper = q.upper()
    for word in BLOCKED:
        if re.search(rf"\b{word}\b", upper):
            return {"valid": False, "reason": f"Blocked keyword: {word}"}
    if ";" in q:
        return {"valid": False, "reason": "Multiple statements are not permitted"}
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return {"valid": False, "reason": "Only SELECT queries are permitted"}
    return {"valid": True, "reason": "OK"}


def generate_sql(query: str) -> dict:
    prompt = f"""{SCHEMA_CONTEXT}
Write ONE SQLite SELECT query that answers this question: {query}
Return ONLY the SQL. No explanation and no markdown."""
    result = generate(prompt, max_tokens=1024)
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", result["text"].strip(), flags=re.IGNORECASE).strip()
    return {"sql": sql, "input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"]}


def run(query: str) -> dict:
    sql_result = generate_sql(query)
    sql = sql_result["sql"]
    validation = validate_sql(sql)

    if not validation["valid"]:
        return {
            "answer": f"Query blocked: {validation['reason']}",
            "sql": sql, "columns": [], "rows": [], "validation": "FAILED",
            "input_tokens": sql_result["input_tokens"],
            "output_tokens": sql_result["output_tokens"],
        }

    try:
        # read-only connection as a second layer of defence
        conn = sqlite3.connect("file:./data/database.sqlite?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        conn.close()

        prompt = f"""The user asked: {query}

SQL query used: {sql}

Columns: {cols}
Results (up to 50 rows): {rows[:50]}

Explain the results clearly and concisely. Use ONLY the numbers in the results above.
Format currency with $ and thousands separators. Do not invent figures."""
        interpretation = generate(prompt, max_tokens=1024)

        return {
            "answer": interpretation["text"],
            "sql": sql, "columns": cols, "rows": rows, "validation": "PASSED",
            "input_tokens": sql_result["input_tokens"] + interpretation["input_tokens"],
            "output_tokens": sql_result["output_tokens"] + interpretation["output_tokens"],
        }
    except Exception as e:
        return {
            "answer": f"Query execution failed: {e}",
            "sql": sql, "columns": [], "rows": [], "validation": "ERROR",
            "input_tokens": sql_result["input_tokens"],
            "output_tokens": sql_result["output_tokens"],
        }