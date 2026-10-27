from app.locales import Locale


def build_system_prompt(locale: Locale, tool_names: list[str]) -> str:
    tools = ", ".join(sorted(tool_names)) or locale.no_tools
    return f"{locale.system_path.read_text()}\n\n## {locale.tools_heading}\n{tools}\n"
