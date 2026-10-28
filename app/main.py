"""Server: web test client (/api/offer) + WhatsApp calls webhook.

Run: uv run uvicorn app.main:app --port 7860
"""

import asyncio
import hmac
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from loguru import logger
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.request_handler import (
    IceCandidate,
    SmallWebRTCPatchRequest,
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)

from app import whatsapp
from app.auth import Policies
from app.config import settings
from app.locales import resolve_locale
from app.logutil import mask
from app.pipeline import LOCALES, run_bot

STATIC = Path(__file__).resolve().parent.parent / "static"
WEB_CALLER = "web-demo"

webrtc_handler = SmallWebRTCRequestHandler()
whatsapp_calls: dict[str, SmallWebRTCConnection] = {}
bot_tasks: set[asyncio.Task] = set()


def spawn_bot(connection: SmallWebRTCConnection, caller: str, language: str | None = None) -> None:
    # Policies are reloaded per call so policies.yaml edits apply without a restart.
    policies = Policies.load()
    locale = resolve_locale(caller, policies, LOCALES, settings.default_language, language)
    task = asyncio.create_task(run_bot(connection, caller, locale, policies))
    bot_tasks.add(task)
    task.add_done_callback(bot_tasks.discard)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.default_language not in LOCALES:
        raise RuntimeError(
            f"DEFAULT_LANGUAGE={settings.default_language!r} not found in agent/locales/ "
            f"(available: {', '.join(LOCALES)})"
        )
    yield
    await webrtc_handler.close()
    for conn in whatsapp_calls.values():
        await conn.disconnect()


# No public OpenAPI/Swagger pages on a server that handles live calls.
app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


# --- Web test client ------------------------------------------------------------------


LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def require_web_access(request: Request) -> None:
    """The web client picks its own caller, so it is for trusted testers only.

    With WEB_API_TOKEN set, a matching bearer token is required; otherwise only loopback clients
    are accepted (behind a reverse proxy every client looks like loopback: set the token there).
    """
    token = settings.web_api_token
    if token:
        supplied = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not hmac.compare_digest(supplied.encode(), token.encode()):
            raise HTTPException(401, "invalid or missing token")
    elif (request.client.host if request.client else "") not in LOOPBACK:
        raise HTTPException(403, "set WEB_API_TOKEN to use the web client remotely")


def require_capacity() -> None:
    if len(bot_tasks) >= settings.max_sessions:
        raise HTTPException(503, "too many active calls")


@app.post("/api/offer")
async def offer(request: Request):
    require_web_access(request)
    require_capacity()
    data = await request.json()
    request_data = data.get("request_data") or data.get("requestData") or {}
    caller = str(request_data.get("caller") or WEB_CALLER)
    language = request_data.get("language") or None
    if language and language not in LOCALES:
        raise HTTPException(400, f"unknown language {language!r}; available: {', '.join(LOCALES)}")

    async def on_connection(connection: SmallWebRTCConnection):
        spawn_bot(connection, caller, language)

    return await webrtc_handler.handle_web_request(SmallWebRTCRequest.from_dict(data), on_connection)


@app.patch("/api/offer")
async def ice_candidate(request: Request):
    require_web_access(request)
    data = await request.json()
    if not isinstance(data.get("pc_id"), str):
        raise HTTPException(400, "pc_id is required")
    await webrtc_handler.handle_patch_request(
        SmallWebRTCPatchRequest(
            pc_id=data["pc_id"],
            candidates=[IceCandidate(**c) for c in data.get("candidates", [])],
        )
    )
    return {"status": "ok"}


# --- WhatsApp Business Calling API ----------------------------------------------------


@app.get("/whatsapp/webhook")
async def whatsapp_verify(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
):
    expected = settings.whatsapp_verify_token
    if expected and mode == "subscribe" and hmac.compare_digest(token.encode(), expected.encode()):
        return Response(challenge, media_type="text/plain")
    raise HTTPException(403, "invalid verify token")


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    body = await request.body()
    if not whatsapp.verify_signature(body, request.headers.get("X-Hub-Signature-256"), settings.whatsapp_app_secret):
        raise HTTPException(401, "invalid signature")

    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(400, "invalid JSON") from None
    if not isinstance(payload, dict):
        raise HTTPException(400, "invalid payload")

    for event in whatsapp.parse_call_events(payload):
        logger.info(f"WhatsApp call {event.call_id}: {event.event} from {mask(event.caller)}")
        if event.event == "connect" and event.sdp:
            if len(whatsapp_calls) >= settings.max_sessions or event.call_id in whatsapp_calls:
                logger.warning(f"Ignoring call {event.call_id}: at capacity or duplicate")
                continue
            task = asyncio.create_task(answer_whatsapp_call(event))
            bot_tasks.add(task)
            task.add_done_callback(bot_tasks.discard)
        elif event.event == "terminate" and (conn := whatsapp_calls.pop(event.call_id, None)):
            await conn.disconnect()
    # Meta requires a fast 200; the call is handled in the background.
    return {"status": "ok"}


async def answer_whatsapp_call(event: whatsapp.CallEvent) -> None:
    connection = SmallWebRTCConnection()

    # The bot ended on our side (e.g. the pipeline finished) → tell WhatsApp.
    # If the user hung up, the "terminate" webhook already removed the entry.
    @connection.event_handler("closed")
    async def on_closed(conn):
        if whatsapp_calls.pop(event.call_id, None):
            await terminate_quietly(event.call_id)

    try:
        # aiortc only returns the answer after gathering every ICE candidate,
        # which is required: WhatsApp does not do trickle ICE.
        await connection.initialize(sdp=event.sdp, type="offer")
        answer = connection.get_answer()["sdp"]
        whatsapp_calls[event.call_id] = connection
        await whatsapp.call_action(event.call_id, "pre_accept", answer)
        spawn_bot(connection, event.caller)
        await whatsapp.call_action(event.call_id, "accept", answer)
    except Exception:
        logger.exception(f"Failed to answer call {event.call_id}")
        whatsapp_calls.pop(event.call_id, None)
        await connection.disconnect()
        await terminate_quietly(event.call_id)


async def terminate_quietly(call_id: str) -> None:
    try:
        await whatsapp.call_action(call_id, "terminate")
    except Exception:
        logger.warning(f"Could not terminate call {call_id} on WhatsApp")
