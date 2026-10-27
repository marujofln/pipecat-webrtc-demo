"""Servidor: cliente web de teste (/api/offer) + webhook de chamadas do WhatsApp.

Rodar: uv run uvicorn app.main:app --port 7860
"""

import asyncio
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
from app.config import settings
from app.pipeline import run_bot

STATIC = Path(__file__).resolve().parent.parent / "static"
WEB_CALLER = "web-demo"

webrtc_handler = SmallWebRTCRequestHandler()
whatsapp_calls: dict[str, SmallWebRTCConnection] = {}
bot_tasks: set[asyncio.Task] = set()


def spawn_bot(connection: SmallWebRTCConnection, caller: str) -> None:
    task = asyncio.create_task(run_bot(connection, caller))
    bot_tasks.add(task)
    task.add_done_callback(bot_tasks.discard)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await webrtc_handler.close()
    for conn in whatsapp_calls.values():
        await conn.disconnect()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


# --- Cliente web de teste -------------------------------------------------------------


@app.post("/api/offer")
async def offer(request: Request):
    data = await request.json()
    caller = (data.get("request_data") or data.get("requestData") or {}).get("caller", WEB_CALLER)

    async def on_connection(connection: SmallWebRTCConnection):
        spawn_bot(connection, caller)

    return await webrtc_handler.handle_web_request(SmallWebRTCRequest.from_dict(data), on_connection)


@app.patch("/api/offer")
async def ice_candidate(request: Request):
    data = await request.json()
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
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return Response(challenge, media_type="text/plain")
    raise HTTPException(403, "verify token inválido")


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    body = await request.body()
    if not whatsapp.verify_signature(
        body, request.headers.get("X-Hub-Signature-256"), settings.whatsapp_app_secret
    ):
        raise HTTPException(401, "assinatura inválida")

    for event in whatsapp.parse_call_events(json.loads(body)):
        logger.info(f"WhatsApp call {event.call_id}: {event.event} de {event.caller}")
        if event.event == "connect" and event.sdp:
            asyncio.create_task(answer_whatsapp_call(event))
        elif event.event == "terminate" and (conn := whatsapp_calls.pop(event.call_id, None)):
            await conn.disconnect()
    # A Meta exige 200 rápido; o atendimento segue em background.
    return {"status": "ok"}


async def answer_whatsapp_call(event: whatsapp.CallEvent) -> None:
    connection = SmallWebRTCConnection()

    # Bot encerrou do nosso lado (ex.: pipeline terminou) → avisa o WhatsApp.
    # Se foi o usuário que desligou, o webhook "terminate" já removeu a entrada.
    @connection.event_handler("closed")
    async def on_closed(conn):
        if whatsapp_calls.pop(event.call_id, None):
            await terminate_quietly(event.call_id)

    try:
        # aiortc só devolve o answer depois de coletar todos os ICE candidates,
        # o que é necessário: o WhatsApp não faz trickle ICE.
        await connection.initialize(sdp=event.sdp, type="offer")
        answer = connection.get_answer()["sdp"]
        whatsapp_calls[event.call_id] = connection
        await whatsapp.call_action(event.call_id, "pre_accept", answer)
        spawn_bot(connection, event.caller)
        await whatsapp.call_action(event.call_id, "accept", answer)
    except Exception:
        logger.exception(f"Falha ao atender chamada {event.call_id}")
        whatsapp_calls.pop(event.call_id, None)
        await connection.disconnect()
        await terminate_quietly(event.call_id)


async def terminate_quietly(call_id: str) -> None:
    try:
        await whatsapp.call_action(call_id, "terminate")
    except Exception:
        logger.warning(f"Não foi possível encerrar a chamada {call_id} no WhatsApp")
