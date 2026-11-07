# Sahayi Specification Review

Review of `Sahayi_Complete_WhatsApp_Voice_Assistant_Specification.pdf` (8 pages).
Facts about external APIs (Sarvam, Meta, Groq) were not checked against live docs and must be verified before building.

## 1. Overall assessment

The spec is unusually honest for a hackathon document. It does not pretend WhatsApp can call 112, it keeps the LLM away from the dispatch decision, it plans for consent and data minimisation, and it labels demo data as synthetic. Keep all of that.

Its weaknesses are technical:
- The language-routing design is circular.
- It omits the timing and fallback behaviour that make an SOS system work.
- It splits the agent into more modules than a 4-hour build can support.
- It has no TTS, despite being a "voice assistant".
- Things the cover promises (user journeys, data model) are missing.

## 2. Critical review

### Design flaws (most important first)

| # | Issue | Why it matters | Spec ref |
|---|---|---|---|
| 1 | Language detection before STT is circular: you must know the language to pick the STT provider, but the audio is untranscribed. Whisper's Malayalam accuracy is also generally weak. | A wrong route yields garbage that looks like a transcript. The "uncertain/mixed" row has no workable mechanism. | 3.2 |
| 2 | No timers. "If the user cannot respond, follow the safety protocol" never says who notices silence. | A fallen senior who does not answer "Are you alone?" is the most likely real emergency. | 5 |
| 3 | STT is least reliable exactly when it matters (slurred speech, pain, noise). | Transcript-only triage will miss real emergencies. Unintelligible audio from a registered senior should raise the level. | 3, 4 |
| 4 | WhatsApp is the only alert channel, with no delivery guarantee and no caregiver acknowledgement. | "Informed" is not "responding". Needs ack, timeout, next contact or another channel. | 5, 6 |
| 5 | The 24-hour messaging window is ignored. Business-initiated messages to caregivers need pre-approved templates unless they messaged the bot in the last 24h (confirm in Meta docs). | Caregivers who have not messaged the bot get nothing. Likely demo-breaker. | 5 |
| 6 | Free-tier hosting (Render) sleeps. | Webhook timeouts, retries and duplicates. | 11 |
| 7 | The senior cannot trigger SOS directly. | Add a keyword ("സഹായം", "help") and a quick-reply button handled deterministically. | 5, 6 |
| 8 | Level 0 notification on every conversation is noisy. | Caregivers will mute it. Make it a configurable digest. | 5 |

### Over-complexity

- Section 9 lists question_planner, problem_analyzer, urgency_classifier and message_generator separately. Use one structured-output LLM call plus a deterministic rules module.
- `/api/conversations/{id}/process` should be an internal function, not an endpoint.
- `/raise-sos` and `/member-sos` can be one endpoint with a source field.
- RAG and vector stores are correctly absent; do not add them.

### Missing requirements

- Data model (promised on the cover).
- User journeys (promised on the cover).
- Voice replies (TTS) for seniors with low literacy or vision.
- Live location via WhatsApp location pins, not only a preset address.
- Onboarding and consent capture, including revocation.
- Dashboard authentication (Supabase Auth with row-level security).
- Session model: when a conversation ends and a new incident begins.
- Rate limits and abuse protection.
- Observability.
- Regulatory: India's DPDP Act 2023 (sensitive data, guardian consent for persons with disabilities); confirm with counsel. Also check Meta's current rules for AI chatbots on WhatsApp Business; a task-specific bot should be fine, but verify.

### Already well designed

- Honest 112 handling and the "do not fake dispatch" rule (6.3).
- Deterministic policy over LLM judgment for calling (6.4).
- Minimum necessary data in alerts (7).
- Idempotency and audit trail (12).
- Separation of transcript facts, profile facts and AI inference (12).
- MVP prioritisation (13) and the 3-minute demo script (14).

## 3. Suggested improvements

### Must add (high value, low cost)

1. Replace the language router with one Sarvam STT call (Malayalam, English, code-mixed, auto-detect). Keep Groq Whisper only as a failure fallback. Check Sarvam's audio length limit (REST was about 30 s as I recall).
2. Add a deterministic safety layer in parallel with the LLM: keyword/pattern rules in Malayalam, Manglish and English. Levels only go up during an incident. Two unintelligible audios in a row, or no reply within N minutes, escalates.
3. Add caregiver acknowledgement ("I'm on it" button) and an escalation chain. No ack within T seconds notifies the next contact. Final fallback: automated outbound voice call or SMS to the caregiver (Exotel, Twilio, etc.). This never touches 112.
4. Forward the original voice note to caregivers at Level 2 and 3 (with consent).
5. Add TTS replies as short Malayalam OGG/Opus voice notes, with text as fallback.
6. Accept WhatsApp location pins as current location; fall back to the preset address with its verified date.
7. Caregiver onboarding via a "join <code>" message. It opens the 24h window, proves the number and records opt-in. Submit utility templates (with a phone-number button for 112) early.

### Simplify or remove for the MVP

- Collapse the agent modules into one LLM call.
- Level 0 opt-in, off by default for the demo.
- Dashboard lowest priority: seeded data plus a read-only page.

### Later

- Daily check-ins and missed-check-in alerts (likely the most valuable post-MVP feature).
- Medication reminders, more languages, emergency-service integration after formal approval.

## 4. Recommended stack

