"""LLM call for the Sahayi agent (Groq-hosted GPT-OSS). The prompt lives in prompt.py."""
import os

from groq import Groq

from bia_hackaton_2026.llm.prompt import SYSTEM_PROMPT

# Was a local Ollama model (gemma4:e2b); now Groq-hosted GPT-OSS.
MODEL = "openai/gpt-oss-120b"
MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b")


def ask_llm(
    user_input: str,
    history: list[dict] = (),
    model: str = MODEL,
    api_key: str | None = None,
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    """Returns the model's JSON reply as a string (parsed/validated by the caller)."""
    key = (api_key or os.environ.get("GROQ_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("Groq API key missing (set GROQ_API_KEY in .env or the sidebar).")
    r = Groq(api_key=key).chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_input},
        ],
        response_format={"type": "json_object"},  # equivalent of Ollama's format="json"
        reasoning_effort="low",                   # equivalent of think=False: keep it fast
        temperature=0.2,
    )
    return r.choices[0].message.content or ""
