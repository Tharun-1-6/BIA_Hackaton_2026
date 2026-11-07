"""LLM call for the Sahayi agent (Groq-hosted with multi-model fallback). The prompt lives in prompt.py."""
import json
import os
from dotenv import load_dotenv

from groq import Groq

from bia_hackaton_2026.llm.prompt import SYSTEM_PROMPT

# Preferred Groq models (verified accessible and active)
MODEL = "openai/gpt-oss-120b"
MODELS = ("openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b")


def ask_llm(
    user_input: str,
    history: list[dict] = (),
    model: str = MODEL,
    api_key: str | None = None,
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    """Returns the model's JSON reply as a string (parsed/validated by the caller)."""
    load_dotenv(override=True)
    key = (api_key or os.environ.get("GROQ_API_KEY") or "").strip()

    # 1. Groq Provider (Ultra-fast intelligence)
    if key:
        client = Groq(api_key=key)
        for candidate_model in (model, "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"):
            try:
                r = client.chat.completions.create(
                    model=candidate_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *history,
                        {"role": "user", "content": user_input},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                if r.choices and r.choices[0].message.content:
                    return r.choices[0].message.content
            except Exception as e:
                print(f"[LLM GROQ WARNING] Model {candidate_model} failed: {e}")
                continue

    # 2. Google Gemini Fallback
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from google import genai
            g_client = genai.Client(api_key=gemini_key)
            resp = g_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=user_input,
                config={"system_instruction": system_prompt, "response_mime_type": "application/json"},
            )
            if resp.text:
                return resp.text
        except Exception as ge:
            print(f"[LLM GEMINI WARNING] {ge}")

    # 3. Rule-based graceful fallback (offline or keys missing)
    lower = user_input.lower()
    emergency_words = ["sos", "help", "pain", "fell", "തലകറക്കം", "നെഞ്ചുവേദന", "ശ്വാസം", "വീണു", "വേദന"]
    is_emergency = any(w in lower for w in emergency_words)
    level = 3 if is_emergency else 1

    return json.dumps({
        "user": {
            "text": (
                "Sahayi: അടിയന്തര സാഹായ അഭ്യർത്ഥന രേഖപ്പെടുത്തി. ശാന്തരായിരിക്കുക, കെയർഗിവർക്ക് വിവരമറിയിച്ചു. "
                "(Emergency alert received. Your caregiver has been notified. Please stay calm.)"
                if is_emergency
                else f"Sahayi: നമസ്കാരം! സന്ദേശം ലഭിച്ചു. സുഖമാണോ? (Hello! Message received. How are you feeling today?)"
            ),
            "follow_up": None,
        },
        "family": {
            "summary": f"Senior member sent: '{user_input}'. Emergency detected." if is_emergency else f"Senior message: '{user_input}'",
            "suggested_level": level,
            "send": is_emergency,
        },
    })
