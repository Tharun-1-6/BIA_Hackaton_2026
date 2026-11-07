from typing import Dict


def mock_text_payload(
    body: str = "Hello",
    sender: str = "whatsapp:+919876543210",
    message_sid: str = "SM1234567890abcdef",
) -> Dict[str, str]:
    """Helper mimicking Twilio incoming WhatsApp text message webhook POST form payload."""
    return {
        "From": sender,
        "Body": body,
        "NumMedia": "0",
        "MessageSid": message_sid,
    }


def mock_audio_payload(
    sender: str = "whatsapp:+919876543210",
    media_url: str = "https://api.twilio.com/2010-04-01/Accounts/ACmock/Messages/MMmock/Media/MEmock",
    content_type: str = "audio/ogg",
    message_sid: str = "MM1234567890abcdef",
    body: str = "",
) -> Dict[str, str]:
    """Helper mimicking Twilio incoming WhatsApp audio note webhook POST form payload."""
    return {
        "From": sender,
        "Body": body,
        "NumMedia": "1",
        "MediaUrl0": media_url,
        "MediaContentType0": content_type,
        "MessageSid": message_sid,
    }

