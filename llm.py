from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemini-3.5-flash"
_client = genai.Client()  # reads GEMINI_API_KEY from .env


def generate(prompt: str, max_tokens: int = 1024) -> dict:
    # Keep max_tokens generous: Gemini "thinking" tokens can count against the
    # limit, and a tiny limit can return an empty answer.
    response = _client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=max_tokens),
    )
    usage = response.usage_metadata
    return {
        "text": (response.text or "").strip(),
        "input_tokens": usage.prompt_token_count or 0,
        # thinking tokens are billed as output but reported separately
        "output_tokens": (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0),
    }