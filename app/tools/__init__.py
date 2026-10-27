from app.rag import KnowledgeBase
from app.tools.crm import LIST_SLOTS, SCHEDULE
from app.tools.parking import OPEN_GATE
from app.tools.registry import Tool, ToolRegistry


def build_registry(kb: KnowledgeBase) -> ToolRegistry:
    async def search_knowledge(args: dict) -> dict:
        chunks = kb.search(args["query"])
        return {"results": [{"title": c.heading, "text": c.text} for c in chunks]}

    search = Tool(
        name="search_knowledge",
        description="Busca na base de conhecimento (horários, preços, regras, endereço, procedimentos).",
        properties={"query": {"type": "string", "description": "Pergunta ou palavras-chave"}},
        required=["query"],
        handler=search_knowledge,
    )
    return ToolRegistry([search, LIST_SLOTS, SCHEDULE, OPEN_GATE])
