"""One agent turn. Same flow as process_message() in the repo-root main.py (retry once, fallback
Turn, family-send rule), but returns everything so the Streamlit UI can display it."""
import sys
import time

from bia_hackaton_2026.llm.response import MODEL, ask_llm
from bia_hackaton_2026.message_processor.formatter import format_family_message, format_user_message
from bia_hackaton_2026.message_processor.parser import parse_response
from bia_hackaton_2026.message_processor.schema import Turn
from bia_hackaton_2026.message_processor.validator import validate_turn
from bia_hackaton_2026.whatsapp.sender import send_message

# send_message() prints the family alert, which contains an emoji; Windows consoles (cp1252) crash on it.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

USER_PHONE = "+919876543210"      # example numbers, as in main.py
FAMILY_PHONE = "+919876543211"
MEMORY_LIMIT = 20                 # plain truncation of old messages, as in main.py


def run_turn(user_input: str, history: list[dict], model: str = MODEL, api_key: str | None = None,
             send: bool = True) -> dict:
    """Appends the exchange to `history` (in place). Returns dict with turn, messages, send flag,
    raw LLM output, attempts, fallback flag, error, seconds, model."""
    t0 = time.perf_counter()
    raw, error, turn, attempts = "", "", None, 0
    for attempt in range(2):
        attempts = attempt + 1
        try:
            raw = ask_llm(user_input, history[-MEMORY_LIMIT:], model, api_key)
        except Exception as e:
            error = f"LLM call failed: {e}"
            continue
        turn = parse_response(raw)
        if turn is not None and validate_turn(turn):
            error = ""
            break
    else:
        turn = None

    fallback = turn is None
    if fallback:
        turn = Turn(
            user={"text": "I couldn't understand that. Please tell me again.", "follow_up": None},
            family={"summary": "Sahayi could not process the user's message.", "suggested_level": 1, "send": False},
        )

    user_message = format_user_message(turn)
    family_message = format_family_message(turn)
    family_sent = bool(turn.family.send or turn.family.suggested_level >= 2)
    if send:  # transports that deliver messages themselves (Telegram) pass send=False
        send_message(USER_PHONE, user_message)  # prints to the terminal
        if family_sent:
            send_message(FAMILY_PHONE, family_message)

    history += [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": turn.model_dump_json()},
    ]
    return {
        "turn": turn, "user_message": user_message, "family_message": family_message,
        "family_sent": family_sent, "raw": raw, "attempts": attempts, "fallback": fallback,
        "error": error, "seconds": round(time.perf_counter() - t0, 2), "model": model,
    }
