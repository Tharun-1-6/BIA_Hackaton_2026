# 🤝 Sahayi Developer & Teammate Integration Guide

This guide explains how to connect your AI, LLM, or Voice agents with the live Sahayi WhatsApp & Emergency SOS pipeline.

---

## 🚀 1. The Core Developer Tools (`service.orchestrator`)

Import the tools directly in your scripts or agents:

```python
from bia_hackaton_2026.service.orchestrator import (
    trigger_sos_escalation,
    send_proactive_notification,
    process_inbound_text,
    process_inbound_voice,
)
```

### A. Trigger Emergency SOS from Anywhere
Call this function whenever your AI agent, fall detection sensor, or health monitor detects an emergency:

```python
result = trigger_sos_escalation(
    elder_phone="+917012649561",
    trigger_source="AI_VOICE_AGENT",
    summary="Senior reported acute chest pain and dizziness in voice call"
)
```
**What happens automatically:**
1. Dispatches the high-priority `🚨 SAHAYI EMERGENCY ALERT` to the Caregiver (`+917736246747`).
2. Sends a calming, bilingual reassurance to the Elder (`+917012649561`) confirming help is on the way.

---

### B. Send Proactive Notifications (e.g. Medicine Reminders)
```python
send_proactive_notification(
    to_phone="+917012649561",
    message="Sahayi: നമസ്കാരം! ഉച്ചയ്ക്കുള്ള പ്രഷറിന്റെ മരുന്ന് കഴിക്കാൻ സമയമായി. (Reminder to take afternoon medication.)"
)
```

---

## 🎙️ 2. Connecting Voice (STT) and LLMs

The pipeline supports modular AI backends in `src/bia_hackaton_2026/ai/`:

- **STT (Speech-to-Text)**: [`src/bia_hackaton_2026/ai/stt.py`](src/bia_hackaton_2026/ai/stt.py)
  - Supports **Groq Whisper** (`GROQ_API_KEY`) for ultra-fast Malayalam/English transcription.
  - Supports **OpenAI Whisper** (`OPENAI_API_KEY`).
- **Care Agent & Intent Detection**: [`src/bia_hackaton_2026/ai/agent.py`](src/bia_hackaton_2026/ai/agent.py)
  - Evaluates conversational text in Malayalam/English.
  - Automatically identifies medical emergencies (even if the senior doesn't explicitly type "SOS").
  - Supports **Google Gemini** (`GEMINI_API_KEY`), **Groq Llama 3** (`GROQ_API_KEY`), or **OpenAI** (`OPENAI_API_KEY`).

---

## 🧪 3. Local Testing & Verification

1. **Run Unit Tests:**
   ```bash
   uv run pytest src/bia_hackaton_2026/tests/
   ```

2. **Simulate an SOS Message Locally:**
   ```bash
   uv run python test_sos_simulation.py
   ```

3. **Start the Live Backend Server:**
   ```bash
   uv run uvicorn bia_hackaton_2026.main:app --reload --port 8000
   ```

