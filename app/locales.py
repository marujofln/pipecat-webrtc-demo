"""Per-language agent content (agent/locales/<code>/) and per-call language resolution."""

from dataclasses import dataclass
from pathlib import Path

import yaml
from pipecat.transcriptions.language import Language

from app.auth import Policies

LOCALES_DIR = Path(__file__).resolve().parent.parent / "agent" / "locales"


@dataclass(frozen=True)
class Locale:
    code: str
    dir: Path
    language: Language
    greeting: str
    tools_heading: str
    no_tools: str
    error_retry: str
    error_hangup: str
    voices: dict[str, str]
    tts_instructions: str | None = None

    @property
    def base_language(self) -> Language:
        """Language without region ("pt-BR" → "pt"), for services that only take the base code."""
        return Language(self.language.value.split("-")[0])

    @property
    def system_path(self) -> Path:
        return self.dir / "system.md"

    @property
    def knowledge_dir(self) -> Path:
        return self.dir / "knowledge"


def load_locales(directory: Path = LOCALES_DIR) -> dict[str, Locale]:
    locales = {}
    for path in sorted(p for p in directory.iterdir() if (p / "locale.yaml").exists()):
        data = yaml.safe_load((path / "locale.yaml").read_text())
        locales[path.name] = Locale(
            code=path.name,
            dir=path,
            language=Language(data["language"]),
            greeting=data["greeting"],
            tools_heading=data["tools_heading"],
            no_tools=data["no_tools"],
            error_retry=data["error_retry"],
            error_hangup=data["error_hangup"],
            voices=data.get("voices", {}),
            tts_instructions=data.get("tts_instructions"),
        )
    return locales


def resolve_locale(
    caller: str,
    policies: Policies,
    locales: dict[str, Locale],
    default: str,
    requested: str | None = None,
) -> Locale:
    """Precedence: requested (web client) > caller/country code in policies > default."""
    code = requested or policies.language_of(caller) or default
    if code not in locales:
        raise ValueError(f"Unknown language {code!r}; available: {', '.join(locales)}")
    return locales[code]
