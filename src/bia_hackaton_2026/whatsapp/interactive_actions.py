from datetime import datetime, timezone
from typing import Any, Dict

DETERMINISTIC_SOS_TRIGGERS = {"INITIATE SOS", "SOS", "EMERGENCY", "HELP"}


def handle_member_sos(sender_number: str, command: str) -> Dict[str, Any]:
    """Evaluates deterministic SOS triggers and returns a structured escalation dictionary.

    Args:
        sender_number: The phone number of the user initiating the SOS.
        command: The incoming command text to evaluate.

    Returns:
        dict: Structured dictionary containing escalation action, bilingual instructions,
              caregiver alert text, and audit metadata.
    """
    normalized_command = (command or "").strip().upper()
    is_triggered = normalized_command in DETERMINISTIC_SOS_TRIGGERS
    now_iso = datetime.now(timezone.utc).isoformat()

    if is_triggered:
        ml_text = "അടിയന്തര സഹായം രേഖപ്പെടുത്തി. കെയർ ടീം നിങ്ങളെ ഉടൻ ബന്ധപ്പെടും. ശാന്തരായിരിക്കുക."
        en_text = "Emergency alert received. Our care team has been notified and will contact you immediately. Please stay calm."
        caregiver_alert = (
            f"🚨 *SAHAYI അടിയന്തര മുന്നറിയിപ്പ് (EMERGENCY ALERT)*\n\n"
            f"• *Member Phone:* {sender_number}\n"
            f"• *Trigger:* {normalized_command}\n"
            f"• *Time:* {now_iso}\n"
            f"• *Status:* Urgent assistance requested by senior member.\n\n"
            f"Please check on them or call immediately!"
        )
        return {
            "status": "triggered",
            "sender_number": sender_number,
            "command": command,
            "escalation_action": "EMERGENCY_DISPATCH_AND_CARE_TEAM_ALERT",
            "instructions": f"Sahayi SOS: {ml_text} ({en_text})",
            "caregiver_alert": caregiver_alert,
            "instruction_details": {
                "malayalam": ml_text,
                "english": en_text,
            },
            "audit_metadata": {
                "timestamp": now_iso,
                "trigger_word": normalized_command,
                "source": "whatsapp_incoming",
                "severity": "CRITICAL",
                "escalated": True,
            },
        }

    ml_fallback = "കമാൻഡ് തിരിച്ചറിഞ്ഞില്ല. സഹായത്തിന് 'SOS' അല്ലെങ്കിൽ 'INITIATE SOS' അയക്കുക."
    en_fallback = "Command not recognized as SOS. Send 'SOS' or 'INITIATE SOS' for emergency assistance."
    return {
        "status": "ignored",
        "sender_number": sender_number,
        "command": command,
        "escalation_action": "NONE",
        "instructions": f"{ml_fallback} ({en_fallback})",
        "caregiver_alert": None,
        "instruction_details": {
            "malayalam": ml_fallback,
            "english": en_fallback,
        },
        "audit_metadata": {
            "timestamp": now_iso,
            "trigger_word": normalized_command,
            "source": "whatsapp_incoming",
            "severity": "INFO",
            "escalated": False,
        },
    }
