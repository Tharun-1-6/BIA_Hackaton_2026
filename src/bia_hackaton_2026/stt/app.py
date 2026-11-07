import hashlib
import os

import streamlit as st
from dotenv import load_dotenv

from bia_hackaton_2026.agent import run_turn
from bia_hackaton_2026.llm.response import MODELS as LLM_MODELS
from bia_hackaton_2026.vlm import build_agent_input, describe_verified
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
st.session_state.setdefault("img_gen", 0)
st.session_state.setdefault("agent_history", [])
st.session_state.setdefault("agent_turns", [])
st.session_state.setdefault("img_result", None)
gen = st.session_state.widget_gen


def clear_audio():
    """Delete the current audio and its result so a new one can be added."""
    st.session_state.widget_gen += 1
    st.session_state.result = None


def clear_image():
    """Delete the current image and its description so a new one can be added."""
    st.session_state.img_gen += 1
    st.session_state.img_result = None


with st.sidebar:
    st.header("API keys")
    groq_key = st.text_input("Groq API key", value=os.environ.get("GROQ_API_KEY", ""), type="password")
    gemini_key = st.text_input("Gemini API key (image cross-check)", value=os.environ.get("GEMINI_API_KEY", ""), type="password")
    sarvam_key = st.text_input("Sarvam API key", value=os.environ.get("SARVAM_AI", ""), type="password")
    llm_model = st.selectbox("Agent LLM (Groq)", LLM_MODELS)
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

st.divider()
st.subheader("🖼️ Image (optional)")
img_up = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png", "webp"], key=f"img_up_{st.session_state.img_gen}")
img_cam = st.camera_input("…or take a photo", key=f"img_cam_{st.session_state.img_gen}")
image = img_up or img_cam
if image:
    st.image(image, width=300)
typed_text = st.text_input("Extra text to send with the image (optional)")

def run_vlm(img, digest):
    with st.spinner("Analysing image with two models and a judge…"):
        st.session_state.img_result = describe_verified(
            img.getvalue(), img.type or "image/jpeg", groq_key, gemini_key
        ) | {"fname": img.name or "photo", "size_kb": round(len(img.getvalue()) / 1024, 1), "digest": digest}


i1, i2 = st.columns(2)
redo = i1.button("Re-describe image", disabled=image is None, use_container_width=True)
i2.button("🗑️ Delete image / new image", on_click=clear_image, disabled=image is None, use_container_width=True)

# Auto-describe: runs as soon as a new image appears (or on re-describe), no button needed
if image is not None:
    digest = hashlib.md5(image.getvalue()).hexdigest()
    cur = st.session_state.img_result
    if redo or cur is None or cur.get("digest") != digest:
        run_vlm(image, digest)

ir = st.session_state.img_result
if ir:
    if ir["description"]:
        if ir["status"] == "verified":
            badge = {"high": "✅ Models agree", "partial": "🟡 Minor differences", "low": "🔴 Models disagree"}.get(
                ir["agreement"], "Checked")
            st.success(f"{badge} · final description chosen by judge ({ir['judge_model']}) · {ir['seconds']} s · "
                       f"{ir['fname']} ({ir['size_kb']} KB)")
        else:
            st.warning(f"⚠️ Not cross-checked ({ir['status']}). {ir['error']}")
        if ir["needs_human_review"]:
            st.error("A human should look at this image: the models disagree or the image is unclear.")
        st.markdown(ir["description"])
        with st.expander("🔎 Image analysis notes (both models + judge)"):
            st.markdown(
                f"- **Winner:** {ir['winner'] or '-'} · **Agreement:** {ir['agreement'] or '-'}\n"
                f"- **Judge reasoning:** {ir['reasoning'] or '-'}\n"
                f"- **Discrepancies:** {'; '.join(ir['discrepancies']) if ir['discrepancies'] else 'none'}"
            )
            ca, cb = st.columns(2)
            for col, key, title in ((ca, "a", "Model A"), (cb, "b", "Model B")):
                r = ir[key]
                col.markdown(f"**{title}: {r['model']}** · {r['seconds']} s")
                col.markdown(r["description"] or f"_failed: {r['error']}_")
    else:
        st.error(ir["error"])

st.divider()
st.subheader("📨 Combined message for the LLM agent")
transcript = res["text"] if res and res["text"] else ""
user_text = "\n".join(t for t in (transcript, typed_text.strip()) if t)
combined = build_agent_input(user_text, ir["description"] if ir else "")
if combined:
    st.code(combined, language=None)
    st.caption(
        f"Sources used: voice transcript = {'yes' if transcript else 'no'} · "
        f"typed text = {'yes' if typed_text.strip() else 'no'} · "
        f"image description = {'yes' if ir and ir['description'] else 'no'}"
    )
else:
    st.caption("Transcribe audio and/or describe an image to build the message.")

st.divider()
st.subheader("🤖 Sahayi agent")
st.caption("Sends the combined message above to the LLM; shows the reply to the user and the alert for family.")
a1, a2 = st.columns(2)
if a1.button("Send to Sahayi", type="primary", disabled=not combined, use_container_width=True):
    with st.spinner("Sahayi is thinking…"):
        out = run_turn(combined, st.session_state.agent_history, llm_model, groq_key)
    st.session_state.agent_turns.insert(0, {"input": combined, **out})
if a2.button("Reset conversation", disabled=not st.session_state.agent_turns, use_container_width=True):
    st.session_state.agent_history = []
    st.session_state.agent_turns = []
    st.rerun()

for n, t in enumerate(st.session_state.agent_turns):
    turn = t["turn"]
    with st.container(border=True):
        if t["fallback"]:
            st.error(t["error"] or "Model output was invalid twice - fallback reply used.")
        st.markdown("**Reply to the user**")
        st.info(t["user_message"])
        lvl = turn.family.suggested_level
        st.markdown(f"**Family alert** - level {lvl} - {'SENT' if t['family_sent'] else 'not sent'}")
        (st.error if lvl == 3 else st.warning if lvl == 2 else st.success)(t["family_message"])
        st.caption(
            f"Model: {t['model']} - {t['seconds']} s - attempts: {t['attempts']} - "
            f"{'FALLBACK used' if t['fallback'] else 'valid JSON'} - turn {len(st.session_state.agent_turns) - n}"
        )
        with st.expander("Input sent to the LLM / raw output"):
            st.code(t["input"], language=None)
            st.code(t["raw"] or "(none)", language="json")

if st.session_state.history:
    st.subheader("History")
    for i, h in enumerate(st.session_state.history):
        with st.expander(f"{h['name']} · {h['lang']} · {h['provider']}"):
            st.write(h["text"])
            if st.button("Delete this entry", key=f"del_{i}"):
                st.session_state.history.pop(i)
                st.rerun()
