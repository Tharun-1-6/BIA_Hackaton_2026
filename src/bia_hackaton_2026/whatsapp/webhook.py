import json
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import APIRouter, BackgroundTasks, Form, Request, Response
from fastapi.responses import PlainTextResponse

from bia_hackaton_2026.whatsapp.config import (
    CAREGIVER_WHATSAPP_NUMBER,
    ELDER_PHONE_NUMBER,
    META_VERIFY_TOKEN,
)
from bia_hackaton_2026.whatsapp.interactive_actions import handle_member_sos
from bia_hackaton_2026.whatsapp.media import download_audio_media, download_meta_audio
from bia_hackaton_2026.whatsapp.sender import send_whatsapp_message, send_whatsapp_template

router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp Webhook"])


@router.get("")
@router.get("/")
async def verify_webhook(request: Request) -> Response:
    """Handles Meta WhatsApp Webhook verification handshake."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        print(f"[META WEBHOOK VERIFIED] Challenge: {challenge}")
        return PlainTextResponse(content=challenge, status_code=200)

    return PlainTextResponse(content="Forbidden", status_code=403)


@router.post("")
@router.post("/")
async def receive_whatsapp(
    request: Request,
    background_tasks: BackgroundTasks,
    From: str = Form(""),
    MessageSid: str = Form(""),
    Body: Optional[str] = Form(None),
    NumMedia: str = Form("0"),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None),
) -> Response:
    """Handles incoming WhatsApp webhooks from both Meta Cloud API (JSON) and Twilio (Form)."""
    content_type = request.headers.get("content-type", "")

    # ==========================================
    # BRANCH 1: META WHATSAPP CLOUD API (JSON)
    # ==========================================
    if "application/json" in content_type:
        try:
            body_json: Dict[str, Any] = await request.json()
        except Exception:
            return PlainTextResponse(content="Invalid JSON", status_code=400)

        # Log full incoming Meta webhook event to file for debugging
        try:
            with open("whatsapp_events.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.now().isoformat()}] META WEBHOOK EVENT:\n{json.dumps(body_json, indent=2)}\n")
        except Exception:
            pass

        entries = body_json.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Check Meta delivery status updates (sent, delivered, failed)
                statuses = value.get("statuses", [])
                for status in statuses:
                    status_id = status.get("id")
                    status_val = status.get("status")
                    recipient = status.get("recipient_id")
                    errors = status.get("errors", [])
                    if status_val == "failed" or errors:
                        print(f"[META DELIVERY FAILED] To: +{recipient} | ID: {status_id} | Errors: {errors}")
                        for err in errors:
                            if err.get("code") == 131047:
                                print(f"[AUTO-RECOVERY] Recipient +{recipient} 24h window closed. Dispatching template bypass!")
                                background_tasks.add_task(send_whatsapp_template, recipient, "hello_world")
                    else:
                        print(f"[META DELIVERY STATUS] To: +{recipient} | Status: {status_val} | ID: {status_id}")

                messages = value.get("messages", [])
                for msg in messages:
                    sender = msg.get("from", "")  # e.g. "917012649561"
                    msg_id = msg.get("id", "")
                    msg_type = msg.get("type", "text")
                    sender_formatted = f"+{sender}" if not sender.startswith("+") else sender

                    clean_sender = sender_formatted.replace("+", "").strip()
                    clean_elder = ELDER_PHONE_NUMBER.replace("+", "").strip()
                    clean_caregiver = (
                        CAREGIVER_WHATSAPP_NUMBER.replace("whatsapp:", "").replace("+", "").strip()
                    )

                    if clean_sender == clean_elder:
                        role_tag = "ELDER"
                    elif clean_sender == clean_caregiver:
                        role_tag = "CAREGIVER"
                    else:
                        role_tag = "USER"

                    print(f"\n[META INBOUND - {role_tag}] ID: {msg_id} | From: {sender_formatted} | Type: {msg_type}")

                    # Case A: Inbound message from Caregiver
                    if role_tag == "CAREGIVER":
                        caregiver_welcome = (
                            "🛡️ *Sahayi Caregiver Portal Connected*\n\n"
                            "നമസ്കാരം! താങ്കൾ Sahayi കെയർഗിവറായി വിജയകരമായി ബന്ധിപ്പിക്കപ്പെട്ടു.\n"
                            f"മുതിർന്ന അംഗം ({ELDER_PHONE_NUMBER}) SOS അല്ലെങ്കിൽ അടിയന്തര സഹായം ആവശ്യപ്പെടുമ്പോൾ ഈ നമ്പറിലേക്ക് തത്സമയ മുന്നറിയിപ്പുകൾ ലഭിക്കുന്നതാണ്.\n\n"
                            "(Welcome! You are connected as emergency caregiver for Elder. You will receive real-time SOS alerts here.)"
                        )
                        background_tasks.add_task(send_whatsapp_message, sender_formatted, caregiver_welcome)
                        continue

                    # Case B: Audio Voice Note from Elder/User
                    if msg_type == "audio":
                        audio_info = msg.get("audio", {})
                        audio_id = audio_info.get("id")
                        if audio_id:
                            try:
                                audio_path = download_meta_audio(audio_id)
                                print(f"[META AUDIO SAVED] Path: {audio_path}")
                            except Exception as e:
                                print(f"[META AUDIO DOWNLOAD ERROR] {e}")

                        reply_msg = (
                            "Sahayi: വോയ്സ് സന്ദേശം ലഭിച്ചു. പരിശോധിക്കുന്നു... "
                            "(Voice note received, processing...)"
                        )
                        background_tasks.add_task(send_whatsapp_message, sender_formatted, reply_msg)
                        continue

                    # Case C: Text Message / SOS
                    text_body = msg.get("text", {}).get("body", "").strip()
                    normalized_text = text_body.upper()

                    if normalized_text in ["INITIATE SOS", "SOS", "EMERGENCY", "HELP"]:
                        sos_result = handle_member_sos(sender_formatted, text_body)
                        caregiver_alert = sos_result.get("caregiver_alert")

                        # 1. Clear reassurance confirmation for Elder (NOT the caregiver emergency dispatch)
                        elder_ack = (
                            "Sahayi SOS: അടിയന്തര സഹായം രേഖപ്പെടുത്തി. നിങ്ങളുടെ കെയർഗിവർക്ക് "
                            f"(+{clean_caregiver}) വിവരം അറിയിച്ചിട്ടുണ്ട്. ഉടൻ സഹായം എത്തും, ശാന്തരായിരിക്കുക.\n"
                            f"(Emergency alert received. Your caregiver +{clean_caregiver} has been notified and help is on the way. Please stay calm.)"
                        )
                        background_tasks.add_task(send_whatsapp_message, sender_formatted, elder_ack)

                        # 2. Urgent Emergency Alert dispatched ONLY to the Caregiver
                        if clean_caregiver and clean_caregiver != clean_sender:
                            print(f"[SOS ESCALATION] Alerting caregiver exclusively: +{clean_caregiver}")
                            background_tasks.add_task(send_whatsapp_message, clean_caregiver, caregiver_alert)
                    else:
                        fallback_reply = (
                            f"Sahayi: സന്ദേശം ലഭിച്ചു '{text_body}'. വോയ്സ് മെസ്സേജ് അയക്കാവുന്നതാണ്. "
                            f"(Message received. You can also send voice notes.)"
                        )
                        background_tasks.add_task(send_whatsapp_message, sender_formatted, fallback_reply)

        return PlainTextResponse(content="EVENT_RECEIVED", status_code=200)

    # ==========================================
    # BRANCH 2: TWILIO WHATSAPP (FORM-ENCODED)
    # ==========================================
    sender = From.replace("whatsapp:", "").strip()
    try:
        media_count = int(NumMedia)
    except (ValueError, TypeError):
        media_count = 0

    incoming_text = (Body or "").strip()
    print(f"\n[TWILIO INBOUND] ID: {MessageSid} | Sender: {sender} | Text: {incoming_text}")

    if not From:
        return Response(content="<Response/>", media_type="application/xml", status_code=200)

    # Audio note
    if media_count > 0 and "audio" in (MediaContentType0 or "").lower():
        if MediaUrl0:
            try:
                local_audio_path = download_audio_media(MediaUrl0, MessageSid)
                print(f"[AUDIO SAVED] Path: {local_audio_path}")
            except Exception as audio_err:
                print(f"[AUDIO DOWNLOAD WARNING] Failed to download media: {audio_err}")

        reply_msg = (
            "Sahayi: വോയ്സ് സന്ദേശം ലഭിച്ചു. പരിശോധിക്കുന്നു... "
            "(Voice note received, processing...)"
        )
        background_tasks.add_task(send_whatsapp_message, From, reply_msg)
        return Response(content="<Response/>", media_type="application/xml", status_code=200)

    # SOS Escalation
    if incoming_text.upper() in ["INITIATE SOS", "SOS", "EMERGENCY", "HELP"]:
        sos_result = handle_member_sos(sender, incoming_text)
        caregiver_alert = sos_result.get("caregiver_alert")

        # 1. Elder confirmation
        elder_ack = (
            "Sahayi SOS: അടിയന്തര സഹായം രേഖപ്പെടുത്തി. നിങ്ങളുടെ കെയർഗിവറെ വിവരം അറിയിച്ചിട്ടുണ്ട്. ഉടൻ സഹായം എത്തും, ശാന്തരായിരിക്കുക.\n"
            "(Emergency alert received. Your caregiver has been notified and help is on the way. Please stay calm.)"
        )
        background_tasks.add_task(send_whatsapp_message, From, elder_ack)

        # 2. Caregiver alert
        if CAREGIVER_WHATSAPP_NUMBER and caregiver_alert:
            target_caregiver = (
                CAREGIVER_WHATSAPP_NUMBER
                if CAREGIVER_WHATSAPP_NUMBER.startswith("whatsapp:")
                else f"whatsapp:{CAREGIVER_WHATSAPP_NUMBER}"
            )
            if target_caregiver.lower() != From.lower():
                print(f"[SOS ESCALATION] Alerting caregiver exclusively: {target_caregiver}")
                background_tasks.add_task(send_whatsapp_message, target_caregiver, caregiver_alert)

        return Response(content="<Response/>", media_type="application/xml", status_code=200)

    # Text Fallback
    fallback_reply = (
        f"Sahayi: സന്ദേശം ലഭിച്ചു '{incoming_text}'. വോയ്സ് മെസ്സേജ് അയക്കാവുന്നതാണ്. "
        f"(Message received. You can also send voice notes.)"
    )
    background_tasks.add_task(send_whatsapp_message, From, fallback_reply)
    return Response(content="<Response/>", media_type="application/xml", status_code=200)
