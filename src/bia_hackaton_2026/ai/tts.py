"""Text-to-Speech (TTS) module for Sahayi Voice Replies.

Converts AI agent responses (Malayalam or English) into voice notes
using gTTS and saves them for WhatsApp audio delivery.
"""
import re
import uuid
from pathlib import Path
from typing import Optional
from gtts import gTTS

from bia_hackaton_2026.whatsapp.config import SAHAYI_AUDIO_DIR


def contains_malayalam(text: str) -> bool:
    """Checks if text contains Malayalam characters."""
    return any("\u0D00" <= c <= "\u0D7F" for c in text)


def synthesize_speech(
    text: str,
    output_filename: Optional[str] = None,
) -> Optional[str]:
    """Generates audio file (.mp3) from text in Malayalam or English.

    Args:
        text: Text to synthesize.
        output_filename: Optional custom filename.

    Returns:
        Path string to generated audio file, or None on failure.
    """
    if not text or not text.strip():
        return None

    # Clean emojis, markdown asterisks, URLs, and bracketed text for smooth speech
    clean_text = re.sub(r"[*_~#`]", "", text)
    clean_text = re.sub(r"https?://\S+", "", clean_text)
    clean_text = re.sub(r"\[.*?\]", "", clean_text)
    clean_text = clean_text.strip()
    if not clean_text:
        return None

    # Detect language: Malayalam vs English
    lang = "ml" if contains_malayalam(clean_text) else "en"

    out_dir = Path(SAHAYI_AUDIO_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not output_filename:
        output_filename = f"reply_{uuid.uuid4().hex[:8]}.mp3"

    out_path = out_dir / output_filename
    try:
        tts = gTTS(text=clean_text, lang=lang, slow=False)
        tts.save(str(out_path))
        print(f"[TTS GENERATED] Lang: {lang} | Path: {out_path}")
        return str(out_path)
    except Exception as e:
        print(f"[TTS ERROR] Failed to synthesize speech: {e}")
        return None
