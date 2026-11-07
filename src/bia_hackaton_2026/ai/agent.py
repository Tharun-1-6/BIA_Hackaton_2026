"""AI Care Agent & Intent Detection for Sahayi.

Provides:
1. Semantic Emergency Intent Detection (identifies medical emergencies even without explicit 'SOS' keyword).
2. Bilingual conversational responses (Malayalam + English) tailored for seniors.
3. Pluggable backend: Google Gemini, Groq (Llama-3), OpenAI, or rule-based fallback.
"""

import json
import os
from typing import Any, Dict, Optional

SYSTEM_PROMPT = """You are Sahayi, an empathetic, caring, and bilingual AI companion for elderly members in Kerala, India.
Primary language: Malayalam (മലയാളം), accompanied by clear English.

CRITICAL INSTRUCTIONS:
1. You must assess if the user's message indicates an EMERGENCY (e.g. fall, severe chest pain, shortness of breath, loss of consciousness, dizziness, bleeding, calling for help).
2. If it is an EMERGENCY:
   - set "is_emergency": true
   - "urgency": "CRITICAL"
   - provide a short, calm, reassuring response in Malayalam and English telling the senior to stay calm and that their family/caregiver is being alerted immediately.
   - provide a "caregiver_summary" explaining the emergency.
3. If it is NOT an emergency (e.g. general conversation, asking for medicine time, greeting):
   - set "is_emergency": false
   - "urgency": "NORMAL"
   - provide a warm, respectful, concise response in Malayalam with English translation.
4. Output MUST be valid JSON with keys:
   {
     "is_emergency": bool,
     "urgency": "NORMAL" | "CRITICAL",
     "response_text": str,
     "caregiver_summary": str
   }
"""


def detect_emergency_keywords(text: str) -> bool:
    """Fast deterministic check for common emergency keywords in English & Malayalam."""
    normalized = text.lower()
    emergency_phrases = [
        "sos", "emergency", "help", "help me", "fell down", "chest pain",
        "heart attack", "can't breathe", "cannot breathe", "bleeding",
        "സഹായം", "നെഞ്ചുവേദന", "ശ്വാസം മുട്ടുന്നു", "വീണു", "തലകറക്കം",
        "അടിയന്തിരം", "ഡോക്ടർ", "ആശുപത്രി"
    ]
    return any(phrase in normalized for phrase in emergency_phrases)


def generate_care_response(
    message: str,
    user_phone: str,
    role: str = "ELDER",
) -> Dict[str, Any]:
    """Generates an AI response and emergency intent evaluation for an incoming message.

    Args:
        message: The user's input text (spoken or typed).
        user_phone: The phone number of the user.
        role: "ELDER", "CAREGIVER", or "USER".

    Returns:
        Dict with keys:
            - is_emergency: bool
            - urgency: str ("NORMAL" | "CRITICAL")
            - response_text: str (User-facing reply)
            - caregiver_summary: str (Summary for caregiver dispatch)
    """
    clean_text = (message or "").strip()
    has_emergency_keyword = detect_emergency_keywords(clean_text)

    # 1. Try Google Gemini API
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            prompt = f"User role: {role}\nUser phone: {user_phone}\nMessage: {clean_text}\n\nAssess emergency and respond in JSON:"
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={"system_instruction": SYSTEM_PROMPT, "response_mime_type": "application/json"},
            )
            result = json.loads(resp.text)
            if has_emergency_keyword:
                result["is_emergency"] = True
            return result
        except Exception as e:
            print(f"[AI GEMINI ERROR] {e}")

    # 2. Try Groq API (Llama 3.3)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Message: {clean_text}"},
            ]
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
            )
            raw_content = chat_completion.choices[0].message.content
            result = json.loads(raw_content)
            if has_emergency_keyword:
                result["is_emergency"] = True
            return result
        except Exception as e:
            print(f"[AI GROQ ERROR] {e}")

    # 3. Rule-based Deterministic Fallback (when no LLM key is configured)
    if has_emergency_keyword:
        return {
            "is_emergency": True,
            "urgency": "CRITICAL",
            "response_text": (
                "Sahayi SOS: അടിയന്തര സാഹായ അഭ്യർത്ഥന ലഭിച്ചു. നിങ്ങളുടെ കെയർഗിവർക്ക് വിവരം അയച്ചിട്ടുണ്ട്. "
                "ദയവായി ശാന്തരായിരിക്കുക.\n"
                "(Emergency alert received. Your caregiver has been notified and help is on the way. Please stay calm.)"
            ),
            "caregiver_summary": f"Senior member reported distress: '{clean_text}'",
        }

    return {
        "is_emergency": False,
        "urgency": "NORMAL",
        "response_text": (
            f"Sahayi: നമസ്കാരം! താങ്കളുടെ സന്ദേശം ലഭിച്ചു: '{clean_text}'. സുഖമാണോ? എന്തെങ്കിലും സഹായം ആവശ്യമുണ്ടോ?\n"
            f"(Hello! Message received: '{clean_text}'. How are you feeling today? Let me know if you need any assistance.)"
        ),
        "caregiver_summary": "",
    }

