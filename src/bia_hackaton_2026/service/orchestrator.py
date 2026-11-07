"""Central Orchestration Pipeline & Developer Tools for Sahayi.

This module provides the primary integration API for team members developing
AI agents, sensors, scheduled tasks, and health monitors.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bia_hackaton_2026.ai.agent import generate_care_response
from bia_hackaton_2026.ai.stt import transcribe_audio
from bia_hackaton_2026.whatsapp.config import (
    CAREGIVER_WHATSAPP_NUMBER,
    ELDER_PHONE_NUMBER,
)
from bia_hackaton_2026.whatsapp.interactive_actions import handle_member_sos
from bia_hackaton_2026.whatsapp.sender import (
    send_whatsapp_message,
    send_whatsapp_template,
)


def trigger_sos_escalation(
    elder_phone: Optional[str] = None,
    trigger_source: str = "MANUAL_SOS",
    summary: str = "Emergency assistance requested",
    caregiver_phone: Optional[str] = None,
) -> Dict[str, Any]:
    """Developer Tool: Programmatically triggers an Emergency SOS Escalation.

    Can be invoked by:
    - Teammate AI agents (detecting distress from conversation)
    - Fall detection / IoT sensors
    - Medication reminder cron jobs (after repeated missed doses)

    Args:
        elder_phone: The senior member's phone number (defaults to ELDER_PHONE_NUMBER).
        trigger_source: Origin of trigger (e.g. "VOICE_STT", "LLM_DETECTION", "FALL_SENSOR").
        summary: Description or transcription of the emergency.
        caregiver_phone: Custom caregiver number (defaults to CAREGIVER_WHATSAPP_NUMBER).

    Returns:
        Dict containing dispatch status, timestamps, and message IDs.
    """
    target_elder = elder_phone or ELDER_PHONE_NUMBER
    target_caregiver = caregiver_phone or CAREGIVER_WHATSAPP_NUMBER
    clean_caregiver = target_caregiver.replace("whatsapp:", "").replace("+", "").strip()
    clean_elder = target_elder.replace("whatsapp:", "").replace("+", "").strip()

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 1. Format the Critical Caregiver Dispatch Alert
    caregiver_alert = (
        f"🚨 *SAHAYI അടിയന്തര മുന്നറിയിപ്പ് (EMERGENCY ALERT)*\n\n"
        f"• *Member:* +{clean_elder}\n"
        f"• *Source:* {trigger_source}\n"
        f"• *Time:* {now_iso}\n"
        f"• *Details:* {summary}\n\n"
        f"⚠️ Please call or check on the senior member immediately!"
    )

    # 2. Calming Reassurance for Elder
    elder_reassurance = (
        f"Sahayi SOS: അടിയന്തര സഹായ അഭ്യർത്ഥന ലഭിച്ചു. നിങ്ങളുടെ കെയർഗിവർക്ക് (+{clean_caregiver}) "
        f"വിവരം നൽകിയിട്ടുണ്ട്. ഉടൻ സഹായം എത്തും, ശാന്തരായിരിക്കുക.\n"
        f"(Emergency alert registered. Help notification sent to caregiver +{clean_caregiver}. Help is on the way.)"
    )

    # Dispatch Outbound
    print(f"\n[ORCHESTRATOR - SOS ESCALATION] Source: {trigger_source} | Member: +{clean_elder} -> Caregiver: +{clean_caregiver}")
    elder_msg_id = send_whatsapp_message(target_elder, elder_reassurance)
    caregiver_msg_id = send_whatsapp_message(clean_caregiver, caregiver_alert)

    return {
        "status": "ESCALATED",
        "timestamp": now_iso,
        "trigger_source": trigger_source,
        "elder_phone": f"+{clean_elder}",
        "caregiver_phone": f"+{clean_caregiver}",
        "elder_message_id": elder_msg_id,
        "caregiver_message_id": caregiver_msg_id,
        "summary": summary,
    }


def send_proactive_notification(to_phone: str, message: str) -> str:
    """Developer Tool: Send a direct proactive WhatsApp notification.

    Used by teammates for:
    - Medication reminders
    - Scheduled daily health check-in
    - Caregiver updates
    """
    return send_whatsapp_message(to_phone, message)


def process_inbound_text(
    sender_phone: str,
    text: str,
    role: str = "USER",
) -> Dict[str, Any]:
    """Processes any inbound text message from a user or caregiver.

    Evaluates:
    1. Deterministic SOS triggers (SOS, HELP, INITIATE SOS)
    2. Caregiver portal interactions
    3. AI/LLM semantic intent detection & response generation
    """
    clean_sender = sender_phone.replace("whatsapp:", "").replace("+", "").strip()
    normalized = (text or "").strip().upper()

    # Case 1: Caregiver Message
    if role == "CAREGIVER":
        reply = (
            "🛡️ *Sahayi Caregiver Portal Connected*\n\n"
            "നമസ്കാരം! താങ്കൾ Sahayi കെയർഗിവറായി വിജയകരമായി ബന്ധിപ്പിക്കപ്പെട്ടു.\n"
            f"മുതിർന്ന അംഗം ({ELDER_PHONE_NUMBER}) SOS അല്ലെങ്കിൽ അടിയന്തര സഹായം ആവശ്യപ്പെടുമ്പോൾ ഈ നമ്പറിലേക്ക് തത്സമയ മുന്നറിയിപ്പുകൾ ലഭിക്കുന്നതാണ്.\n\n"
            "(Welcome! You are connected as emergency caregiver for Elder. You will receive real-time SOS alerts here.)"
        )
        msg_id = send_whatsapp_message(sender_phone, reply)
        return {"action": "CAREGIVER_ACK", "reply_text": reply, "message_id": msg_id}

    # Case 2: Deterministic Keyword SOS
    if normalized in ["INITIATE SOS", "SOS", "EMERGENCY", "HELP"]:
        sos_res = trigger_sos_escalation(
            elder_phone=sender_phone,
            trigger_source="KEYWORD_SOS",
            summary=f"Member typed '{text}'",
        )
        return {"action": "EMERGENCY_ESCALATION", "details": sos_res}

    # Case 3: AI Agent / Semantic Care Evaluation
    ai_result = generate_care_response(text, sender_phone, role=role)
    if ai_result.get("is_emergency"):
        sos_res = trigger_sos_escalation(
            elder_phone=sender_phone,
            trigger_source="AI_SEMANTIC_DETECTION",
            summary=ai_result.get("caregiver_summary") or text,
        )
        return {"action": "EMERGENCY_ESCALATION", "details": sos_res, "ai_eval": ai_result}

    # Normal Conversational Response
    reply_text = ai_result.get("response_text", f"Sahayi: സന്ദേശം ലഭിച്ചു '{text}'.")
    msg_id = send_whatsapp_message(sender_phone, reply_text)
    return {"action": "CONVERSATIONAL_REPLY", "reply_text": reply_text, "message_id": msg_id}


def process_inbound_voice(
    sender_phone: str,
    audio_path: str,
    role: str = "USER",
) -> Dict[str, Any]:
    """Processes an incoming voice note (.ogg/.wav).

    1. Transcribes audio via STT (Groq Whisper or OpenAI Whisper)
    2. Passes transcription to process_inbound_text for AI evaluation & dispatch.
    """
    print(f"\n[ORCHESTRATOR - VOICE PROCESSING] Audio path: {audio_path}")
    transcription = transcribe_audio(audio_path)

    if transcription:
        print(f"[ORCHESTRATOR - STT COMPLETE] Speech: '{transcription}'")
        return process_inbound_text(sender_phone, transcription, role=role)

    # Fallback if no STT configured or transcription failed
    fallback_msg = (
        "Sahayi: താങ്കളുടെ വോയ്സ് സന്ദേശം സുരക്ഷിതമായി ലഭിച്ചു. എന്തെങ്കിലും അടിയന്തര ആവശ്യമുണ്ടെങ്കിൽ 'SOS' എന്ന് അയക്കുക.\n"
        "(Voice message received safely. If you need urgent emergency help, please send 'SOS'.)"
    )
    msg_id = send_whatsapp_message(sender_phone, fallback_msg)
    return {"action": "VOICE_FALLBACK", "reply_text": fallback_msg, "message_id": msg_id}

