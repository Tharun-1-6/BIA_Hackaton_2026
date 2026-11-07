from bia_hackaton_2026.message_processor.schema import Turn


def format_user_message(turn: Turn) -> str:

    message = turn.user.text

    if turn.user.follow_up:
        message += "\n\n" + turn.user.follow_up

    return message


def format_family_message(turn: Turn) -> str:

    message = (
        "⚠️ *SAHAYI – FAMILY ALERT*\n\n"
        f"*Situation:*\n{turn.family.summary}\n\n"
        f"*Suggested urgency level:* {turn.family.suggested_level}"
    )

    return message