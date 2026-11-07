"""STT helpers ported from MBAssist-AI speech.py (Sarvam for Malayalam, Groq Whisper for English)."""
import io
import os

import requests
from groq import Groq

SARVAM_URL = "https://api.sarvam.ai/speech-to-text"

MIME_BY_EXT = {
    "wav": "audio/wav", "mp3": "audio/mpeg", "aac": "audio/aac", "m4a": "audio/mp4",
    "ogg": "audio/ogg", "opus": "audio/ogg", "webm": "audio/webm", "flac": "audio/flac",
    "aiff": "audio/aiff",
}


def guess_mime(filename: str) -> str:
    return MIME_BY_EXT.get(filename.rsplit(".", 1)[-1].lower(), "audio/wav")


def transcribe_audio(
    file_bytes: bytes,
    filename: str = "audio.wav",
    language: str = "en",
    sarvam_key: str | None = None,
    groq_key: str | None = None,
) -> tuple[str, str, str]:
    """Transcribes audio using Sarvam (if available) or Groq Whisper (ultra-fast multilingual).
    Returns (text, provider, error).
    """
    from dotenv import load_dotenv
    load_dotenv(override=True)

    if language in ("ml", "ml-mix"):
        sarvam_key = sarvam_key or os.environ.get("SARVAM_AI")
        if sarvam_key:
            mode = "codemix" if language == "ml-mix" else "transcribe"
            try:
                r = requests.post(
                    SARVAM_URL,
                    headers={"api-subscription-key": sarvam_key.strip()},
                    files={"file": (filename, file_bytes, guess_mime(filename))},
                    data={"model": "saaras:v3", "mode": mode, "language_code": "ml-IN"},
                    timeout=30,
                )
                if r.status_code == 200:
                    text = r.json().get("transcript", "").strip()
                    if text:
                        return text, "sarvam", ""
            except Exception as e:
                print(f"[SARVAM STT ERROR] {e}")

        # High-accuracy Groq Whisper fallback with Malayalam prompt conditioning
        groq_key = groq_key or os.environ.get("GROQ_API_KEY")
        if not groq_key:
            return "", "none", "STT API key missing (set GROQ_API_KEY or SARVAM_AI in .env)."
        try:
            buf = io.BytesIO(file_bytes)
            buf.name = filename
            t = Groq(api_key=groq_key.strip()).audio.transcriptions.create(
                file=(filename, buf),
                model="whisper-large-v3",
                prompt="Malayalam and English speech from an elderly person: സുഖമാണോ, എനിക്ക് സുഖമില്ല, തലകറക്കം, നെഞ്ചുവേദന, വീണു, വേദന, സഹായം, പനി, മരുന്ന്, Sahayi",
                response_format="json",
            )
            return t.text.strip(), "groq", ""
        except Exception as e:
            return "", "groq", f"Groq Whisper fallback failed: {e}"

    groq_key = groq_key or os.environ.get("GROQ_API_KEY")
    if not groq_key:
        return "", "none", "Groq API key missing (set GROQ_API_KEY in .env or the sidebar)."
    try:
        buf = io.BytesIO(file_bytes)
        buf.name = filename
        t = Groq(api_key=groq_key.strip()).audio.transcriptions.create(
            file=(filename, buf), model="whisper-large-v3", language="en", response_format="json"
        )
        return t.text.strip(), "groq", ""
    except Exception as e:
        return "", "groq", f"Groq Whisper failed: {e}"
