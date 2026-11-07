import os
from typing import Optional
import requests
from twilio.rest import Client
from bia_hackaton_2026.whatsapp.config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_NUMBER,
    get_meta_phone_id,
    get_meta_token,
)


def _get_twilio_client() -> Client:
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_whatsapp_template(
    to_number: str,
    template_name: str = "hello_world",
    language_code: str = "en_US",
    components: Optional[list] = None,
) -> str:
    """Dispatches an approved Meta WhatsApp template message (can bypass 24h window)."""
    clean_number = to_number.replace("whatsapp:", "").replace("+", "").strip()
    token = get_meta_token()
    phone_id = get_meta_phone_id()

    if token and phone_id:
        url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        if components:
            payload["template"]["components"] = components
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            data = resp.json()
            if resp.status_code in (200, 201):
                msg_id = data.get("messages", [{}])[0].get("id", "TEMPLATE_SENT")
                print(f"[META TEMPLATE SENT] ID: {msg_id} | To: +{clean_number} | Template: {template_name}")
                return str(msg_id)
            else:
                print(f"[META TEMPLATE ERROR] Status {resp.status_code}: {data}")
        except Exception as e:
            print(f"[META TEMPLATE EXCEPTION] {e}")

    return ""


def send_whatsapp_message(to_number: str, message: str) -> str:
    """Dispatches outbound WhatsApp messages via Meta Cloud API or Twilio.

    Automatically handles number formatting for both providers.

    Args:
        to_number: Recipient phone number (e.g. '+917012649561' or 'whatsapp:+917012649561').
        message: The message body text.

    Returns:
        The message ID/SID, or empty string on failure.
    """
    clean_number = to_number.replace("whatsapp:", "").replace("+", "").strip()
    token = get_meta_token()
    phone_id = get_meta_phone_id()

    # 1. Meta WhatsApp Cloud API (Primary if configured)
    if token and phone_id:
        url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_number,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            data = resp.json()
            if resp.status_code in (200, 201):
                msg_id = data.get("messages", [{}])[0].get("id", "META_SENT")
                print(f"[META OUTBOUND SENT] ID: {msg_id} | To: +{clean_number}")
                return str(msg_id)
            else:
                err_code = data.get("error", {}).get("code")
                if err_code == 190 or resp.status_code == 401:
                    print(
                        "\n🚨 [CRITICAL: META ACCESS TOKEN EXPIRED] (Error 190)\n"
                        "Your Meta Temporary Access Token has expired.\n"
                        "To fix: Go to https://developers.facebook.com -> Your App -> WhatsApp -> API Setup,\n"
                        "copy the fresh Temporary Access Token, and paste it into META_ACCESS_TOKEN in .env\n"
                    )
                    return ""
                print(f"[META OUTBOUND ERROR] Status {resp.status_code}: {data}")
        except Exception as e:
            print(f"[META OUTBOUND EXCEPTION] {e}")

    # 2. Twilio (Fallback only if Meta is not configured)
    if not (token and phone_id):
        recipient = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
        from_number = (
            TWILIO_WHATSAPP_NUMBER
            if TWILIO_WHATSAPP_NUMBER.startswith("whatsapp:")
            else f"whatsapp:{TWILIO_WHATSAPP_NUMBER}"
        )

        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            client = _get_twilio_client()
            try:
                sent_message = client.messages.create(
                    body=message,
                    from_=from_number,
                    to=recipient,
                )
                print(f"[TWILIO OUTBOUND SENT] SID: {sent_message.sid} | To: {recipient}")
                return str(sent_message.sid)
            except Exception as exc:
                print(f"[TWILIO OUTBOUND ERROR] Failed to send WhatsApp message to {recipient}: {exc}")
                return ""

    return ""


def place_voice_call(to_number: str, twiml_message: str) -> str:
    """Places an emergency voice call using Twilio Voice with a TTS message.

    Args:
        to_number: Recipient phone number.
        twiml_message: Plain text to be spoken via TTS, or a valid TwiML XML string.

    Returns:
        The Twilio call SID, or empty string on failure.
    """
    recipient = to_number.replace("whatsapp:", "").strip()
    caller_id = (
        os.getenv("TWILIO_CALLER_ID")
        or os.getenv("TWILIO_PHONE_NUMBER")
        or TWILIO_WHATSAPP_NUMBER.replace("whatsapp:", "").strip()
    )

    if twiml_message.strip().startswith("<Response>"):
        twiml = twiml_message
    else:
        twiml = f"<Response><Say>{twiml_message}</Say></Response>"

    client = _get_twilio_client()
    try:
        call = client.calls.create(
            to=recipient,
            from_=caller_id,
            twiml=twiml,
        )
        return str(call.sid)
    except Exception as exc:
        print(f"[VOICE CALL ERROR] Failed to place call to {recipient}: {exc}")
        return ""


def send_whatsapp_audio(to_number: str, audio_path: str) -> str:
    """Dispatches outbound audio/voice message via Meta Cloud API.

    Uploads local audio file to Meta Media endpoint and sends as audio message.
    """
    clean_number = to_number.replace("whatsapp:", "").replace("+", "").strip()
    token = get_meta_token()
    phone_id = get_meta_phone_id()

    if not (token and phone_id):
        print("[META AUDIO OUTBOUND] Meta credentials not configured.")
        return ""

    from pathlib import Path
    path = Path(audio_path)
    if not path.exists():
        print(f"[META AUDIO OUTBOUND ERROR] File not found: {audio_path}")
        return ""

    mime = "audio/mpeg" if path.suffix.lower() == ".mp3" else "audio/ogg"

    # 1. Upload audio to Meta Graph API
    media_url = f"https://graph.facebook.com/v21.0/{phone_id}/media"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with open(path, "rb") as f:
            upload_resp = requests.post(
                media_url,
                headers=headers,
                data={"messaging_product": "whatsapp"},
                files={"file": (path.name, f.read(), mime)},
                timeout=20,
            )
        if upload_resp.status_code not in (200, 201):
            print(f"[META AUDIO UPLOAD ERROR] Status {upload_resp.status_code}: {upload_resp.text}")
            return ""

        media_id = upload_resp.json().get("id")
        if not media_id:
            print("[META AUDIO UPLOAD ERROR] No media id returned.")
            return ""

        # 2. Dispatch audio message
        msg_url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
        msg_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_number,
            "type": "audio",
            "audio": {"id": media_id},
        }
        send_resp = requests.post(
            msg_url,
            headers={**headers, "Content-Type": "application/json"},
            json=msg_payload,
            timeout=15,
        )
        data = send_resp.json()
        if send_resp.status_code in (200, 201):
            msg_id = data.get("messages", [{}])[0].get("id", "META_AUDIO_SENT")
            print(f"[META AUDIO OUTBOUND SENT] ID: {msg_id} | To: +{clean_number}")
            return str(msg_id)
        else:
            print(f"[META AUDIO SEND ERROR] Status {send_resp.status_code}: {data}")
            return ""
    except Exception as e:
        print(f"[META AUDIO EXCEPTION] {e}")
        return ""


# Teammate interface alias: maps send_message directly to real WhatsApp Meta API
send_message = send_whatsapp_message
