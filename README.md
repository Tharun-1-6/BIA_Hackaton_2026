# Sahayi (സഹായി)

A Malayalam-first Telegram assistant for seniors and people with disabilities. A member sends a
voice note, photo or text. Sahayi replies calmly, rates how urgent the situation is (1 to 3), and
keeps a connected family member informed. It never calls emergency services: it notifies family,
who decide what to do.

Built at the BIA GenAI Hackathon 2026 ("AI for Inclusive Kerala") by Adithyan RS, V Anantha krishnan
and Tharun Thomas Eapen (Mar Baselios College of Engineering and Technology).

<!-- Add a demo GIF here: ![demo](docs/demo.gif) -->

## Features

- **Voice, text and photos.** Malayalam, English and code-mixed speech.
- **Urgency rating.** Level 1 calm, 2 check in, 3 emergency. Level 3 replies include the emergency number 112.
- **Family link by code.** A member shares a code; family joins with `/family CODE`.
- **Family tools.** Ask about the member's day (answered only from the conversation log), or relay a message with `/tell`.
- **Timestamps** on every alert and message, in IST.
- **Scope guard.** Coding and off-topic requests are refused before and after the model runs.
- **Photo request.** Sahayi asks for a photo when a visible injury is described.

## How it works

```
Telegram -> speech-to-text -> language detection -> image description (2 models + judge)
         -> LLM care agent (urgency + reply) -> guards -> SQLite log -> family alerts
```

| Stage | Choice |
|---|---|
| Malayalam / code-mixed speech | Sarvam `saaras:v3` |
| English speech | Groq `whisper-large-v3` (language pinned to English) |
| Language detection | Script ratio of the Malayalam transcript |
| Image description | Groq Qwen and Gemini in parallel, reconciled by a judge model |
| Care agent | Groq `gpt-oss-120b`, JSON output validated with Pydantic |
| Storage | SQLite (members, family links, activity log, history) |

Design notes:

- Code performs every action. The model can only suggest a reply and an urgency level, and is
  told never to claim it sent or relayed anything.
- Two vision models plus a judge reduce the chance of one model misdescribing an injury. Results
  are labelled verified, single-model or failed, and the agent treats them as supporting evidence only.
- There is no silent fallback between speech models: an early version mislabelled Malayalam as
  Tamil because of one.

The pipeline is a guarded sequence with one LLM decision step and a multi-model verifier. It is
not a fully autonomous agent.

## Setup

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
copy .env.example .env    # then fill in the keys
```

Run the Telegram bot:

```powershell
uv run python -m bia_hackaton_2026.telegram.bot
```

Run the Streamlit test console (audio, image and agent testing without Telegram):

```powershell
uv run streamlit run src/bia_hackaton_2026/stt/app.py
```

### Commands

Members: `/start`, `/code`, `/newcode`, `/help`.
Family: `/family CODE`, `/status`, `/ask`, `/tell`, `/stopfamily`, `/help`.

## Limitations

- Urgency is decided by the model under prompt rules. It is not guaranteed, and there is no
  deterministic safety layer yet.
- Speech-to-text and image descriptions can be wrong; neither has been formally evaluated.
- Replies are in English. Malayalam replies are not implemented.
- Not a medical device and not a replacement for emergency services.

## Roadmap

- Member approval for family joins
- Deterministic red-flag safety floor
- Alert acknowledgement and escalation to a second contact
- Daily check-ins
- Malayalam replies
- Test suite and evaluation set
- WhatsApp channel
