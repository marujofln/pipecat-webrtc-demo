from pathlib import Path

SYSTEM_PATH = Path(__file__).resolve().parent.parent / "agent" / "system.md"


def build_system_prompt(tool_names: list[str], path: Path = SYSTEM_PATH) -> str:
    tools = ", ".join(sorted(tool_names)) or "nenhuma"
    return f"{path.read_text()}\n\n## Ferramentas disponíveis nesta ligação\n{tools}\n"
