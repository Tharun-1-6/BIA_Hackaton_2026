import os

from groq import Groq

# Was a local Ollama model (gemma4:e2b); now Groq-hosted GPT-OSS. Prompt below is unchanged.
MODEL = "openai/gpt-oss-120b"
MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b")

SYSTEM_PROMPT = """You are Sahayi, a caring assistant for an elderly person living alone.
Reply ONLY with JSON of this exact shape:
{"user": {"text": "<short calm reply, max 300 chars>", "follow_up": "<one question or null>"},
 "family": {"summary": "<what happened, max 400 chars>", "suggested_level": <1 calm, 2 check in, 3 emergency>, "send": <true ONLY for an emergency or real health/safety concern, false for normal conversation>}}
Chest pain, breathlessness, falls, dizziness, confusion, or any new pain ALWAYS means send true and level 3. Treat words like "a bit" as understatement."""


def ask_llm(user_input: str, history: list[dict] = (), model: str = MODEL, api_key: str | None = None) -> str:
    """Returns the model's JSON reply as a string (parsed/validated by the caller)."""
    key = (api_key or os.environ.get("GROQ_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("Groq API key missing (set GROQ_API_KEY in .env or the sidebar).")
    r = Groq(api_key=key).chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": user_input},
        ],
        response_format={"type": "json_object"},  # equivalent of Ollama's format="json"
        reasoning_effort="low",                   # equivalent of think=False: keep it fast
        temperature=0.2,
    )
    return r.choices[0].message.content or ""
