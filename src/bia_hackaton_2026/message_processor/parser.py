from pydantic import ValidationError
from bia_hackaton_2026.message_processor.schema import Turn


def parse_response(llm_text: str) -> Turn | None:

    try:
        return Turn.model_validate_json(llm_text)

    except (ValidationError, ValueError):
        return None