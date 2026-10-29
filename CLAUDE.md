# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                              # install deps
uv run uvicorn mock_apis.server:app --port 8002      # fake CRM (in-memory, no auth)
uv run uvicorn app.main:app --port 7860              # the agent (web client at http://localhost:7860)
docker compose up --build                            # both; code is baked into the image, so rebuild after changes

uv run pytest                                        # all tests (asyncio_mode=auto)
uv run pytest tests/test_tools.py::test_name         # single test
uv run ruff check . && uv run ruff format .          # lint + format (line length 120, bandit rules on)
```

Config comes from `.env` (see `.env.example`); `app/config.py` is the settings model.

## Architecture

A Pipecat voice agent. Each call is a `SmallWebRTCConnection` that `app/pipeline.py:run_bot` turns into a pipeline: `transport.input → STT → user aggregator → LLM → LLMSuccessWatcher → TTS → transport.output → assistant aggregator`. Calls enter through two paths in `app/main.py`, both ending in `spawn_bot`:

- **Browser**: `POST /api/offer`. The caller number comes from the client itself, so it is test-only, restricted to loopback unless `WEB_API_TOKEN` is set.
- **WhatsApp**: `/whatsapp/webhook` (HMAC-signed). A `connect` event carries an SDP offer; the server answers via aiortc (all ICE candidates gathered up front, since WhatsApp has no trickle ICE), calls `pre_accept` → `accept` through `app/whatsapp.py`, and the caller is the `from` number. The webhook must return 200 fast, so the call is handled in a background task.

Key design points that span files:

- **Authorization is enforced in code, not in the prompt.** `agent/policies.yaml` maps caller number → role → allowed tools. `Policies` (`app/auth.py`) is reloaded on every call (edits apply without restart). `ToolRegistry` (`app/tools/registry.py`) both filters the tool schema sent to the LLM *and* re-checks `can_call` inside every handler, so a tool the LLM shouldn't have is denied even if called. New tools: add in `app/tools/`, register in `build_registry` (`app/tools/__init__.py`), and grant them to roles in `policies.yaml`. Tool descriptions stay in English for every language.
- **Languages are folders** under `agent/locales/<code>/` (`system.md`, `knowledge/*.md`, `locale.yaml`); adding one needs no code changes. Resolution order (`app/locales.py`): web selector > per-caller language in policies > longest country-code prefix > `DEFAULT_LANGUAGE`. STT gets the full code (`pt-BR`), TTS the base (`pt`); accent comes from the voice in `locale.yaml`.
- **RAG** (`app/rag.py`) is BM25 over knowledge files, one chunk per `#`/`##` heading, exposed to the LLM as the `search_knowledge` tool. One `KnowledgeBase`/registry per language, cached in `pipeline.registry_for`.
- **Providers** (`app/providers.py`): STT/LLM/TTS chosen by env vars through `match` statements; add a provider by adding a `case`.
- **LLM failure recovery** (`app/recovery.py`): on an LLM `ErrorFrame`, retry once, then apologize, then hang up (3 consecutive failures or an unusable service). Decided by usability, deliberately not by `ErrorCategory.is_permanent`, because Groq's random 400s on invalid tool calls pass on retry.
- Concurrency is capped by `MAX_SESSIONS`; logs mask caller numbers (`app/logutil.mask`) and tool args are logged by key only, since values may be personal data.
- `mock_apis/server.py` stands in for a real scheduling API; `app/tools/crm.py` talks to it via `CRM_BASE_URL`.

README.md (English) and README.pt-BR.md are kept as parallel translations; update both when changing docs.
