import json
from pathlib import Path

from bia_hackaton_2026.llm.response_generator import ask_llm

from bia_hackaton_2026.message_processor.parser import parse_response
from bia_hackaton_2026.message_processor.validator import validate_turn
from bia_hackaton_2026.message_processor.formatter import (
    format_user_message,
    format_family_message
)

from bia_hackaton_2026.message_processor.schema import Turn
from bia_hackaton_2026.whatsapp.sender import send_message


# Contact details (example numbers)
USER_PHONE = "+919876543210"
FAMILY_PHONE = "+919876543211"

MEMORY_FILE = Path("memory.json")
# shortcut: plain truncation of old messages, summarise them if this window starts to matter
MEMORY_LIMIT = 20


def load_memory() -> list[dict]:
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return []


def process_message(user_input: str, history: list[dict]):

    # 1. Get LLM response
    for attempt in range(2):

        raw_response = ask_llm(user_input, history[-MEMORY_LIMIT:])

        # 2. Parse JSON
        turn = parse_response(raw_response)

        # 3. Validate response
        if turn is not None and validate_turn(turn):
            break

    else:
        # 4. Fallback if both attempts fail
        turn = Turn(
            user={
                "text": "I couldn't understand that. Please tell me again.",
                "follow_up": None
            },
            family={
                "summary": "Sahayi could not process the user's message.",
                "suggested_level": 1,
                "send": False
            }
        )

    # 5. Format messages
    user_message = format_user_message(turn)
    family_message = format_family_message(turn)

    # 6. Send messages
    send_message(USER_PHONE, user_message)

    if turn.family.send or turn.family.suggested_level >= 2:  # safety net for a weak model
        send_message(FAMILY_PHONE, family_message)

    history += [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": turn.model_dump_json()},
    ]
    MEMORY_FILE.write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")

    return turn


if __name__ == "__main__":

    print("===== SAHAYI =====")

    history = load_memory()

    while user_input := input("\nUser (blank to quit): ").strip():
        process_message(user_input, history)