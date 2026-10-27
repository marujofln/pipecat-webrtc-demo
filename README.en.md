# Pipecat WebRTC Demo — voice agent for WhatsApp

🇧🇷 [Leia em português](README.md)

A Portuguese-speaking voice agent that answers WebRTC calls (WhatsApp Business Calling API or a
browser), follows instructions written in Markdown, looks up a knowledge base (RAG) and calls
external APIs (CRM, parking system) **only when the caller is authorized**.

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
uv run uvicorn mock_apis.server:app --port 8002     # fake CRM + parking APIs
uv run uvicorn app.main:app --port 7860             # the agent
```

Open http://localhost:7860, pick a caller and click **Ligar** (Call).

Test script (the agent speaks Brazilian Portuguese):
- "Que horas vocês abrem?" (What time do you open?) → answered from the knowledge base (`search_knowledge`).
- As `5511999990001` (patient): "Quero marcar uma consulta" (I want to book an appointment) → lists slots and books in the CRM.
- As `5511999990002` (resident): "Abre a cancela, placa ABC1D23" (Open the gate, plate ABC1D23) → opens the gate.
- As `5500000000000` (guest): ask to open the gate → the agent refuses.

## Customizing the agent

| What | Where |
|---|---|
| Persona, tone and service rules | `agent/system.md` |
| Knowledge base (RAG) | `agent/knowledge/*.md`, one chunk per `#`/`##` heading |
| Who may use each tool | `agent/policies.yaml` (role → tools; phone number → role) |
| New tools / APIs | `app/tools/` + register in `app/tools/__init__.py` |
| Providers | `STT_PROVIDER`, `LLM_PROVIDER`, `TTS_PROVIDER` in `.env` |

Supported providers: STT `deepgram|openai`, LLM `anthropic|openai|google`, TTS `cartesia|elevenlabs|openai`.
To add another one, add a `case` in `app/providers.py`.

To run the agent in another language, translate `agent/system.md` and `agent/knowledge/`, and
change the `language` settings in `app/providers.py`.

### Authorization
The prompt only tells the LLM which tools exist; the real gate is in each tool's handler
(`app/tools/registry.py` → `Policies.can_call`). Even if the LLM calls a tool it is not allowed
to use, the call is denied and logged. Tools outside the caller's allowlist are also left out of
the schema sent to the LLM.

On WhatsApp, the caller is the originating number (`from`) in the webhook. In the web client,
the caller is supplied by the browser itself (`request_data.caller`): **this is for local
testing only**. Do not expose `/api/offer` publicly without authentication.

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

They cover authorization, RAG, tools against the mock (including denial when the LLM tries a
disallowed tool) and WhatsApp webhook parsing/signature checks.

## Out of scope for v1
Persistence, multi-tenancy, handoff to a human, transcripts and analytics, vector RAG.
