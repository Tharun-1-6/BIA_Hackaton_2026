import os

import streamlit as st
from dotenv import load_dotenv

from bia_hackaton_2026.stt.detect import MODELS, classify_text, detect_and_transcribe, timed_step

load_dotenv()
st.set_page_config(page_title="Sahayi STT", page_icon="🎙️")
st.title("🎙️ Sahayi – Speech to Text")
st.caption("English → Groq Whisper · Malayalam → Sarvam AI")

LANGS = {
    "Auto-detect": "auto",
    "English": "en",
    "Malayalam": "ml",
    "Malayalam + English (code-mix)": "ml-mix",
}
MODES = {"en": "language=en", "ml": "transcribe", "ml-mix": "codemix"}

# widget_gen is bumped to reset (delete) the audio widgets; history keeps past results
st.session_state.setdefault("widget_gen", 0)
st.session_state.setdefault("history", [])
st.session_state.setdefault("result", None)
gen = st.session_state.widget_gen


def clear_audio():
    """Delete the current audio and its result so a new one can be added."""
    st.session_state.widget_gen += 1
    st.session_state.result = None


with st.sidebar:
    st.header("API keys")
    groq_key = st.text_input("Groq API key", value=os.environ.get("GROQ_API_KEY", ""), type="password")
    sarvam_key = st.text_input("Sarvam API key", value=os.environ.get("SARVAM_AI", ""), type="password")
    st.divider()
    if st.button("Clear history", disabled=not st.session_state.history):
        st.session_state.history = []
        st.rerun()

lang_label = st.selectbox("Language", list(LANGS))

st.subheader("Audio")
recorded = st.audio_input("Record a voice message", key=f"rec_{gen}")
uploaded = st.file_uploader(
    "…or upload a file",
    type=["wav", "mp3", "m4a", "ogg", "opus", "webm", "flac"],
    key=f"up_{gen}",
)
audio = uploaded or recorded
if audio:
    st.audio(audio)

c1, c2 = st.columns(2)
if c1.button("Transcribe", type="primary", disabled=audio is None, use_container_width=True):
    data = audio.getvalue()
    name = audio.name or "audio.wav"
    with st.spinner("Transcribing…"):
        if LANGS[lang_label] == "auto":
            r = detect_and_transcribe(data, name, sarvam_key, groq_key)
            text, provider, error = r["text"], r["provider"], r["error"]
            detected, trace, first_pass, share = r["language"], r["trace"], r["first_pass"], r["ml_share"]
        else:
            code = LANGS[lang_label]
            text, provider, error, row = timed_step("1. manual", MODES[code], data, name, code, sarvam_key, groq_key)
            detected, trace, first_pass = f"{code} (manual)", [row], ""
            share = classify_text(text)[1] if text else 0.0
    st.session_state.result = {
        "text": text, "provider": provider, "error": error, "detected": detected,
        "trace": trace, "first_pass": first_pass, "share": share, "selected": lang_label,
        "size_kb": round(len(data) / 1024, 1), "fname": name,
    }
    if text:
        st.session_state.history.insert(
            0, {"name": name, "lang": detected, "provider": provider, "text": text}
        )
c2.button("🗑️ Delete audio / new audio", on_click=clear_audio, disabled=audio is None, use_container_width=True)

res = st.session_state.result
if res:
    if res["text"]:
        st.success(f"Language: {res['detected']} · Provider used: {res['provider']}")
        st.text_area("Transcript", res["text"], height=150)
    else:
        st.error(res.get("error") or "Transcription failed.")

    with st.expander("🔎 Analysis notes", expanded=True):
        st.markdown(
            f"- **Selected mode:** {res['selected']}\n"
            f"- **Detected language:** {res['detected']} (Malayalam-letter share: {res['share']:.0%})\n"
            f"- **Final provider / model:** {res['provider']} / {MODELS.get(res['provider'], '-')}\n"
            f"- **Audio:** {res['fname']} ({res['size_kb']} KB)"
        )
        st.caption("Pipeline steps (each row is one STT API call):")
        st.dataframe(res["trace"], use_container_width=True, hide_index=True)
        if res["first_pass"] and res["first_pass"] != res["text"]:
            st.caption("First-pass (Sarvam code-mix) transcript, replaced by the English re-run:")
            st.code(res["first_pass"], language=None)
        if res["error"]:
            st.warning(res["error"])

if st.session_state.history:
    st.subheader("History")
    for i, h in enumerate(st.session_state.history):
        with st.expander(f"{h['name']} · {h['lang']} · {h['provider']}"):
            st.write(h["text"])
            if st.button("Delete this entry", key=f"del_{i}"):
                st.session_state.history.pop(i)
                st.rerun()
