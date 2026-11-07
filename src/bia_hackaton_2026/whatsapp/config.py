import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Meta WhatsApp Cloud API Credentials
META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
META_PHONE_NUMBER_ID: str = os.getenv("META_PHONE_NUMBER_ID", "")
META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "sahayi_token_2026")

# Member / Caregiver Numbers
ELDER_PHONE_NUMBER: str = os.getenv("ELDER_PHONE_NUMBER", "+917012649561")
CAREGIVER_WHATSAPP_NUMBER: str = os.getenv("CAREGIVER_WHATSAPP_NUMBER", "+919746654062")

# Audio Directory
SAHAYI_AUDIO_DIR: str = os.getenv("SAHAYI_AUDIO_DIR", "/tmp/sahayi_audio")

# Twilio Credentials (Fallback)
TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+17372508034")
