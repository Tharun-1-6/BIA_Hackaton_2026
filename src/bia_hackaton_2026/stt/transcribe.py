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
    """language: 'en' -> Groq Whisper, 'ml' -> Sarvam transcribe, 'ml-mix' -> Sarvam codemix.
    Returns (text, provider, error). No cross-language fallback: Malayalam is never sent
    to Whisper (it auto-detects and often mislabels Malayalam as Tamil)."""
    if language in ("ml", "ml-mix"):
        sarvam_key = sarvam_key or os.environ.get("SARVAM_AI")
        if not sarvam_key:
            return "", "none", "Sarvam API key missing (set SARVAM_AI in .env or the sidebar)."
        mode = "codemix" if language == "ml-mix" else "transcribe"
        try:
            r = requests.post(
                SARVAM_URL,
                headers={"api-subscription-key": sarvam_key.strip()},
                files={"file": (filename, file_bytes, guess_mime(filename))},
                data={"model": "saaras:v3", "mode": mode, "language_code": "ml-IN"},
                timeout=30,
            )
        except Exception as e:
            return "", "sarvam", f"Sarvam request failed: {e}"
        if r.status_code != 200:
            return "", "sarvam", f"Sarvam returned {r.status_code}: {r.text[:300]}"
        text = r.json().get("transcript", "").strip()
        if not text:
            return "", "sarvam", "Sarvam returned an empty transcript."
        return text, "sarvam", ""

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
