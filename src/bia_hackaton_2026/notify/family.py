"""Deliver Sahayi family alerts to family members on WhatsApp (Meta Cloud API).

Same Graph API calls as the WhatsApp teammate's sender (text + template), without the Twilio dependency
and without hardcoded phone numbers: everything comes from .env.

  META_ACCESS_TOKEN, META_PHONE_NUMBER_ID   Meta WhatsApp Cloud API credentials
  FAMILY_WHATSAPP_NUMBERS                   comma-separated, e.g. +919XXXXXXXXX,+918XXXXXXXXX
  META_ALERT_TEMPLATE (optional)            approved template name, used when the 24-hour window is closed
  META_ALERT_TEMPLATE_LANG (optional)       template language code, default "en"

WhatsApp rule: a free-text message is only delivered if the family member messaged the business number in the
last 24 hours. Otherwise Meta rejects it (error 131047) and only an approved template can be sent.
"""
import os
import time

import requests

GRAPH_URL = "https://graph.facebook.com/v21.0/{phone_id}/messages"
WINDOW_CLOSED = 131047          # Meta error: outside the 24-hour customer-service window
COOLDOWN_SECONDS = 600          # do not repeat the same-or-lower level alert for a chat within 10 minutes

_LAST_ALERT: dict[str, tuple[int, float]] = {}   # chat_id -> (level, timestamp)


def family_numbers() -> list[str]:
    raw = os.environ.get("FAMILY_WHATSAPP_NUMBERS", "")
    return [n for n in ("".join(c for c in x if c.isdigit()) for x in raw.split(",")) if n]


def _post(payload: dict) -> tuple[bool, str, int | None]:
    """Returns (ok, message_id_or_error_text, meta_error_code)."""
    token = os.environ.get("META_ACCESS_TOKEN", "").strip()
    phone_id = os.environ.get("META_PHONE_NUMBER_ID", "").strip()
    if not token or not phone_id:
        return False, "META_ACCESS_TOKEN / META_PHONE_NUMBER_ID not configured", None
    try:
        r = requests.post(
            GRAPH_URL.format(phone_id=phone_id),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload, timeout=15,
        )
        data = r.json()
    except Exception as e:
        return False, f"request failed: {e}", None
    if r.status_code in (200, 201):
        return True, (data.get("messages") or [{}])[0].get("id", "sent"), None
    err = data.get("error", {})
    return False, err.get("message", str(data))[:200], err.get("code")


def send_text(to: str, body: str) -> tuple[bool, str, int | None]:
    return _post({"messaging_product": "whatsapp", "recipient_type": "individual", "to": to,
                  "type": "text", "text": {"preview_url": False, "body": body}})


def send_template(to: str, name: str, lang: str, param: str) -> tuple[bool, str, int | None]:
    # template parameters may not contain newlines
    param = " | ".join(p.strip() for p in param.splitlines() if p.strip())[:900]
    return _post({"messaging_product": "whatsapp", "recipient_type": "individual", "to": to, "type": "template",
                  "template": {"name": name, "language": {"code": lang},
                               "components": [{"type": "body", "parameters": [{"type": "text", "text": param}]}]}})


def notify_family(chat_id, elder_name: str, alert_text: str, level: int) -> dict:
    """Send the alert to every configured family number. Returns dict:
    delivered (list of numbers), failed (dict number -> reason), skipped (reason or ''), configured (bool)."""
    chat_id = str(chat_id)
    out = {"delivered": [], "failed": {}, "skipped": "", "configured": False}
    numbers = family_numbers()
    if not numbers:
        out["failed"]["-"] = "FAMILY_WHATSAPP_NUMBERS not set"
        return out
    out["configured"] = True

    last = _LAST_ALERT.get(chat_id)
    if last and level <= last[0] and time.time() - last[1] < COOLDOWN_SECONDS:
        out["skipped"] = "an alert of the same or higher level was already sent in the last 10 minutes"
        out["delivered"] = ["(earlier alert)"]
        return out

    body = (f"{alert_text}\n\n*Member:* {elder_name} (via Sahayi on Telegram)\n"
            "Please check on them now. If it is an emergency, call 112 yourself.")
    template = os.environ.get("META_ALERT_TEMPLATE", "").strip()
    lang = os.environ.get("META_ALERT_TEMPLATE_LANG", "en").strip() or "en"

    for n in numbers:
        ok, info, code = send_text(n, body)
        if not ok and code == WINDOW_CLOSED and template:
            ok, info, code = send_template(n, template, lang, f"{elder_name}: {alert_text}")
        if ok:
            out["delivered"].append(n)
        else:
            reason = info
            if code == WINDOW_CLOSED:
                reason = ("24-hour window closed: this person must send a message to the Sahayi WhatsApp number "
                          "first, or META_ALERT_TEMPLATE must be set. " + info)
            out["failed"][n] = reason

    if out["delivered"]:
        _LAST_ALERT[chat_id] = (level, time.time())
    return out
