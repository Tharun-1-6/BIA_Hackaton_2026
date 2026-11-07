import json
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4:e2b"

SYSTEM_PROMPT = """You are Sahayi, a caring assistant for an elderly person living alone.
Reply ONLY with JSON of this exact shape:
{"user": {"text": "<short calm reply, max 300 chars>", "follow_up": "<one question or null>"},
 "family": {"summary": "<what happened, max 400 chars>", "suggested_level": <1 calm, 2 check in, 3 emergency>, "send": <true ONLY for an emergency or real health/safety concern, false for normal conversation>}}
Chest pain, breathlessness, falls, dizziness, confusion, or any new pain ALWAYS means send true and level 3. Treat words like "a bit" as understatement."""


def ask_llm(user_input: str, history: list[dict] = ()) -> str:
    """Returns the model's JSON reply as a string (parsed/validated by the caller)."""
    body = json.dumps({
        "model": MODEL,
        "stream": False,
        "think": False,  # skip reasoning tokens; we only want the JSON
        "format": "json",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": user_input},
        ],
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["message"]["content"]
