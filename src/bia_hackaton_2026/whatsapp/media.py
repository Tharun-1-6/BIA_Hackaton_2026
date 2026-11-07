import os
import requests
from bia_hackaton_2026.whatsapp.config import (
    META_ACCESS_TOKEN,
    SAHAYI_AUDIO_DIR,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
)


def download_audio_media(media_url: str, message_sid: str) -> str:
    """Download incoming WhatsApp audio (.ogg) from Twilio media storage.

    Args:
        media_url: The Twilio media URL.
        message_sid: The unique message SID for naming the saved file.

    Returns:
        The local absolute file path to the saved .ogg audio file.
    """
    os.makedirs(SAHAYI_AUDIO_DIR, exist_ok=True)
    target_path = os.path.abspath(os.path.join(SAHAYI_AUDIO_DIR, f"{message_sid}.ogg"))

    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN) else None

    response = requests.get(media_url, auth=auth, stream=True, timeout=30)
    response.raise_for_status()

    with open(target_path, "wb") as audio_file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                audio_file.write(chunk)

    return target_path


def download_meta_audio(media_id: str) -> str:
    """Downloads incoming WhatsApp voice note from Meta Cloud API using media ID.

    Args:
        media_id: The WhatsApp media ID provided in Meta's webhook payload.

    Returns:
        The local absolute file path to the saved .ogg audio file.
    """
    os.makedirs(SAHAYI_AUDIO_DIR, exist_ok=True)
    target_path = os.path.abspath(os.path.join(SAHAYI_AUDIO_DIR, f"{media_id}.ogg"))

    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}

    # Step 1: Query Meta Graph API for media URL
    media_info_url = f"https://graph.facebook.com/v21.0/{media_id}"
    res = requests.get(media_info_url, headers=headers, timeout=15)
    res.raise_for_status()
    download_url = res.json().get("url")

    if not download_url:
        raise ValueError(f"Could not retrieve download URL for Meta media ID {media_id}")

    # Step 2: Download the binary audio stream
    audio_res = requests.get(download_url, headers=headers, stream=True, timeout=30)
    audio_res.raise_for_status()

    with open(target_path, "wb") as audio_file:
        for chunk in audio_res.iter_content(chunk_size=8192):
            if chunk:
                audio_file.write(chunk)

    return target_path
