from bia_hackaton_2026.message_processor.schema import Turn


def validate_turn(turn: Turn) -> bool:
    """
    Additional application-level validation.
    """

    if not turn.user.text.strip():
        return False

    if not turn.family.summary.strip():
        return False

    if turn.family.suggested_level not in (1, 2, 3):
        return False

    return True