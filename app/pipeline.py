"""Builds and runs the voice pipeline for a WebRTC connection (browser or WhatsApp)."""

from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.workers.runner import WorkerRunner

from app.auth import Policies
from app.config import settings
from app.prompt import build_system_prompt
from app.providers import make_llm, make_stt, make_tts
from app.rag import KnowledgeBase
from app.tools import build_registry

KB = KnowledgeBase()
REGISTRY = build_registry(KB)


async def run_bot(connection: SmallWebRTCConnection, caller: str) -> None:
    policies = Policies.load()
    logger.info(f"New session: caller={caller} role={policies.role_of(caller)}")

    transport = SmallWebRTCTransport(
        webrtc_connection=connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )
    stt, llm, tts = make_stt(settings), make_llm(settings), make_tts(settings)

    tools = REGISTRY.tools_for(policies, caller)
    REGISTRY.register(llm, policies, caller)
    context = LLMContext(
        messages=[{"role": "system", "content": build_system_prompt([t.name for t in tools])}],
        tools=REGISTRY.schema_for(policies, caller),
    )
    aggregators = LLMContextAggregatorPair(
        context, user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer())
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            aggregators.user(),
            llm,
            tts,
            transport.output(),
            aggregators.assistant(),
        ]
    )
    worker = PipelineWorker(pipeline, params=PipelineParams(enable_metrics=True))

    @transport.event_handler("on_client_connected")
    async def on_connected(transport, client):
        context.add_message(
            {"role": "user", "content": "(A ligação começou. Cumprimente e pergunte como pode ajudar.)"}
        )
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(transport, client):
        logger.info(f"Session ended: caller={caller}")
        await worker.cancel()

    await WorkerRunner(handle_sigint=False).run(worker)
