"""Central Orchestration Pipeline & Developer Tools for Sahayi.

Connects:
1. Speech-to-Text (Sarvam saaras:v3 for Malayalam, Groq Whisper for English)
2. Vision (Groq Qwen Vision for photos)
3. LLM Agent Turn (Groq / Gemini / OpenAI with Malayalam urgency rules)
4. WhatsApp Cloud API & Twilio Delivery (Elder & Caregiver)
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

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

# In-memory conversation history per phone number (persisted to disk)
_MEMORY_DIR = Path("data/memory")
_HISTORIES: Dict[str, List[dict]] = {}


def get_user_history(phone: str) -> List[dict]:
    """Retrieves conversation history for a specific user phone number."""
    clean = phone.replace("whatsapp:", "").replace("+", "").strip()
    if clean in _HISTORIES:
        return _HISTORIES[clean]

    # Try loading from disk
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    hist_file = _MEMORY_DIR / f"{clean}.json"
    if hist_file.exists():
        try:
            data = json.loads(hist_file.read_text(encoding="utf-8"))
            _HISTORIES[clean] = data
            return data
        except Exception:
            pass

    _HISTORIES[clean] = []
    return _HISTORIES[clean]


def save_user_history(phone: str, history: List[dict]) -> None:
    """Saves conversation history for a user (truncated to last 20 messages)."""
    clean = phone.replace("whatsapp:", "").replace("+", "").strip()
    trimmed = history[-20:]
    _HISTORIES[clean] = trimmed
    try:
        _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        hist_file = _MEMORY_DIR / f"{clean}.json"
        hist_file.write_text(json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[MEMORY SAVE ERROR] {e}")


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
        f"Sahayi SOS: അടിയന്തര സഹായം രേഖപ്പെടുത്തി. നിങ്ങളുടെ കെയർഗിവർക്ക് (+{clean_caregiver}) "
        f"വിവരം നൽകിയിട്ടുണ്ട്. ഉടൻ സഹായം എത്തും, ശാന്തരായിരിക്കുക.\n"
        f"(Emergency alert registered. Help notification sent to caregiver +{clean_caregiver}. Help is on the way.)"
    )

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
    """Developer Tool: Send a direct proactive WhatsApp notification."""
    return send_whatsapp_message(to_phone, message)


def process_inbound_text(
    sender_phone: str,
    text: str,
    role: str = "USER",
) -> Dict[str, Any]:
    """Processes inbound text message using the complete AI agent pipeline."""
    clean_sender = sender_phone.replace("whatsapp:", "").replace("+", "").strip()
    clean_caregiver = CAREGIVER_WHATSAPP_NUMBER.replace("whatsapp:", "").replace("+", "").strip()
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

    # Case 2: Deterministic Keyword SOS (Instant bypass for life-critical speed)
    if normalized in ["INITIATE SOS", "SOS", "EMERGENCY", "HELP"]:
        sos_res = trigger_sos_escalation(
            elder_phone=sender_phone,
            trigger_source="KEYWORD_SOS",
            summary=f"Senior explicitly requested urgent help: '{text}'",
        )
        return {"action": "EMERGENCY_ESCALATION", "details": sos_res}

    # Case 3: Teammate LLM Agent Turn (Full contextual comprehension & urgency rules)
    try:
        from bia_hackaton_2026.agent.runner import run_turn
        history = get_user_history(sender_phone)
        turn_result = run_turn(
            user_input=text,
            history=history,
            user_phone=sender_phone,
            family_phone=clean_caregiver,
        )
        save_user_history(sender_phone, history)
        return {"action": "AGENT_TURN", "details": turn_result}
    except Exception as e:
        print(f"[AGENT RUNNER WARNING] Falling back to default care agent: {e}")

    # Fallback to local care response evaluator
    ai_result = generate_care_response(text, sender_phone, role=role)
    if ai_result.get("is_emergency"):
        sos_res = trigger_sos_escalation(
            elder_phone=sender_phone,
            trigger_source="AI_SEMANTIC_DETECTION",
            summary=ai_result.get("caregiver_summary") or text,
        )
        return {"action": "EMERGENCY_ESCALATION", "details": sos_res, "ai_eval": ai_result}

    reply_text = ai_result.get("response_text", f"Sahayi: സന്ദേശം ലഭിച്ചു '{text}'.")
    msg_id = send_whatsapp_message(sender_phone, reply_text)
    return {"action": "CONVERSATIONAL_REPLY", "reply_text": reply_text, "message_id": msg_id}


def process_inbound_voice(
    sender_phone: str,
    audio_path: str,
    role: str = "USER",
) -> Dict[str, Any]:
    """Processes incoming WhatsApp voice notes (.ogg) through STT and LLM agent."""
    print(f"\n[ORCHESTRATOR - VOICE PROCESSING] Audio path: {audio_path}")
    transcription = ""

    # 1. Teammate STT: Sarvam (Malayalam) / Groq Whisper (English)
    audio_file = Path(audio_path)
    if audio_file.exists():
        try:
            from bia_hackaton_2026.stt.detect import detect_and_transcribe
            with open(audio_file, "rb") as f:
                audio_bytes = f.read()
            res = detect_and_transcribe(audio_bytes, audio_file.name)
            transcription = res.get("text", "").strip()
            if transcription:
                print(f"[ORCHESTRATOR - SARVAM/GROQ STT COMPLETE] Speech: '{transcription}' (Lang: {res.get('language')})")
        except Exception as stt_err:
            print(f"[ORCHESTRATOR - STT DETECT FALLBACK] {stt_err}")

    # 2. Secondary STT fallback
    if not transcription and audio_file.exists():
        transcription = transcribe_audio(audio_path) or ""

    # 3. If speech was transcribed, feed directly into LLM Agent Turn!
    if transcription:
        return process_inbound_text(sender_phone, transcription, role=role)

    # 4. Fallback if no STT configured or empty audio
    fallback_msg = (
        "Sahayi: വോയ്സ് സന്ദേശം ലഭിച്ചു. എന്തെങ്കിലും അടിയന്തര ആവശ്യമുണ്ടെങ്കിൽ 'SOS' എന്ന് അയക്കുക.\n"
        "(Voice message received safely. If you need urgent emergency help, please send 'SOS'.)"
    )
    msg_id = send_whatsapp_message(sender_phone, fallback_msg)
    return {"action": "VOICE_FALLBACK", "reply_text": fallback_msg, "message_id": msg_id}


def process_inbound_image(
    sender_phone: str,
    image_path: str,
    caption: str = "",
    role: str = "USER",
) -> Dict[str, Any]:
    """Processes incoming WhatsApp image/photo through Groq Qwen Vision (VLM)."""
    print(f"\n[ORCHESTRATOR - IMAGE PROCESSING] Image path: {image_path}")
    agent_input = caption
    try:
        from bia_hackaton_2026.vlm.describe import describe_image, build_agent_input
        with open(image_path, "rb") as f:
            img_bytes = f.read()
        desc_res = describe_image(img_bytes, mime="image/jpeg", user_text=caption)
        description = desc_res.get("description", "")
        if description:
            agent_input = build_agent_input(caption, description)
            print(f"[ORCHESTRATOR - VLM COMPLETE] Description:\n{description}")
    except Exception as vlm_err:
        print(f"[ORCHESTRATOR - VLM ERROR] {vlm_err}")

    return process_inbound_text(sender_phone, agent_input or "The user sent a photo.", role=role)
