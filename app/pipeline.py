"""Builds and runs the voice pipeline for a WebRTC connection (browser or WhatsApp)."""

from functools import cache

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
from app.locales import Locale, load_locales
from app.prompt import build_system_prompt
from app.providers import make_llm, make_stt, make_tts
from app.rag import KnowledgeBase
from app.recovery import LLMRecovery, LLMSuccessWatcher, install
from app.tools import ToolRegistry, build_registry

LOCALES = load_locales()


@cache
def registry_for(locale_code: str) -> ToolRegistry:
    """One knowledge base (and so one registry) per language, built on first use."""
    return build_registry(KnowledgeBase(LOCALES[locale_code].knowledge_dir))


async def run_bot(connection: SmallWebRTCConnection, caller: str, locale: Locale, policies: Policies) -> None:
    logger.info(f"New session: caller={caller} role={policies.role_of(caller)} language={locale.code}")

    transport = SmallWebRTCTransport(
        webrtc_connection=connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )
    stt, llm, tts = make_stt(settings, locale), make_llm(settings), make_tts(settings, locale)

    registry = registry_for(locale.code)
    tools = registry.tools_for(policies, caller)
    registry.register(llm, policies, caller)
    context = LLMContext(
        messages=[{"role": "system", "content": build_system_prompt(locale, [t.name for t in tools])}],
        tools=registry.schema_for(policies, caller),
    )
    aggregators = LLMContextAggregatorPair(
        context, user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer())
    )

    recovery = LLMRecovery()
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            aggregators.user(),
            llm,
            LLMSuccessWatcher(recovery),
            tts,
            transport.output(),
            aggregators.assistant(),
        ]
    )
    worker = PipelineWorker(pipeline, params=PipelineParams(enable_metrics=True))
    install(worker, llm, recovery, locale)

    @transport.event_handler("on_client_connected")
    async def on_connected(transport, client):
        context.add_message({"role": "user", "content": locale.greeting})
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(transport, client):
        logger.info(f"Session ended: caller={caller}")
        await worker.cancel()

    await WorkerRunner(handle_sigint=False).run(worker)
