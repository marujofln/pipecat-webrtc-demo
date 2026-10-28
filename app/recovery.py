"""Keeps the call from going silent when the LLM fails: retry, then apologize, then hang up."""

import asyncio
from enum import Enum

from loguru import logger
from pipecat.frames.frames import (
    EndFrame,
    ErrorFrame,
    Frame,
    FunctionCallsStartedFrame,
    LLMRunFrame,
    LLMTextFrame,
    TTSSpeakFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.locales import Locale

RETRY_DELAY_SECS = 0.5


class Action(Enum):
    RETRY = "retry"
    APOLOGIZE = "apologize"
    HANG_UP = "hang_up"


class LLMRecovery:
    """Counts consecutive LLM failures and picks what to do about the latest one."""

    def __init__(self):
        self.failures = 0

    def on_error(self, usable: bool) -> Action:
        # Decided by usability, not ErrorCategory.is_permanent: Pipecat files every HTTP 400 as
        # permanent, yet Groq's 400 for an invalid tool call is random and passes on a retry.
        self.failures += 1
        if not usable or self.failures >= 3:
            return Action.HANG_UP
        return Action.RETRY if self.failures == 1 else Action.APOLOGIZE

    def on_success(self) -> None:
        self.failures = 0


class LLMSuccessWatcher(FrameProcessor):
    """Sits right after the LLM and resets the failure count once it actually answers."""

    def __init__(self, recovery: LLMRecovery):
        super().__init__()
        self._recovery = recovery

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, (LLMTextFrame, FunctionCallsStartedFrame)):
            self._recovery.on_success()
        await self.push_frame(frame, direction)


def install(worker, llm, recovery: LLMRecovery, locale: Locale) -> None:
    """Handles LLM errors on the worker; errors from other services are left as they are."""

    @worker.event_handler("on_pipeline_error")
    async def on_pipeline_error(worker, frame: ErrorFrame):
        if frame.processor is not llm:
            return
        action = recovery.on_error(llm.is_usable)
        logger.warning(f"LLM failed ({recovery.failures} in a row): {action.value}")
        match action:
            case Action.RETRY:
                await asyncio.sleep(RETRY_DELAY_SECS)
                await worker.queue_frames([LLMRunFrame()])
            case Action.APOLOGIZE:
                await worker.queue_frames([TTSSpeakFrame(locale.error_retry)])
            case Action.HANG_UP:
                await worker.queue_frames([TTSSpeakFrame(locale.error_hangup), EndFrame()])
