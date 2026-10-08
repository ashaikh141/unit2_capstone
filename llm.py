import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

MODEL = "gemini-3.5-flash"
_client = genai.Client()  # reads GEMINI_API_KEY from .env
MAX_ATTEMPTS = 6
RETRY_CODES = {429, 500, 503, 504}


def generate(prompt: str, max_tokens: int = 1024) -> dict:
    # Gemini "thinking" tokens count against the output limit, so keep it generous.
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = _client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(max_output_tokens=max(max_tokens, 4096)),
            )
            break
        except errors.APIError as e:
            code = getattr(e, "code", None)
            if code not in RETRY_CODES or attempt == MAX_ATTEMPTS:
                raise
            match = re.search(r"retry in ([\d.]+)s", str(e))
            if match:
                wait = float(match.group(1)) + 1
            else:
                wait = min(60, 5 * 2 ** (attempt - 1))  # 5s, 10s, 20s, 40s, 60s
            print(f"[retry {attempt}/{MAX_ATTEMPTS - 1}] Gemini error {code}, waiting {wait:.0f}s...", flush=True)
            time.sleep(wait)

    usage = response.usage_metadata
    return {
        "text": (response.text or "").strip(),
        "input_tokens": usage.prompt_token_count or 0,
        # thinking tokens are billed as output but reported separately
        "output_tokens": (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0),
    }