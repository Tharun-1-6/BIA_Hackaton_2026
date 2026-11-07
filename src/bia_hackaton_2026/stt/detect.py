"""Language identification for voice messages: English / Malayalam / code-mix.

Approach: transcribe once with Sarvam (codemix mode, handles ml, en and mixed), then classify by
script of the transcript. Whisper's own language detection is not used because it confuses
Malayalam with Tamil. English results are re-transcribed with Groq Whisper (language pinned)."""
import time

from .transcribe import transcribe_audio

MODELS = {"sarvam": "saaras:v3", "groq": "whisper-large-v3"}


def timed_step(label, mode, file_bytes, filename, lang, sarvam_key, groq_key):
    """Run one STT call; return (text, provider, error, trace_row)."""
    t0 = time.perf_counter()
    text, provider, err = transcribe_audio(file_bytes, filename, lang, sarvam_key, groq_key)
    row = {"step": label, "provider": provider, "model": MODELS.get(provider, "-"), "mode": mode,
           "seconds": round(time.perf_counter() - t0, 2), "chars": len(text), "ok": bool(text), "error": err}
    return text, provider, err, row

ML_MIN_SHARE = 0.05   # below this share of Malayalam letters -> English
EN_MIN_SHARE = 0.10   # below this share of Latin letters -> Malayalam


def classify_text(text: str) -> tuple[str, float]:
    """Return ('en' | 'ml' | 'ml-mix', malayalam_share) from the script mix of `text`."""
    ml = sum('ഀ' <= c <= 'ൿ' for c in text)
    latin = sum(c.isascii() and c.isalpha() for c in text)
    total = ml + latin
    if total == 0:
        return "unknown", 0.0
    ml_share = ml / total
    if ml_share < ML_MIN_SHARE:
        return "en", ml_share
    if 1 - ml_share < EN_MIN_SHARE:
        return "ml", ml_share
    return "ml-mix", ml_share


def detect_and_transcribe(file_bytes, filename, sarvam_key=None, groq_key=None):
    """Returns dict: text, language, provider, ml_share, error, trace (list of step rows), first_pass."""
    trace = []
    text, provider, err, row = timed_step("1. detect + transcribe", "codemix", file_bytes, filename, "ml-mix", sarvam_key, groq_key)
    trace.append(row)
    if not text:
        return {"text": "", "language": "unknown", "provider": provider, "ml_share": 0.0, "error": err,
                "trace": trace, "first_pass": ""}
    first_pass = text
    lang, share = classify_text(text)
    if lang == "en":
        en_text, en_provider, _, row = timed_step("2. English re-transcribe", "language=en", file_bytes, filename, "en", sarvam_key, groq_key)
        trace.append(row)
        if en_text:
            text, provider = en_text, en_provider
    return {"text": text, "language": lang, "provider": provider, "ml_share": share, "error": "",
            "trace": trace, "first_pass": first_pass}
