import json
from datetime import datetime

# Gemini 3.5 Flash list price (per 1M tokens: $1.50 in, $9.00 out). Re-check before submitting:
# https://ai.google.dev/gemini-api/docs/pricing
COST_PER_1K_INPUT = 0.0015
COST_PER_1K_OUTPUT = 0.009
LOG_FILE = "tokenomics_log.jsonl"


def log(query: str, agent: str, input_tokens: int, output_tokens: int) -> dict:
    input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT
    output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT
    total_cost = input_cost + output_cost

    entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "agent": agent,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(total_cost, 6),
        "cost_per_1000_queries": round(total_cost * 1000, 2),
    }
    print(f"[TOKENOMICS] Agent: {agent} | Input: {input_tokens} | Output: {output_tokens} | Cost: ${total_cost:.6f}")

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry