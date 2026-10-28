# Pipecat WebRTC Demo — voice agent for WhatsApp

🇧🇷 [Leia em português](README.pt-BR.md)

A multilingual voice agent (pt-BR and en, extensible) that answers WebRTC calls (WhatsApp Business Calling API or a
browser), follows instructions written in Markdown, looks up a knowledge base (RAG) and calls
external APIs (appointment CRM) **only when the caller is authorized**.

```
WhatsApp ──webhook (SDP offer)──► /whatsapp/webhook ─┐
Browser  ──POST /api/offer──────────────────────────┤
                                                     ▼
              SmallWebRTCTransport → STT → LLM (+tools, RAG) → TTS → audio back
```

## Running

```bash
uv sync
cp .env.example .env        # fill in the keys for the providers you choose
uv run uvicorn mock_apis.server:app --port 8002     # fake CRM API
uv run uvicorn app.main:app --port 7860             # the agent
```

The appointment scheduling API is **mocked** (`mock_apis/server.py`): an in-memory fake CRM with fixed
slots (`GET /crm/slots`, `POST /crm/appointments`) and no auth or persistence. It stands in for a real
scheduling system; point `CRM_BASE_URL` in `.env` at your own API to replace it (adapt `app/tools/crm.py` if its contract differs).

Open http://localhost:7860, pick a caller and click **Ligar** (Call).

Test script (pick **English (en)** in the language selector to run it in English; the phrases below are for pt-BR):
- "Que horas vocês abrem?" (What time do you open?) → answered from the knowledge base (`search_knowledge`).
- As `5511999990001` (patient): "Quero marcar uma consulta" (I want to book an appointment) → lists slots and books in the CRM.
- As `5500000000000` (guest): ask to book an appointment → the agent refuses.

## Customizing the agent

| What | Where |
|---|---|
| Persona, tone and service rules | `agent/locales/<language>/system.md` |
| Knowledge base (RAG) | `agent/locales/<language>/knowledge/*.md`, one chunk per `#`/`##` heading |
| Greeting, LLM error lines, voices and language code | `agent/locales/<language>/locale.yaml` |
| Who may use each tool, language per number/country code | `agent/policies.yaml` |
| New tools / APIs | `app/tools/` + register in `app/tools/__init__.py` |
| Providers | `STT_PROVIDER`, `LLM_PROVIDER`, `TTS_PROVIDER` in `.env` |

Supported providers: STT `deepgram|openai|groq`, LLM `anthropic|openai|google|groq`, TTS `cartesia|elevenlabs|openai|groq` (Groq TTS is English-only).
To add another one, add a `case` in `app/providers.py`.

### Languages

Each language is a folder under `agent/locales/` (currently `pt-BR` and `en`) holding
`system.md`, the knowledge base and a `locale.yaml` (language code, greeting and a voice per TTS
provider). The language of each call is picked in this order:

1. The web client's language selector (`request_data.language`), for local testing only.
2. The caller's explicit language in `policies.yaml`: `"5511999990003": {role: patient, language: en}`.
3. The longest matching country code in `languages.by_prefix` (`"55": pt-BR`, `"1": en`).
4. `DEFAULT_LANGUAGE` in `.env`.

STT gets the full code (`pt-BR`) and TTS gets the base language (`pt`). The `pt` code does not
set the accent; the voice does, which is why the `pt-BR` locale uses Brazilian voices. OpenAI has
no per-accent voices, so the optional `tts_instructions` field asks its TTS for the accent. Tool descriptions are in
English for every language; each language's `system.md` sets the language the agent replies in.

To add a language, copy a folder under `agent/locales/` and name it after the new language (e.g.
`es`), translate `system.md` and `knowledge/`, set `language` (a Pipecat `Language` enum value,
e.g. `es-ES`) and the voices in `locale.yaml`, and map country codes in `policies.yaml`. No code
changes are needed.

### Authorization
The prompt only tells the LLM which tools exist; the real gate is in each tool's handler
(`app/tools/registry.py` → `Policies.can_call`). Even if the LLM calls a tool it is not allowed
to use, the call is denied and logged. Tools outside the caller's allowlist are also left out of
the schema sent to the LLM.

On WhatsApp, the caller is the originating number (`from`) in the webhook. In the web client,
the caller is supplied by the browser itself (`request_data.caller`): **this is for local
testing only**. `/api/offer` therefore only accepts loopback clients by default; to use it remotely, set `WEB_API_TOKEN`
and send it as a bearer token (the test page has a field for it). Behind a reverse proxy every client looks like
loopback, so always set the token there. `MAX_SESSIONS` caps concurrent calls. The WhatsApp webhook is rejected
unless `WHATSAPP_APP_SECRET` and `WHATSAPP_VERIFY_TOKEN` are set.

## WhatsApp Business Calling API

1. A business number on the Cloud API with calling enabled (Phone number settings → Calling).
2. Expose the server: `ngrok http 7860`.
3. In the Meta app, under Webhooks, set `https://<ngrok>/whatsapp/webhook`, use the same
   `WHATSAPP_VERIFY_TOKEN` as in `.env`, and subscribe to the **calls** field.
4. Fill in `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` and `WHATSAPP_APP_SECRET`
   (the latter validates `X-Hub-Signature-256`).
5. Call the number from WhatsApp.

Flow: a `connect` event with an SDP offer → the server builds the SDP answer (aiortc, with ICE
candidates already included, since WhatsApp does not do trickle ICE) → `pre_accept` → `accept` →
the agent speaks. A `terminate` event ends the session; if the agent ends first, the server sends
`terminate` to the Graph API.

Behind restrictive NAT, a TURN server may be required for media.

## Tests

```bash
uv run pytest
```

Lint and format with [ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`):

```bash
uv run ruff check .
uv run ruff format .
```

They cover authorization, language resolution, RAG in both languages, tools against the mock (including denial when the LLM tries a
disallowed tool) and WhatsApp webhook parsing/signature checks.

## Out of scope for v1
Persistence, multi-tenancy, handoff to a human, transcripts and analytics, vector RAG.
