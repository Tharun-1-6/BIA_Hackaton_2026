import os
from dotenv import load_dotenv

# Load environment variables from .env file with override enabled
load_dotenv(override=True)


def get_meta_token() -> str:
    """Dynamically reads the latest META_ACCESS_TOKEN from environment."""
    load_dotenv(override=True)
    return os.getenv("META_ACCESS_TOKEN", "").strip()


def get_meta_phone_id() -> str:
    """Dynamically reads the latest META_PHONE_NUMBER_ID from environment."""
    return os.getenv("META_PHONE_NUMBER_ID", "").strip()


# Meta WhatsApp Cloud API Credentials
META_ACCESS_TOKEN: str = get_meta_token()
META_PHONE_NUMBER_ID: str = get_meta_phone_id()
META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "sahayi_token_2026")

# Member / Caregiver Numbers
ELDER_PHONE_NUMBER: str = os.getenv("ELDER_PHONE_NUMBER", "+917012649561")
CAREGIVER_WHATSAPP_NUMBER: str = os.getenv("CAREGIVER_WHATSAPP_NUMBER", "+917736246747")

# Audio Directory for saving voice messages
SAHAYI_AUDIO_DIR: str = os.getenv("SAHAYI_AUDIO_DIR", "data/saved_audio")

# Twilio Credentials (Fallback)
TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+17372508034")
