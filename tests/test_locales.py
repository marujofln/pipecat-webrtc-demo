import pytest
from pipecat.transcriptions.language import Language

from app.auth import Policies
from app.locales import load_locales, resolve_locale

LOCALES = load_locales()
POLICIES = Policies(
    {
        "roles": {"guest": {"tools": []}},
        "languages": {"by_prefix": {"1": "en", "55": "pt-BR", "5511": "en"}},
        "callers": {"5521000000000": {"role": "guest", "language": "en"}},
    }
)


def resolve(caller, requested=None, default="pt-BR"):
    return resolve_locale(caller, POLICIES, LOCALES, default, requested).code


def test_shipped_locales_are_complete():
    assert {"pt-BR", "en"} <= set(LOCALES)
    for locale in LOCALES.values():
        assert locale.system_path.exists()
        assert list(locale.knowledge_dir.glob("*.md"))
        assert {"cartesia", "elevenlabs", "openai"} <= set(locale.voices)


def test_base_language_drops_region():
    assert LOCALES["pt-BR"].language == Language.PT_BR
    assert LOCALES["pt-BR"].base_language == Language.PT
    assert LOCALES["en"].base_language == Language.EN


def test_requested_language_wins():
    assert resolve("15550000000", requested="pt-BR") == "pt-BR"


def test_explicit_caller_language_beats_prefix():
    assert resolve("+5521000000000") == "en"


def test_longest_prefix_wins():
    assert resolve("5521999999999") == "pt-BR"
    assert resolve("5511999999999") == "en"
    assert resolve("15550000000") == "en"


def test_falls_back_to_default():
    assert resolve("4420000000") == "pt-BR"
    assert resolve("web-demo", default="en") == "en"


def test_unknown_language_raises():
    with pytest.raises(ValueError, match="Unknown language"):
        resolve("4420000000", default="fr")
