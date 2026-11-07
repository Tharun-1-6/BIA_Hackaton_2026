"""Speech-to-Text (STT) interface for Sahayi Voice Processing.

Supports multiple providers with automatic fallback:
1. Groq Whisper (ultra-fast, multilingual Malayalam/English)
2. OpenAI Whisper
"""

import os
from pathlib import Path
from typing import Optional


def transcribe_audio(audio_file_path: str) -> Optional[str]:
    """Transcribes local .ogg or audio file into text.

    Args:
        audio_file_path: Path to the downloaded audio file on disk.

    Returns:
        Transcribed text, or None if transcription is unavailable/fails.
    """
    path = Path(audio_file_path)
    if not path.exists():
        print(f"[STT WARNING] Audio file not found: {audio_file_path}")
        return None

    # 1. Groq Whisper (Primary - blazing fast Malayalam/English STT)
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        try:
            from groq import Groq

            client = Groq(api_key=groq_api_key)
            with open(path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=(path.name, audio_file.read()),
                    model="whisper-large-v3",
                    response_format="text",
                )
            text = str(transcription).strip()
            print(f"[STT GROQ SUCCESS] Transcribed: '{text}'")
            return text
        except Exception as e:
            print(f"[STT GROQ ERROR] {e}")

    # 2. OpenAI Whisper (Fallback)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=openai_api_key)
            with open(path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )
            text = transcription.text.strip()
            print(f"[STT OPENAI SUCCESS] Transcribed: '{text}'")
            return text
        except Exception as e:
            print(f"[STT OPENAI ERROR] {e}")

    print("[STT INFO] No STT API keys (GROQ_API_KEY or OPENAI_API_KEY) configured.")
    return None

