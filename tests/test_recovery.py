import pytest
from pipecat.frames.frames import EndFrame, ErrorFrame, LLMRunFrame, TTSSpeakFrame

from app import recovery as rec
from app.locales import load_locales
from app.recovery import Action, LLMRecovery, install

LOCALE = load_locales()["pt-BR"]


class FakeWorker:
    def __init__(self):
        self.handlers = {}
        self.queued = []

    def event_handler(self, name):
        def register(fn):
            self.handlers[name] = fn
            return fn

        return register

    async def queue_frames(self, frames):
        self.queued.append(list(frames))


class FakeService:
    is_usable = True


@pytest.fixture(autouse=True)
def no_delay(monkeypatch):
    monkeypatch.setattr(rec, "RETRY_DELAY_SECS", 0)


def test_retry_then_apologize_then_hang_up():
    r = LLMRecovery()
    assert [r.on_error(True) for _ in range(3)] == [Action.RETRY, Action.APOLOGIZE, Action.HANG_UP]


def test_success_resets_the_count():
    r = LLMRecovery()
    r.on_error(True)
    r.on_success()
    assert r.on_error(True) == Action.RETRY


def test_unusable_llm_hangs_up_at_once():
    assert LLMRecovery().on_error(False) == Action.HANG_UP


def setup():
    worker, llm = FakeWorker(), FakeService()
    install(worker, llm, LLMRecovery(), LOCALE)
    return worker, llm, worker.handlers["on_pipeline_error"]


def error_from(processor):
    frame = ErrorFrame(error="boom")
    frame.processor = processor
    return frame


async def test_llm_errors_retry_then_ask_to_repeat():
    worker, llm, handler = setup()
    await handler(worker, error_from(llm))
    await handler(worker, error_from(llm))
    first, second = worker.queued
    assert isinstance(first[0], LLMRunFrame)
    assert isinstance(second[0], TTSSpeakFrame) and second[0].text == LOCALE.error_retry


async def test_unusable_llm_says_goodbye_and_ends_the_call():
    worker, llm, handler = setup()
    llm.is_usable = False
    await handler(worker, error_from(llm))
    speak, end = worker.queued[0]
    assert speak.text == LOCALE.error_hangup
    assert isinstance(end, EndFrame)


async def test_errors_from_other_services_are_ignored():
    worker, _, handler = setup()
    await handler(worker, error_from(FakeService()))
    assert worker.queued == []
