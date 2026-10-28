import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.config import settings
from app.main import require_web_access


def req(host="127.0.0.1", auth=None):
    headers = [(b"authorization", auth.encode())] if auth else []
    return Request({"type": "http", "headers": headers, "client": (host, 1234)})


def test_loopback_allowed_without_token(monkeypatch):
    monkeypatch.setattr(settings, "web_api_token", "")
    require_web_access(req("127.0.0.1"))


def test_remote_denied_without_token(monkeypatch):
    monkeypatch.setattr(settings, "web_api_token", "")
    with pytest.raises(HTTPException) as e:
        require_web_access(req("203.0.113.9"))
    assert e.value.status_code == 403


def test_token_required_when_set(monkeypatch):
    monkeypatch.setattr(settings, "web_api_token", "s3cret")
    require_web_access(req("203.0.113.9", "Bearer s3cret"))
    for bad in (None, "Bearer nope"):
        with pytest.raises(HTTPException) as e:
            require_web_access(req("127.0.0.1", bad))
        assert e.value.status_code == 401