| Layer | Pick | Why | Alternatives / limits |
|---|---|---|---|
| Messaging | Meta WhatsApp Cloud API | Direct, no BSP markup; spec choice. | Twilio is easier but costs more. Test number allows few pre-verified recipients. |
| Backend | Python 3.12 + FastAPI + httpx (async) | Spec choice; repo already uses uv. | n/a |
| Webhook | Verify `X-Hub-Signature-256` on the raw body, return 200 immediately, process in the background | Meta retries slow webhooks. | Postgres-backed job table for MVP; no Celery or Redis. |
| Timers | `scheduled_actions` table polled every few seconds by an asyncio task | Survives restarts; no extra infra. | `pg_cron` or APScheduler later. Polling is a known shortcut. |
| Audio | ffmpeg (OGG/Opus to/from WAV) | WhatsApp voice notes are OGG/Opus. | Needs a Docker image. |
| STT | Sarvam, one call | Built for Indian languages. | Groq Whisper fallback; Google Chirp. |
| TTS | Sarvam Bulbul (ml-IN) | Same vendor and key. | Azure ml-IN voices, Google TTS. |
| LLM | Gemini Flash-class, plain-text response (JSON requested in the prompt), temperature 0. Pydantic validates it (see 4.1). | Fast, cheap, strong Indic coverage. Works with any provider, no vendor-specific schema mode needed. | Groq Llama is faster but weaker in Malayalam; test Sarvam chat models. Code, not the LLM, chooses levels and recipients. |
| Memory | Last N turns per incident in Postgres, 30-minute idle timeout | No vector DB needed. | Profile goes straight into the prompt. |
| Database | Supabase Postgres (India region if available) | Row-level security, Auth, admin UI. | Neon or Railway Postgres. |
| Frontend | React + Vite on Vercel, Supabase Auth | Spec choice. | Only if time remains. |
| Hosting | Paid Render/Railway/Fly (about $5-7), or laptop with Cloudflare Tunnel/ngrok for the demo | Free tiers sleep. | Move to proper hosting after the hackathon. |
| Monitoring | Structured JSON logs, Sentry free tier, UptimeRobot on `/health` | Cheap and enough. | Alert on failed notification sends. |
| Security | Env-var secrets, RLS, encrypted-at-rest DB, audio deleted after transcription by default, redacted logs | Meets section 12. | Transcript retention is a policy decision. |

### 4.1 LLM output handling (text in, Pydantic out)

The LLM returns plain text. Pydantic turns it into one validated object that feeds two separate messages: one to the senior, one to the immediate family member.

```python
from pydantic import BaseModel, Field

class UserReply(BaseModel):
    text: str = Field(max_length=300)      # short, plain Malayalam or English
    follow_up: str | None = None           # at most one question

class FamilyAlert(BaseModel):
    summary: str = Field(max_length=400)   # transcript facts only
    suggested_level: int = Field(ge=0, le=3)  # a suggestion; code decides
    needs_action: bool

class Turn(BaseModel):
    user: UserReply
    family: FamilyAlert

def parse_turn(llm_text: str) -> Turn | None:
    try:  # shortcut: strips only ```json fences, upgrade if the model wraps JSON in prose
        return Turn.model_validate_json(llm_text.strip().removeprefix("```json").removesuffix("```"))
    except ValueError:
        return None  # caller sends the deterministic fallback below
```

Rules:
- The prompt asks for JSON matching `Turn`. The model's raw reply is treated as untrusted text.
- If `parse_turn` returns None, retry once. If it fails again, send a fixed template to the user ("Please tell me again, or call 112 if urgent") and a fixed "Sahayi could not understand a message" notice to the family member. Never drop the message.
- `suggested_level` only feeds the deterministic rule layer, which can raise the level but never lower it. The LLM cannot decide to call anyone.
- Family text is generated per recipient preference (language) and never includes profile fields beyond the minimum.
- Add one test: valid JSON, fenced JSON, malformed JSON, and a level of 9 (rejected).

Latency budget: download, convert, STT, LLM, TTS and send total about 5-8 seconds. Mark the message as read immediately and send a short acknowledgement.

## 5. Feasibility

- Easy: webhook, media download, STT, structured LLM reply, DB, alerts to caregivers who joined via the bot.
- Moderate: TTS conversion to a WhatsApp voice note, timers and escalation chain, template approval.
- Hard or external: anything touching real emergency services. Keep it as a manual fallback, as the spec says.
- Cost: negligible for a demo; STT, TTS, LLM usage and Meta template pricing are the only meaningful costs.
- External risks: Meta test-number limits and template approval time, Sarvam audio length and rate limits, Malayalam TTS availability. Verify early.

## 6. Final recommendations

### Biggest weaknesses to fix now
1. The circular language router.
2. No silence or timeout handling.
3. No caregiver ack, plus the 24-hour window and template issue.
4. Free-tier hosting for the webhook.

### Architecture changes (the rest of the spec stands)
- One Sarvam STT call.
- One LLM call plus a monotonic rule layer.
- Add the timer table, ack buttons and TTS.
- Add a data model: profiles, contacts, consents, incidents, messages, alerts, scheduled_actions, audit_log.

### Prioritised roadmap (4 hours)
1. Webhook with signature check, idempotency and media download (30 min).
2. Sarvam STT plus ffmpeg (30 min).
3. LLM structured reply plus rule layer and level ratchet (45 min).
4. Caregiver "join" onboarding, templates and alerts with ack buttons (45 min).
5. Member SOS, location and 112 manual fallback (30 min).
6. TTS voice reply (30 min).
7. Timers and escalation (20 min).
8. Seed data and a minimal dashboard only if time remains; rehearse the demo.

### Not verified
- Live vendor limits (Sarvam, Meta, Groq).
- Malayalam STT quality on distressed speech. Test with real recordings before trusting the safety layer; if transcripts fail there, the timeout and unintelligible-audio rules carry the safety case.
