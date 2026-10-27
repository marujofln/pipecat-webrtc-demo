import httpx
import pytest

from app.auth import Policies
from app.locales import load_locales
from app.rag import KnowledgeBase
from app.tools import build_registry, crm, parking
from mock_apis.server import app as mock_app

KNOWLEDGE_DIR = load_locales()["pt-BR"].knowledge_dir

POLICIES = Policies(
    {
        "roles": {"guest": {"tools": ["search_knowledge"]}, "staff": {"tools": ["open_gate", "schedule_appointment", "list_available_slots"]}},
        "default_role": "guest",
        "callers": {"staff-1": "staff"},
    }
)


class FakeLLM:
    def __init__(self):
        self.handlers = {}

    def register_function(self, name, handler):
        self.handlers[name] = handler


class FakeParams:
    def __init__(self, arguments):
        self.arguments = arguments
        self.result = None

    async def result_callback(self, result):
        self.result = result


@pytest.fixture(autouse=True)
def mock_http(monkeypatch):
    """Routes the tools' httpx calls straight to the in-memory mock_apis."""
    real = httpx.AsyncClient

    def client(**kw):
        return real(transport=httpx.ASGITransport(app=mock_app), base_url="http://mock", **kw)

    monkeypatch.setattr(crm.httpx, "AsyncClient", client)
    monkeypatch.setattr(parking.httpx, "AsyncClient", client)
    monkeypatch.setattr(crm.settings, "crm_base_url", "http://mock/crm")
    monkeypatch.setattr(parking.settings, "parking_base_url", "http://mock/parking")


def handlers_for(caller):
    llm = FakeLLM()
    build_registry(KnowledgeBase(KNOWLEDGE_DIR)).register(llm, POLICIES, caller)
    return llm.handlers


async def test_authorized_caller_opens_gate():
    params = FakeParams({"plate": "ABC1D23"})
    await handlers_for("staff-1")["open_gate"](params)
    assert params.result == {"status": "opened", "plate": "ABC1D23"}


async def test_unauthorized_caller_is_denied_even_if_llm_calls_tool():
    params = FakeParams({"plate": "ABC1D23"})
    await handlers_for("desconhecido")["open_gate"](params)
    assert params.result["error"] == "not_authorized"


async def test_schedule_flow_against_mock_crm():
    h = handlers_for("staff-1")
    slots = FakeParams({})
    await h["list_available_slots"](slots)
    slot = slots.result["slots"][0]
    booked = FakeParams({"patient_name": "Maria", "slot": slot})
    await h["schedule_appointment"](booked)
    assert booked.result["status"] == "confirmed"


def test_schema_only_exposes_allowed_tools():
    names = [t.name for t in build_registry(KnowledgeBase(KNOWLEDGE_DIR)).tools_for(POLICIES, "desconhecido")]
    assert names == ["search_knowledge"]
